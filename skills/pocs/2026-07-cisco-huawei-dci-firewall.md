# POC: Cisco firewall service insertion across two Huawei CloudFabric DCs

> Based on product documentation, not lab-tested. Exception: the TC-16 steps marked as
> observed ran in a lab with a different topology, 2026-11.

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
| VPC-A | 10.1.1.0/24 | `100:6000` | `300:11000` | 6000 / 5000 | 11000 / 10000 |
| VPC-B | 10.2.2.0/24 | `200:6001` | `400:11001` | 6001 / 5001 | 11001 / 10001 |

- **RTs**: each DC's controller provisions its own VPCs, so the RTs differ per DC. Only
  the RT prefix is planned; the documentation says the controller generates the rest
  ([cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md#logical-routers-and-logical-switches)).
  In a lab the generated value was `<RT prefix>:<VNI>`, with prefix 0 when none is set, so
  the table assumes that form; confirm it on the device after creation. The table lists
  the logical switch (Layer 2) RT, which EXT imports in MC-01.
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
- **Configuration**: values for DC1; DC2 uses `bgp 65003`, RTs `300:11000`/`400:11001`,
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
     ip extcommunity-filter basic VPC-LS-RT index 1 deny rt 0:1          # placeholder, never removed
     ip extcommunity-filter basic VPC-LS-RT index 6000 permit rt 100:6000 # VPC-A, index = VNI
     ip extcommunity-filter basic VPC-LS-RT index 6001 permit rt 200:6001 # VPC-B
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
       vpn-target 100:6000 import-extcommunity evpn    # VPC-A logical switch
       vpn-target 200:6001 import-extcommunity evpn    # VPC-B logical switch
       import route-policy EXT-IMPORT-EVPN evpn
     #
     bgp 65002
      ipv4-family vpn-instance EXT
       routing-table rib-only route-policy EXT-RIB-ONLY
     ```

     Configure `VPC-LS-RT` before the policies reference it: an `if-match
     extcommunity-filter` naming a missing filter matches all routes [3]. The `index 1`
     deny entry keeps the filter in place when the last VPC entry is removed. Entries and
     RTs within an entry match with OR [3], so one entry per subnet, indexed by the
     logical switch VNI, matches the same routes as one entry listing every RT, and lets
     a subnet be added or removed on its own line. TC-16 adds these per-subnet lines with
     a workflow.
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

- **Where**: FMC: Devices > Device Management > edit the device > Routing > Static
  Route > Add Routes > IPv4 [4].
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
that table, TC-15 tests failover, and TC-16 automates adding a VPC subnet. TC-01 to TC-04, TC-06, TC-08, TC-10 to TC-12, and
TC-15 run in each DC; TC-05, TC-07, TC-09, TC-13, TC-14, and TC-16 cover what crosses
between the DCs.

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

### TC-16: Adding a VPC subnet with a Runbook workflow

**Objective**: Validate that one Runbook workflow on the MDC adds a new VPC subnet's
per-subnet configuration in both DCs in parallel, that a rerun changes nothing, and that a rollback removes only
what the run added. Per DC, the workflow adds:

| Configuration | Source in this record | How the workflow adds it |
|---|---|---|
| EXT route-list entry toward the FW | Controller-provisioned configuration | Built-in VPC action |
| `VPC-LS-RT` entry | MC-01 step 1 | Custom Smart CLI action |
| EXT import RT (`vpn-target … import-extcommunity evpn`) | MC-01 step 1 | Built-in GND action |
| `VPC-HOST32` entry, only for a subnet outside `10.0.0.0/8` | MC-01 step 1 | Built-in GND action |

The rest of the per-subnet work has no iMaster NCE-Fabric action and stays manual: the
FMC static route (MC-02) and, for a subnet outside `10.0.0.0/8`, the `FTD-IN-HOST32`
entry (MC-03) and the core's static route (MC-01 step 2).

**Prerequisites**:
- TC-13 passed with the existing VPCs. The new VPC's logical router and logical switch
  exist in each DC, with Host info collect on and the planned RT prefix. The RT prefix
  can't be changed after creation
  ([cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md#logical-routers-and-logical-switches)).
- MC-01 is configured on both border leaves of each DC, including the `VPC-LS-RT`
  `index 1` placeholder.
- The MDC manages both domain controllers, and the border leaves appear in its inventory
  as learned from them (ISSUE-03).
- The built-in VPC actions need a certificate and a DomainController third-party system
  for the controller they call
  ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#prerequisites-for-the-built-in-vpc-action-packages)).
  On the MDC, that means one system per domain controller, at its northbound floating IP;
  without it the VPC actions fail (ISSUE-01).
- Every built-in VPC and GND action has a `systemId` input. On the MDC it selects the
  domain controller, so each DC branch sets it to that DC's domain controller.

**Procedure**:

1. **Create two Smart CLI actions** for the `VPC-LS-RT` entry. No GND action covers the
   extended community filter. Huawei's preset template for a community filter,
   `filterCommunityRoute` (Smart CLI > Template Management > Default Template), is the
   guide: a Velocity body with an `#if` around the filter lines, `commit`, and matching
   rollback commands. A preset template can be published as a custom one and then edited
   ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#preset-templates-and-snd-packages)).
   1. Create an action package, for example `VPC_Subnet`, under Runbook > Resource
      Management > Action Package Management.
   2. Create two custom templates under Smart CLI > Template Management > Custom
      Template, or publish `filterCommunityRoute` as a custom template and replace its
      commands. Each uses vendor Huawei, the CE SND package, and package `VPC_Subnet`.
      Both take the variables `filterName`, `lsVni`, and `rtPrefix`.
   3. Publish the templates, then the package
      ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#creating-a-smart-cli-action)).

   | Action | Step kind | Purpose |
   |---|---|---|
   | `configVpcLsRt` | Delivery, with rollback commands | Writes the filter entry; rollback removes only that index |
   | `showVpcLsRt` | Delivery of a `display` command, no rollback | Pre-check: shows whether the filter entry exists |

   `configVpcLsRt` delivery commands:

   ```
   return
   system-view
   #set($rt = "${rtPrefix}:${lsVni}")
   ip extcommunity-filter basic ${filterName} index ${lsVni} permit rt ${rt}
   commit
   return
   ```

   `configVpcLsRt` rollback commands:

   ```
   return
   system-view
   undo ip extcommunity-filter basic ${filterName} index ${lsVni}
   commit
   return
   ```

   `showVpcLsRt` commands:

   ```
   return
   display current-configuration | include ${filterName} index ${lsVni} perm
   ```

   The command ends in `perm` on purpose. The step's output is assumed to include the
   command line itself, so the workflow tests the output for `permit rt`, which appears
   only in a matching configuration line. The space after the index keeps `6000` from
   matching `60001`. A detection-item step could check the output instead, but its
   failure on no match would stop the workflow rather than skip a step
   ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#templates)).

   Where this differs from the preset:
   - It writes `ip extcommunity-filter` (matching RTs), not `ip community-filter`, and it
     leaves the BGP EVPN peers and route-policy nodes alone, because MC-01 configures those
     once.
   - Its rollback names the index. The preset undoes the whole filter, which here would
     also remove the placeholder and the other subnets' entries.

2. **Define the input data type.** Each DC's input has to be its own block, because the
   pickers are chosen by field name. These rules were seen in the lab:

   | Rule | Consequence |
   |---|---|
   | Only a field named exactly `HW-switch` or `HW-router` gets the logical switch or logical router picker; a name such as `HW-switch1` gets none | Two switches can't sit side by side in one block |
   | The `HW-switch` and `HW-router` pickers appear only on an MDC deployment | |
   | iMaster NCE-Fabric identifies every object by UUID. The picker filters by fabric but returns only the selected object's UUID | The branch also needs the controller, so a separate `systemId` field is set to the same controller |
   | A field named `systemId` gets the system picker, and one whose name contains `ne-id` gets the device ID picker | |
   | A field whose name contains `ip` gets the device IP picker, which lists managed devices | `nexthop-ip` shows it too, but the FW isn't a managed device, so its address is typed in the field or imported |
   | Field names can't contain `.` | |

   Define one type under **Data Type**, for example `DCInput`:

   | Field | Type | Picker | Holds |
   |---|---|---|---|
   | `systemId` | string | System | The DC's domain controller |
   | `HW-router` | string | Logical router | The EXT logical router |
   | `HW-switch` | string | Logical switch | The new logical switch |
   | `rt-prefix` | integer | | 0 unless planned |
   | `bl1-ne-id` | string | Device | Border leaf 1 (ISSUE-06) |
   | `bl2-ne-id` | string | Device | Border leaf 2 |
   | `nexthop-ip` | string | Device IP (not used) | The FW `ext` address, `172.16.100.1` (DC1) / `172.16.200.1` (DC2) |

   Then add two inputs of that type, `DC1` and `DC2`, in the workflow's **Interface Info**.
   Each DC branch reads only its own block, for example `DC1.HW-switch`.

3. **Build the workflow** on the MDC with one branch per DC. The branches have no
   dependency on each other, so they run in parallel. Every action in a branch takes that
   DC's `systemId`. A step marked "per leaf" is placed once for each border leaf, each
   with its own device ID input, so each leaf shows as its own step in Execution Details.

   ```mermaid
   flowchart LR
       S([Start]) --> B1["DC1 branch<br/>systemId = DC1 controller"]
       S --> B2["DC2 branch<br/>systemId = DC2 controller"]
       B1 --> E([End])
       B2 --> E
   ```

   Each branch:

   ```mermaid
   flowchart LR
       W2[W2 querySubnetList] --> W4[W4 getRouteSets] --> W5["W5 addroute<br/>if no route"]
       W2 --> W6["W6 query prefix entry<br/>per leaf"] --> W7["W7 create prefix entry<br/>if outside 10/8 and missing"]
       W1[W1 queryLogicSwitch] --> W6
       W1 --> W8["W8 showVpcLsRt<br/>per leaf"] --> W9["W9 configVpcLsRt<br/>if entry missing"]
       W3[W3 getLogicRouter] --> W10["W10 query EXT VRF<br/>per leaf"] --> W11["W11 add import RT<br/>if missing"]
       W1 --> W10
   ```

   Every step also takes `DCx.systemId`. `blN-ne-id` is `bl1-ne-id` or `bl2-ne-id`,
   depending on the leaf.

   | Step | Does | Action | Inputs and their sources | Depends on | Runs when | Lab |
   |---|---|---|---|---|---|---|
   | W1 | Read the new switch | `l2l3app-logic-switchs` / `queryLogicSwitch` | `id` ← `DCx.HW-switch` | — | Always | Run |
   | W2 | Read its subnet | `l2l3app-subnets` / `querySubnetList` | `logicSwitchId` ← `DCx.HW-switch` | — | Always | Run |
   | W3 | Read the EXT router | `l2l3app-logic-routers` / `getLogicRouter` | `id` ← `DCx.HW-router` | — | Always | Run |
   | W4 | Look for the route | `l2l3app-logic-routers` / `getRouteSets` | `logicRouterId` ← `DCx.HW-router`; `destinations` ← [W2 CIDR] | W2 | Always | Run |
   | W5 | Add the EXT route | `l2l3app-logic-routers` / `addroute` | `id` ← `DCx.HW-router`; destination ← W2 CIDR; next hop ← `DCx.nexthop-ip`; condition ← W4 (table below) | W4 | W4 found no route set | Run, without the condition |
   | W6 | Check the prefix entry, per leaf | `gnd-ip-prefix-filter` / `query_…:ip-prefix-filter-nodes` | `ne-id` ← `DCx.blN-ne-id`; `node-sequence` ← W1 VNI | W1, W2 | Always | Run |
   | W7 | Add the prefix entry, per leaf | `gnd-ip-prefix-filter` / `create_…:ip-prefix-filter-nodes` | `ne-id` ← `DCx.blN-ne-id`; `node-sequence` ← W1 VNI; address and mask ← W2 CIDR; condition ← W6 | W6 | Outside `10.0.0.0/8` and W6 returned nothing | Run, without the 10/8 check |
   | W8 | Check the filter entry, per leaf | `VPC_Subnet` / `showVpcLsRt` | `neResId` ← `DCx.blN-ne-id`; `lsVni` ← W1 VNI; `rtPrefix` ← `DCx.rt-prefix` | W1 | Always | Not run |
   | W9 | Add the filter entry, per leaf | `VPC_Subnet` / `configVpcLsRt` | Same as W8; condition ← W8 output | W8 | W8's output has no `permit rt` | Not run |
   | W10 | Check the EXT import RT, per leaf | `gnd-vpn-instance` / `query_…:model-vpn-instance` | `ne-id` ← `DCx.blN-ne-id`; `vrf-name` ← W3 VRF name | W1, W3 | Always | Run |
   | W11 | Add the EXT import RT, per leaf | `gnd-vpn-instance` / `create_…:vpn-targets` | `ne-id` ← `DCx.blN-ne-id`; VRF name ← W3; `target-value` ← `DCx.rt-prefix` + W1 VNI; condition ← W10 | W10 | No entry in W10 with that RT | Run, without the condition |

   Each W-step source is reachable through **Depends on**: W7 reaches W1 and W2 through
   W6, W9 reaches W1 through W8, and W11 reaches W1 and W3 through W10.

   W5's attributes, as run in the lab. Everything not listed stays Unassigned (ISSUE-04):

   | Attribute | Value |
   |---|---|
   | `id` | `HW-router` |
   | `body.routeId` | A new UUID from the Blockly **get uuid** block |
   | `routeSetId` (root) | The same UUID, read back from `body.routeId` with **get property** on the step itself |
   | `body.source` | `Manual` |
   | `body.routes[0].destination` | W2's `subnetPagedDtoWrapper.subnet[0].cidr`, the network address (ISSUE-05) |
   | `body.routes[0].nexthopIp` | `DCx.nexthop-ip` |
   | `body.routes[0].nexthopType` / `addressFamilyType` | `Ip` / `Ipv4` |

   Use `addroute`, not `updateroute`. In the lab, `updateroute` replaces the whole route
   set it's given. The add, update, and delete actions return no output, so the new set's
   ID is only visible in W5's input.

   W6's and W7's attributes, per leaf. Assignment modes are as defined in
   [digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#workflow-components):

   | Attribute | W6 (query) | W7 (create) | Assignment |
   |---|---|---|---|
   | `model-ip-prefix-filter-af-type` | `ip` | `ip` | Constant Value |
   | `model-ip-prefix-filter-filter-name` | `VPC-HOST32` | `VPC-HOST32` | Constant Value |
   | `ne-id` | `DCx.bl1-ne-id` (or `bl2-ne-id`) | Same | From Process Input |
   | `systemId` | `DCx.systemId` | Same | From Process Input |
   | `node-sequence` | W1 VNI | `body.node-sequence` = W1 VNI | From Other Step Output |
   | `body.match-mode` | | `permit` | Constant Value |
   | `body.ip-addr` | | Address from W2 | Advanced Mode (JSON below) |
   | `body.mask-len` | | Mask from W2 | Advanced Mode (JSON below) |
   | `body.greater-equal` / `body.less-equal` | | `32` / `32` | Constant Value |

   W8's and W9's attributes, per leaf. A Smart CLI action takes an `neParams` list with one
   element per device. `neResId` is added to every Smart CLI action and names the target
   device; the other fields are the template's variables
   ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#creating-a-smart-cli-action)):

   | Attribute | Value | Assignment |
   |---|---|---|
   | `neParams[0].neResId` | `DCx.bl1-ne-id` (or `bl2-ne-id`), the same device ID as the GND steps' `ne-id` | From Process Input |
   | `neParams[0].filterName` | `VPC-LS-RT` | Constant Value |
   | `neParams[0].lsVni` | W1 VNI | From Other Step Output |
   | `neParams[0].rtPrefix` | `DCx.rt-prefix` | From Process Input |

   W10's and W11's attributes, per leaf:

   | Attribute | W10 (query) | W11 (create) | Assignment |
   |---|---|---|---|
   | `ne-id` | `DCx.bl1-ne-id` (or `bl2-ne-id`) | Same | From Process Input |
   | `systemId` | `DCx.systemId` | Same | From Process Input |
   | `vrf-name` / `model-vpn-instance-vrf-name` | W3 VRF name | Same | From Other Step Output |
   | `model-vpn-instance-afs-af-type` | | `ipv4-unicast` | Constant Value |
   | `body.target-af` | | `evpn` | Constant Value |
   | `body.target-type` | | `import-extcommunity` | Constant Value |
   | `body.target-value` | | `<rt-prefix>:<VNI>`, for example `100:6000` | Advanced Mode (**concatenate**) |

   W11 adds only that one target to the VRF the VPC service created. Its preview creates a
   single `extend-vpn-target` entry, and the CLI view shows one added line, `+ vpn-target
   … import-extcommunity evpn`. In the lab, W10 returned only targets added through
   GND, not the controller's own `0:<VNI>` targets, so the check looks for the new RT
   alone.

   Values for the other steps:

   | Value | Source | Notes |
   |---|---|---|
   | VNI | W1, `queryLogicSwitchDtoWrapper.switch[0].vni` | W6/W7 sequence, W8/W9 filter index, and the RT for W9/W11 |
   | Address and mask | W2, `subnetPagedDtoWrapper.subnet[0].cidr` | Split as shown below |
   | EXT VRF name | W3, `logicRoutersDtoWrapper.router[0].vrfName`, for W10/W11 | Matched the device's VPN instance name in the lab, for example `FI-R1_5000` for a logical router with VNI 5000 |
   | RT prefix | Workflow input | 0 unless planned; W1's path list doesn't offer it |
   | Device IDs, `systemId`, FW next hop | Workflow input | Constant per DC; device IDs as the MDC picker lists them for that DC's controller |

   **Address and mask (W7).** Enter these in the attribute's Advanced Mode as Blockly JSON,
   or build the same nesting from blocks. **str split** cuts the CIDR at `/`, and **json
   query** picks item `$[0]` (address) or `$[1]` (mask). The mask needs **to number** as the
   outer block (ISSUE-02). `nick_name` is the W2 step's name.

   `body.ip-addr`:

   ```json
   {"function":"json_query","flag":"single","path":"$[0]",
    "data":{"function":"str_split","separator":"/",
      "string_input":{"function":"get_attribute","nick_name":"querySubnetList",
        "path":"subnetPagedDtoWrapper.subnet[0].cidr","primary_key":null}}}
   ```

   `body.mask-len`:

   ```json
   {"function":"to_number","input_value":
     {"function":"json_query","flag":"single","path":"$[1]",
      "data":{"function":"str_split","separator":"/",
        "string_input":{"function":"get_attribute","nick_name":"querySubnetList",
          "path":"subnetPagedDtoWrapper.subnet[0].cidr","primary_key":null}}}}
   ```

   **W7's branch condition** (on the W6 → W7 line), without the 10/8 check, as run in the
   lab. `nick_name` is the W6 step's name:

   ```json
   {"function":"isEmpty","input_value":
     {"function":"get_attribute","nick_name":"query_gnd-ip-prefix-filter:ip-prefix-filter-nodes",
      "path":"body","primary_key":null}}
   ```

   - **Why the switch VNI:** the logical switch VNI is used, not the logical router's.
     All subnets of one VPC share the router's VNI, so a second subnet would find the
     first subnet's entry and be skipped. Switch VNIs are unique, and their range fits
     both the sequence and the index range (1-4294967295) [3]. The VNI pools start at
     5000, so a VNI never takes index 1 of `VPC-LS-RT` or index 10 of `VPC-HOST32`.
   - **Why W2 and not the switch's own subnet:** the logical switch's `subnets` field
     holds the gateway address, such as `192.168.1.1/24`. Both the route and the prefix
     entry need the network address.
   - **A step reads only steps it depends on.** From Other Step Output offers only steps
     that the current step depends on, directly or indirectly
     ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#workflow-components)).
     W11's RT needs the switch VNI from W1 and the VRF name from W3, so W10 depends on
     both. Likewise W6 depends on W1 and W2, and W7 and W9 reach them through W6 and W8.
   - **Each conditional step ends its chain.** When a branch condition is false, the step
     is skipped and the steps that depend on it don't run either. So W5, W7, W9, and W11
     have no steps after them, and W10/W11 depend on W1 and W3, not on W9. The import RT may
     therefore land before its `VPC-LS-RT` entry. That's safe: `EXT-IMPORT-EVPN` denies
     routes that no `VPC-LS-RT` entry matches, and the `index 1` placeholder keeps the
     filter in place (MC-01).
   - **Run conditions** are branch conditions on the line into each conditional step
     (W4 → W5, W6 → W7, W8 → W9, W10 → W11). Hover over the line and click the edit (hammer) icon to
     open Edit Branch Condition
     ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#workflow-components)).
     W7's condition, `is empty` on W6's `body`, worked in the lab. The rest are untested:
     - **W5:** `is empty` on W4's route-set list, assumed at
       `logicRouterRoutesListWrapper.routes`. An empty W4 result succeeded in the lab, and
       reading a field from it gave null rather than an error.
     - **W7, 10/8 check:** MC-01's `VPC-HOST32 index 10` already matches every host route
       in `10.0.0.0/8`, so only a subnet outside it needs its own entry. The condition
       is an **and** of two parts: "first octet of the address" (**split** on `.`, then
       **json query** `$[0]`) **!=** `10`, and the `is empty` test above
       ([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#blockly-function-blocks)).
     - **W9:** **not** on **string find** (W8's output, `permit rt`). The docs give
       string find a Boolean result.
       The output path is assumed to be `response.scriptList[0].stepRecordList[0].echo`;
       pick it from W8's Output tab after a first run.
     - **W11:** **is empty** on a **list filter** of W10's
       `body.model-vpn-instance-afs[0].vpn-targets`, with item path `target-value` **==**
       the RT.

4. **Prepare the input.** In each DC's block, pick `systemId` first, then `HW-router`,
   `HW-switch`, and the border leaves with that controller selected. Only `HW-switch` and,
   when planned, `rt-prefix` change from run to run, so export the input once and import
   it for each run:

   ```json
   {
     "DC1": {
       "systemId": "<DC1 domain controller system ID>",
       "HW-router": "<DC1 EXT logical router, picked on the MDC>",
       "HW-switch": "<DC1 new logical switch, picked on the MDC>",
       "rt-prefix": 0,
       "bl1-ne-id": "<Border1-1 device ID>",
       "bl2-ne-id": "<Border1-2 device ID>",
       "nexthop-ip": "172.16.100.1"
     },
     "DC2": { "...": "same fields for DC2" }
   }
   ```

5. **Run the workflow and check each border leaf.**

   ```
   display current-configuration | include VPC-LS-RT
   display current-configuration configuration vpn-instance <EXT VRF> | include import-extcommunity
   display current-configuration | include VPC-HOST32
   display ip routing-table vpn-instance <EXT VRF> <subnet>
   ```

6. **Run it again with the same input**, and compare Execution Details with the first
   run.
7. **Roll back the first run's instance** and repeat the procedure step 5 commands.
   Check that EXT still has its other routes.

**Expected result**:

| Procedure step | Expected |
|---|---|
| 5, first run | EXT's route list in iMaster NCE-Fabric shows the subnet toward the FW, and the border leaves route it to the FW. Each border leaf shows the new `VPC-LS-RT` index line and the `vpn-target … import-extcommunity evpn` line. A subnet outside `10.0.0.0/8` also gets its `VPC-HOST32` entry, for example `ip ip-prefix VPC-HOST32 index 6002 permit 192.168.242.0 24 greater-equal 32 less-equal 32`. TC-13 then passes for the new subnet |
| 6, rerun | W5, W7, W9, and W11 show as not run, and the configuration is unchanged |
| 7, rollback | The route set and the lines from procedure step 5 are gone. The `index 1` placeholder and the earlier subnets' entries and routes stay. This assumes `addroute`'s rollback removes the set it added. If it doesn't, a separate undo workflow runs `getRouteSets` and then `delroute` on the set it finds |

Observed in the lab, 2026-11:

| Steps | Result |
|---|---|
| W1–W5 | Succeeded in both DC branches in parallel once W5's attributes were set as above (ISSUE-04, ISSUE-05) |
| W6, W7 | A leaf that already had the sequence: W6 returned the entry, W7 showed 0%, and the workflow reached End |
| W6, W7 | A leaf without the filter: W6 succeeded with no output, and W7 created the filter and its entry in one step |
| Rollback | Removed the prefix entry and the filter that run had created |
| W10, W11 | On a logical router's VRF (`FI-R1_5000`), W11 added `vpn-target 10000:5000 import-extcommunity evpn` next to the controller's `0:5000` targets, and W10 then returned that one target. Before W11, W10 returned nothing for this VRF or for an external gateway's VRF |
| Rollback | Removed only the added target; the controller's RD and targets stayed |

Whether a target added through GND survives a later re-delivery of the logical router is
untested. Hand-entered configuration on the same VRF would be at greater risk.

**If it fails**:
- **A VPC action reports that third-party system interconnection isn't configured:**
  ISSUE-01.
- **A step fails with a type error, such as "string to number fail":** check the
  nesting of the Blockly blocks (ISSUE-02).
- **The device picker is empty, or a step reports that the device doesn't exist in the
  system:** the device IDs come from the wrong inventory (ISSUE-03).
- **A step fails with "require string, but null":** an attribute is mapped to an output
  that is empty (ISSUE-04).
- **`addroute` rejects the destination:** it is in gateway form (ISSUE-05).
- **W9 always runs, or never runs:** open W8's Output tab and check the output path and
  its text.
- **Host routes stop arriving in EXT after a rollback:** check that `VPC-LS-RT` still
  exists. A missing filter matches all routes [3].
- **The device and iMaster NCE-Fabric disagree after a manual change:** iMaster
  NCE-Fabric keeps its own record of GND-delivered configuration. Remove entries through
  the workflow's rollback rather than by hand, or resynchronize the device afterward.

## Issues encountered

### ISSUE-01: Built-in VPC actions fail on a domain controller

**Found in**: TC-16 (lab)

**Symptom**: Every built-in VPC action, such as `getLogicRouterlist`, fails with "Third-party
system interconnection is not configured." GND actions in the same workflow succeed.

**Root cause**: The built-in VPC action packages need a DomainController third-party
system for the controller they call. On the MDC, that system is each domain controller.
On a domain controller running the workflow itself, it is the controller's own
northbound floating IP
([digital-map-runbook.md](../vendor-matrix/huawei/digital-map-runbook.md#prerequisites-for-the-built-in-vpc-action-packages)).

**Fix**: Complete the four documented steps. Create a Third-party northbound user, import
the APIGWService certificate into mdcInterconnectionService, and create the
DomainController third-party system on port 18002.

**Verification**: Connection Status shows Online, and the VPC query steps succeed.

### ISSUE-02: Blockly expression fails with "string to number fail"

**Found in**: TC-16 (lab)

**Symptom**: The prefix-entry step fails while it builds `mask-len` from the subnet CIDR.

**Root cause**: The **to number** block sat in the **json query** block's path field,
so it tried to convert the path text `$[1]`.

**Fix**: Make **to number** the outer block and plug **json query** (path `$[1]`) into
it. The address uses the same json query with `$[0]` and no **to number**.

**Verification**: The step delivers the mask as a number, for example `24`.

### ISSUE-03: Device IDs differ between the MDC and the domain controller

**Found in**: TC-16 (lab)

**Symptom**: On the MDC, the device picker is empty once a domain controller is
selected. With the MDC's own device IDs and the domain controller's system ID, a GND step
fails because the device doesn't exist in that system.

**Root cause**: In the lab, the MDC's devices were added by hand rather than learned from
the domain controller. Each system therefore gave the same border leaf its own ID, and
the MDC had no devices listed for the domain controller.

**Fix**: Sync the devices to the MDC from the domain controller instead of adding them by
hand. Then pick the device IDs in the MDC picker with that domain controller selected,
and set the same domain controller's system ID on the branch.

**Verification**: With the domain controller selected, the MDC picker lists the border
leaves, and the GND steps succeed.

### ISSUE-04: A step fails with "require string, but null"

**Found in**: TC-16 (lab, W5)

**Symptom**: `addroute` stops early. The error names an input attribute, such as
`routeSetId`, and says a string was required but the value was null.

**Root cause**: The attribute was mapped to another step's output that came back empty.
EXT had no routes yet, so fields read from W4's or W3's route data were null, and the
workflow engine rejects a null before sending the request.

**Fix**: Map only the attributes in W5's table. Leave `body.routes[0].id` and
`body.routes[0].routeSetId` Unassigned, and give `body.routeId` and the root `routeSetId`
the same new UUID. The W4 result decides only whether W5 runs. It feeds no attribute.

**Verification**: W5 succeeds in both DC branches.

### ISSUE-05: `addroute` rejects the subnet in gateway form

**Found in**: TC-16 (lab, W5)

**Symptom**: `addroute` fails when the destination comes from the logical switch's
`subnets` field, such as `192.168.1.1/24`.

**Root cause**: The route destination has to be the network address. The logical switch
holds its gateway address instead.

**Fix**: Take the destination from W2, `querySubnetList` filtered by the logical switch,
which returns the network form such as `192.168.1.0/24`.

**Verification**: W5 succeeds, and EXT's route list shows the network address.

### ISSUE-06: The border leaves can't be found from the EXT logical router

**Found in**: TC-16 (lab, W3)

**Symptom**: The workflow needs each DC's border-leaf device IDs for the GND and Smart CLI
steps, but no step returns them. `getLogicRouter` on the EXT logical router lists only
the fabric under `routerLocations` (`fabricId`, `fabricName`), with no device group.

**Root cause**: EXT is a Normal logical router, and for it the router's location carries
no device group, so the border leaves can't be derived from it.

**Fix**: Make the border-leaf device IDs workflow inputs (`bl1-ne-id`, `bl2-ne-id` in the
DC data type). They stay the same from run to run, so they live in the exported input.

**Verification**: The GND steps reach both border leaves of each DC.

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
advertise-community (IPv4). Confirmed Nov. 12, 2026. For OR matching and index ranges: >
IP Routing > Routing Policy Configuration Commands > ip extcommunity-filter basic and ip
ip-prefix. Confirmed Nov. 18, 2026.

[4] "Cisco Secure Firewall Management Center Device Configuration Guide, 10.x," Cisco.
Verify in: Routing > Static and Default Routes (Add a static route; Routing tables > How
forwarding decisions are made), Routing > BGP (Configure basic BGP settings; Configure BGP
Neighbor Settings > Filtering Routes), Object Management > Prefix lists > Configure an IPv4
prefix list, and Access Control Rules (Default action behavior; security zone conditions).
https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/device-config/100/management-center-device-config-10-0.html
(chapters `routing-static.html`, `routing-bgp.html`, `objects-object-mgmt.html`,
`access-rules.html`). Confirmed Nov. 12, 2026.
