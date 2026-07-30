# Spanning Tree Protocol (STP)

- STP prevents loops in switched Ethernet topologies with redundant paths by
  blocking ports algorithmically, so only one active path exists at any point.
  The variants that matter in design conversations:

| Protocol | Standard | Per-VLAN? | Cross-vendor interop |
|---|---|---|---|
| **STP** (802.1D) [1] | IEEE | No — one spanning tree for all VLANs | Yes, universally |
| **RSTP** (802.1w) [2] | IEEE | No — same limitation as STP | Yes, universally |
| **MSTP** (802.1s) [3] | IEEE | Yes — multiple instance, map VLANs to instances | Yes, standard across all vendors |
| **PVST+** | Cisco proprietary | Yes — one spanning tree instance per VLAN | **No** — Cisco-only. Huawei/Arista/Juniper do not implement PVST+. |
| **RPVST+** | Cisco proprietary | Yes — per-VLAN RSTP (rapid convergence) | **No** — Cisco-only. |

## BPDU frame format

STP exchanges topology information through **BPDUs** (Bridge Protocol Data
Units). The BPDU is an Ethernet frame with an 802.2 LLC header (DSAP=0x42,
SSAP=0x42), not an IP packet — it operates purely at Layer 2. The format
differs across STP variants, which is the root cause of cross-vendor interop
failures: a switch running one variant does not recognize or process BPDUs
from a different variant.

### Destination MAC per variant

| Protocol | Destination MAC | Scope |
|---|---|---|
| **STP** (802.1D) | `01-80-C2-00-00-00` | IEEE reserved — all 802.1D/RSTP/MSTP BPDUs on the native VLAN |
| **RSTP** (802.1w) | `01-80-C2-00-00-00` | Same as STP — the RSTP BPDU reuses the 802.1D address |
| **MSTP** (802.1s) | `01-80-C2-00-00-00` | Same MAC — MSTP is encapsulated within the RSTP BPDU format |
| **PVST+** | `01-00-0C-CC-CC-CD` | Cisco proprietary — separate destination MAC for PVST+ BPDUs |
| **RPVST+** | `01-00-0C-CC-CC-CD` | Same Cisco-proprietary MAC as PVST+ |

This MAC split is why PVST+ BPDUs are invisible to non-Cisco switches: Huawei,
Arista, and Juniper switches listen for `01-80-C2-00-00-00` and drop or flood
frames to `01-00-0C-CC-CC-CD` as unknown multicast.

### 802.1D BPDU structure

The standard 802.1D Configuration BPDU ([1], §9.2.6) carries these key fields
(offsets relative to the BPDU payload after the LLC header):

| Field | Size | Description |
|---|---|---|
| Protocol Identifier | 2 bytes | Always 0x0000 |
| Protocol Version ID | 1 byte | 0x00 for STP, 0x02 for RSTP, 0x03 for MSTP |
| BPDU Type | 1 byte | 0x00 = Configuration BPDU, 0x80 = TCN (Topology Change Notification) |
| Flags | 1 byte | Bit 0: Topology Change (TC), Bit 7: Topology Change Acknowledgment (TCA) |
| Root Identifier | 8 bytes | Bridge ID of the current root bridge |
| Root Path Cost | 4 bytes | Cumulative path cost from this bridge to the root |
| Bridge Identifier | 8 bytes | Bridge ID of the transmitting bridge |
| Port Identifier | 2 bytes | Port number of the transmitting port |
| Message Age | 2 bytes | Time elapsed since the root originated the BPDU (units of 1/256 second) |
| Max Age | 2 bytes | Maximum age before the BPDU is considered expired |
| Hello Time | 2 bytes | Interval between BPDU transmissions from the root |
| Forward Delay | 2 bytes | Time spent in listening and learning states |

Total BPDU payload: 35 bytes (802.1D Configuration BPDU, excluding the 802.2
LLC + Ethernet headers).

### Bridge ID format

The Bridge ID (8 bytes) identifies each switch in the spanning tree. Its format
changed between 802.1D and 802.1t (2001 amendment):

| Field | 802.1D (original) | 802.1t / MSTP / RSTP |
|---|---|---|
| Bridge Priority | 2 bytes (0–65535) | 4 bits (0–15, incremented in steps of 4096) |
| System ID Extension | — | 12 bits (carries the VLAN ID for PVST+ or the MST instance number for MSTP) |
| MAC Address | 6 bytes | 6 bytes |

In modern (802.1t+) implementations, the 16-bit priority field is split into a
4-bit priority (multiplied by 4096) and a 12-bit VLAN/instance identifier. This
is why bridge priorities are always multiples of 4096 in `show spanning-tree`
output.

### TCN (Topology Change Notification) BPDU

A TCN BPDU is a 4-byte frame (Protocol Identifier + Version + BPDU Type 0x80)
sent upstream toward the root when a port transitions to forwarding or
blocking. In 802.1D, TCNs propagate hop-by-hop through the root bridge, which
sets the TC flag in the next Configuration BPDU to flush MAC address tables
across the entire tree. RSTP eliminates the separate TCN BPDU — topology
changes are signaled via the TC flag in the RSTP BPDU itself, converging much
faster.

### Why PVST+ BPDUs differ

PVST+ takes the standard 802.1D BPDU format and wraps it inside a Cisco-proprietary
SSTP (Shared Spanning Tree Protocol) encapsulation that adds:

- A VLAN tag in the LLC/SNAP header (so each VLAN's BPDU can be distinguished)
- The Cisco proprietary destination MAC (`01-00-0C-CC-CC-CD`)
- An additional TLVs section for PVST+ extensions

This is why a Huawei switch sees PVST+ BPDUs as unknown multicast frames — they
don't match the IEEE BPDU MAC or the standard 802.2 LLC DSAP/SSAP, and Huawei
VRP has no code path to parse them even if forwarded to the CPU.

## Cross-vendor / variants

Cisco's default STP mode is **PVST+** (or RPVST+ on current platforms). When
connecting a Cisco switch to a non-Cisco switch (Huawei, Arista, Juniper), the
Cisco side runs per-VLAN BPDUs that the other side either drops or
misinterprets. The result is **STP failing to converge** — loops form, or the
non-Cisco switch becomes root for some VLANs while Cisco claims root for
others.

- **Fix**: pick a common STP mode on both sides, and that common mode is
  **MSTP** (802.1s). All vendors implement MSTP from the IEEE standard. Map
  VLANs to MST instances consistently on both sides.
- If the Huawei side is already running MSTP (its default) and the Cisco side
  is PVST+, the Cisco side must be migrated to MSTP — this is a clean break,
  not an interoperable coexistence.

### PVST+ exception: multi-chassis LAG between pairs (vPC ↔ M-LAG)

When both sides are multi-chassis pairs — Cisco vPC on one side, Huawei M-LAG
on the other — connected by a **single inter-pair port-channel**, the topology
has no physical loop spanning the pairs. The only loop domain is within each
pair's own peer-link, handled internally by vPC and M-LAG respectively. In this
specific topology, BPDU filtering on the inter-pair port-channel is safe because
there is nothing for STP to block — the port-channel is a single logical link
with no redundant path.

- **Cisco vPC side**: `spanning-tree bpdufilter enable` on the port-channel
- **Huawei M-LAG side**: `stp disable` on the Eth-Trunk [5]

This is the only PVST+-safe L2 interconnection without migrating to MSTP. It
requires strict operational discipline — a second inter-pair port-channel (or
any accidental redundant link) creates a loop with no STP protection. If a
second path is planned, both sides must migrate to MSTP first.

## Design considerations

- **Root bridge placement**: always set the root bridge explicitly (bridge
  priority) rather than relying on the lowest MAC address election — it's
  cheap to get wrong and expensive to clean up after.
- **Instance planning for MSTP**: group VLANs into MST instances with intent
  (by failure domain, by forwarding path), not arbitrarily. Different instance
  numbers on different switches produce separate, non-looping regions with a
  single common spanning tree (CST) bridging them — this is how MSTP degrades
  when misconfigured, not a feature.
- **STP edge ports (PortFast)**: an edge port is a port that connects to an end
  host (server, workstation, printer) — not to another switch. Edge ports skip
  the STP listening/learning phases and transition directly to forwarding, so
  the host gets network connectivity in under a second instead of waiting 30
  seconds for STP to converge. Without this, every time a host reboots or
  reconnects, it sits through a full STP forward-delay before it can send
  traffic. Edge ports should always be combined with **BPDU Guard** — if a
  switch (or any device sending BPDUs) is accidentally plugged into an edge
  port, BPDU Guard shuts it down instead of allowing it to disrupt the spanning
  tree topology.

  | Vendor | CLI | Notes |
  |---|---|---|
  | Cisco (IOS-XE, NX-OS) | `spanning-tree portfast` / `spanning-tree port type edge` | "PortFast" is Cisco's term; NX-OS uses `spanning-tree port type edge` |
  | Huawei (VRP, CloudEngine) | `stp edged-port enable` | Huawei's term matches the IEEE "edge port" naming |
  | Arista (EOS) | `spanning-tree portfast` | Same CLI as Cisco |
  | Juniper (Junos) | `set protocols rstp interface <int> edge` | — |
  | Extreme (Switch Engine) | `spanning-tree edge-port` | — |
  | Extreme (Fabric Engine/VOSS) | `spanning-tree port <int> edge-port true` | Different CLI from Switch Engine |

- **STP Toolkit**: BPDU Guard on access ports (shut the port if a rogue switch
  is plugged in), Root Guard on distribution-facing ports (prevent an
  unexpected switch from claiming root), and Loop Guard / UDLD for
  unidirectional-link detection.
- **Routed access as an alternative**: in modern campus designs
  ([core-agg-access.md](core-agg-access.md)), pushing L3 down to the access
  layer eliminates STP entirely from the access-to-distribution topology —
  ECMP replaces blocked ports for redundancy, and STP is limited to the
  access-layer edge only.
- Relevant in cross-vendor interconnection specifically because the default
  mismatch (PVST+ vs. MSTP) is a common first-connect failure between Cisco
  and any other vendor — it won't work silently, but it also won't be obvious
  why until someone checks the STP mode on both sides.

## Relationship to other techniques

- [core-agg-access.md](core-agg-access.md) — routed access design eliminates STP
  from the access-to-distribution topology, replacing blocked ports with ECMP.
- [management-plane.md](management-plane.md) — LLDP is the cross-vendor neighbor
  discovery protocol; CDP is Cisco-only and irrelevant in multi-vendor STP domains.

## References

[1] IEEE 802.1D-2004, "IEEE Standard for Local and Metropolitan Area Networks:
    Media Access Control (MAC) Bridges."

[2] IEEE 802.1w-2001, "IEEE Standard for Local and Metropolitan Area Networks:
    Rapid Reconfiguration of Spanning Tree."

[3] IEEE 802.1s-2002, "IEEE Standard for Local and Metropolitan Area Networks:
    Amendment to 802.1Q: Virtual Bridged Local Area Networks — Multiple
    Spanning Trees."

[4] IEEE 802.1Q-2018, "IEEE Standard for Local and Metropolitan Area
    Networks — Bridges and Bridged Networks." (MSTP was merged into this base
    standard in the 2018 revision and is no longer a separate amendment.)

[5] Huawei, "Configuring M-LAG Through the Root Bridge," CX320 Switch Module
    V100R001 Configuration Guide.
    *Changeable* — verify at Huawei CloudEngine configuration guides:
    https://support.huawei.com/enterprise/en/
    Search for current product series M-LAG configuration guide; look for
    "stp disable" on Eth-Trunk interfaces in M-LAG scenarios.
    Last confirmed: 2026-07-30 — via doc-fetcher search_web, "STP is disabled
    on the interface" noted in M-LAG configuration snippet for Eth-Trunk
    member interfaces.
