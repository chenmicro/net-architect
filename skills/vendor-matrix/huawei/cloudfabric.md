# Huawei CloudFabric

Huawei's data center network solution: iMaster NCE-Fabric plans, provisions, and
monitors, and [CloudEngine switches](cloudengine.md) execute. Read in that order:
this file for what the solution does and requires, `cloudengine.md` for what the
devices can do, then the [technique files](../../techniques/) for protocol behavior.
See the [Huawei hub](huawei.md) for other product lines.

## Solution model

- As with ACI vs. NX-OS-native EVPN-VXLAN (see
  [vendor-matrix/cisco/cisco.md](../cisco/cisco.md)), whether a Huawei DC design is
  NCE-controller-managed or manually-configured EVPN-VXLAN is a real
  architectural fork affecting operational model and automation capability —
  confirm which is intended rather than assuming a specific one. The manual path
  uses only [cloudengine.md](cloudengine.md).

## Device capabilities used

| CloudFabric feature | Device-side reference |
|---|---|
| Fabric underlay and overlay | [Role and capabilities](cloudengine.md#role-and-capabilities) |
| Software release scope | [Version line](cloudengine.md#version-line-v300) |

## Digital Map (iMaster NCE-Fabric)

An iMaster NCE-Fabric O&M feature that builds topology views and path navigation from
collected network data [1]. Digital Map runs in the MDC scenario: only the MDC solution
documentation covers it, and the fabric-scenario solution documentation carries no Digital Map
topics at all [2]. Data sources, device coverage, and limits are in
[digital-map.md](digital-map.md).

## DCI and cross-vendor interconnect

Huawei CloudFabric's recommended DCI model for interconnecting independent
fabrics is **Segment VXLAN** (as opposed to E2E VXLAN, which assumes a single
iMaster NCE-Fabric domain across all sites) [3]:

- Each CloudFabric is an **independent VXLAN/EVPN domain** with its own
iMaster NCE-Fabric instance
- iMaster NCE provisions the DCI VNI stitching on the
[CloudEngine DCI gateways](#dci-gateway-role)

### DCI gateway role

- **CloudEngine DCI gateways** (CE8800 / CE16800 / CE6860 series, any CE
  switch with EVPN VXLAN capability at the fabric border) establish MP-BGP
  EVPN peering across an Inter-Site Network to the remote fabric's border
  gateways [3]
- DCI VXLAN tunnels exist only between the gateways — the internal fabric
  VXLAN stays within each DC [3]
- The gateway function is configured on CloudEngine leaf/spine nodes at
  the fabric edge [3]
- **Naming:** the solution documentation calls these nodes **DCI leaf nodes**,
  "also called DCI gateways and fabric gateways" [2]. The term **IPN is not used
  anywhere** in the CloudFabric solution documentation — it is Cisco ACI terminology
  (checked against both the non-MDC and MDC libraries: TOCs plus the DCI, multi-fabric
  and inter-DC interconnection topics, Nov. 7, 2026). Each DCI leaf belongs to exactly
  one fabric: on the forwarding path the MDC documentation writes
  `Service Leaf1 of Fabric1 > Fabric GW1 of Fabric1 > Fabric GW2 of Fabric2 >
  Service Leaf2 of Fabric2` [1].
- **What they do:** BGP EVPN on the DCI leaves creates the Segment VXLAN
  tunnel; VXLAN received from one DC is decapsulated, re-encapsulated and
  tunnelled to the peer DC, so the two fabrics keep independent inner VXLAN
  domains [2].
- **Routing:** EBGP between the two fabrics' DCI leaves, IBGP inside each
  fabric [2].
- **Placement:** when both Layer 2 and Layer 3 DCI are in use the DCI leaves run
  active-active and must not connect servers, firewalls or load balancers [2].
  They need large routing and MAC tables, and their service model differs from
  server, service and border leaves, so deploying them separately is
  recommended [2].
- **Management:** each iMaster NCE-Fabric orchestrates only its own fabric's DCI
  leaves; settings that must match across fabrics are kept consistent by hand [2].

To interconnect Segment VXLAN on CloudFabric with **Cisco ACI**, the ACI
fabric must present an **ACI Border Gateway** (BGW). See
[cisco/aci.md](../cisco/aci.md#aci-border-gateway-heterogeneous-fabric-interconnect)
for the full architecture — ACI BGW addressing (MS-Ext-VIP/MS-Int-VIP/PIP),
control plane flow, data plane tunnel stitching, namespace normalization
(ACI 6.1(4)+), and multi-fabric policy enforcement. The CloudFabric side
connects by presenting standard EVPN VXLAN border gateways (above) that
peer with the ACI BGWs via MP-BGP EVPN over an L3 Inter-Site Network. All
ACI-side constraints (VNI namespace, multicast, Multi-Site support) apply
from the Cisco side.

For connecting CloudFabric to other non-Huawei EVPN VXLAN fabrics that
speak MP-BGP EVPN at the border (e.g. Arista, Juniper, NX-OS EVPN-VXLAN),
the same Segment VXLAN model applies with the foreign fabric presenting an
EVPN Multi-Site border gateway.

## iMaster NCE-Fabric releases

C00 releases are LTS, and C10 releases are normal releases.
A C00 release can be reached from the two previous C00 releases and the C10
releases between them. A C10 release can be reached only from the C00 of the
same release. The upgrade guides fit this rule:

| Target | One-click upgrade from |
|---|---|
| V100R026C00SPC100 | V100R024C00, V100R024C10, V100R025C00, V100R025C10 |
| V100R025C10SPC180 | V100R025C00 |
| V100R025C10SPC100 | V100R025C00 |

## References

[1] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612446 (verify at
support.huawei.com HedEx, `docid=EDOC1100612446`). Verify in: Digital Map > Digital Map Usage
Guide > Overview. Confirmed Nov. 4, 2026.

[2] "Stellar AI Fabric Data Center Network Solution Product Documentation," Huawei,
V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612448 (verify at
support.huawei.com HedEx, `docid=EDOC1100612448`). Read for the solution documentation set: it
has no Digital Map section, so Digital Map is an MDC-scenario feature [1]; and for the DCI-leaf
role — "DCI Scenario Overview" and "Configuring Underlay Network Connectivity Between DCI Leaf
Nodes" (DCI Scenario (Multi-Site and Non-MDC Scenario), DCI leaf naming, BGP EVPN stitching,
EBGP/IBGP split, active-active placement, separate deployment), and "Multi-fabric Network
Management". Confirmed Nov. 4, 2026; DCI topics rechecked Nov. 7, 2026.

[3] "What DCI Solutions Are Available? — E2E VXLAN and Segment VXLAN," Huawei Support Encyclopedia. [Online]. Available: https://info.support.huawei.com/info-finder/encyclopedia/en/DCI.html
