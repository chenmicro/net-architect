# POC: Cisco firewall service insertion across two Huawei CloudFabric DCs

> Based on product documentation, not lab-tested.

## Background

- **Date**: 2026-11
- **Scope**: Two Huawei CloudFabric DCs. In each DC, a Cisco FTD sits between two VPCs
  (VPC-A, VPC-B) and a third VPC, EXT, that faces the core, all on the border-leaf M-LAG
  pair. Between the DCs: VPC subnets stretched at Layer 2 by DCI leaf pairs, Layer 3
  through EXT and the core switches, a separate north-south egress per DC, and host
  routes that steer traffic to the DC where a host is.
- **Scenario**:

## Test environment

### Topology

The two DCs connect over two paths: the DCI leaf pairs on a dedicated link carry Layer 2,
and the core switches, which iMaster NCE-Fabric doesn't manage, carry Layer 3. Device
names carry the DC number (Device list).

- **Border-leaf pair, per DC**: a CE6885 M-LAG pair, combined border and
  service leaf, with the VRFs VPC-A, VPC-B, and EXT. EXT is a VPC, not an iMaster
  NCE-Fabric external gateway.
- **Firewall, per DC**: an off-path Cisco FTD managed by FMC. It attaches to the
  border-leaf pair over an Eth-Trunk, a plain LACP EtherChannel on the FTD side, with
  one 802.1Q sub-interface per VRF.
- **Core, per DC**: a non-SDN Huawei switch. The FW and the core each run one public
  routing table and peer eBGP with EXT.
- **DCI leaf pair, per DC**: separate from the border leaves, as the solution guide
  recommends [1]. The pairs stitch the fabrics with Segment VXLAN over BGP EVPN [1] and
  carry only the Layer 2 stretch, through one MDC L2 transit VPC [2].
- **Servers, per DC**: two server-leaf M-LAG pairs, each with one VPC-A and one VPC-B
  server dual-homed to the pair.

[Figure 1 — Physical topology: both DCs' border-leaf M-LAG pairs with their off-path firewalls, the DCI leaf pairs on their dedicated link, and the cross-DC core link](2026-07-cisco-huawei-dci-firewall-fig1.drawio)

### Device list

| Name | Role | DC | Vendor | Model | Software version |
|---|---|---|---|---|---|
| Border1-1 | Border leaf / service leaf, M-LAG pair member | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Border1-2 | Border leaf / service leaf, M-LAG pair member | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| FW1 | Firewall (public routing table; sub-interfaces to VPC-A, VPC-B, EXT) | DC1 | Cisco | Secure Firewall Threat Defense (FTD), managed by FMC |  |
| Core1 | Core switch (non-SDN, public routing table) | DC1 | Huawei |  |  |
| DCI1-1 | DCI leaf, M-LAG pair member | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| DCI1-2 | DCI leaf, M-LAG pair member | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Spine1-1 | Spine (RR) | DC1 |  |  |  |
| Spine1-2 | Spine (RR) | DC1 |  |  |  |
| Leaf1-1 | Server leaf (VTEP), pair 1 | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf1-2 | Server leaf (VTEP), pair 1 | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf1-3 | Server leaf (VTEP), pair 2 | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf1-4 | Server leaf (VTEP), pair 2 | DC1 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Srv1-A1 | Server, VPC-A, under pair 1 | DC1 |  |  |  |
| Srv1-B1 | Server, VPC-B, under pair 1 | DC1 |  |  |  |
| Srv1-A2 | Server, VPC-A, under pair 2 | DC1 |  |  |  |
| Srv1-B2 | Server, VPC-B, under pair 2 | DC1 |  |  |  |
| Border2-1 | Border leaf / service leaf, M-LAG pair member | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Border2-2 | Border leaf / service leaf, M-LAG pair member | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| FW2 | Firewall (public routing table; sub-interfaces to VPC-A, VPC-B, EXT) | DC2 | Cisco | Secure Firewall Threat Defense (FTD), managed by FMC |  |
| Core2 | Core switch (non-SDN, public routing table) | DC2 | Huawei |  |  |
| DCI2-1 | DCI leaf, M-LAG pair member | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| DCI2-2 | DCI leaf, M-LAG pair member | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Spine2-1 | Spine (RR) | DC2 |  |  |  |
| Spine2-2 | Spine (RR) | DC2 |  |  |  |
| Leaf2-1 | Server leaf (VTEP), pair 1 | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf2-2 | Server leaf (VTEP), pair 1 | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf2-3 | Server leaf (VTEP), pair 2 | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Leaf2-4 | Server leaf (VTEP), pair 2 | DC2 | Huawei | CE6885 | V300R026C00, VRP V800 |
| Srv2-A1 | Server, VPC-A, under pair 1 | DC2 |  |  |  |
| Srv2-B1 | Server, VPC-B, under pair 1 | DC2 |  |  |  |
| Srv2-A2 | Server, VPC-A, under pair 2 | DC2 |  |  |  |
| Srv2-B2 | Server, VPC-B, under pair 2 | DC2 |  |  |  |

### Network plan

#### Addressing

- **Point-to-point links**: from `172.16.0.0/16`, for the underlay and every
  interconnection link. DC1 uses `172.16.100.0/24`, DC2 `172.16.200.0/24`, and links
  between the DCs `172.16.255.0/24`.
- **Service subnets** (the VPC subnets): from `10.0.0.0/8`.

**Border-leaf pair ↔ FW.** One sub-interface per VRF, all in the FW's one public table,
so every subnet differs. The VLANs come from the solution guide's example gateway ↔
firewall range, 3000-3499 [1], and are the same in both DCs. In each /29 the FW takes
the first host address and the border-leaf pair's shared VBDIF the second. The fabric
uses VBDIF interfaces, not VLANIF.

| FW sub-interface | VRF | VLAN | DC1 | DC2 |
|---|---|---|---|---|
| `ext` | EXT | 3000 | `172.16.100.0/29` | `172.16.200.0/29` |
| `vpc-a` | VPC-A | 3001 | `172.16.100.8/29` | `172.16.200.8/29` |
| `vpc-b` | VPC-B | 3002 | `172.16.100.16/29` | `172.16.200.16/29` |

| EXT link role | DC1 | DC2 |
|---|---|---|
| FW `ext` | `172.16.100.1` | `172.16.200.1` |
| VBDIF primary IP (both border leaves) | `172.16.100.2` | `172.16.200.2` |
| Border1-1 / Border2-1 M-LAG IP (BGP source) | `172.16.100.3` | `172.16.200.3` |
| Border1-2 / Border2-2 M-LAG IP (BGP source) | `172.16.100.4` | `172.16.200.4` |

**Core ↔ EXT and between the cores.**

| Role | DC1 (`172.16.100.24/29`) | DC2 (`172.16.200.24/29`) |
|---|---|---|
| Core switch | `172.16.100.25` | `172.16.200.25` |
| Border1-1 / Border2-1 (EXT) | `172.16.100.26` | `172.16.200.26` |
| Border1-2 / Border2-2 (EXT) | `172.16.100.27` | `172.16.200.27` |

| Link | Subnet |
|---|---|
| Core1 ↔ Core2 | `172.16.255.8/30` (Core1 `.9`, Core2 `.10`) |
| DCI1-1 ↔ DCI2-1 | `172.16.255.0/30` |
| DCI1-2 ↔ DCI2-2 | `172.16.255.4/30` |
| DCI leaf loopbacks (BGP EVPN source, VTEP) | |

#### BGP AS plan

| Device | DC1 | DC2 |
|---|---|---|
| Fabric: border-leaf pair (EXT), spines, server leaves, DCI leaves | 65002 | 65003 |
| Firewall | 65010 | 65010 |
| Core switch | 65100 | 65200 |

BGP is iBGP inside each fabric and eBGP between the two fabrics' DCI leaves [1]. Each
fabric needs its own AS: a DC1 host route reaches the DC2 EXT with the AS path
`65200 65100 65002`, and with one shared AS, AS loop detection would drop it
([bgp.md](../techniques/bgp.md#design-considerations)).

#### VPC mapping

Each VPC subnet is one subnet stretched across both DCs: an MDC L2 transit VPC holds a
transit switch associated with the VPC's logical switch in each DC [2]. Subnets never
overlap across VPCs.

| VPC | VPC subnet | DC1 logical switch RT | DC2 logical switch RT | DC1 VNI / L3VNI | DC2 VNI / L3VNI |
|---|---|---|---|---|---|
| VPC-A | 10.1.1.0/24 | `100:<assigned>` | `300:<assigned>` | 6000 / 5000 | 11000 / 10000 |
| VPC-B | 10.2.2.0/24 | `200:<assigned>` | `400:<assigned>` | 6001 / 5001 | 11001 / 10001 |

- **RTs**: each DC's controller provisions its own VPCs, so the RTs differ per DC. Only
  the RT prefix is planned; the controller assigns the rest, so read the full value from
  the device after creation ([cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md#logical-routers-and-logical-switches)).
  The table lists the logical switch (Layer 2) RT, which EXT imports in MC-01.
- **VNIs**: DC1 uses 5000-9999 and DC2 10000-15000, splitting the guide's example pool
  5000-15000 [1]. The MDC global transit VNIs are 1600-1700, the MDC guide's example
  [2], outside both DC ranges.

#### Traffic paths

Routing tables steer traffic through the FWs; no device uses PBR.

[Figure 2 — Overlay: the VPC-A, VPC-B, and EXT VRFs on the border-leaf pair, the public-only firewall and core, the stretched subnets on the DCI leaves, and the Layer 3 path between the cores](2026-07-cisco-huawei-dci-firewall-fig2.drawio)

| Flow | Example | Path, first direction (the other is the reverse) | TC |
|---|---|---|---|
| Layer 2, intra-DC (same subnet) | Srv1-A1 → Srv1-A2 | Leaf1-1/1-2 → Leaf1-3/1-4 over VXLAN in the fabric; no FW | TC-06 |
| Layer 2, inter-DC (same subnet) | Srv1-A1 → Srv2-A1 | Leaf1-1/1-2 → DCI1 → DCI2 → Leaf2-1/2-2 (L2 transit VPC, Segment VXLAN); no FW | TC-07 |
| Layer 3, intra-DC (VPC-A ↔ VPC-B) | Srv1-A1 → Srv1-B2 | Leaf1-1/1-2 (VPC-A default route) → Border1 VPC-A → FW1 (static `10.2.2.0/24`) → Border1 VPC-B → Leaf1-3/1-4 | TC-08 |
| Layer 3, inter-DC (VPC-A ↔ VPC-B) | Srv1-A1 → Srv2-B1 | Leaf1-1/1-2 → Border1 VPC-A → FW1 (Srv2-B1's /32) → Border1 EXT → Core1 → Core2 → Border2 EXT (route list) → FW2 (static `10.2.2.0/24`) → Border2 VPC-B → Leaf2-1/2-2 | TC-09 |
| North-south, intra-DC | Inbound to Srv1-A1 through DC1 | DC1 egress → Core1 (Srv1-A1's /32 or `10.0.0.0/8`) → Border1 EXT (route list) → FW1 (static `10.1.1.0/24`) → Border1 VPC-A → Leaf1-1/1-2 | TC-10, TC-11, TC-12 |
| North-south, inter-DC | Inbound to Srv1-A1 through DC2 | DC2 egress → Core2 (Srv1-A1's /32) → Core1 → Border1 EXT (route list) → FW1 → Border1 VPC-A → Leaf1-1/1-2. Outbound goes back through DC2 only when the routing toward the destination points there | TC-13, TC-14 |

No VPC interconnection is configured, so VPC-A ↔ VPC-B traffic always crosses a FW, and
both directions of a flow cross the same FWs. The DCI leaves carry no Layer 3.

[Figure 3 — Traffic paths: the six flows of the table, first direction, with the route that decides each hop](2026-07-cisco-huawei-dci-firewall-fig3.drawio)

#### Controller-provisioned configuration

Configured in iMaster NCE-Fabric. The rules behind each object are in
[cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md#logical-networks-vpc).

- **FW as a logical VAS**: device type Unmanaged Firewall, because the managed Firewall
  type lists only Huawei models [1]. Route Deploy Disable stays off. The interconnection
  VLANs and IPs are entered by hand (Addressing).
- **VPC logical switches**: Host info collect enabled, which makes the gateways advertise
  host routes as IRB routes [1]. RT prefixes as in VPC mapping.
- **Route lists** (static routes on each logical router; a Normal route toward the FW is
  delivered to the border-leaf pair as the service leaf [1]):

  | Logical router | Destination | DC1 next hop | DC2 next hop |
  |---|---|---|---|
  | VPC-A | `0.0.0.0/0` | `172.16.100.9` (FW `vpc-a`) | `172.16.200.9` |
  | VPC-B | `0.0.0.0/0` | `172.16.100.17` (FW `vpc-b`) | `172.16.200.17` |
  | EXT | `10.1.1.0/24` | `172.16.100.1` (FW `ext`) | `172.16.200.1` |
  | EXT | `10.2.2.0/24` | `172.16.100.1` (FW `ext`) | `172.16.200.1` |
  | EXT | `0.0.0.0/0` | `172.16.100.25` (Core1) | `172.16.200.25` (Core2) |

  EXT's default route carries north-south traffic out through the DC's own core. A host
  /32 learned from the core is more specific, so traffic to the other DC's hosts still
  follows the /32.

- **EXT BGP peers** (BGP Peer tab, vpnv4-instance, Direct connection, device group =
  border-leaf pair [1]): the core and the FW (each M-LAG IP). Neither peer has a policy
  on the tab, and Permit AS loops stays off: the FW-facing export policy is on the CLI
  (MC-01 step 3), and the FW advertises nothing (MC-03).

#### Standard pre-configuration on the DCI leaves

In a normal delivery a script applies this before the controllers provision services,
following the solution guide's manual underlay deployment for multi-site DCI [1]. On
both DCI leaves in each DC, `bgp` → `l2vpn-family evpn`:

- **Layer 2 DCI**: put the remote DCI-leaf peer group in a split horizon group (`peer
  <remote-dci-group> split-group <name>`), and enable `import reoriginate` and `advertise
  route-reoriginated evpn mac` toward both the remote DCI leaves and the local spines
  [1]. The MDC L2 transit VPC needs the same split horizon group [2].
- **DCI route filtering**: `route-policy underlay_dci_router_policy_export deny node
  65535` (and optionally `…_import`), applied to the remote DCI peer with `peer <ip>
  route-policy … export` (`import`). The policies must exist before iMaster NCE-Fabric
  delivers its permit nodes below 65535, and the names must match the DCI route policies
  in its GUI [1].
- **Verification**: TC-05, TC-07.

#### Manual configuration not in the solution documentation

Neither the controllers nor the delivery script apply these; they are entered by hand,
based on the device documentation.

##### MC-01: Host routes through the EXT VRF

- **Why it's manual**: a stretched subnet's route can't tell the core which DC a host is
  in, and the solution documentation doesn't cover host routes for this design. Its DCI
  route optimization tags local-leaf routes with a community, but on DCI leaves doing
  Layer 3 DCI [1]; here the DCI leaves are Layer 2 only.
- **Where**: the border-leaf pair (EXT), the core switches, and the BGP EVPN peers of
  every fabric device.
- **Configuration**: values for DC1; DC2 uses `bgp 65003`, RTs `300`/`400:<assigned>`,
  communities swapped (`65003:100` local), and `172.16.200.x` addresses.
  1. **Local host routes into EXT, advertise-only** (border-leaf pair). The spine RRs
     reflect the server leaves' IRB routes to the border leaves (`peer BorderLeaf
     advertise irb`) [1], and EXT imports those carrying the local logical switch RTs [3].
     Only the local DC's hosts arrive, because the DCI leaves re-originate MAC routes
     only [1]. `rib-only` keeps the /32s out of EXT's IP routing table, so EXT advertises
     them but forwards local-host traffic by its route list through the FW [3]; routes
     from the core carry no logical switch RT and stay forwardable. Command behavior:
     [multi-tenancy.md](../techniques/multi-tenancy.md#cross-vendor--variants),
     [bgp.md](../techniques/bgp.md#cross-vendor--variants).

     ```
     ip ip-prefix VPC-HOST32 index 10 permit 10.0.0.0 8 greater-equal 32 less-equal 32
     ip extcommunity-filter basic VPC-LS-RT index 10 permit rt 100:<assigned> rt 200:<assigned>
     #
     route-policy EXT-IMPORT-EVPN permit node 10
      if-match extcommunity-filter VPC-LS-RT
      if-match ip-prefix VPC-HOST32
     route-policy EXT-IMPORT-EVPN deny node 100
     #
     route-policy EXT-RIB-ONLY permit node 10
      if-match extcommunity-filter VPC-LS-RT
      if-match ip-prefix VPC-HOST32
     #
     ip vpn-instance EXT
      ipv4-family
       vpn-target 100:<assigned> import-extcommunity evpn    # VPC-A logical switch
       vpn-target 200:<assigned> import-extcommunity evpn    # VPC-B logical switch
       import route-policy EXT-IMPORT-EVPN evpn
     #
     bgp 65002
      ipv4-family vpn-instance EXT
       routing-table rib-only route-policy EXT-RIB-ONLY
     ```

     Configure `VPC-LS-RT` before the policies reference it: an `if-match
     extcommunity-filter` naming a missing filter matches all routes [3].
  2. **EXT → core → the other DC's EXT** (core switches). EXT advertises the local /32s
     to its core over the controller-delivered core peer. The cores exchange them over
     the cross-DC link, passing communities on every peer. The receiving EXT's policies
     match only its own DC's RTs, so the remote /32s are installed and forward toward
     the core. Each core reaches all local VPC subnets through one static `10.0.0.0/8`
     to its EXT; a remote host's /32 is more specific.

     ```
     bgp 65100                                   # DC2: bgp 65200
      peer 172.16.100.26 as-number 65002         # Border1-1 EXT
      peer 172.16.100.27 as-number 65002         # Border1-2 EXT
      peer 172.16.255.10 as-number 65200         # Core2 (on Core2: 172.16.255.9, 65100)
      ipv4-family unicast
       peer 172.16.100.26 enable
       peer 172.16.100.27 enable
       peer 172.16.255.10 enable
       peer 172.16.100.26 advertise-community
       peer 172.16.100.27 advertise-community
       peer 172.16.255.10 advertise-community
     #
     ip route-static 10.0.0.0 8 172.16.100.26
     ip route-static 10.0.0.0 8 172.16.100.27
     ```

     The core model isn't recorded; check `advertise-community` against its
     documentation (verified for CloudEngine [3]).
  3. **Only remote host routes to the FW** (server leaves, all fabric devices,
     border-leaf pair). A local host's /32 on the FW would beat its static segment
     route (MC-02) and send local traffic to EXT. The server leaves tag every route
     they advertise with the DC's community; EXT's export policy toward the FW drops
     the local community and passes the remote one.

     ```
     # Server leaves (all)
     route-policy SL-EVPN-EXPORT permit node 10
      apply community 65002:100 additive
     #
     bgp 65002
      l2vpn-family evpn
       peer <spine-peer> route-policy SL-EVPN-EXPORT export

     # All fabric devices (server leaves, spines, border leaves, DCI leaves)
     bgp 65002
      l2vpn-family evpn
       peer <peer-or-group> advertise-community      # every BGP EVPN peer

     # Border-leaf pair
     ip community-filter basic LOCAL-HOST index 10 permit 65002:100
     ip community-filter basic REMOTE-HOST index 10 permit 65003:100
     #
     route-policy EXT-TO-FW deny node 10
      if-match community-filter LOCAL-HOST
     route-policy EXT-TO-FW permit node 20
      if-match community-filter REMOTE-HOST
      if-match ip-prefix VPC-HOST32
     route-policy EXT-TO-FW deny node 100
     #
     bgp 65002
      ipv4-family vpn-instance EXT
       peer 172.16.100.1 route-policy EXT-TO-FW export
       peer 172.16.100.25 advertise-community        # core
     ```

     `SL-EVPN-EXPORT` has no `if-match`, so it tags every route and drops none; an EVPN
     export policy advertises only matching routes [3]. If the remote community is lost
     anywhere on the path, node 20 matches nothing and the FW gets no host routes.
- **Verification**: on a border leaf, `display bgp vpnv4 vpn-instance EXT
  routing-table` lists the local /32s with the local community, and `display ip
  routing-table vpn-instance EXT` doesn't. On the FW only the other DC's /32s arrive.
  TC-03, TC-13, TC-14.

##### MC-02: Static routes on the FW

- **Where**: FMC: Devices > Device Management > edit the device > Routing > Static Route
  > Add Routes > IPv4 [4].
- **Why it's manual**: the FW is an Unmanaged Firewall VAS; the controller configures
  only the gateway side [1].
- **Configuration**: the default route needs a network object for `0.0.0.0/0` [4].

  | Interface (VLAN) | Destination | DC1 gateway | DC2 gateway | Metric |
  |---|---|---|---|---|
  | `vpc-a` (3001) | `10.1.1.0/24` | `172.16.100.10` | `172.16.200.10` | 1 |
  | `vpc-b` (3002) | `10.2.2.0/24` | `172.16.100.18` | `172.16.200.18` | 1 |
  | `ext` (3000) | `0.0.0.0/0` | `172.16.100.2` | `172.16.200.2` | 1 |

  A remote host's /32 from BGP and the static segment route have different prefix
  lengths, so FTD installs both and forwards on the longer one [4].
- **Verification**: TC-03, TC-08, TC-10, TC-12.

##### MC-03: eBGP from the FW to the EXT VRF

- **Where**: FMC: Devices > Device Management > edit the device > Routing > BGP, and
  BGP > IPv4 > Neighbor; prefix lists under Objects > Object Management > Prefix List >
  IPv4 Prefix List [4].
- **Why it's manual**: as MC-02.
- **Configuration**:
  - *BGP process*: AS `65010`, Router Id Manual = the FW's `ext` address. No Networks and
    no redistribution.
  - *Prefix lists*: entry masks must be 1-32, so two `/1` entries stand in for
    `0.0.0.0/0` [4].

    | Object | Seq | Action | Address | Min length | Max length |
    |---|---|---|---|---|---|
    | `FTD-IN-HOST32` | 10 | Allow | `10.0.0.0/8` | 32 | 32 |
    | `FTD-IN-HOST32` | 20 | Block | `0.0.0.0/1` | | 32 |
    | `FTD-IN-HOST32` | 30 | Block | `128.0.0.0/1` | | 32 |
    | `FTD-OUT-NONE` | 10 | Block | `0.0.0.0/1` | | 32 |
    | `FTD-OUT-NONE` | 20 | Block | `128.0.0.0/1` | | 32 |

  - *Neighbors*: one per border-leaf member's M-LAG IP, since BGP over M-LAG runs a
    session to each member from its own M-LAG IP [3]. On the border leaves the M-LAG IP
    sits on the VBDIF as a secondary address in the primary IP's subnet; `m-lag ip
    address` works on a VBDIF only after the BD is bound to a VNI, and unbinding the
    VNI deletes it [3]:

    | Neighbor (DC1 / DC2) | Remote AS (DC1 / DC2) | Incoming | Outgoing |
    |---|---|---|---|
    | `172.16.100.3` / `172.16.200.3` (Border1-1 / Border2-1) | 65002 / 65003 | `FTD-IN-HOST32` | `FTD-OUT-NONE` |
    | `172.16.100.4` / `172.16.200.4` (Border1-2 / Border2-2) | 65002 / 65003 | `FTD-IN-HOST32` | `FTD-OUT-NONE` |

    `FTD-OUT-NONE` is needed because FTD's eBGP otherwise advertises learned routes back
    to the peer ([bgp.md](../techniques/bgp.md#cross-vendor--variants)).
- **Verification**: TC-02, TC-03.

## Test cases

TC-01 to TC-05 check the setup. TC-06 to TC-14 follow the traffic paths in the order of
that table, and TC-15 tests failover. TC-01 to TC-04, TC-06, TC-08, TC-10 to TC-12, and
TC-15 run in each DC; TC-05, TC-07, TC-09, TC-13, and TC-14 cover what crosses between
the DCs.

### TC-01: Underlay reachability

**Objective**:

**Prerequisites**:

**Procedure**:
```
# From Border1-1 to FW1's EXT sub-interface
ping -vpn-instance EXT 172.16.100.1

# From FW (public table) to both M-LAG IPs
ping 172.16.100.3
ping 172.16.100.4

# From a server leaf to Border1-1 (underlay)
ping <Border1-1-underlay-IP> source loopback0
```

**Expected result**: All pings succeed with <1ms latency, no packet loss.

**If it fails**:
- MTU mismatch (ping with `-s 1472 -f`, then `-s 1500 -f`)

### TC-02: BGP peering

**Objective**: Validate eBGP between the EXT VRF on the border-leaf pair and the FW, and
between EXT and the core.

**Prerequisites**: TC-01 passed.

**Procedure**:
```
# On Border1-1 and Border1-2
display bgp vpnv4 vpn-instance EXT peer

# On FW
show bgp summary
```

**Expected result**: On the FW, two sessions `Established`, to `172.16.100.3` (Border1-1) and
`172.16.100.4` (Border1-2). On each border leaf, the FW and core peers `Established`. No flaps.

**If it fails**:
- M-LAG IP or BGP source misconfiguration
- Wrong AS number or update-source

### TC-03: FW routing table

**Objective**: Validate the FW's public routing table: static routes to the local VPC
segments, and only the other DC's host routes from EXT.

**Prerequisites**: TC-02 passed in both DCs; MC-01 configured.

**Procedure**:
```
# On FW
show route static
show bgp neighbors 172.16.100.3 routes
show bgp neighbors 172.16.100.4 routes
show route 10.1.1.0 255.255.255.0 longer-prefixes
```

**Expected result**: Static routes for `10.1.1.0/24` and `10.2.2.0/24` point to the
`vpc-a` and `vpc-b` sub-interfaces, and the default route to `ext`. The other DC's host
/32s arrive from both M-LAG IPs; no local host /32 does. The FW advertises nothing.

**If it fails**:
- Static segment route missing or pointing to the wrong sub-interface
- Remote host routes missing: not imported in the other DC's EXT, or a community lost on
  the way (MC-01)
- Local host routes present: the server-leaf community or `EXT-TO-FW` missing (MC-01
  step 3)

### TC-04: VPC VRF default route to the FW

**Objective**: Validate that each VPC VRF sends unknown destinations to the FW over its
own sub-interface, and that the server leaves have the default route.

**Prerequisites**: TC-01 passed.

**Procedure**:
```
# On Border1-1
display ip routing-table vpn-instance VPC-A 0.0.0.0
display ip routing-table vpn-instance VPC-B 0.0.0.0

# On a server leaf
display bgp evpn all routing-table | include 0.0.0.0/0
```

**Expected result**: In each VPC VRF the default route points to that VPC's FW
sub-interface. The server leaves install it with the border-leaf pair's VTEP as next hop.

**If it fails**:
- Default route missing in the VPC VRF, or pointing to another VRF's sub-interface
- The route-list static route not delivered because its next hop is outside the
  interconnection interface's subnet
- Default route not advertised into EVPN toward the server leaves

### TC-05: DCI leaf peering and underlay

**Objective**: Validate that the DCI leaves of the two DCs reach each other over the
dedicated DCI link and establish BGP EVPN peering.

**Prerequisites**: TC-01 passed in both DCs; the standard DCI-leaf pre-configuration
applied.

**Procedure**:
```
# On a DC1 DCI leaf
ping <DC2-DCI-leaf-loopback> -a <local-loopback>
display bgp evpn peer
display vxlan tunnel
```

**Expected result**: The remote DCI leaf loopbacks are reachable. The BGP EVPN peers to
the remote DCI leaves and to the local spines are `Established`, and VXLAN tunnels to the
remote DCI leaves are up.

**If it fails**:
- DCI leaf loopbacks not exchanged over the dedicated DCI link
- MTU on the dedicated DCI link too small for VXLAN encapsulation

### TC-06: Intra-DC east-west between server-leaf pairs

**Objective**: Validate east-west traffic inside one DC, within a VPC, between servers on
the two server-leaf pairs.

**Prerequisites**: TC-04 passed; servers attached to both server-leaf pairs.

**Procedure**:
```
# VPC-A server on pair 1 to VPC-A server on pair 2
ping <VPC-A-pair-2-server-IP>
tracert <VPC-A-pair-2-server-IP>

# On a pair-1 server leaf
display bgp evpn all routing-table mac-route
display bgp evpn all routing-table prefix-route
```

**Expected result**: Traffic goes from pair 1 to pair 2 across the fabric without passing
the firewall. Each pair-1 server leaf holds the pair-2 hosts' EVPN routes.

**If it fails**:

### TC-07: Layer 2 stretch between the DCs

**Objective**: Validate that hosts in the same stretched subnet communicate across the DCs
through the L2 transit switch, without BUM loops.

**Prerequisites**: TC-05 passed; the L2 transit VPC is provisioned on the MDC.

**Procedure**:
```
# From a VPC-A host in DC1 to a VPC-A host in DC2 (same subnet 10.1.1.0/24)
ping <DC2-host-IP>

# On a DC1 DCI leaf
display bgp evpn all routing-table mac-route
```

**Expected result**: The ping succeeds. The DC1 DCI leaf holds the DC2 host's MAC route
learned from the remote DCI leaf and re-originates it toward the local spines. No
duplicated or looping BUM traffic.

**If it fails**:
- Split horizon group missing on a DCI leaf (standard pre-configuration)
- MAC re-origination missing toward the remote DCI leaves or the local spines (standard
  pre-configuration)

### TC-08: Intra-DC Layer 3 between VPCs through the firewall

**Objective**: Validate that traffic between VPC-A and VPC-B inside one DC goes VPC-A VRF
→ FW → VPC-B VRF, and the return traffic takes the same FW.

**Prerequisites**: TC-03 and TC-04 passed; MC-02 configured.

**Procedure**:
```
# VPC-A server on pair 1 to VPC-B server on pair 2, then the reverse
ping <VPC-B-pair-2-server-IP>
tracert <VPC-B-pair-2-server-IP>

# On a pair-1 server leaf, VPC-A VRF
display ip routing-table vpn-instance VPC-A <VPC-B-pair-2-server-IP>

# On the FW
show route <VPC-B-pair-2-server-IP>
show conn address <VPC-A-pair-1-server-IP>
```

**Expected result**: The VPC-A VRF matches only its default route toward the FW. The FW
matches its static route for the local VPC-B segment (`10.2.2.0/24` → `172.16.100.18` in
DC1) and forwards on `vpc-b`. The connection enters on `vpc-a` and leaves on `vpc-b`, and
the reverse direction hits the same connection.

**If it fails**:
- A direct route between the VPC-A and VPC-B VRFs, from a VPC interconnection, bypasses
  the FW
- The FW's static route for the local VPC-B segment missing (MC-02)
- A local host's /32 on the FW, sending the traffic to EXT (MC-01 step 3)
- The FTD access control policy has no rule allowing traffic from the `vpc-a`
  interface's security zone to the `vpc-b` interface's zone, so the default action
  handles it [4]

### TC-09: Cross-DC Layer 3 through the firewall and the cores

**Objective**: Validate that inter-subnet traffic between the DCs goes VPC VRF → FW1 →
Border1 EXT → Core1 → Core2 → Border2 EXT → FW2, not through the DCI leaves.

**Prerequisites**: TC-03 and TC-04 passed in both DCs.

**Procedure**:
```
# From a VPC-A host in DC1 to a VPC-B host in DC2
ping <DC2-VPC-B-host-IP>
tracert <DC2-VPC-B-host-IP>

# On the DC1 FW
show route <DC2-VPC-B-host-IP>
```

**Expected result**: The DC1 FW matches the DC2 host's /32 from EXT rather than its static
`10.2.2.0/24`, and the trace crosses the cores and the DC2 FW.

**If it fails**:
- The DC2 host's /32 missing on the DC1 FW, so the static segment route sends the traffic
  to the local VPC-B VRF (TC-03, MC-01)
- EXT ↔ core eBGP or the cross-DC core link down

### TC-10: Ping across service chain

**Objective**: Validate north-south reachability from a VPC server through its DC's FW,
EXT, and core.

**Prerequisites**: TC-04 passed.

**Procedure**:
```
# From Srv1-A1
ping <FW1-vpc-a-IP>
ping <external-IP>                          # via FW1, EXT, Core1; no NAT
```

**Expected result**: Ping to FW1's `vpc-a` sub-interface succeeds. Ping to the external
address succeeds without address translation: Srv1-A1 → FW1 (0/0) → EXT (0/0) → Core1 →
external network, and the return the same way.

**If it fails**:
- FW access control policy blocking the VPC subnet
- EXT's default route to the core missing from its route list
- Next-hop mismatch in a VRF routing table

### TC-11: TCP traffic through firewall

**Objective**:

**Prerequisites**: TC-10 passed.

**Procedure**:
```
# iperf3 test across the service chain
iperf3 -c <internet-test-server> -t 30
```

**Expected result**: Full throughput, no timeouts or retransmits.

**If it fails**:
- FW TCP inspection parameters

### TC-12: North-south traffic through each DC's own egress

**Objective**: Validate that each DC's hosts reach the external network through their own
DC's firewall and egress.

**Prerequisites**: TC-10 passed in both DCs.

**Procedure**:
```
# From a host in DC1, then from a host in DC2
tracert <external-IP>
```

**Expected result**: DC1 traffic leaves through DC1's firewall and egress, and DC2 traffic
through DC2's. No north-south traffic crosses the DCI.

**If it fails**:

### TC-13: Host-route steering for a stretched subnet

**Objective**: Validate that traffic from outside toward a host in the stretched subnet
enters the DC where the host is (MC-01).

**Prerequisites**: TC-07 and TC-12 passed; MC-01 configured.

**Procedure**:
```
# On each core and each FW, for a DC1 host and a DC2 host
display ip routing-table <DC1-host-IP>        # core
show route <DC2-host-IP>                      # FW

# From the external network
tracert <DC1-host-IP>
tracert <DC2-host-IP>
```

**Expected result**: Each host has a /32 route pointing at its own DC, and traffic from
outside to each host enters that DC.

**If it fails**:

### TC-14: Host moves between the DCs

**Objective**: Validate that the host route follows a host when it moves to the other DC.

**Prerequisites**: TC-13 passed.

**Procedure**:
```
# Move a VPC-A host from DC1 to DC2 (keeping its IP and MAC), then
display ip routing-table <host-IP>
tracert <host-IP>
```

**Expected result**: The /32 is withdrawn from DC1 and advertised from DC2, and traffic
follows the host. Record the convergence time.

**If it fails**:

### TC-15: HA / M-LAG member failure

**Objective**: Validate M-LAG HA: traffic survives single CE member failure through the
BGP session on the other member.

**Prerequisites**: TC-11 passed.

**Procedure**:
```
# Shut down Border1-1's service-chain link to FW1 (or Border1-1 entirely)
# Observe BGP state on the remaining Border1-2
display bgp vpnv4 vpn-instance EXT peer 172.16.100.1

# Verify traffic continues
ping <internet-IP> from VPC-A server
```

**Expected result**: The session to Border1-1 goes down and the session to Border1-2 stays
`Established`. Zero or sub-second traffic interruption.

**If it fails**:

## Issues encountered

## Conclusion

## References

[1] "Stellar AI Fabric Data Center Network Solution Product Documentation," Huawei,
V100R026C00, Library Version 01, 2026-09-30 (HedEx library EDOC1100612448, login required).
Verify in: Deployment Guide > Underlay Basic Network Pre-configuration > Manually Deploying
the Underlay Network > Multi-DC Interconnection Pre-configuration > Multi-DC Overview, and >
Pre-configuration in the DCI Scenario (Multi-Site and Non-MDC Scenario) > DCI Scenario
Overview, Configuring Layer 2 DCI, and Pre-configuration for DCI Route Optimization; and >
Basic Network Pre-configuration of the Distributed Network Overlay in a Single DC >
Three-Layer Networking with Service Leaf Nodes and Border Leaf Nodes Combined (Network
Planning > Network Parameter Planning for interconnection VLANs 3000-3499; Underlay Network
Deployment > Configuring Spine Nodes for the IRB reflection to the border leaves).
Deployment Guide > Service Deployment > Datacenter Virtualization Solution > Service
Provisioning Guide > Non-Multi-Tenant Network > VPC > Creating Logical Networks > Creating a
Logical Router (Route List and BGP Peer tabs), Creating a Logical Switch (Host info
collect), and Creating a Logical VAS. Deployment Guide > Service Deployment > Deployment
Guide Reference > iMaster NCE-Fabric Deployment Guide Reference > Interconnection and
Commissioning Reference > Resource Pool Management > Configuring Global Resources (VNI pool
5000-15000). Confirmed Nov. 12, 2026.

[2] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30 (HedEx library EDOC1100612446, login
required). Verify in: Multi-Cloud Orchestration > Service Provisioning > Provisioning Multi-DC
Interconnection on Private Clouds > Examples of Service Provisioning > Single PoD in the Private
Cloud Multi-Site Scenario > East-West Inter-DC Layer 2 Communication; and Multi-Cloud
Orchestration > Multi-Cloud Access > Private Cloud Access > Configuring Global Transit VNIs.
Confirmed Nov. 12, 2026.

[3] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation," Huawei,
V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login required). Verify
in: Configuration > Configuration Guide > High Availability Configuration > M-LAG
Configuration > Configuring a Dynamic Routing Protocol for Communication with an M-LAG >
Configuring BGP or BGP4+ over M-LAG (confirmed Oct. 31, 2026); References > Command
Reference > High Availability > M-LAG Configuration Commands > m-lag ip address (VBDIF and
VLANIF views; confirmed Nov. 12, 2026). References > Command
Reference > VXLAN > VXLAN Configuration Commands > vpn-target evpn (VPN instance IPv4
address family view), import route-policy evpn, peer route-policy export and peer
advertise-community (BGP-EVPN address family view); > IP Routing > Routing Policy
Configuration Commands > if-match extcommunity-filter; > IP Routing > BGP Configuration
Commands > routing-table rib-only (BGP-VPN instance IPv4 address family view) and peer
advertise-community (IPv4). Confirmed Nov. 12, 2026.

[4] "Cisco Secure Firewall Management Center Device Configuration Guide, 10.x," Cisco.
Verify in: Routing > Static and Default Routes (Add a static route; Routing tables > How
forwarding decisions are made), Routing > BGP (Configure basic BGP settings; Configure BGP
Neighbor Settings > Filtering Routes), Object Management > Prefix lists > Configure an IPv4
prefix list, and Access Control Rules (Default action behavior; security zone conditions).
https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/device-config/100/management-center-device-config-10-0.html
(chapters `routing-static.html`, `routing-bgp.html`, `objects-object-mgmt.html`,
`access-rules.html`). Confirmed Nov. 12, 2026.
