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
collected network data [1][2].

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

## References

[1] "iMaster NCE-Fabric Product Documentation," Huawei, V100R025C00, Issue 04,
Jun. 30, 2026 (HedEx library EDOC1100509727, login required). Verify in: Digital Map Usage
Guide (Overview, Licensing Requirements, Fundamentals, Path Navigation, Topology
Restoration, FAQ); Restrictions and Precautions > Digital Map Constraints and
Precautions; Getting Started > Functions. Confirmed Oct. 31, 2026.

[2] "iMaster NCE-Fabric MDC Product Documentation," Huawei, V100R025C00, Issue 04,
Jun. 30, 2026 (HedEx library EDOC1100509717, login required). Verify in: Digital Map > Simulation
View > Multi-Cloud Simulation (Restrictions and Limitations, Licensing
Requirements); Digital Map > Security View; Digital Map > Job View; Digital Map >
Digital Map Usage Guide > General Configurations (Path Navigation, Topology
Restoration). Confirmed Oct. 31, 2026.

[3] "What DCI Solutions Are Available? — E2E VXLAN and Segment VXLAN," Huawei Support Encyclopedia. [Online]. Available: https://info.support.huawei.com/info-finder/encyclopedia/en/DCI.html
