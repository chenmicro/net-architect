# EVPN

- EVPN (BGP address-family, RFC 7432) is the control plane for [vxlan.md](vxlan.md)'s
  data plane, replacing flood-and-learn with MAC/IP advertisement via BGP. This
  eliminates unknown-unicast flooding for known hosts and gives ARP suppression at
  the ingress VTEP. It rides on ordinary BGP sessions — see [bgp.md](bgp.md) for
  eBGP/iBGP and route-reflector mechanics; a common pattern is an eBGP-only
  underlay ([spine-leaf-clos.md](spine-leaf-clos.md)) carrying a separate iBGP+
  route-reflector overlay just for the EVPN address family, since the overlay
  doesn't need the same one-AS-per-node scheme the underlay does.
- Route types that matter in design conversations:
  - **Type 1** (Ethernet Auto-Discovery, "A-D") — advertised per-ES and per-EVI.
    The per-ES route is what a leaf withdraws on link/NVE failure, triggering mass
    withdrawal (fast convergence) at every remote VTEP with one route pull instead
    of a per-MAC update; the per-EVI route is what drives Aliasing/Backup Path, so
    remote VTEPs load-balance across every leaf on a multi-homed ES instead of
    pinning to whichever one first learned a given MAC.
  - **Type 2** (MAC/IP advertisement) — host reachability, the bread and butter route.
  - **Type 3** (Inclusive Multicast) — builds the BUM (broadcast/unknown-unicast/
    multicast) replication tree per VNI; ingress replication is the common choice
    over PIM in the underlay to avoid multicast state.
  - **Type 4** (Ethernet Segment route) — auto-discovers which leaves share an ESI
    and drives Designated Forwarder (DF) election, so exactly one leaf forwards BUM
    traffic for a given segment/VLAN when a device is multi-homed active-active.
  - **Type 5** (IP Prefix) — inter-subnet/inter-VRF route advertisement, used for
    route summarization and connecting to L3 ([multi-tenancy.md](multi-tenancy.md),
    DCI) without stretching L2.
- **Anycast gateway**: the same gateway IP/MAC is configured on every leaf, so a host's
  default gateway is always local regardless of which leaf it's attached to — this is
  what makes VM/workload mobility across the fabric transparent to the host.
- **Multi-homing**: EVPN Multihoming (EVPN-MH, ESI-based, RFC 8365) is the modern,
  vendor-interoperable way to dual-home a server or downstream switch to two leaves
  with active-active forwarding, replacing proprietary MLAG/vPC pairs at the
  server-facing edge. Note EVPN-MH and vPC/MLAG are not directly interoperable —
  pick one per fabric generation, don't mix at the same tier.
  - Split-horizon (loop prevention for BUM traffic on an all-active ES) can't reuse
    MPLS-EVPN's ESI-label trick here — VXLAN has no label stack to carry it. RFC 8365
    §8.3.1 instead uses **Local Bias**: every VTEP tracks which peer VTEPs share an
    ESI with it and filters BUM traffic sourced from those peers' tunnel IPs, so a
    frame never loops back out the same segment it entered.

## Silent host handling — EVPN vs. ACI COOP-gleaning

EVPN (RFC 7432) defines four route types — A-D, MAC/IP, Inclusive Multicast, and
Ethernet Segment — and **none of them describe a fabric-initiated endpoint probe
mechanism** [1]. EVPN advertises endpoints *after* they are learned via data-plane
traffic; it does not autonomously discover silent hosts.

When a leaf receives traffic for a destination MAC/IP that has no corresponding
BGP EVPN Type 2 route, the behavior is purely passive:

- **ARP requests**: The ARP is treated as BUM traffic and flooded via ingress
  replication (or P2MP LSP) to every VTEP in the VNI. The silent host receives it,
  replies, and EVPN learns the Type 2 route.
- **Non-ARP unknown unicast** (e.g. TCP SYN to a stale MAC): Flooded as unknown
  unicast BUM to every VTEP — no fabric-side ARP generation, no gleaning.
- **No probe generation**: RFC 7432 §7 (BGP EVPN Routes) defines no route type or
  procedure for a VTEP or route reflector to originate a discovery probe toward an
  unknown host. The entire control plane is reactive to data-plane learning [1].

This means silent hosts are reachable *only when something else ARPs for them*.
If all senders have stale ARP caches or use static ARP entries, and the MAC table
on the ingress leaf has aged out, traffic is consumed by unknown-unicast flooding —
hitting the multicast/BUM queue on every leaf-to-spine uplink, replicated to every
VTEP in the VNI.

COOP + gleaning (see [cisco/aci.md](../../vendor-matrix/cisco/aci.md#silent-host-detection-arp-gleaning--gipo-tree))
is a Cisco ACI proprietary mechanism layered on top of the standards-based VXLAN
data plane. It has no equivalent in RFC 7432/8365.

### How this differs from ACI

| | ACI (COOP + gleaning) | Standard EVPN-VXLAN |
|---|---|---|
| Endpoint database | COOP (IS-IS, spine-based, fabric-wide) | BGP EVPN Type 2 (standards, per-VTEP advertisement) |
| Unknown destination decision | COOP miss at spine | No BGP Type 2 route |
| Probe generation | Spine sends glean pkt to 239.255.255.240 → leaf generates ARP | **None** — fabric floods whatever it received |
| Discovery model | Active (fabric probes) | Passive (relies on external ARP) |

### Workaround

The standard fix is to ensure ARP entries on sending hosts age out **before** MAC
entries on VTEPs, so the next packet always triggers a fresh ARP that gets
flooded and reaches the silent host. In practice, many operators run a periodic
ARP scan (nmap, arping) from a host in each subnet to keep EVPN Type 2 routes
populated.

See [cisco/aci.md](../../vendor-matrix/cisco/aci.md#silent-host-detection-arp-gleaning--gipo-tree)
for the ACI-specific mechanism that fills this gap.

## Cross-vendor / variants

- **ACI (Cisco)**: Proprietary COOP + gleaning — the only fabric that proactively
  probes for silent hosts without pre-configuration. See [cisco/aci.md](../../vendor-matrix/cisco/aci.md#silent-host-detection-arp-gleaning--gipo-tree).
- **Juniper Junos** (23.4R1+): **Static MAC-IP binding with ARP/ND probing** [2].
  You manually configure `static-mac-ip` entries per silent host on the attaching
  PE. The PE probes the host with exponential backoff using an all-zero sender IP
  (`0.0.0.0`). If the host replies, the binding is learned as static and
  propagated via EVPN Type 2. Configurable per-VNI/BD; probing can be disabled
  globally with `set protocols l2-learning arp-nd-probe-disable`. This is not
  fabric-wide automatic discovery — it's a configured probe list, and probes
  originate only from the PE where the entry is defined. Targeted at
  infrastructure hosts (BMS, management interfaces), not general-purpose silent
  endpoint discovery [2].
- **Arista EOS**: ARP gleaning in centralized-routing designs [3]. When a spine
  acts as a centralized L3 gateway and receives a packet for an unknown IP on a
  VXLAN-attached subnet, it performs standard ARP resolution locally. This is
  router-level ARP behavior, not a fabric-wide COOP equivalent — it only helps
  if traffic hits the spine that owns the SVI. No automatic probing of silent
  hosts attached to leaf switches.
- **NX-OS VXLAN EVPN (Cisco)**: Standards-based, no COOP, no gleaning. ARP
  suppression caches known bindings and proxies ARP replies but does not
  discover silent hosts.
- **Huawei CloudEngine**: Standards-based EVPN. ARP broadcast suppression (VTEP
  proxies ARP from EVPN-learned host info) [4]. `arp broadcast-detect enable`
  on VBDIF interfaces triggers ARP probes when VXLAN tunnels go down — a
  convergence mechanism for detecting host moves on tunnel failure, not silent
  host discovery [4]. Static ARP/MAC entries are configurable per BD for manual
  silent-host provisioning. No automatic fabric-wide gleaning or COOP equivalent
  found in V200R024C00 documentation [4], [5].

## Design considerations

- For deployments with silent hosts (BMS, sensors, printers, syslog collectors),
  ACI's gleaning is a meaningful operational advantage — no periodic ARP scanning
  needed, no unknown-unicast flooding risk.
- In standard EVPN-VXLAN, tune MAC aging > ARP aging to minimize the silent-host
  flooding window. On NX-OS, ARP timeout defaults to 1500s (25 min); on EOS/IOS,
  4 hours — both are far longer than typical MAC aging (300s), which guarantees
  periodic flooding.
- The nmap scanning workaround works but adds operational complexity and
  generates synthetic traffic at scale — size the scanning interval against your
  MAC aging timer.

## Relationship to other techniques

- [vxlan.md](vxlan.md): EVPN provides the control plane; VXLAN is the data plane
  that carries the flooded BUM/ARP traffic for silent host discovery.
- [bgp.md](bgp.md): EVPN Type 2 routes are the BGP mechanism that advertises
  learned endpoints; silent hosts generate no Type 2 until discovered.
- [spine-leaf-clos.md](spine-leaf-clos.md): Ingress replication (BUM flooding) and
  ECMP hashing both operate over the spine-leaf underlay.

## References

[1] A. Sajassi et al., "BGP MPLS-Based Ethernet VPN," IETF RFC 7432, February 2015.
[Online]. Available: https://www.rfc-editor.org/rfc/rfc7432.txt — the normative EVPN
specification. §7 defines four route types (A-D, MAC/IP, Inclusive Multicast, Ethernet
Segment); none define a fabric-side probe/gleaning procedure. EVPN advertises endpoints
already learned via data-plane; discovery is delegated to BUM flooding of the sender's
traffic.

[2] "Static configuration of MAC-IP bindings with EVPN-VXLAN," Juniper Networks,
Junos OS Release Notes 23.4R1. [Online]. Available: https://www.juniper.net/
documentation/us/en/software/junos/release-notes/23.4/junos-release-notes-23.4r1/
topics/new-features/feature-descriptions/evpn-6.html — static-mac-ip with ARP/ND
probing (exponential backoff, all-zero sender IP), arp-nd-probe-disable,
drop-unknown-macip. Last confirmed Aug 2026.

[3] "EVPN VXLAN Single-Gateway Centralized Routing," Arista EOS User Manual, 4.36.1F.
[Online]. Available: https://www.arista.com/en/um-eos/eos-evpn-vxlan-single-gateway-
centralized-routing — centralized routing architecture: VARP MAC, EVPN type-2 route
generation with `redistribute router-mac next-hop vtep primary`, ARP behavior for
virtual IPs. The ARP resolution for unknown hosts on VXLAN-attached subnets follows
standard IP router behavior (ARP gleaning at the gateway SVI) rather than a
fabric-wide discovery mechanism. Last confirmed Aug 2026.

[4] "ARP Broadcast Suppression on a VXLAN," Huawei CloudEngine 9800/8800/6800/5800
V200R024C00 Configuration Guide (also covers V300R025C10 per Update Date 2024-11-13).
[Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100420161/
c7801b0d/arp-broadcast-suppression-on-a-vxlan — standard ARP suppression, arp
broadcast-detect for tunnel-down convergence probing. Last confirmed Aug 2026.

[5] "EVPN Basic Principles," Huawei CloudEngine 9800/8800/6800/5800 V200R024C00
Configuration Guide (also covers V300R025C10 per Update Date 2024-11-13).
[Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100420161/
a7119a61/evpn-basic-principles — MAC/IP route advertisement, host information
synchronization via BGP EVPN. No COOP/gleaning mechanism described.
Last confirmed Aug 2026.
