# First-Hop Redundancy Protocol (FHRP)

- FHRPs provide a virtual default-gateway IP/MAC shared across two or more
  physical routers — one router forwards while the other(s) standby, so hosts
  configured with a single default gateway survive a router failure.

## The three FHRPs

| Protocol | Standard | Owner | How it works |
|---|---|---|---|
| **VRRP** (v2/v3) | RFC 5798 (v3) [1] | Open — every major vendor | One master, one or more backups. Master owns the virtual IP and answers ARP for the virtual MAC. Preemption optional. |
| **HSRP** | Cisco proprietary | Cisco only | Cisco's pre-standard answer to VRRP. Same master/standby model but different MAC address range and different group-numbering scheme. |
| **GLBP** | Cisco proprietary | Cisco only | Adds load balancing — multiple active forwarders share one virtual IP, each answering ARP with a different virtual MAC. No open equivalent. |

## The cross-vendor problem

VRRP is the **only** FHRP that works across vendors. HSRP and GLBP are
Cisco-specific — a Huawei, Arista, or Juniper switch does not implement them.
When interconnecting Cisco and Huawei at L2 (access/distribution boundary,
WAN edge handoff), the default-gateway redundancy protocol must be VRRP on
both sides.

- Huawei defaults vary by product line but typically support VRRP natively.
- Cisco supports VRRP on all platforms (Catalyst, Nexus, ISR/ASR) alongside
  its own HSRP/GLBP — but many Cisco shops default to HSRP out of habit, not
  because VRRP is inferior.

## VRRP design considerations

- **Version**: VRRPv2 is IPv4-only; VRRPv3 (RFC 5798) adds IPv6 support and
  sub-second timers. If IPv6 is in scope, pick v3 from the start — migrating
  later requires a maintenance window.
- **Preemption**: whether a higher-priority router should reclaim the master
  role after recovering from failure. Preemption is on by default in VRRP and
  HSRP — consider disabling it if the recovery triggers a routing protocol
  convergence cascade (OSPF/BGP reconvergence when the new master takes over).
- **Tracking**: tie the VRRP priority to an upstream interface or route
  reachability — when the tracked object fails, the priority drops and the
  standby takes over. Without tracking, the master stays master even if it
  can't reach the upstream network.
- **Timer tuning**: VRRPv3 default advertisement interval is 1s with a 3×
  master-down timer; faster timers (sub-second) are possible but increase CPU
  and risk false failovers during transient congestion — only tune down when
  sub-second failover is a hard requirement.

## When FHRPs don't apply

- **Anycast gateway** (EVPN, spine-leaf Clos): the same gateway IP/MAC is
  active on every leaf — no master election, no standby, no failover delay.
  This makes FHRP irrelevant inside a DC fabric running EVPN. See
  [evpn.md](evpn.md).
- **Routed access** (campus): if L3 is pushed to the access switch, the access
  switch itself is the host's default gateway — no shared virtual IP needed,
  no FHRP. See [core-agg-access.md](core-agg-access.md).

FHRP is relevant at the **L2 boundary** — where a VLAN terminates on two
redundant routers and hosts rely on a single virtual IP. In cross-vendor
designs, that means VRRP.

## Relationship to other techniques

- [evpn.md](evpn.md) — anycast gateway (same IP/MAC on every leaf) replaces FHRP
  inside a DC fabric; FHRP is only relevant at the L2 boundary outside the fabric.
- [core-agg-access.md](core-agg-access.md) — routed access eliminates the shared
  L2 VLAN where FHRP operates, removing the need for FHRP entirely.

## References

[1] R. Hinden, Ed., "Virtual Router Redundancy Protocol (VRRP) Version 3,"
    RFC 5798, March 2010. [Online]. Available: https://www.rfc-editor.org/rfc/rfc5798
