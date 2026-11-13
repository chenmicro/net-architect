# Huawei HiSecEngine USG Firewalls

**Scope: HiSecEngine USG6000F and USG6000G, V600R026C00** [1]. This file records what the
product documentation says about two-device hot standby and the inter-DC cluster. See the
[Huawei hub](huawei.md) for other product lines.

## Version and models

V600R026C00 covers these series and models [1]:

| Series | Models |
|---|---|
| USG6000F-E | USG6000F-E06-D, USG6000F-E06-DL, USG6000F-E12-D |
| USG6500F | USG6510F-D, USG6510F-DL, USG6510F-DPL, USG6525F, USG6530F-D, USG6530F-DL, USG6530F-DPL, USG6555F, USG6560F-D, USG6565F, USG6585F, USG6585F-B |
| USG6600F | USG6615F, USG6625F, USG6635F, USG6636F, USG6655F, USG6656F, USG6685F, USG6686F |
| USG6700F | USG6710F, USG6715F, USG6725F |
| USG6500G | USG6505G-D, USG6550G-D, USG6550G-D5G, USG6550G-DP, USG6550G-DP5G, USG6570G-D, USG6590G-D |
| USG6800G | USG6855G, USG6875G, USG6885G |

All of these support hot standby. Only the USG6600F, USG6700F and USG6800G series support
the inter-DC cluster [1].

## Hot standby

Hot standby is between two devices [1]:

- **What is shared:** the two devices back up status entries, so the peer can process packets
  after a switchover without the client reconnecting. They also back up configuration and run a
  consistency check on key configuration such as security policies and NAT [1].
- **Steering traffic:** hot standby uses the device priority to change VRRP group state, VLAN
  state or dynamic-route costs, which steers upstream and downstream devices to the active
  device [1].
- **Virtual systems:** hot standby works only between two physical devices, never between two
  virtual systems [1].

### Working modes

| Mode | Behaviour |
|---|---|
| Active/standby | The active device processes all traffic and the standby takes over on failure [1] |
| Load sharing | Both devices process traffic and back each other up [1] |
| Mirroring | An active/standby variant used mainly in CloudFabric data center networks [1] |

In load sharing mode [1]:

- Content security functions such as intrusion prevention and antivirus may fail, because
  forward and return traffic can take different devices.
- NAT needs extra configuration so the two devices don't allocate conflicting addresses. In
  NAT No-PAT mode, `nat resource load-balance enable` makes one device allocate addresses and
  ports for both.
- If one device or its link fails, its priority drops and the pair falls back to
  active/standby.

### Heartbeat link

The two devices exchange Huawei Redundancy Protocol (HRP) packets over heartbeat interfaces:
hellos every 1 s by default, configuration and entry backups, link detection, and
configuration consistency checks. Security policies don't apply to these packets [1].

- **Interfaces:** up to 16 heartbeat interfaces, but only one carries traffic other than
  link detection at a time [1].
- **Placement:** Huawei advises installing the two devices in the same or adjacent racks and
  connecting the heartbeat interfaces directly [1].
- **Bandwidth:** at least 20% of the service interface bandwidth, because entry backup scales
  with service traffic [1].
- **MTU:** at least 1500 bytes on every interface the HRP packets cross, because backup packets
  are up to 1500 bytes and can't be fragmented [1].
- **Heartbeat escape:** if every heartbeat interface fails, `hrp escape enable` sends hellos
  over other interfaces so both devices don't become active. Huawei states escape is not
  guaranteed to succeed [1].

### Licences

Hot standby itself needs no licence. Licensed functions such as IPS and antivirus aren't
shared: both devices need their own licences with the same control items, quantities and
expiry [1].

### IPsec with hot standby

- **Active/standby:** the two devices form a VRRP group and the IPsec tunnel ends on the
  group's virtual address. If the active device or its link fails, the standby processes the
  traffic and the tunnel isn't torn down [1].
- **Load balancing:** documented for LTE base-station scenarios: independent tunnels to each
  device, or active and standby tunnels per peer [1].
- **Configuration:** apply the IPsec policy or profile on the active device so it's backed up
  to the standby. With `alone`, a policy or profile isn't backed up [1].

## Inter-DC cluster

The inter-DC cluster links firewall pairs in different data centers so that a pair can process
traffic switched from another DC. It can do this because it already holds that DC's service
entries [1].

- **Cluster:** two devices in hot standby, in active/standby or mirroring mode [1].
- **Cluster group:** several clusters working together; each is the others' peer cluster [1].
- **What's shared across clusters:** only service entries, never configuration [1].
  - Within a cluster, HRP backs up configuration and entries.
  - Across clusters, the Huawei Redundancy Session Protocol (HRSP) runs between the active
    devices.
  - The new active device of a cluster re-synchronizes its entries to the peer cluster's
    active device after a failover.

### Network requirements

| Requirement | Detail |
|---|---|
| Hardware | Every device in a cluster group is the same model [1] |
| Software | Same software and patch versions, except during an upgrade [1] |
| Mode | Routing mode only [1] |
| DCI latency | Under 10 ms between DCs [1] |
| Cluster channels | Private lines across equipment rooms; never through GRE, IPsec or other encrypted tunnels; separated from service traffic on the DCI, e.g. by VLAN; full mesh recommended [1] |
| MTU | At least 1500 bytes on every interface cluster packets cross [1] |
| Heartbeat interface | Fixed IP addresses (no PPPoE or DHCP); dedicated, not a management or service interface; Layer 3 Ethernet, Eth-Trunk (recommended) or VLANIF [1] |
| Consistency | Same interface types, numbers, VLAN IDs and security zones on every member; same hash-based CPU selection mode and hash factors; same system time and clock source [1] |
| Configuration | Firewalls across DCs don't run a cluster management protocol, so a controller must keep service configuration consistent [1] |
| Licences | Not shared; each member needs its own, with matching resources [1] |

### Asymmetric paths between clusters

The cluster group tolerates forward and return traffic crossing different clusters, within
limits [1]:

- **Session backup timing:** by default a TCP session is backed up only after the three-way
  handshake, so a SYN-ACK that reaches the other cluster first is dropped.
  - `cluster group sync session fast enable` backs up a session at the SYN, or at the first
    UDP or ICMP request.
  - `firewall session sync-enhance` delays SYN-ACK processing until the backup has arrived.
  - Within one cluster, `hrp mirror session enable` does the same for the two devices.
- **Link-state check:** where forward and return paths differ between members, turn it off
  (`undo firewall session link-state check`) so a cluster heartbeat outage doesn't drop
  traffic.
- **Features that need the same path both ways:** IPsec, SSL VPN, SLB layer-7 sessions,
  health check, TCP proxy, SSL proxy, email proxy and content security fail or are
  interrupted otherwise.
- **Cost:** fast session backup raises CPU load and heartbeat-interface bandwidth.

### Feature support in a cluster

- **NAT:** NAT PAT, No-PAT, NAT Server, destination NAT and bidirectional NAT are supported
  and rely on session backup between clusters. With PAT, give each cluster its own address
  pool if traffic is diverted between clusters. Three-tuple NAT isn't supported [1].
- **L3VPN:** IPv4 and IPv6 L3VPN aren't supported [1].

### Steering traffic between clusters

Two documented ways to make upstream and downstream devices move traffic to the peer cluster
when a cluster is unavailable [1]:

- **Service availability probe:** neighbours ping a probe IP on the cluster and use
  policy-based routing to switch. The cluster drops the pings while it's unavailable, for
  example during the first batch backup or a CPU fault.
- **Dynamic routes:** the cluster raises its route cost or MED while unavailable.

## References

[1] "HiSecEngine USG6000F, USG6000G Product Documentation," Huawei, V600R026C00, Issue 01,
Sep. 30, 2026 (HedEx library EDOC1100605493, login required). Verify in:
- models: Required Software Versions > Product Models;
- hot standby: Configuration > Configuration Guide > High Availability Configuration > Hot
  Standby Configuration > Overview of Hot Standby; > Understanding Hot Standby > Heartbeat
  Link; > Hot Standby Working Modes and Device Roles; > Configuration Precautions for Hot
  Standby;
- IPsec: Configuration > Configuration Guide > VPN Configuration > IPsec Configuration >
  Understanding IPsec > IPsec Enhancements > Understanding IPsec Hot Standby;
- inter-DC cluster: Configuration > Configuration Guide > High Availability Configuration >
  Inter-DC Cluster Configuration > Overview of the Inter-DC Cluster; > Understanding the
  Inter-DC Cluster > Basic Concepts, Cluster Heartbeat Interface, Cluster Networking, Status
  Information Backup > Session Backup When Forward and Return Paths Are Different, Cluster
  Traffic Diversion > Traffic Diversion Between Clusters, Feature List; > Configuration
  Precautions for CSS.

Confirmed Nov. 13, 2026.
