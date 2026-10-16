# EVPN

- EVPN (BGP address-family, RFC 7432) is the control plane for [vxlan.md](vxlan.md)'s
  data plane, replacing flood-and-learn with MAC/IP advertisement via BGP. This
  eliminates unknown-unicast flooding for known hosts and gives ARP suppression at
  the ingress VTEP. It rides on ordinary BGP sessions — see [bgp.md](bgp.md) for
  eBGP/iBGP and route-reflector mechanics; a common pattern is an eBGP-only
  underlay ([spine-leaf-clos.md](spine-leaf-clos.md)) carrying a separate iBGP+
  route-reflector overlay just for the EVPN address family, since the overlay
  doesn't need the same one-AS-per-node scheme the underlay does.
- Route types that matter in design conversations [1], [6]:
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

RFC 9135 §5.3's **MUST** applies to a specific **symmetric-IRB, inter-subnet**
case where participating PEs do not all have every subnet locally attached.
It does not require a bridge-only EVPN service to probe arbitrary unknown
hosts [6].

For subnet A on PE1 and subnet B on PE2/PE3:

1. A sends a routed packet to B, which is in a different subnet.
2. PE1 has no local subnet-B IRB attachment. A subnet-B **RT-5 prefix route**
   carries the packet to PE2 or PE3.
3. The receiving subnet-B PE performs the glean lookup and sends ARP over
   subnet B's **L2 overlay**. The selected PE can discover B even if B is
   attached to the other PE.
4. B's reply lets its attaching PE learn and advertise the MAC/IP binding;
   later traffic can use that reachability [6].

RT-5 supplies the destination-subnet path; it does not carry the ARP probe or
create a universal RT-5 requirement for same-subnet bridging. RFC 9135 §7.3
separately covers probing a **previously learned** host after a silent move;
that is not initial discovery of an arbitrary unknown host [6].

For same-subnet ARP suppression, unknown-MAC forwarding, and the ACI COOP
workflow, see [arp.md](arp.md#arp-in-fabric-overlay-contexts). Those behaviors
are covered there rather than repeated here.

## Cross-vendor / variants

- **Juniper Junos** (23.4R1+): **Static MAC-IP binding with ARP/ND probing** [2].
  You manually configure `static-mac-ip` entries per silent host on the attaching
  PE. The PE probes the host with exponential backoff using an all-zero sender IP
  (`0.0.0.0`). If the host replies, the binding is learned as static and
  propagated via EVPN Type 2. Configured per logical attachment in a BD/VLAN;
  probing can be disabled
  globally with `set protocols l2-learning arp-nd-probe-disable`. This is not
  fabric-wide automatic discovery — it's a configured probe list, and probes
  originate only from the PE where the entry is defined. Targeted at
  configured infrastructure hosts, not a subnet scan.
- **Arista EOS**: Its public TOI index describes ARP broadcast/NS multicast generated by
  **post-routing glean traffic** and an EOS 4.32.2F head-end replication
  optimization. Detailed TOI content requires login, so platform/configuration
  limits were not independently revalidated [10].
- **NX-OS VXLAN EVPN (Cisco)**: Check the applicable IRB/SVI discovery and
  ARP-learning configuration. Cisco's 10.6(x) IPv4 guide documents ordinary
  glean resolution, enhanced local proxy ARP (`ip local-proxy-arp reachable`)
  that gleans unknown destinations, and optional periodic ARP refresh following
  MAC deletion (`ip arp refresh-adj-on-mac-delete retry`, introduced in
  10.2(4)M and disabled by default). These are distinct features, not an
  unconditional statement that every VXLAN mode probes every unknown host [7].
- **Huawei CloudEngine**: Tunnel-failure broadcast detection is a separate
  convergence feature [4]. See
  [arp.md](arp.md#arp-active-detection-huawei-smart-discover) for the distinct
  legacy VLAN active-discovery feature.

## Design considerations

- For the RFC 9135 §5.3 workflow, confirm symmetric IRB, subnet-B RT-5
  reachability, and an L2 overlay path on a PE that can perform the destination
  subnet's glean lookup [6].
- Platform-specific gleaning, suppression, and refresh features have their own
  mode and release prerequisites; verify those before treating optional device
  behavior as a general EVPN guarantee [7], [10].

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
Segment). This route-type list does not establish the absence of gateway probing;
see the later EVPN IRB specification [6].

[2] "Static Configuration of MAC-IP Bindings," Juniper Networks, Junos OS
EVPN documentation. [Online]. Available:
https://www.juniper.net/documentation/us/en/software/junos/evpn/topics/concept/static-mac-ip.html
— verify response-gated learning/RT-2 advertisement, all-zero sender IP,
logical attachment scope, and arp-nd-probe-disable; confirm platform/release
support in Feature Explorer. Rechecked Oct. 16, 2026. Historical introduction:
"EVPN," Junos OS Release Notes 23.4R1,
https://www.juniper.net/documentation/us/en/software/junos/release-notes/23.4/junos-release-notes-23.4r1/topics/new-features/feature-descriptions/evpn-6.html
— introduction applies to the listed platforms, not all Junos products.

[4] "ARP Broadcast Suppression on a VXLAN," Huawei CloudEngine 9800/8800/6800/5800
V200R024C00 Configuration Guide (also covers V300R025C10 per Update Date 2024-11-13).
[Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100420161/
c7801b0d/arp-broadcast-suppression-on-a-vxlan — standard ARP suppression, arp
broadcast-detect for tunnel-down convergence probing. Last confirmed Aug 2026.

[6] A. Sajassi, S. Salam, S. Thoria, J. Drake, and J. Rabadan, "Integrated
Routing and Bridging in Ethernet VPN (EVPN)," IETF RFC 9135, October 2021,
§5.3 and §7.3. [Online]. Available: https://www.rfc-editor.org/rfc/rfc9135.html
— §5.3 specifies local subnet RT-5 advertisement and traffic-triggered gleaning
for symmetric IRB with non-uniform subnet provisioning; the receiving PE's
glean lookup triggers ARP flooded over the L2 overlay. §7.3 describes age-out
ARP probing for a silent host that moved. Verified via doc-fetcher Oct. 16,
2026. These procedures are standard-defined; support/configuration must still
be verified for each platform and topology.

[7] "IPv4 Addresses," Cisco Nexus 9000 Series NX-OS Unicast Routing
Configuration Guide, Release 10.6(x), updated Apr. 27, 2026. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/unicast-routing-configuration/cisco-nexus-9000-series-nx-os-unicast-routing-configuration-guide/m-n9k-configuring-ipv4-93x.html
— verify "Glean throttles," "Configuring local proxy ARP on SVIs," "Periodic
ARP refresh on MAC delete," and its configuration/limitations sections.
Refresh requires a subsequent MAC-delete trigger and existing adjacency
context; it is not an initial scan of every IP. Rechecked Oct. 16, 2026.

[10] K. Mandal, "VXLAN Optimized Headend Replication of Glean ARPs," Arista
TOI public ARP index, EOS 4.32.2F, posted Oct. 15, 2024, updated Dec. 12,
2025. [Online]. Available: https://www.arista.com/en/support/toi/tag/arp
— verify the named public entry, which describes post-routing glean-generated
ARP/NS replication. Detail URL:
https://www.arista.com/en/support/toi/eos-4-32-2f/20417-vxlan-optimized-headend-replication-of-glean-arps
requires login; detailed configuration/platform limitations unverified.
Public entry rechecked Oct. 16, 2026.
