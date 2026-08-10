# ARP (Address Resolution Protocol)

ARP resolves a known IPv4 address to an unknown MAC address on a local subnet.
Defined in RFC 826 (1982), it is one of the simplest and most fundamental
protocols in IP networking — and one of the most consequential for fabric design,
because how a fabric handles ARP directly determines endpoint learning behavior,
BUM traffic volume, and silent-host reachability [1].

## Protocol basics

ARP operates on a single broadcast domain (VLAN / BD). The process [1]:

1. **Sender broadcasts an ARP Request**: destination MAC `ff:ff:ff:ff:ff:ff`,
   containing the sender's own MAC+IP and the target IP to resolve.
2. **Target unicasts an ARP Reply**: sent directly to the requester's MAC,
   containing the target's MAC.
3. **Bidirectional learning**: all hosts that receive the ARP Request learn the
   sender's MAC↔IP mapping from the request itself — not just the target. RFC 826
   specifies this explicitly: the `<protocol, sender IP, sender MAC>` triplet is
   merged into every receiver's ARP table before evaluating whether it is the
   target.

## ARP in fabric / overlay contexts

ARP behaves differently in traditional switched networks vs. VXLAN/EVPN fabrics,
and this difference is a primary driver of fabric design choices.

### Flooded ARP (traditional / EVPN without suppression)

In a standard EVPN-VXLAN fabric without ARP suppression, an ARP Request is treated
as BUM (broadcast) traffic. The ingress VTEP encapsulates it and replicates it to
every VTEP in the VNI via ingress replication (or multicast underlay). Every leaf
delivers the ARP to all its local ports in that BD.

This works — the target receives the ARP and replies — but every ARP Request
consumes bandwidth on every leaf-to-spine uplink and hits the multicast/BUM queue
on every VTEP. At scale (thousands of hosts, 30–60s Linux ARP timeouts), ARP
flooding alone can saturate the fabric's BUM capacity [2], [3].

### ARP suppression (EVPN proxy ARP)

ARP suppression is the EVPN control-plane optimization: the ingress VTEP
intercepts the ARP Request and checks its local ARP cache, which is populated
from BGP EVPN Type 2 (MAC/IP Advertisement) routes. If the target MAC↔IP binding
is known, the VTEP responds directly with an ARP Reply — the request never enters
the fabric.

This eliminates BUM flooding for all ARP Requests directed at *known* hosts.
It is not a discovery mechanism — it only helps for hosts that have already been
learned and advertised via EVPN [2], [3].

### ARP gleaning (ACI COOP)

ACI extends the suppression concept with proactive discovery. When the spine's
COOP database has no entry for a destination IP, the spine triggers a glean
packet over the VRF-GIPo multicast tree. The leaf that owns the BD SVI generates
an ARP Request on the fabric's behalf, flooding it to all local BD ports. The
silent host replies and is learned.

This is one of two fabric-side ARP generation mechanisms — standard EVPN has no
equivalent. See [cisco/aci.md](../../vendor-matrix/cisco/aci.md#silent-host-detection-arp-gleaning--gipo-tree)

### ARP active detection (Huawei smart-discover)

Huawei CloudEngine V300 provides `arp smart-discover enable` in **VLANIF
interface view** — proactive periodic ARP probing for silent hosts [5].
After enabling, the device sends ARP probe messages to each host on the
gateway's network segment at the configured interval (default 1s, max 128
probes per interval). Existing ARP entries, device IPs, and VRRP VIPs are
excluded from probing [5].

Key characteristics:
- **Proactive, not reactive** — polls all hosts on the segment periodically,
  not triggered by a traffic miss. Contrast with ACI gleaning which is
  reactive (COOP miss).
- **Leaf-local, no spine involvement** — no fabric-wide endpoint database or
  multicast tree; the VLANIF on each leaf probes its own segment independently.
- **Disabled by default** — must be explicitly enabled.
- **Not for proactive-host environments** — the doc warns that if hosts send
  ARP proactively, enabling this may slow ARP learning [5].
- **Companion command**: `arp smart-discover interval <interval> count <count>`
  to tune the probe rate [5].

The reactive counterpart is the default **ARP Miss** mechanism on VBDIF/VLANIF:
when traffic arrives for an unknown destination, the interface generates an ARP
Request automatically (`undo arp miss disable` — enabled by default) [5].

Note: `arp smart-discover` is documented under VLANIF interface view [5]; for
VXLAN/EVPN fabrics where the L3 gateway is a VBDIF interface, verify whether
the command is also available under VBDIF, or whether the BD must be accessed
via a VLANIF binding.


### ARP / MAC timer mismatch

A design pitfall that arises in any fabric (EVPN or ACI): if ARP cache timers on
hosts or gateways exceed MAC address aging timers on VTEPs, a host can send
unicast traffic to a stale MAC address. The ingress VTEP has aged out the MAC
entry but still has the EVPN Type 2 route — it knows *which* leaf the host is on
but not the exact interface. The resulting unknown unicast flood hits every VTEP
in the VNI [3].

| Platform | Default ARP timeout | Default MAC aging |
|---|---|---|
| Linux (host) | 30s (randomized 15–45s) | N/A |
| Cisco NX-OS | 1500s (25 min) | 300s |
| Cisco IOS / Arista EOS | 14400s (4 hours) | 300s |
| Juniper Junos | 14400s (4 hours) | 300s |

The guiding rule: **MAC aging must exceed ARP aging** so a fresh ARP always
occurs before the MAC entry is evicted [3].

## Cross-vendor / variants

| Vendor | ARP suppression | Fabric-side ARP generation | Notes |
|---|---|---|---|
| **Cisco ACI** | Yes (COOP-based proxy) | Yes (gleaning) | Proprietary. ARP Flooding BD option controls whether ARP Requests from hosts are flooded or unicast-routed. See [cisco/aci.md](../../vendor-matrix/cisco/aci.md#silent-host-detection-arp-gleaning--gipo-tree). |
| **Cisco NX-OS EVPN** | Yes (`suppress-arp` under VNI) | No | Standards-based. Disabled by default. |
| **Arista EOS** | Yes (enabled by default on SVIs) | No (router-level ARP only) | Standards-based. VARP MAC for anycast gateway consistency. See [evpn.md](../evpn.md) [3]. |
| **Juniper Junos** | Yes (enabled by default on VLANs) | Partial (23.4R1+ `static-mac-ip` probing) | `arp-nd-probe-disable` to suppress probing. See [evpn.md](../evpn.md) [2]. |
| **Huawei CloudEngine** | Yes (ARP broadcast suppression) | Yes (`arp smart-discover enable`, proactive) | ARP Miss reactive by default, smart-discover for periodic probing. See §ARP active detection. V300R024C00 [5]. |

**NDP (IPv6 Neighbor Discovery Protocol)** is the IPv6 equivalent of ARP (RFC
4861). The same suppression, proxy, and gleaning concepts apply — ACI and EVPN
implementations generally support both ARP and ND suppression/pass-through with
the same architecture. IPv6 uses multicast solicited-node addresses
(`ff02::1:ffXX:XXXX`) instead of broadcast, so the BUM impact is more targeted
but still non-zero without suppression.

## Design considerations

- **ARP suppression is near-mandatory at scale.** Without it, every ARP Request
  from every host is a fabric-wide BUM event. At 1000+ hosts with Linux-default
  ARP timers, this generates hundreds of BUM packets per second.
- **Silent hosts break the model.** ARP suppression helps known hosts; ARP
  gleaning (ACI) or static MAC-IP entries (Juniper) are needed for hosts that
  never announce themselves.
- **Tune ARP timers below MAC aging.** On most switch platforms, the default ARP
  timeout (1500s–14400s) vastly exceeds MAC aging (300s), guaranteeing periodic
  unknown-unicast flooding for silent or low-traffic hosts. Lower the ARP timeout
  or raise MAC aging.
- **ARP suppression and anycast gateway (SVI) interaction.** In EVPN fabrics,
  every leaf has the same anycast gateway IP/MAC. ARP suppression ensures that an
  ARP for the gateway is answered locally by the ingress leaf, never flooded —
  but the gateway's own MAC must be advertised via EVPN Type 2 for this to work
  (`redistribute router-mac` on Arista, implicit on NX-OS).
- **Static ARP entries as last resort.** For hosts that are genuinely ARP-deaf
  (embedded systems with hard-coded neighbor tables), a static ARP/MAC entry on
  the attaching leaf is the only option — on any fabric, including ACI.

## Relationship to other techniques

- [evpn.md](evpn.md): EVPN Type 2 routes carry MAC↔IP bindings that drive ARP
  suppression; ARP flooding vs. suppression is a primary EVPN design decision.
- [vxlan.md](vxlan.md): VXLAN carries ARP packets as BUM traffic when suppression
  is disabled or the target is unknown.
- [ai-gpu-fabric.md](ai-gpu-fabric.md): ARP is irrelevant to RoCEv2 data-path
  (RDMA uses QP numbers, not ARP), but the IP fabric that RoCE rides on still
  uses ARP for control-plane reachability.
- [fhrp.md](fhrp.md): VRRP/HSRP use virtual MACs that ARP must resolve; anycast
  gateway in EVPN fabrics eliminates the need for FHRP ARP entirely.

## References

[1] D. C. Plummer, "An Ethernet Address Resolution Protocol," IETF RFC 826,
November 1982. [Online]. Available: https://www.rfc-editor.org/rfc/rfc826.txt —
the normative ARP specification. Defines the Request/Reply exchange, bidirectional
learning from ARP Request, and table-merge semantics.

[2] "ACI Fabric Endpoint Learning White Paper," Cisco, Release 5.2(1g).
[Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-
virtualization/application-centric-infrastructure/white-paper-c11-739989.html —
ARP gleaning, ARP flooding vs. unicast forwarding, L2 Unknown Unicast options,
silent host considerations. Last confirmed Aug 2026.

[3] "Silent Hosts in EVPN Fabrics," ipSpace.net blog, Ivan Pepelnjak, May 2023.
[Online]. Available: https://blog.ipspace.net/2023/05/silent-hosts-evpn/ —
ARP/MAC timer mismatch analysis, default timeout values across platforms,
nmap scanning workaround. Last confirmed Aug 2026.

[4] "Troubleshoot ACI Intra-Fabric Forwarding — MultiPod Forwarding," Cisco
Support, Doc ID 218013. [Online]. Available: https://www.cisco.com/c/en/us/
support/docs/cloud-systems-management/application-policy-infrastructure-controller-
apic/218013-troubleshoot-aci-intra-fabric-forwarding.html — COOP database lookup,
glean packet to 239.255.255.240, pervasive static route for ARP glean trigger.
Last confirmed Aug 2026.

[5] \"ARP Configuration Commands — CloudEngine 9800, 8800, and 6800
V300R024C00 Command Reference,\" Huawei, EDOC1100439391. [Online]. Available:
https://support.huawei.com/enterprise/en/doc/EDOC1100439391/1c40b472/arp-configuration-commands
— `arp smart-discover enable` in VLANIF interface view, ARP active detection
for proactive silent-host learning. Last confirmed Aug 2026.