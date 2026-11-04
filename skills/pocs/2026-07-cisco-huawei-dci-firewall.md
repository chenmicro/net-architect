# POC: Cisco firewall service insertion in Huawei CloudFabric

## Background

- **Date**: ~2026-07
- **Scope**: Huawei CE M-LAG ↔ Cisco FW BGP peering (service insertion within a single fabric)
- **Scenario**:

## Test environment

### Topology

```
                     ┌──────────────────┐
                     │   Cisco FW       │
                     │   .1/29          │
                     │   (FW inside)    │
                     └────┬───┬────────┘
                          │   │  Eth-Trunk (M-LAG uplink)
                     ┌────┘   └────┐
                     ▼             ▼
               ┌──────────┐ ┌──────────┐
               │  CE-1    │ │  CE-2    │
               │  M-LAG   │ │  M-LAG   │
               │  owns .3 │ │  owns .4 │
               │  owns .2 │ │  owns .2 │
               └────┬─────┘ └────┬─────┘
                    │   peer-link │
                    └─────────────┘
               ┌──────────┐ ┌──────────┐
               │  Spine   │ │  Spine   │
               └────┬─────┘ └────┬─────┘
                    │             │
               ┌────┴─────────────┴───┐
               │    Tenant Leaf       │
               │    (VTEP)            │
               └──────────────────────┘
```

### Device list

| Role | Vendor | Model | Software version |
|---|---|---|---|
| Service leaf (M-LAG pair: CE-1, CE-2) | Huawei | CE6885 | V300R025C10, VRP V800 |
| Firewall (per-VRF BGP peering) | Cisco | ASA/FTD | |
| Spine | | | |
| Tenant Leaf (VTEP) | | | |

### Network plan

#### IP addressing (service leaf → FW link)

| Role | IP | Owner |
|---|---|---|
| Firewall inside interface | `172.16.100.1/29` | Cisco FW |
| VLANIF primary IP | `172.16.100.2/29` | Both CE-1 and CE-2 (same address) |
| CE-1 M-LAG IP (BGP source) | `172.16.100.3/29` | CE-1 only |
| CE-2 M-LAG IP (BGP source) | `172.16.100.4/29` | CE-2 only |

#### Tenant mapping

| Tenant | VNI | L3VNI | VRF | RT | CE VLAN | FW VLAN | Tenant subnet |
|---|---|---|---|---|---|---|---|
| Tenant-A | 10000 | 50000 | Tenant-A | 100:100 | 100 | 100 | 10.1.1.0/24 |
| Tenant-B | 20000 | 60000 | Tenant-B | 200:200 | 200 | 200 | 10.2.2.0/24 |

## Test cases

### TC-01: Underlay reachability

**Objective**:

**Prerequisites**:

**Procedure**:
```
# From CE-1 to FW
ping -vpn-instance Tenant-A 172.16.100.1

# From FW to both M-LAG IPs
ping vrf Tenant-A 172.16.100.3
ping vrf Tenant-A 172.16.100.4

# From Tenant Leaf to CE-1 (underlay)
ping <CE-1-underlay-IP> source loopback0
```

**Expected result**: All pings succeed with <1ms latency, no packet loss.

**If it fails**:
- MTU mismatch (ping with `-s 1472 -f`, then `-s 1500 -f`)

### TC-02: BGP peering

**Objective**: Validate BGP route exchange between Huawei CE M-LAG pair and Cisco FW over an M-LAG uplink.

**Prerequisites**: TC-01 passed.

**Procedure**:
```
# On CE-1 and CE-2
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1

# On FW
show bgp vpnv4 unicast vrf Tenant-A summary | include 172.16.100
```

**Expected result**: Two sessions in state `Established`, FW to `172.16.100.3` on CE-1 and FW to `172.16.100.4` on CE-2. Uptime increasing. No flaps.

**If it fails**:
- M-LAG IP or BGP source misconfiguration (see ISSUE-01)
- FW TCP normalization dropping SYN (see ISSUE-03)
- Wrong AS number or update-source

### TC-03: Route exchange (CE → FW direction)

**Objective**: Validate EVPN Type-5 → BGP redistribution: tenant host routes from fabric reach the FW.

**Prerequisites**: TC-02 passed.

**Procedure**:
```
# On FW — verify routes received from each member
show bgp vpnv4 unicast vrf Tenant-A neighbors 172.16.100.3 routes
show bgp vpnv4 unicast vrf Tenant-A neighbors 172.16.100.4 routes

# On FW — verify routing table
show route vrf Tenant-A
```

**Expected result**: FW sees tenant host routes (`10.1.1.0/24` or `/32` entries) via next-hops `172.16.100.3` and `172.16.100.4`.

**If it fails**:
- Missing `import-route evpn` on CE (see ISSUE-02)
- Route-policy filtering on the CE export side

### TC-04: Route exchange (FW → CE direction)

**Objective**: Validate return path: FW default route redistributes into EVPN Type-5 and reaches all fabric leaves.

**Prerequisites**: TC-03 passed.

**Procedure**:
```
# On CE-1
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1 received-routes

# On Tenant Leaf
display bgp evpn all routing-table | include 0.0.0.0/0
```

**Expected result**: CE-1 receives `0.0.0.0/0` from FW. Tenant Leaf installs the default route with CE-1's VTEP as next-hop.

**If it fails**:
- FW not advertising default route in BGP
- Missing `import-route bgp` under EVPN instance on CE (see ISSUE-04)

### TC-05: Ping across service chain

**Objective**:

**Prerequisites**: TC-04 passed.

**Procedure**:
```
# From a Tenant-A server
ping 172.16.100.1                          # FW inside interface
ping <internet-IP>                          # via FW + NAT
```

**Expected result**: Ping to FW succeeds. Ping to Internet succeeds (NAT translates source): Tenant server → FW → outside (NAT) → Internet → return.

**If it fails**:
- FW ACL blocking tenant subnet
- NAT pool not configured
- Next-hop mismatch in VRF routing table

### TC-06: TCP traffic through firewall

**Objective**:

**Prerequisites**: TC-05 passed.

**Procedure**:
```
# iperf3 test across the service chain
iperf3 -c <internet-test-server> -t 30
```

**Expected result**: Full throughput, no timeouts or retransmits.

**If it fails**:
- FW TCP inspection parameters

### TC-07: HA / M-LAG member failure

**Objective**: Validate M-LAG HA: traffic survives single CE member failure through the BGP session on the other member.

**Prerequisites**: TC-06 passed.

**Procedure**:
```
# Shut down CE-1's uplink to FW (or CE-1 entirely)
# Observe BGP state on remaining CE-2
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1

# Verify traffic continues
ping <internet-IP> from Tenant-A server
```

**Expected result**: The session to CE-1 goes down and the session to CE-2 stays `Established`. Zero or sub-second traffic interruption.

## Issues encountered

### ISSUE-01: BGP over M-LAG — SYN never completes

**Found in**: TC-02

**Symptom**: Issue on the firewall side. Huawei CE BGP state stuck in `Connect`. TCP
shows SYN sent but no SYN-ACK received.

**Root cause**: The firewall's BGP neighbor used the shared IP (`172.16.100.2`) instead of each member's M-LAG IP.

**Fix** (corrected against the CloudEngine V300R026C00 documentation, 2026-10; not
lab-tested): BGP over M-LAG uses a separate session to each member, on the VLANIF
interface for the M-LAG, with each member using its own M-LAG IP as the source [1].
Configure the same primary IP and virtual MAC on both members, a different M-LAG IP on
each, and routed proxy ARP. Peer the firewall with both M-LAG IPs [1].

```
# On CE-1 (on CE-2, use 172.16.100.4 as the M-LAG IP and BGP source)
interface Vlanif100
 ip binding vpn-instance Tenant-A
 ip address 172.16.100.2 255.255.255.248
 m-lag ip address 172.16.100.3 255.255.255.248
 mac-address 0000-5e00-0101
 arp proxy enable

bgp 65002
 ipv4-family vpn-instance Tenant-A
  peer 172.16.100.1 as-number 65010
  peer 172.16.100.1 connect-interface Vlanif100 172.16.100.3
```

```
# On Cisco FW — one neighbor per M-LAG member
router bgp 65010
 neighbor 172.16.100.3 remote-as 65002
 neighbor 172.16.100.3 description "Huawei-MLAG-CE-1"
 neighbor 172.16.100.3 update-source Vlan100
 neighbor 172.16.100.4 remote-as 65002
 neighbor 172.16.100.4 description "Huawei-MLAG-CE-2"
 neighbor 172.16.100.4 update-source Vlan100
```

If BGP imports direct routes, add a routing policy so the M-LAG IPs aren't
advertised [1]. The CE6885 is on the supported model list for `m-lag ip address` [1].

**Verification**: Run `display bgp peer` on both members [1], then repeat TC-02.

### ISSUE-02: BGP established but no routes on FW

**Found in**: TC-03

**Symptom**: BGP session is `Established`. FW `show bgp vpnv4 vrf Tenant-A
neighbors 172.16.100.3 routes` returns empty.

**Root cause**: The Huawei CE didn't have `import-route evpn` configured under
`ipv4-family vpn-instance Tenant-A`. EVPN Type-5 routes exist in the VRF's EVPN
table but are never redistributed into BGP toward the FW.

**Fix**:
```
bgp 65002
 ipv4-family vpn-instance Tenant-A
  peer 172.16.100.1 as-number 65010
  import-route evpn
```

**Verification**:
```
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1 advertised-routes
→ shows tenant routes (was empty before fix)
```

### ISSUE-03: FW TCP normalization drops BGP SYN

**Found in**: TC-02

**Symptom**: `capture capin` on FW shows SYN arriving from CE, but FW doesn't
reply. No ACL deny logged.

**Root cause**: ASA/FTD TCP stateful inspection drops the BGP SYN.

**Fix**:
```
access-list BGP-BYPASS extended permit tcp host 172.16.100.1 host 172.16.100.3 eq bgp
access-list BGP-BYPASS extended permit tcp host 172.16.100.1 host 172.16.100.4 eq bgp
class-map BGP-CLASS
  match access-list BGP-BYPASS
policy-map GLOBAL-POLICY
  class BGP-CLASS
    no inspect tcp
```

**Verification**:

### ISSUE-04: Firewall default route not advertised to fabric

**Found in**: TC-04

**Symptom**: FW sends `0.0.0.0/0` to CE. CE receives it. Tenant Leaf doesn't
install it.

**Root cause**: CE receives BGP route from FW but doesn't redistribute it into
EVPN Type-5. `import-route evpn` is one-directional (EVPN→BGP only).

**Fix**:
```
bgp 65002 instance evpn1
 ipv4-family vpn-instance Tenant-A
  import-route bgp
```

**Verification**:
```
display bgp evpn all routing-table | include 0.0.0.0/0
→ shows default route with CE's VTEP as next-hop
```

## Conclusion

## References

[1] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation,"
Huawei, V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login required). Verify in:
Configuration > Configuration Guide > High Availability Configuration > M-LAG
Configuration > Configuring a Dynamic Routing Protocol for Communication with an M-LAG >
Configuring BGP or BGP4+ over M-LAG; Configuration > Typical Configuration Examples >
Multi-Feature Configuration Examples > Example for Configuring Dynamic Routing Protocols
for Communication with an M-LAG (applies to V300R020C00 or later); References > Command
Reference > High Availability > M-LAG Configuration Commands > m-lag ip address.
Confirmed Oct. 31, 2026.
