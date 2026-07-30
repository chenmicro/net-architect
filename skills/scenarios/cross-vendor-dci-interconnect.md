# Cross-vendor DCI: Cisco ↔ Huawei CloudFabric

Interconnect a Cisco fabric (either **ACI** or **NX-OS EVPN-VXLAN**) with a
Huawei CloudFabric (iMaster NCE-managed, EVPN-VXLAN) over an Inter-Site
Network. Two variants with very different Cisco-side complexity:

- **[Variant A: ACI BGW](#variant-a-aci-bgw)** — requires ACI 6.1(x)+ and a
  dedicated ACI Border Gateway translation layer
- **[Variant B: NX-OS EVPN Multi-Site](#variant-b-nx-os-evpn-multi-site)** —
  native MP-BGP EVPN, dramatically simpler

## Variant A: ACI BGW

### Composition

1. **[vendor-matrix/cisco/aci.md](../vendor-matrix/cisco/aci.md#aci-border-gateway-heterogeneous-fabric-interconnect)**
   — ACI BGW architecture, addressing (MS-Ext-VIP / MS-Int-VIP / PIP),
   control and data plane flow, namespace normalization, supported topologies
   by ACI release, policy enforcement across fabrics.

2. **[vendor-matrix/huawei.md](../vendor-matrix/huawei.md#dci-and-cross-vendor-interconnect)**
   — Huawei-side Segment VXLAN mode, CloudEngine DCI gateway roles.

3. **[techniques/evpn.md](../techniques/evpn.md)**, **[vxlan.md](../techniques/vxlan.md)**,
   **[bgp.md](../techniques/bgp.md)**, **[multi-tenancy.md](../techniques/multi-tenancy.md)**
   — shared protocol fundamentals.

### Cross-cutting judgment

- **VNI namespace**: ACI auto-assigns VNIDs; CloudEngine must use matching
  VNIs or wait for ACI 6.1(4)+ namespace normalization.
- **Policy**: No translation possible — ACI contracts ≠ Huawei ACLs.
- **Split ops**: ACI operator + VRP operator.
- **Procurement**: Huawei restrictions may limit where CloudFabric can sit.

### Fallbacks

VRF-lite handoff, VLAN trunk, or insert NX-OS as a middle layer.

## Variant B: NX-OS EVPN Multi-Site

NX-OS already speaks native MP-BGP EVPN — its **EVPN Multi-Site** feature
(available since NX-OS 7.0(3)I7(1), 2017) peers directly with any standards-
compliant BGW [1]. No translation layer, no version dependency beyond basic
EVPN support, no special hardware constraints. The CloudFabric side is
identical to Variant A.

### Composition

1. **[vendor-matrix/cisco/nxos-vxlan.md](../vendor-matrix/cisco/nxos-vxlan.md)**
   — NX-OS EVPN-VXLAN fundamentals, release history, Multi-Site support.

2. **[vendor-matrix/huawei.md](../vendor-matrix/huawei.md#dci-and-cross-vendor-interconnect)**
   — Huawei-side Segment VXLAN mode, CloudEngine DCI gateway roles.

3. **[techniques/evpn.md](../techniques/evpn.md)**, **[vxlan.md](../techniques/vxlan.md)**,
   **[bgp.md](../techniques/bgp.md)**, **[multi-tenancy.md](../techniques/multi-tenancy.md)**
   — shared protocol fundamentals.

### Cross-cutting judgment

- **VNI namespace**: Fully under your control — configure matching VNIs on
  both sides. No auto-assignment conflict.
- **Policy**: No cross-vendor policy — standard EVPN route filtering on both
  sides. NX-OS GPO microsegmentation is Cisco-specific but not required for
  basic DCI.
- **Split ops**: NX-OS operator + VRP operator — but both sides speak the
  same protocol (BGP EVPN), so troubleshooting the DCI itself is uniform.
- **Management planes**: NDFC (Cisco) + iMaster NCE — independent but no
  translation layer complexity.

### Configuration example: NX-OS 10.6(3)F BGW → CloudEngine V300R025C10 DCI GW

This is the actual CLI from the Cisco 10.6(x) EVPN Multi-Site Config Guide [1]
and the Huawei Segment VXLAN example [2].

#### NX-OS BGW (anycast mode)

```cisco
! --- Underlay to ISN ---
interface Ethernet1/1
  no switchport
  ip address 192.168.100.1/30
  ip pim sparse-mode
  evpn multisite dci-tracking    ! mandatory on DCI-facing links

! --- Loopbacks ---
interface Loopback0
  ip address 10.0.0.1/32          ! router-id
interface Loopback1
  ip address 10.255.0.1/32        ! NVE source (PIP)
interface Loopback100
  ip address 192.0.2.1/32          ! Multi-Site anycast VIP
  ip pim sparse-mode

! --- EVPN Multi-Site ---
evn multisite border-gateway 100
  dci-interface Loopback100
  remote-vtep 203.0.113.1          ! CloudEngine DCI GW anycast IP

! --- NVE / VXLAN ---
interface nve1
  no shutdown
  source-interface Loopback1
  host-reachability protocol bgp
  multisite border-gateway interface Loopback100
  member vni 10000
    mcast-group 239.1.1.1
  member vni 10000 associate-vrf

! --- BGP EVPN to CloudFabric ---
router bgp 65001
  neighbor 203.0.113.1 remote-as 65002
  neighbor 203.0.113.1 update-source Loopback100
  address-family l2vpn evpn
    send-community extended
    send-community large
    activate
```

#### CloudEngine DCI GW (Segment VXLAN)

```
# --- Underlay to ISN ---
interface 10GE1/0/1
  undo portswitch
  ip address 192.168.200.2 255.255.255.0
  ospf 1 area 0.0.0.0

# --- Loopbacks ---
interface LoopBack1
  ip address 203.0.113.1 255.255.255.255  ! DCI GW anycast IP
  ospf 1 area 0.0.0.0
interface LoopBack2
  ip address 10.255.0.2 255.255.255.255   ! NVE source (VTEP)

# --- EVPN / VXLAN basic enable ---
evn-overlay enable

# --- Bridge domain for stretched tenant (L2VNI 10000) ---
bridge-domain 10
  vxlan vni 10000
  evpn
    route-distinguisher 100:1
    vpn-target 100:100 export-extcommunity
    vpn-target 100:100 import-extcommunity

# --- Tenant-facing interface ---
interface 10GE1/0/2.1 mode l2
  encapsulation dot1q vid 10
  bridge-domain 10

# --- NVE ---
interface Nve1
  source 10.255.0.2
  vni 10000 head-end peer-list protocol bgp

# --- BGP EVPN to NX-OS ---
bgp 65002 instance evpn1
  peer 192.0.2.1 as-number 65001
  peer 192.0.2.1 connect-interface LoopBack1
  l2vpn-family evpn
    policy vpn-target
    peer 192.0.2.1 enable
```

#### What must match

| Parameter | NX-OS | CloudEngine |
|---|---|---|
| **VNI** | `member vni 10000` | `vxlan vni 10000` |
| **BGP ASN** | 65001 | 65002 |
| **Peer IP** | `neighbor 203.0.113.1` | `peer 192.0.2.1` |
| **Anycast GW MAC** | Same vMAC on all leaves | Same vMAC on all leaves |
| **Route targets** | Per VRF/BD | `vpn-target 100:100` |

## References

[1] "Configure VXLAN EVPN Multi-Site," Cisco Nexus 9000 Series NX-OS VXLAN
Configuration Guide, Release 10.6(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/vxlan/
cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-106x/
m_configuring_multisite_93x.html

[2] "Example for Configuring Segment VXLAN to Implement Layer 2 Interworking
(Local VNI Mode)," CloudEngine 16800 Series Typical Configuration Examples,
Huawei. [Online]. Available:
https://support.huawei.com/enterprise/en/doc/EDOC1000039339/6c964738/
example-for-configuring-segment-vxlan-to-implement-layer-2-interworking-local-vni-mode

ACI BGW-specific references: see [aci.md](../vendor-matrix/cisco/aci.md#references).
