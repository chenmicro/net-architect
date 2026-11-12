# Huawei CloudFabric

Huawei's data center network solution: iMaster NCE-Fabric plans, provisions, and
monitors, and [CloudEngine switches](cloudengine.md) execute. Read in that order:
this file for what the solution does and requires, `cloudengine.md` for what the
devices can do, then the [technique files](../../techniques/) for protocol behavior.
See the [Huawei hub](huawei.md) for other product lines.

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

## Logical networks (VPC)

### Logical routers and logical switches

- **Logical-router static routes (Route List tab):** a logical router takes static
  routes of four next-hop types: Normal, Interconnection interface, End port, and
  Non-direct connection (an indirect route, distributed fabric only, delivered to the
  egress gateway group) [2]. A Normal route destined for a third-party firewall is
  delivered to a service leaf, and its next hop must be within the interconnection
  interface's subnet, or the route can't be delivered [2]. A route can be associated
  with an NQA policy and given a priority from 1 to 255; the destination, next-hop type,
  and next hop can't be modified afterward [2].
- **Logical-router BGP peers (BGP Peer tab):** in the vpnv4-instance or vpnv6-instance
  address family, the controller can import direct routes, static routes, or networks
  into BGP, with a routing policy on the direct and static imports. Routing policies
  can't be selected in the cloud-network integration scenario [2]. Each peer is of type
  IP or BGP Group, is Direct connection or Non-direct connection (Non-direct is
  distributed-fabric only and sources from a loopback), and for a direct peer uses an
  Interconnection Interface or a Logical Switch as the local interface. A peer takes an
  export and an import policy [2].
- **RT prefix:** the logical switch and the logical router each take an optional RT
  Prefix, 0 (the default) or 11-65535, which can't be changed after creation. The rest
  of the RT is generated, so the full value is known only after creation [2].
- **Host info collect (logical switch):** in the distributed scenario, when VXLAN
  gateways advertise IRB routes, this option makes the gateway advertise host routes
  [2].
- **Permit AS loops (BGP peer):** required when a third-party firewall attached in
  bypass mode exchanges BGP routes with the DC gateways. With it on, no import policy
  can be set on that peer [2].
- **General routing policy:** created under Service Provisioning > Policy > Routing >
  Routing Policy and referenced by BGP peers. In network virtualization, iMaster
  NCE-Fabric doesn't create one for a logical router's BGP peer. Nodes match on IP
  prefix, community, extended community, AS path, L2VNI, L3VNI, label, and route type.
  Actions add a community, set the local and protocol priority, the cost, or the AS
  path, or keep the next hop. Node indexes 10, 3000, 3100, and 9999 are reserved in the
  MDC scenario [2]. The same page says the current version no longer creates DCI import
  or DCI dyeing routing policies, only keeping ones from earlier versions [2].
- **Interconnection interface:** connects a logical router directly to a PE, either as a
  Layer 3 routed sub-interface or through a VLANIF or VBDIF. The VLAN comes from the
  global VLAN pool. It has per-device interface IPs and an option to advertise ARP Vlink
  direct routes, which a dynamic routing protocol must then import [2].

### Logical VAS and third-party firewalls

A firewall joins a tenant's service chain as a logical VAS in the VPC's logical network [2]:

- **Device types:** Firewall, Unmanaged Firewall, F5 LB, Check Point Firewall, Palo Alto
  Firewall, Fortinet Firewall, and Unmanaged WAF. The managed Firewall type lists only
  Huawei USG, XH, and Eudemon models [2].
- **Links:** internal links connect the tenant router to the VAS and carry east-west
  traffic. External links connect the VAS to the external network. An administrator
  creates both. A manually added internal link can take its VLAN and the IP addresses at
  both ends either automatically from the interconnection resource pool or by hand [2].
- **Route Deploy Disable (Unmanaged Firewall only):** the controller then doesn't deliver
  the forward and return routes between the firewall and the gateway, so they're
  configured by hand. It can be set only when the VAS is created. A VAS with it enabled
  can't carry the VPC-interconnection and DCI services that pass through the firewall
  [2].

## Resource pools and example ranges

iMaster NCE-Fabric allocates VLANs, VNIs, BDs, and interconnection IPs from resource pools
under Network Planning and Construction > Resource Pool [2]. The guide says the global
resource pools come with default value ranges, but its tables are labelled "Data
(Example)", so read the actual defaults in the GUI of the release in use [2].

| Pool | Example in the guide | Rules recorded with it |
|---|---|---|
| Interconnection VLAN (gateway ↔ firewall, bypass) | 1001-2000; 3000-3499 in the combined service/border leaf planning example | VLAN 2-4094, up to 128 ranges. One VLAN per logical router ↔ VAS link; logical routers can't share interconnection VLANs [2] |
| Interconnection IP (gateway ↔ firewall) | `10.12.0.1-10.12.0.100/30` | Class A/B/C, not `0.0.0.0/8` or `127.0.0.0/8`. Split by /30 for unidirectional links and /29 for bidirectional links; one pair per VAS link, and logical routers may reuse pairs. Fixed once a service references it [2] |
| Global VLAN (VM and external-network access) | 2000-3999; 101-999, 1000-2000, 2001-2999 in the planning example | Must not overlap interconnection VLANs when the fabric's outbound interface is a VLANIF; may overlap when it's a VBDIF [2] |
| BD and VNI | 5000-15000 | VNI 1-16,000,000, up to 1,024 segments. Default VNIs are allocated automatically (one per logical router, logical switch, VBDIF external network, special SFC); reserved VNIs are for DCI [2] |
| Global transit VNI (MDC) | 1600-1700 | Set on the MDC and pushed to every domain controller with Allocation = MDC; must not conflict with any domain controller's VNIs [1] |
| Device interconnection VLAN (manual underlay) | 2-30 | For VLANIF links built by hand, such as FW management and LB service links [2] |
| M-LAG Layer 3 direct-connection VLAN (V3) | 100 | Reserved for the M-LAG; can't be used for anything else [2] |
| Layer 3 main-interface reserved VLANs | 4000-4062 | Needed on CE6856HI, CE6865, CE6857, CE8850E, CE8861, and CE8868 before switching an interface to Layer 3 [2] |

The planning example numbers underlay point-to-point links as /30s from `192.168.1.0/24`
(leaf ↔ spine) and the M-LAG peer-link VLANIF as `10.10.10.1/30` [2].

## DCI and cross-vendor interconnect

When independently deployed DCs need to interconnect, DCI is implemented with Segment
VXLAN: each DC has its own network resource pool and its own controller cluster, and
BGP EVPN on the DCI leaves creates the VXLAN tunnel between them [2]. The multi-PoD
active/standby DR scenario instead joins the DCs into one end-to-end VXLAN domain under
a unified resource pool and one logical controller cluster [2].

### DCI gateway role

- **Naming:** the solution documentation calls these nodes **DCI leaf nodes**,
  "also called DCI gateways and fabric gateways" [2]. On the forwarding path the MDC
  documentation writes
  `Service Leaf1 of Fabric1 > Fabric GW1 of Fabric1 > Fabric GW2 of Fabric2 >
  Service Leaf2 of Fabric2` [1].
- **What they do:** BGP EVPN on the DCI leaves creates the Segment VXLAN
  tunnel; VXLAN received from one DC is decapsulated, re-encapsulated and
  tunnelled to the peer DC [2].
- **Routing:** EBGP between the two fabrics' DCI leaves, IBGP inside each
  fabric [2].
- **Placement:** when both Layer 2 and Layer 3 DCI are in use the DCI leaves run
  active-active and must not connect servers, firewalls or load balancers [2].
  They need large routing and MAC tables, and their service model differs from
  server, service and border leaves, so deploying them separately is
  recommended [2].
- **Management:** each iMaster NCE-Fabric orchestrates only its own fabric's DCI
  leaves; settings that must match across fabrics are kept consistent by hand [2].

### Inter-DC Layer 2 (MDC L2 transit VPC)

When the same VPC service runs in several DCs and needs one subnet in all of them, the MDC
stretches it at Layer 2 [1]:

- **Model:** create a transit VPC of the Layer 2 type, put a transit switch in it, and
  associate the transit switch with the tenant's logical switch in each DC. In the
  example both logical switches carry the same subnet, `192.168.1.0/24` [1]. Transit VPCs
  live in a transit fabric, and the transit objects are instantiated on the fabric
  gateways [1].
- **Forwarding is Segment VXLAN:** known unicast goes server leaf → local fabric gateway →
  remote fabric gateway → remote server leaf, and each fabric gateway decapsulates and
  re-encapsulates. BUM traffic uses BGP EVPN ingress replication both inside and between
  fabrics [1].
- **Loop prevention:** configure a DCI split horizon group on each fabric gateway naming
  the other (`peer { group-name | ipv4-address } split-group split-group-name`), so a
  gateway never forwards BUM traffic back to a member of the same group [1].
- **Prerequisites:** the tenant VPC is already delivered on each domain controller, the
  MDC manages those domain controllers, global transit VNIs are configured, and a transit
  fabric exists [1].
- **Global transit VNIs:** the transit VPC's VNI range is set on the MDC under Multi-cloud
  Orchestration > Multi-cloud Access > Resource Management > Global Resource, as a range
  with a priority (High, Medium, or Low); the guide's example is 1600-1700. The MDC
  pushes the range to every managed domain controller, where it shows in Resource Pool >
  Global Resource > VNI with Allocation set to MDC. If a domain controller's resource
  occupation status isn't Normal, the MDC range conflicts with that controller's own
  VNIs [1].

## References

[1] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612446 (verify at
support.huawei.com HedEx, `docid=EDOC1100612446`). Verify in: Digital Map > Digital Map Usage
Guide > Overview. Confirmed Nov. 4, 2026. For inter-DC Layer 2: Solution Overview >
Baseline Networking > Private Cloud Multi-DC Interconnection > Inter-DC Layer 2 Communication;
Multi-Cloud Orchestration > Service Provisioning > Provisioning Multi-DC Interconnection on
Private Clouds > Examples of Service Provisioning > Single PoD in the Private Cloud
Multi-Site Scenario > East-West Inter-DC Layer 2 Communication; and Solution Overview > Encyclopedia > Private Cloud Interconnection > Transit
VPC and Transit Router. Confirmed Nov. 12, 2026. For global transit VNIs: Multi-Cloud
Orchestration > Multi-Cloud Access > Private Cloud Access > Configuring Global Transit
VNIs. Confirmed Nov. 12, 2026.

[2] "Stellar AI Fabric Data Center Network Solution Product Documentation," Huawei,
V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612448 (verify at
support.huawei.com HedEx, `docid=EDOC1100612448`). Read for the solution documentation set: it
has no Digital Map section, so Digital Map is an MDC-scenario feature [1]; and for the DCI-leaf
role — "DCI Scenario Overview" and "Configuring Underlay Network Connectivity Between DCI Leaf
Nodes" (DCI Scenario (Multi-Site and Non-MDC Scenario), DCI leaf naming, BGP EVPN stitching,
EBGP/IBGP split, active-active placement, separate deployment), and "Multi-fabric Network
Management". Confirmed Nov. 4, 2026; DCI topics rechecked Nov. 7, 2026. For Segment VXLAN
DCI versus the multi-PoD unified VXLAN domain: Deployment Guide > Underlay Basic Network
Pre-configuration > Manually Deploying the Underlay Network > Multi-DC Interconnection
Pre-configuration > Multi-DC Overview, and DCI Scenario Overview. Confirmed Nov. 12, 2026.
For logical VAS: Deployment Guide > Service Deployment >
Deployment Guide Reference > iMaster NCE-Fabric Deployment Guide Reference > Service
Provisioning Reference > Network Virtualization > Creating Logical Networks > Creating a
Logical VAS. For logical-router static routes and BGP peers: Deployment Guide > Service
Deployment > Datacenter Virtualization Solution > Service Provisioning Guide >
Non-Multi-Tenant Network > VPC > Creating Logical Networks > Creating a Logical Router
(Route List and BGP Peer tabs, RT Prefix), Creating a Logical Switch (RT Prefix, Host info
collect), and Creating an Interconnection Interface; and … > Service
Provisioning Reference > Network Virtualization > Configuring Public Policies > Configuring a
Routing Policy. For resource pools: … > Interconnection and Commissioning Reference > Resource
Pool Management > Configuring Interconnection Resources and Configuring Global Resources;
and Manually Deploying the Underlay Network > … > Three-Layer Networking with Service Leaf
Nodes and Border Leaf Nodes Combined > Network Planning > Network Parameter Planning.
Confirmed Nov. 12, 2026.
