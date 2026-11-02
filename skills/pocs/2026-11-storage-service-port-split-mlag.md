# POC: Storage planes, M-LAG service access, and iNOF on one CE6885-SAN leaf pair

> Based on product documentation, not lab-tested.

> Skeleton. Anything marked `TBC` needs confirmation against the release's Configuration
> Precautions before it is quoted to a customer.

## Background

- **Why it matters**: an FC SAN keeps the service network and the storage network on separate
  fabrics, so the question never arises. On Ethernet both are IP, and the usual compromise is
  to split at the **access port**: the storage ports stay plain and independent, the service
  ports form an M-LAG. This record tests that split **with iNOF running**, and with iNOF zone
  isolation deliberately left off.
- **Scope**: one CloudEngine SAN leaf per storage plane — plane A on CE-1, plane B on CE-2,
  both as plain ports that never join a bond — service access as an M-LAG Eth-Trunk across the
  same pair, and iNOF enabled with the reflectors on the spines. Out of scope: the four-box
  variant (dedicated service leaves), long-distance and DCI links, convergence onto the same
  physical ports, and iNOF with `hard-zoning enable`.
- **Design premise**: M-LAG binds per Eth-Trunk — the DFS group and the peer-link are per pair,
  and each interface independently joins or does not join one [1, M-LAG Configuration]. iNOF
  binds to storage interfaces under `ai-service` → `inof` and is indifferent to the M-LAG,
  which is what lets one pair carry both roles.
- **Zone isolation is off, deliberately.** With isolation off, zones classify hosts and scope
  fault notification; they restrict nothing
  ([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#zoning)). Isolation is implemented with
  ACLs — the guide's own advice to keep one host and one storage device per zone exists to
  conserve them — so its cost scales with hosts × devices per zone and, where the fabric also
  carries service traffic, with the service-side policies. One point stays unverified: the pages
  read do not say whether an entry matches only the peer address or also the RoCE UDP port. If
  it matches only the address, enabling isolation on a port that carries both planes would block
  service traffic too; if it matches UDP `4791` as well, only RoCE is affected. What leaving it
  off costs is ISSUE-05.
- **What iNOF adds here**: fault notification instead of a host keepalive timeout, plug-and-play
  target discovery, and RPFR for hosts that cannot run the agent. The agent itself is Linux-only
  and sets the NVMe keep-alive to 100 ms so the kernel declares a path failed almost immediately
  [3] — that setting, not the switch, is where the failover time comes from.
- **What the split does not isolate**: buffer and scheduling are per chip, not per port
  [1, Buffer Optimization Configuration], so storage ports that share a chip with service ports
  also share the headroom pool. The spines carry both halves, so the lossless domain spans the
  fabric however clean the access edge is.
- **Reflector placement decides the plane model.** The guide says to "select one or two spine
  nodes on each plane as iNOF reflectors"
  [2, Three-Layer Networking for Centralized Storage]. This record assumes **two spines per
  plane**, four × CE16800-X4 in total. A site with a single shared spine pair runs one iNOF
  control plane for both planes: record that as a deviation before build, and expect the
  reflector-failure case (TC-13) to hit both planes at once.
- **Product versions**: CloudEngine V300R026C00 [1]; solution documentation V100R025C10 [2].
- **Prerequisites beyond the hardware**: `CE-LIC-iNOF` on every iNOF device (both leaves and
  all spines), `CE-LIC-AFRD` for AI ECN, and the scenario package the guide requires, either
  the "Standard Package for the Centralized Storage Scenarios" or the "Enhanced Package" [2].
- **Related**: [nof-plus.md](../vendor-matrix/huawei/nof-plus.md#fabric-design) for the feature
  expectations and their limits; [nvme-of.md](../techniques/nvme-of.md#design-considerations)
  for the plane rule being tested.
- **Scenario**: none. This record tests a topology, it does not prescribe one.

## Test environment

### Topology

```
  Server ──┬── p1 ──────────────────► CE-1     storage plane A, plain port
           ├── p2 ─┐
           │       ├── LACP bond ───► CE-1 + CE-2   service access, M-LAG
           ├── p3 ─┘
           └── p4 ──────────────────► CE-2     storage plane B, plain port

  CE-1 ═════════════ CE-2       peer-link (Eth-Trunk 1) — service VLANs only
    │                  │
  S1A ══ S2A        S1B ══ S2B   spines, two per plane, iNOF reflectors

  Array ── a1/a2 ──► CE-1 (plane A)        b1/b2 ──► CE-2 (plane B)
```

### Device list

| Role | Vendor | Model | Software version |
|---|---|---|---|
| Storage plane leaf + service M-LAG member | Huawei | CE6885-SAN-56F ×2 (48 × 25GE SFP28/SFP56, 8 × 100GE QSFP28/QSFP56) | V300R026C00 |
| Spine and iNOF reflector | Huawei | CE16800-X4 ×4, two per plane; AI ECN needs the CEX-MPUD or CE-MPUE MPU ([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#fabric-design)) | V300R026C00 |
| Server | | 4 × 25GE: 2 storage ports (no bond), 2 service ports (LACP bond); NoF Enabler 1.2.0 or UltraPath | |
| Server, RPFR case | | VMware host on the OS-native NVMe multipath stack, no agent | |
| Array | Huawei | OceanStor Dorado, 2 ports per plane, SNSD enabled | |
| Test tooling | | `nvme-cli`, `perftest`, `iperf3`, host multipath stack | |

### Network plan

#### Ports, VLANs, and addressing

| Item | CE-1 | CE-2 |
|---|---|---|
| Service access | Eth-Trunk 10 (M-LAG ID 1), VLAN 100, LACP | Eth-Trunk 10 (M-LAG ID 1), VLAN 100, LACP |
| Service VLANIF | `10.10.0.0/24` (M-LAG primary IP + per-member M-LAG IP) | same, other member IP |
| Storage plane A | plain port, VLAN 200, `192.168.10.0/24`, no Eth-Trunk | — |
| Storage plane B | — | plain port, VLAN 300, `192.168.20.0/24`, no Eth-Trunk |
| Peer-link | Eth-Trunk 1, dedicated ports out of the 8 × 100GE | Eth-Trunk 1, dedicated ports out of the 8 × 100GE |
| Peer-link VLAN allow-list | VLAN 100 only | VLAN 100 only |
| Server storage ports | one IP per plane, one plane per port, no bonding | |
| Server service ports | LACP bond, one IP on VLAN 100 | |

#### iNOF plan

| Item | Value |
|---|---|
| Roles | spines `role reflector`; leaves `role reflect-client` |
| `service-address` | the storage VLANIF address on each device; the management interface address is prohibited |
| Port | 19516 on every device (`port-id`), default |
| Authentication | `authentication-mode hmac-sha256 password …`, identical on every iNOF device |
| Client list | on each reflector, `peer <leaf storage address> reflect-client`; the two reflectors are each other's client and must list the same clients |
| Zones | one customized zone per application, members as `host ip-address` or host groups; configured on the reflectors only, identical on both |
| Default-zone auto-add | **disabled** — with isolation off this is the only admission control |
| Zone isolation | **not configured**: no `hard-zoning enable` anywhere |
| Zone information filtering | optional; at most four synchronization policies per device, 4000 zones each |
| Reflector scale | at most 256 IPv4 and 256 IPv6 client addresses per reflector |

#### Lossless profile (proposed)

What matters is that the host's marking and the switch's classification agree; the exact
priority and DSCP are a local decision.

| Item | Value |
|---|---|
| Storage queue | one priority class, end to end; priority and DSCP `TBC` |
| PFC | enabled on the storage class only, on storage ports and their uplinks |
| ECN | AI ECN or static thresholds per [nof-plus.md](../vendor-matrix/huawei/nof-plus.md#buffer-ecn-and-shaping) |
| Service classes | best-effort, PFC never enabled |
| Trust | storage ports trust host DSCP; service ports per policy |
| Deadlock protection | PFC deadlock detection and prevention enabled on storage ports |
| MTU | 9000 on storage ports and their uplinks |

From the Configuration Precautions pages [1]:

- **Licences**: AI ECN (`CE-LIC-AFRD`) and iNOF (`CE-LIC-iNOF`) are under licence control.
  Congestion management, buffer optimisation, and PFC deadlock prevention are not.
- **Deadlock prevention applies to known unicast RoCE traffic only**, and where a DSCP is
  re-marked downstream, the internal priority must map back to the same queue on the
  downstream device or the flow leaves the intended queue.
- **Drop statistics cover four priorities** (default 0–3), so if the PFC priority is moved
  outside that range the per-priority drop counters used in TC-05 are not available until the
  statistics are cleared and re-scoped.

## Test cases

### TC-01: Storage plane baseline with the service side idle

**Objective**: Each plane carries NVMe/RoCE at line rate on its own, and the host runs both
paths active rather than one active and one standby.

**Prerequisites**: VLANs, addresses, and the lossless profile configured; the array exported
on both planes.

**Procedure**:
```
nvme list-subsys                       # both planes present
fio --rw=read --bs=128k --numjobs=8 --iodepth=32 --direct=1 ...
display interface 25GE1/0/1            # PFC / ECN / drop counters
```

**Expected result**: I/O spread across both planes; no `pause` frames in steady state; zero
drops on the storage queue.

**If it fails**: check marking and trust (TC-07), and confirm the host has not bonded the two
storage ports (ISSUE-01).

### TC-02: VLAN scope audit

**Objective**: Prove the storage VLANs cannot reach the M-LAG trunks or the peer-link — the
rule the whole design rests on.

**Procedure**:
```
display eth-trunk 10                   # service trunk: allowed VLANs
display eth-trunk 1                    # peer-link: allowed VLANs
display vlan 200                       # member ports must be storage ports only
display vlan 300
display dfs-group 1 m-lag brief        # which interfaces are M-LAG members
```

**Expected result**: VLAN 200 and 300 appear on the plain storage ports only, and neither
Eth-Trunk 10 nor Eth-Trunk 1 allows them.

**If it fails**: ISSUE-02.

### TC-03: M-LAG member failure

**Objective**: A service-side member failure must not disturb the surviving storage plane.

**Procedure**: shut the service Eth-Trunk member on CE-1, then power CE-1 down entirely.

**Expected result**: the service bond reconverges on the remaining member; storage plane A is
gone with its chassis and the host fails over to plane B by multipathing; plane B shows no
error-down and no PFC surge. Sample `display inof notice packet statistics` before and after:
a service-side failure must produce **no** storage notification (ISSUE-06).

**If it fails**: plane independence is broken — see ISSUE-01.

### TC-04: Peer-link failure

**Objective**: The decisive case. Confirm that losing the peer-link does not touch the plain
storage ports, and record exactly what happens to the M-LAG member ports.

**Procedure**: shut every peer-link member; hold for 60 s; restore.

**Expected result**: M-LAG member ports enter dual-active handling — error-down, unless
dual-active detection proves the peer is alive (`TBC`; confirm in M-LAG Configuration >
Configuration Precautions for the release). The plain storage ports stay up and forwarding
throughout, the host sees no storage path loss, and `display inof notice packet statistics` on
the leaves shows no new notification. If a notification does appear here, a storage port is an
M-LAG member (ISSUE-01) or the two features meet somewhere they should not (ISSUE-06).

**If it fails**: either a storage port is an M-LAG member (ISSUE-01) or a storage VLAN is on
the peer-link (ISSUE-02).

### TC-05: Lossless behaviour under service load

**Objective**: PFC stays on the storage class and never fires on the service classes.

**Procedure**: saturate the service ports with `iperf3`; run storage I/O at ~80% of one
plane; sample both classes' counters. Keep the PFC priority inside the 0–3 range, because
drop statistics are collected for four priorities only [1, Configuration Precautions for
Congestion Management].

**Expected result**: service classes show drops or WRED while TCP backs off; the storage queue
shows ECN marks with few or no PFC pauses; storage latency stays flat. If PFC fires routinely,
either the ECN thresholds are wrong for the available buffer or the fabric is oversubscribed
beyond what congestion control can absorb
([roce.md](../techniques/roce.md#congestion-control)).

**If it fails**: service traffic is being classified into the lossless queue.

### TC-06: Shared-chip buffer contention

**Objective**: Measure what sharing a chip costs, and decide whether the storage ports need a
dedicated chip.

**Procedure**: run TC-05 twice — first with storage ports on a chip that also carries service
ports, then with storage ports on a separate chip or port-group. Compare storage p99 latency
and PFC pause counts.

**Expected result**: a quantified penalty for the shared layout, which is the number to quote
in the design. If long-distance links are in scope, `start long-distance detect` passes in the
separated layout and may fail in the shared one (`TBC`).

**If it fails**: raise `qos buffer headroom-pool size <n> mbytes slot <n>`, or pin the ports —
see ISSUE-04.

### TC-07: Trust boundary

**Objective**: Confirm that the platform's untrusted default strips the host's RoCE marking
when trust is not configured.

**Procedure**: run TC-01, then remove `trust dscp` from the storage port and repeat.

**Expected result**: with trust removed the storage traffic lands in a best-effort queue,
drops appear under load, and RDMA throughput collapses — the behaviour
[qos.md](../techniques/qos.md#trust-models) describes for CloudEngine's default.

**If it fails** (no difference between the two runs): the host is not marking, or PFC is
enabled on a different priority than the one being marked.

### TC-08: Host failover timing with the agent stopped

**Objective**: Establish the baseline the iNOF cases are measured against — the
failure-detection time the host provides on its own, with nothing on the switch telling it
anything.

**Prerequisites**: TC-01 passed; the agent stopped on the test host (`nvme-snsd` service down),
so only the kernel keep-alive and the multipath stack are in play.

**Procedure**: shut one storage port and time recovery; then repeat with a silent break — link
stays up, traffic blackholed — and time recovery.

**Expected result**: fast recovery for link-down; for the silent break, a wait for the NVMe
keep-alive and the multipath stack's own timers
([nvme-of.md](../techniques/nvme-of.md#design-considerations)). Record both numbers — TC-12
measures the same events with the agent running, and the difference is what iNOF is worth here.

**If it fails**: multipathing is not active/active, or the measured time exceeds what the
application tolerates. That number is the case for the agent.

### TC-09: iNOF roles, registration, and zone distribution

**Objective**: Reflectors and clients are in the right roles, hosts and array ports register,
and every client holds the same zone table.

**Prerequisites**: iNOF enabled and licensed on all devices; `service-address`, port 19516, and
the HMAC password set; peers listed on both reflectors; zones created on both; default-zone
auto-add disabled.

**Procedure**:
```
display inof peer connection                    # reflector and client
display inof information host local             # on the leaf: what it learned itself
display inof information host remote            # on the leaf: what the reflector pushed
display inof configuration zone                 # on both reflectors — must be identical
display inof configuration host inconsistent    # on a reflector — must be empty
display inof synchronization packet statistics peer <peer>
display inof lldp packet statistics interface 25GE1/0/1
```

**Expected result**: each reflector shows a connection to the other reflector and to both
leaves; each leaf shows one connection per reflector; hosts appear as *initiator* and array
ports as *target*; the zone tables match on both reflectors and `inconsistent` returns nothing;
synchronization counters climb steadily.

**If it fails**: ISSUE-07 for configuration on the wrong device or out of sync, ISSUE-08 for
the channel itself.

### TC-10: Zones classify, they do not enforce

**Objective**: Prove the deliberate limit of this build — with `hard-zoning enable` absent,
zone membership blocks nothing.

**Procedure**: two servers on the same leaf, each in a different customized zone. (a) `nvme
connect` from one to an array that only the other zone lists; (b) `ping` between their storage
addresses; (c) repeat both after moving them into one zone. (d) Optional, on a lab copy or after
hours: enable `hard-zoning enable` on every reflector and repeat (a) and (b), then add a service
VLAN to the same physical port and check whether that service traffic survives.

**Expected result**: in this build (a) and (b) both **succeed** — the zones changed nothing on
the wire — and (c) behaves the same. Record it explicitly: a storage team coming from FC will
assume the opposite, and this is the sentence that prevents the misunderstanding. Step (d) has
no expected result here: it exists to answer the one question the documentation leaves open —
whether an isolation entry matches the peer address alone or the RoCE UDP port as well — and
whichever way it goes, that answer is what decides whether isolation may ever be enabled on a
port shared with service traffic.

**If it fails**, meaning traffic is blocked: isolation is enabled somewhere. Sweep every
reflector for `hard-zoning enable` — that sweep is the point of ISSUE-05.

### TC-11: Default-zone auto-add disabled keeps unknown hosts out

**Objective**: Confirm that a host in no customized zone is not silently admitted.

**Procedure**: with auto-add off, attach a new host running the agent and leave it out of every
customized zone. Check `display inof information host` on its leaf, the host's `nvme
list-subsys`, and its default-zone membership.

**Expected result**: the host registers over LLDP but gains no zone membership and no
notification. With isolation off it can still pass traffic if an address is configured
statically — that is the residual exposure, not a bug.

**If it fails**, meaning it was admitted: auto-add is still on. The client's local value is
ignored, so check the reflector.

### TC-12: Storage link fault, notification, and failover timing

**Objective**: Measure what iNOF buys over the host-timer baseline in TC-08.

**Procedure**: run I/O, then shut the array's plane-A port and time the return of I/O; repeat
for the host's own port; repeat once more with the agent stopped. Watch `display inof notice
packet statistics` and the daemon log on the host.

**Expected result**: hosts in the zone receive a notification and the daemon reconnects, so I/O
resumes on the notification path rather than after a keep-alive timeout — the gap against TC-08
is the number to quote. Expect exceptions: the array runs its own I/O keepalive check and may
decline to fail over; a `shutdown`-triggered port-down is reported while the port is physically
up; and routing convergence can still drop I/O command packets, leaving the host to retry.

**If it fails**: ISSUE-08, or the host is not in the zone that the array belongs to.

### TC-13: Reflector failure and zone-table continuity

**Objective**: Show what the second reflector is actually for.

**Procedure**: with two reflectors per plane, shut one; hold 60 s; restore. Then shut both.

**Expected result**: with one reflector down, every leaf keeps its remaining connection and its
zone table, and no host churns. With both down, the leaf clears what it learned over those
connections and notifies the terminals in its zones; forwarding continues, but the
control-plane view degrades until a reflector returns.

**If it fails**: the second reflector was not configured identically, which is ISSUE-07.

### TC-14: Rolling upgrade of the pair

**Objective**: Put a number on the coupling that one pair carrying both roles introduces.

**Procedure**: upgrade CE-2, then CE-1, with storage I/O and service traffic running
throughout.

**Expected result**: each chassis upgrade costs one storage plane *and* half the service
bandwidth at the same moment, not one after the other; I/O survives on multipathing.

**If it fails**: this case is not a pass/fail test — it exists so the cost is known before the
maintenance window is agreed.

## Issues encountered

### ISSUE-01: A storage port ended up in an M-LAG Eth-Trunk

**Found in**: TC-03, TC-04

**Symptom**: the two planes behave as one path; a peer-link or member failure drops both planes
at once. `display eth-trunk` shows the storage interfaces under the service trunk, or the host
shows one bond carrying both plane addresses.

**Root cause**: M-LAG membership is per interface [1, M-LAG Configuration], so moving a port or
extending a trunk during maintenance adds a storage port without any visible change to the
storage configuration. The two-plane rule being broken is in
[nvme-of.md](../techniques/nvme-of.md#design-considerations).

**Fix**: remove the storage interfaces from every Eth-Trunk; keep one address per plane per
port, no bonding; and add the TC-02 audit to the change checklist.

**Verification**: TC-03 and TC-04 after the fix show one plane lost, never two.

### ISSUE-02: A storage VLAN was allowed on the peer-link

**Found in**: TC-04

**Symptom**: storage pauses or drops when the peer-link flaps or saturates, and the peer-link's
interfaces show PFC activity or congestion drops that belong to storage traffic.

**Root cause**: Eth-Trunk 1 left at allow-all, or a trunk-mode port whose native VLAN is a
storage VLAN.

**Fix**: explicit allow-list on the peer-link (service VLANs only), and include
`display eth-trunk 1` in the audit.

**Verification**: TC-02 passes, and TC-04 no longer disturbs storage.

### ISSUE-03: RoCE traffic lands in a lossy queue after ingress

**Found in**: TC-07

**Symptom**: I/O is fine at low load; under congestion there are drops and RDMA retransmits,
the storage queue counters stay flat, and a best-effort queue is dropping.

**Root cause**: CloudEngine ports default to untrusted, so the host's DSCP is reset at ingress
unless trust is configured ([qos.md](../techniques/qos.md#trust-models)).

**Fix**: `trust dscp` on the storage ports and their uplinks, and confirm the host marks the
same value the fabric maps to the lossless class.

**Verification**: TC-07 then TC-01.

### ISSUE-04: The headroom pool is too small once service ports share the chip

**Found in**: TC-06

**Symptom**: PFC pauses on the storage queue under combined load; the long-distance check
reports insufficient headroom on a link that passed before the service ports were added.

**Root cause**: the headroom pool is configured per slot/chip
([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#buffer-ecn-and-shaping)), so it is shared
with the service ports' queues on the same chip — buffer isolation is not something port-level
splitting provides.

**Fix**: pin storage ports to a chip or port-group that carries no service ports, or raise
`qos buffer headroom-pool size <n> mbytes slot <n>` and re-run `start long-distance detect`.

**Verification**: TC-06 comparison between the two layouts.

### ISSUE-05: The design treated zones as isolation, but they classify only

**Found in**: TC-10

**Symptom**: a design document, runbook, or customer slide says hosts in different zones are
isolated. The lab shows NVMe connections and even ICMP working straight across two zones.

**Root cause**: with `hard-zoning enable` absent, zone membership "is only a classification: no
communication is restricted"
([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#zoning)). The function is off by default and
the guide calls it optional. This build leaves it off on purpose, so the classification is all
there is.

**Fix**: describe zones for what they do here — notification scope and host grouping — and keep
the word *isolation* out of the design. If enforcement is genuinely required later, enabling
`hard-zoning enable` on **every** reflector is the minimal condition, and the cost is real: the
guide's ACL advice implies entries scaling with hosts × devices per zone, and nothing read says
whether an entry matches only the peer address or also the RoCE UDP port. If it matches only the
address, a port carrying service and storage traffic loses the service traffic too; if it matches
UDP `4791`, only RoCE is affected. That unknown is the reason to keep enforcement away from a
shared port, not a claim that it is broken.

**Verification**: TC-10 passes (traffic flows), and a grep of the design document for
"isolat" returns nothing it cannot defend.

### ISSUE-06: A service-side HA action became a storage fault

**Found in**: TC-03, TC-04

**Symptom**: peer-link failure or M-LAG member removal produces iNOF notifications in the
storage zones, and hosts react to a storage fault that did not happen.

**Root cause**: error-down is one of the fault types iNOF advertises to the whole zone
([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#fault-notification-and-fast-recovery)), and
M-LAG dual-active handling puts member ports into error-down (`TBC` — confirm the port semantics
for the release). The two features only meet if a storage port is an M-LAG member, or if iNOF is
enabled on the service Eth-Trunk.

**Fix**: keep storage ports out of every M-LAG, and keep `ai-service` → `inof` off the service
interfaces; audit both at once, because either alone recreates the fault path.

**Verification**: TC-03 and TC-04 show no growth in `display inof notice packet statistics`.

### ISSUE-07: Zone configuration on the wrong device, or out of sync between reflectors

**Found in**: TC-09, TC-13

**Symptom**: a zone exists on one reflector only; hosts in it lose notification after a
reflector switch; or a client shows no zones at all because someone configured them locally.
`display inof configuration host inconsistent` lists entries.

**Root cause**: zones are configured on the reflector only — a client "cannot be configured
locally", the synchronized configuration applies
([1, Configuring iNOF Zone Isolation]; [nof-plus.md](../vendor-matrix/huawei/nof-plus.md#zoning))
— and with two reflectors their configurations must be identical or the backup between them
fails.

**Fix**: configure both reflectors from the same script, and run
`display inof configuration zone|host-group inconsistent` as a change check. Note also that once
zone or peer configuration exists, a device can no longer be turned back into a client.

**Verification**: TC-09 passes and TC-13 shows zone-table continuity with one reflector down.

### ISSUE-08: The iNOF control channel does not come up

**Found in**: TC-09, TC-12

**Symptom**: `display inof peer connection` is empty or flapping, hosts register over LLDP but
never receive a notification, and the synchronization counters stay flat.

**Root cause**: one of four documented conditions — a destination port that differs from the
rest of the fabric (default 19516, and "all devices in the iNOF system must be configured with
the same port number"), an HMAC-SHA256 password mismatch, a `service-address` set to the
management interface's address (prohibited), or the transport blocked between reflector and
client. Because the channel is TCP through the same fabric, an ACL or queue policy change on the
shared spines can break iNOF while forwarding carries on perfectly
([nof-plus.md](../vendor-matrix/huawei/nof-plus.md#control-channel)).

**Fix**: check port, password, and `service-address` on every device, permit 19516 end to end,
and re-run TC-09 after any ACL or QoS change on the spines.

**Verification**: TC-09 counters climb steadily and TC-12 notifications arrive.

## Conclusion

- **The pattern holds, with two rules.** One leaf pair can carry both roles because M-LAG
  membership is per Eth-Trunk, and the storage planes stay independent in forwarding as long as
  (a) no storage port is ever an M-LAG member and (b) no storage VLAN reaches the peer-link or an
  M-LAG trunk. iNOF does not change either rule — it just makes breaking them louder, because
  error-down becomes a storage notification (ISSUE-06).
- **Zones here are notification scope, not enforcement.** With `hard-zoning enable` off, a host
  in a different zone still talks; TC-10 exists to record that as a measured fact before a
  storage team assumes FC semantics. Isolation is available, but it is an optional function whose
  ACL entries scale with hosts × devices per zone, and how those entries match — peer address
  only, or also the RoCE UDP port — is not documented. On a shared port that difference decides
  whether enabling isolation drops service traffic too; on a storage-only port it does not
  arise. Leaving it out is a decision with a reason, not an omission.
- **Reflectors per plane decide the plane model.** Two spines per plane keeps zone knowledge and
  zone policy inside the plane, and TC-13 shows what the second reflector is for. A shared spine
  pair means one iNOF control plane for both planes, and the same test then fails both at once.
- **What one pair does not isolate**: chip buffer and scheduling, software version and
  maintenance window, and chassis failure — which costs one storage plane and half the service
  bandwidth at the same moment. The spines carry both halves, so the lossless domain spans the
  fabric however clean the access edge is.
- **What iNOF is worth here is a number, not an adjective**: TC-08 and TC-12 measure the same
  faults with the agent stopped and running. Quote that pair, not "near-zero interruption" —
  the array's own keepalive check and the routing-convergence caveat both override a clean
  handover.
- **Open, to confirm with Huawei**: peer-link-failure port semantics and the dual-active
  detection path; the model's port-to-chip map; how an isolation ACL entry matches — peer address
  only, or the RoCE UDP port as well — since that decides whether isolation can ever be enabled
  on a port that carries both planes; whether isolation would apply to locally switched flows
  between hosts on the same leaf; and the exact scenario package, Standard or Enhanced, that the
  site needs.
- **Do not describe the result as "separated networks".** It is a port-level split inside one
  fabric. That distinction is the difference between an accurate design document and a surprise
  during the first maintenance window.

## References

[1] Huawei, *CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation*,
V300R026C00, Issue 01, 2026-09-30, HedEx library EDOC1100611778. Sections:
- Configuration > Configuration Guide > Intelligent Lossless Network Configuration > iNOF
  Configuration: Understanding iNOF (reflector/client connections, TCP port range and the four
  payload types); Configuring an iNOF Reflector > Configuring iNOF Authentication
  (HMAC-SHA256); Configuring an iNOF Reflector > Configuring the iNOF Reflector and Client
  (`role`, `service-address`, `peer … reflect-client`, 256 clients per reflector);
  Configuring an iNOF Zone > (Optional) Configuring iNOF Zone Isolation (role matrix,
  reflector-only); Verifying the Configuration (`display inof peer connection`, `information
  host`, `configuration zone|host-group`, `lldp|notice|synchronization packet statistics`).
- Configuration > Configuration Guide > Intelligent Lossless Network Configuration >
  Configuration Precautions for AI ECN (licensed: `CE-LIC-AFRD`), for Congestion Management (not
  licensed; four-priority drop statistics), for Buffer Optimization (not licensed), and for PFC
  Deadlock Prevention (not licensed; known unicast RoCE traffic only).
- Configuration > Configuration Guide > High Availability Configuration > M-LAG Configuration
  (peer-link and DFS group, M-LAG member interfaces, Configuration Precautions for dual-active
  handling).
- References > Command Reference: iNOF Configuration Commands; M-LAG Configuration Commands;
  QoS Configuration Commands; `display eth-trunk`, `display vlan`.

Last confirmed 2026-11-03.

[2] Huawei, *Xinghe Intelligent Fabric DCN Solution Product Documentation (Intelligent Lossless
Scenario)*, V100R025C10, Library Version 01, 2026-03-31, HedEx library EDOC1100559388. Sections:
- Deployment Guide for the Centralized Storage Scenario > Intra-DC Network Deployment Guide >
  Recommended Networking and Device Models > Three-Layer Networking for Centralized Storage:
  must-deploy list (AI ECN, PFC, PFC deadlock detection and prevention), "iNOF is recommended …
  deployed when Huawei OceanStor Dorado storage is used", "The hard zoning function is optional.
  (To save ACL resources, you are advised to configure one host and one storage device for each
  zone.)", reflector placement ("select one or two spine nodes on each plane as iNOF reflectors"),
  dual planes, single-homed servers, and the scenario restrictions including the required
  "Standard Package for the Centralized Storage Scenarios" or "Enhanced Package".

Last confirmed 2026-11-03.

[3] "nvme-snsd," linux-nvme on GitHub, BSD 3-Clause. [Online]. Available:
https://github.com/linux-nvme/nvme-snsd (README: Linux-only, one IP per physical port, no IPv6 in
the agent, RoCE only, RPFR for VMware; source: `src/snsd_mgt.c` binds a raw LLDP socket and
implements no TCP listener, which is why the iNOF control channel is switch-to-switch only; last
confirmed 2026-11-03).
