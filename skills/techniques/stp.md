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

## The cross-vendor STP problem

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

## Design considerations

- **Root bridge placement**: always set the root bridge explicitly (bridge
  priority) rather than relying on the lowest MAC address election — it's
  cheap to get wrong and expensive to clean up after.
- **Instance planning for MSTP**: group VLANs into MST instances with intent
  (by failure domain, by forwarding path), not arbitrarily. Different instance
  numbers on different switches produce separate, non-looping regions with a
  single common spanning tree (CST) bridging them — this is how MSTP degrades
  when misconfigured, not a feature.
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
