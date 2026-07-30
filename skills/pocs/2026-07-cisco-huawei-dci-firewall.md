# POC: Cisco firewall service insertion in Huawei CloudFabric

## Metadata

| Field | Value |
|---|---|
| **Date** | ~2026-07 |
| **Scope** | Huawei CE M-LAG ↔ Cisco FW BGP peering (service insertion within a single fabric) |
| **Huawei side** | CloudEngine 8800 M-LAG pair (service leaf), V300R025C10, VRP V800 |
| **Firewall** | Cisco ASA/FTD (per-VRF BGP peering) |

---

## 1. Testing Targets

### Objectives

1. Validate BGP route exchange between Huawei CE M-LAG pair and Cisco FW over an M-LAG uplink
2. Validate EVPN Type-5 → BGP redistribution: tenant host routes from fabric reach the FW
3. Validate M-LAG HA: BGP session survives single CE member failure via shared anycast IP
4. Validate return path: FW default route redistributes into EVPN Type-5 and reaches all fabric leaves

### Success criteria

| Criterion | Pass condition |
|---|---|
| BGP peering | `Established` on both CE-1 and CE-2 via anycast IP |
| Route advertisement (C→F) | FW receives tenant host routes (`10.1.1.0/24`) from CE |
| Route advertisement (F→C) | CE receives `0.0.0.0/0` from FW |
| EVPN Type-5 propagation | Tenant Leaf installs default route with CE's VTEP as next-hop |
| Ping across service chain | Tenant server → FW inside interface succeeds |
| Internet egress | Tenant server → FW → outside (NAT) → Internet → return |
| HA / M-LAG member failure | Pull CE-1: BGP stays up via CE-2, traffic continues |

---

## 2. Testing Environment

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

### IP addressing (service leaf → FW link)

| Role | IP | Owner |
|---|---|---|
| Firewall inside interface | `172.16.100.1/29` | Cisco FW |
| Shared anycast (BGP peer IP) | `172.16.100.2/29` | Both CE-1 and CE-2 |
| CE-1 individual M-LAG IP | `172.16.100.3/29` | CE-1 only |
| CE-2 individual M-LAG IP | `172.16.100.4/29` | CE-2 only |

### Tenant mapping

| Tenant | VNI | L3VNI | VRF | RT | CE VLAN | FW VLAN | Tenant subnet |
|---|---|---|---|---|---|---|---|
| Tenant-A | 10000 | 50000 | Tenant-A | 100:100 | 100 | 100 | 10.1.1.0/24 |
| Tenant-B | 20000 | 60000 | Tenant-B | 200:200 | 200 | 200 | 10.2.2.0/24 |

---

## 3. Testing Steps

Each step has a pass/fail gate. Do not proceed to the next step until the current one passes.

### Step 1: Underlay reachability

**Action**:
```
# From CE-1 to FW
ping -vpn-instance Tenant-A 172.16.100.1

# From FW to shared anycast
ping vrf Tenant-A 172.16.100.2

# From Tenant Leaf to CE-1 (underlay)
ping 172.16.100.3 source loopback0
```

**Expected**: All pings succeed with <1ms latency, no packet loss.

**Troubleshooting if fails**:
- Sub-interface VLAN mismatch (see Issue 3)
- MTU mismatch (ping with `-s 1472 -f`, then `-s 1500 -f`)

### Step 2: BGP peering

**Action**:
```
# On CE-1
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1

# On FW
show bgp vpnv4 unicast vrf Tenant-A summary | include 172.16.100.2
```

**Expected**: State = `Established`. Uptime increasing. No flaps.

**Troubleshooting if fails**:
- M-LAG anycast IP misconfiguration (see Issue 1)
- FW TCP normalization dropping SYN (see Issue 4)
- Wrong AS number or update-source

### Step 3: Route exchange (FW → CE direction)

**Action**:
```
# On FW — verify routes received
show bgp vpnv4 unicast vrf Tenant-A neighbors 172.16.100.2 routes

# On FW — verify routing table
show route vrf Tenant-A
```

**Expected**: FW sees tenant host routes (`10.1.1.0/24` or `/32` entries) via next-hop `172.16.100.2`.

**Troubleshooting if fails**:
- Missing `import-route evpn` on CE (see Issue 2)
- Route-policy filtering on the CE export side

### Step 4: Route exchange (CE → FW direction)

**Action**:
```
# On CE-1
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1 received-routes

# On Tenant Leaf
display bgp evpn all routing-table | include 0.0.0.0/0
```

**Expected**: CE-1 receives `0.0.0.0/0` from FW. Tenant Leaf installs the default route with CE-1's VTEP as next-hop.

**Troubleshooting if fails**:
- FW not advertising default route in BGP
- Missing `import-route bgp` under EVPN instance on CE (see Issue 6)

### Step 5: Ping across service chain

**Action**:
```
# From a Tenant-A server
ping 172.16.100.1                          # FW inside interface
ping <internet-IP>                          # via FW + NAT
```

**Expected**: Ping to FW succeeds. Ping to Internet succeeds (NAT translates source).

**Troubleshooting if fails**:
- FW ACL blocking tenant subnet
- NAT pool not configured
- Next-hop mismatch in VRF routing table

### Step 6: TCP traffic through firewall

**Action**:
```
# iperf3 test across the service chain
iperf3 -c <internet-test-server> -t 30
```

**Expected**: Full throughput, no timeouts or retransmits.

**Troubleshooting if fails**:
- MTU fragmentation (see Issue 5)
- FW TCP inspection parameters
- MSS clamping needed on both sides

### Step 7: HA / M-LAG member failure

**Action**:
```
# Shut down CE-1's uplink to FW (or CE-1 entirely)
# Observe BGP state on remaining CE-2
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.1

# Verify traffic continues
ping <internet-IP> from Tenant-A server
```

**Expected**: BGP session stays `Established` via CE-2 (the shared anycast IP moves). Zero or sub-second traffic interruption.

---

## 4. Issues Encountered

### Issue 4.1: BGP over M-LAG — SYN never completes

**Symptom**: Huawei CE BGP state stuck in `Connect`. TCP shows SYN sent but no
SYN-ACK received.

**Root cause**: The firewall's BGP neighbor was configured pointing at one of the
**individual M-LAG member IPs** (`172.16.100.3` or `172.16.100.4`) instead of the
**shared anycast IP** (`172.16.100.2`) that both M-LAG members own. When the
firewall's uplink hashed to the other CE, that CE didn't own the individual IP
→ dropped SYN without reply.

**Topology**:
```
          ┌──────────────┐
          │  Cisco FW    │
          │  .1          │
          │  neighbor: .3│  ← individual CE-1 IP, wrong!
          └──┬────────┬──┘
             │        │
       ┌─────┘        └─────┐
       ▼                     ▼
  ┌──────────┐         ┌──────────┐
  │ CE-1     │         │ CE-2     │
  │ owns .3  │         │ doesn't  │
  │ sends SYN│         │ own .3   │
  │          │         │ → DROP   │
  └──────────┘         └──────────┘
```

**Fix**:
```
# On both CE-1 and CE-2 — shared anycast loopback
interface LoopBack100
 ip address 172.16.100.2 255.255.255.248

bgp 65002
 peer 172.16.100.1 as-number 65010
 peer 172.16.100.1 connect-interface LoopBack100
 peer 172.16.100.1 ebgp-max-hop 2
```

```
# On Cisco FW — peer with .2 (shared anycast)
router bgp 65010
 neighbor 172.16.100.2 remote-as 65002
 neighbor 172.16.100.2 description "Huawei-MLAG-anycast"
 neighbor 172.16.100.2 update-source Vlan100
```

**Note**: The anycast IP `.2` must be advertised into the underlay routing
protocol (OSPF/IS-IS) from both CE-1 and CE-2 so the FW sees it reachable
via ECMP to both members.

---

### Issue 4.2: BGP established but no routes on FW

**Symptom**: BGP session is `Established`. FW `show bgp vpnv4 vrf Tenant-A
neighbors 172.16.100.2 routes` returns empty.

**Root cause**: The Huawei CE didn't have `import-route evpn` configured under
`ipv4-family vpn-instance Tenant-A`. EVPN Type-5 routes exist in the VRF's EVPN
table but are never redistributed into BGP toward the FW.

**Fix**:
```
bgp 65002
 ipv4-family vpn-instance Tenant-A
  peer 172.16.100.2 as-number 65010
  import-route evpn
```

**Verification**:
```
display bgp vpnv4 vpn-instance Tenant-A peer 172.16.100.2 advertised-routes
→ shows tenant routes (was empty before fix)
```

---

### Issue 4.3: Sub-interface VLAN mismatch

**Symptom**: Ping from CE to FW in the same VRF fails. `display ip interface
brief` shows the sub-interface is up/up.

**Root cause**: Huawei CE sub-interface configured with `vlan-type dot1q 100`
but the Cisco FW sub-interface expects `dot1q 200`.

**Fix**: Match VLAN IDs on both sides:
```
# CE: VLAN 100
interface 100GE1/0/1.100
 vlan-type dot1q 100

# FW: VLAN 100
interface GigabitEthernet0/1.100
 vlan 100
```

---

### Issue 4.4: FW TCP normalization drops BGP SYN

**Symptom**: `capture capin` on FW shows SYN arriving from CE, but FW doesn't
reply. No ACL deny logged.

**Root cause**: ASA/FTD TCP stateful inspection drops the BGP SYN.

**Fix**:
```
access-list BGP-BYPASS extended permit tcp host 172.16.100.1 host 172.16.100.2 eq bgp
class-map BGP-CLASS
  match access-list BGP-BYPASS
policy-map GLOBAL-POLICY
  class BGP-CLASS
    no inspect tcp
```

---

### Issue 4.5: MTU fragmentation through the service chain

**Symptom**: BGP establishes, ping works (small packets). TCP iperf stalls.

**Root cause**: VXLAN adds 50 bytes. Link MTU is 1500. Encapsulated packets
fragment; FW stateful inspection drops fragments.

**Fix**:
```
# Increase link MTU
interface 100GE1/0/1
 mtu 9216

# TCP MSS clamping on both sides
interface Vlanif100
 tcp mss 1400
```

---

### Issue 4.6: Firewall default route not advertised to fabric

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

---

## References

[1] "Example for Configuring Segment VXLAN to Implement Layer 2 Interworking (Local VNI Mode)," CloudEngine 16800 Series Typical Configuration Examples, Huawei. [Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1000039339/6c964738/example-for-configuring-segment-vxlan-to-implement-layer-2-interworking-local-vni-mode

[2] "M-LAG Configuration Guide," CloudEngine 8800 V300R025C10, Huawei. [Online]. Available: https://support.huawei.com/enterprise/en/switches/cloudengine-8800-pid-252837183

[3] "ASA/FTD BGP Configuration Guide," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/support/security/asa-5500-series-next-generation-firewalls/products-installation-and-configuration-guides-list.html
