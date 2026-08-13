# Classic DC three-tier — Nexus "7-5-2" (N7K / N5K / N2K)

The classic pre-VXLAN/EVPN Cisco data center architecture — "7-5-2" = Nexus 7000
core + Nexus 5000 aggregation + Nexus 2000 FEX access. Obsolete for new builds
(replaced by Nexus 9000 spine-leaf with EVPN-VXLAN, ACI or NX-OS-native), but a
large installed base still runs it. This file is the **design, its limitations,
and the upgrade path**; platform models, port counts, and EOL/lifecycle data live
in [nexus-hardware.md](nexus-hardware.md).

## Tier roles and mechanisms

- **N2K (Nexus 2000) — access tier**: fabric extenders, not switches — no
  independent control plane, no local STP; they are managed through and appear as
  remote line cards of the parent (N5K or N7K), forwarding all traffic to the
  parent over 10G fabric uplinks [1], [8]. Two structural consequences: access is
  a tree (no ECMP below the parent; FEX-to-FEX traffic hairpins through it), and
  the FEX adds no independent resilience.
- **N5K (Nexus 5000/5500/5600/6000) — aggregation tier**: L2 aggregation, hosts
  the FEX tree, and is the L2/L3 boundary (SVIs + FHRP). Runs in **vPC** pairs so
  dual-homed servers/FEX uplinks are active-active with no blocked ports [2].
  Also the FCoE / unified-fabric tier (FCoE NPV toward the SAN fabric).
- **N7K (Nexus 7000) — core tier**: L3 core (10/40/100G), **VDC** (chassis
  partitioned into multiple logical switches) [3], MPLS, and **OTV** for L2 DCI [4].
  N7K pairs also use vPC. A common collapsed variant parents the FEX tree directly
  (N7K + N2K, no N5K tier) — the L2/L3 boundary then sits on the N7K pair.

## Design characteristics

- The L2 domain extends from access through aggregation/core, so the STP/blast
  radius reaches the parent pair; vPC is what removes blocked ports at the access
  uplinks.
- FCoE makes the stack a "unified fabric" (LAN+SAN over the same links, with
  DCB/PFC).
- **Structural constraint** (the load-bearing fact for refresh planning): at
  multi-rack scale, "one pair of switches total" is achievable only with a
  port-extender/FEX model — and that model is being retired. The minimum-viable
  modern shape is a core pair + one leaf per rack; the FEX "one pair" simplicity
  is replaced by config templates + fabric automation, not by fewer boxes.

## Limitations

- **Availability — a FEX can have at most two parents, so the parent pair is its
  whole redundancy domain.** A FEX has no control plane; if its parent (or both
  uplinks/peer-link) fails, the whole rack's servers go dark at once. Parent count
  is hard-capped: one switch (straight-through) or a vPC pair (dual-homed/AA) —
  "each FEX is dual-homed with two Cisco Nexus ... switches" [9]; there is no 3- or
  4-parent FEX mode. Running more aggregation/core switches in the fabric (multiple
  agg vPC pairs, or a 4-switch L3 core above the agg pair) adds resilience above
  the parent pair only — each FEX still gets at most two paths, and one parent down
  still takes out every FEX pinned to it. N-way path diversity is a leaf property
  (ECMP to N spines) the FEX model cannot deliver; leaf + EVPN multihoming shrinks
  the failure domain to one rack (and dual-homed servers survive even that).
- **Bandwidth — fixed FEX uplink oversubscription.** The bottleneck is the FEX NIF
  uplinks, not the chassis fabric. N2K-C2348UPQ: 48×10G down = 480G vs 6×40G up =
  240G → **2:1** at 10G downlinks [1]. **No N2K FEX serves 25G server downlinks**
  (HIFs cap at 10G) [5] — a 25G-capable leaf (e.g. N9K-C93180YC-FX3, 2:1 at 25G)
  is the equivalent modern device. Rack-local east-west traffic also hairpins
  through the parent.
- **Not a VTEP.** A FEX cannot route or terminate VXLAN; the parent does. Multicast
  (TRM) is not supported behind FEX — "With TRM enabled, FEX is not supported";
  "Multicast Source/Receiver behind FEX is not supported" [6]. If you don't use
  VXLAN/multicast this specific limit is moot, but it caps any future use of the
  same access tier.
- **Table concentration — all forwarding state lives on the parent.** A FEX does
  not perform any local switching: "all traffic is sent to the parent switch that
  provides central forwarding and policy enforcement" [8]. The parent (N5K or N7K)
  carries the whole fabric's state from one forwarding-table budget (flexible
  templates; e.g. up to 2M shared entries on 9300-FX3 [7] — carve MAC vs LPM per
  template): the **MAC table** for every host behind every FEX, the **LPM routing
  table** (the parent pair is the L2/L3 boundary — N5K in the standard 7-5-2, N7K
  in the collapsed variant), and the **ACL/TCAM entries** for FEX host ports —
  "the Fabric Extender supports the full range of ingress access control lists
  (ACLs) that are available on its parent" [8]. Every added rack deepens the
  concentration on the parent pair; leaf-per-rack scale-out partitions the budget
  per switch instead.
- **No new FEX hardware.** The Nexus 2300 "successor" FEX is also EOL [10]; the
  only current product that can act as a FEX is a Nexus 9300-FX2/FX3 in FEX mode
  (Essentials license in ACI [5]; AA-as-device capability unverified — see the
  dual-homing bullet above) — buying a full EVPN-capable leaf to use as a remote
  line card. Absurdity check: per the FEX matrix the FX3-as-FEX can attach to an
  N9K-C93180YC-FX3 parent [5] — the very model Cisco names as the 1:1 replacement
  for the N2K-C2348UPQ FEX [11]. You'd buy the recommended replacement leaf, then
  demote another FX3 to FEX duty behind it.

## FEX support status in current software (recorded 2026-08)

- **N7K NX-OS train (8.4)**: FEX still supported, on F3 and F4 modules (F4 in 40G
  mode from 8.4(1)) [14]. An N7K-7710 + N2K FEX pod remains a supported config.
  The train also supports VXLAN BGP EVPN with the N7K/7700 as VTEP and FEX
  host-interface ports ("Programmable Fabric") [17] — context only: it retains the
  N2K access layer, so it is not an upgrade under the replace-EOL-N2K premise.
- **N9K NX-OS train**: the FEX *feature* is still documented on 10.6(x) (a Release
  10.6 FEX Configuration Guide exists) [8], but the N2K FEX *hardware* is dropped:
  "N2K FEX models are supported until NX-OS Release 10.5(x), but beginning with
  Release 10.6(3)F, these models are not supported" [5], [12]. The
  9300-FX2/FX3-in-FEX-mode option survives this release specifically (the statement
  names "N2K FEX models") — verify the current matrix before relying on it [5].
- **N9K FEX scale limit**: 6 FEX in AA mode on NFE-base ToR, 16 on LSE-base ToR
  (verified scalability guide) [5].
- **Dual-homing (FEX vPC / AA mode) by parent family** — per the Nexus 2300
  datasheet, FEX vPC (dual-homed FEX to a parent vPC pair) is supported on Nexus
  7000/7700 (and 5000/6000); on Nexus 9000 only "server vPC" is listed, so
  **dual-homing an N2K FEX on an N9K parent is not guaranteed** — it's
  per-parent-model and per-release [10], [5]. The 10.6 FEX guide lists dual-homed
  (AA) topology support **by parent**: 9300/9300-EX from 7.0(3)I5(2), C9336C-FX2/
  C93240YC-FX2/C93360YC-FX2/C93216TC-FX2 from 9.3(5), C93180YC-FX3S from 9.3(7);
  "The Cisco Nexus 9300-FX2 and FX3 switches are supported on the ST and the AA
  FEX modes" — in context this is a **parent** capability (the switches that host
  the dual-homed topology), not a statement about the FX2/FX3 acting as the FEX
  device [9]. Whether a 9300-FX2/FX3 running **in FEX mode** (as the FEX device
  itself) supports AA dual-homing is not clearly documented — do not assume it.
  In ACI mode, dual-homed FEX is not supported [5]. FEX vPC is also not supported
  between any FEX model and Nexus 9500 parents [18].

## Upgrade path — options, assessed

**Never propose this stack for a new build — this section is the evidence.**
The stack's only continuation paths each fail on both criteria that matter: they
can neither maintain the current FEX design nor fully deliver the new
architecture. No single Cisco announcement says this in so many words, but every
official signal points the same way (see Grounding below). Each option is judged
against **FEX support in current software** and **hardware EOL status**.

**Operating premise:** a real upgrade must replace the EOL N2K FEX access layer.
The status quo (no change) and any option that retains the N2K access layer are
therefore not options.

**Grounding (from this file and [nexus-hardware.md](nexus-hardware.md))**
- FEX in current software: N7K NX-OS train (8.4) still supports FEX on F3/F4
  modules [14]; N9K NX-OS 10.6(3)F drops all N2K FEX models [5], [12]; the FEX
  feature stays documented on 10.6(x) only for the 9300-FX2/FX3-as-FEX, whose
  AA-as-device capability is unverified [8], [9]; ACI mode has no dual-homed FEX
  and ACI 6.1(1) drops several N2K models [5], with Cisco's own ACI Design Guide
  framing FEX as migration-only ("the main purpose of doing so should be to
  simplify migration from an existing network with fabric extenders") [19].
- Hardware EOL: N2K FEX EOL (waves 2016–~2022, no new units) [11]; N5K family EOL
  (support through 2026-05-31); N7700 EOL (last order 2023-10-12; replacement
  N9500/N9800) [13]; the only 9500 line cards that support FEX are all EOL and
  past Last Date of Support [nexus-hardware.md].

**Option A — Full refresh: spine/core pair + one leaf per rack (EVPN-VXLAN)**
- Suitability: **Suitable — the recommended end-state (listed first).**
- Why: current hardware throughout — 9300 FX3/GX leaves and N9500/N9800 spine
  (Cisco's own replacements for the 7-5-2 hardware [13], [16]); the FEX is
  replaced 1:1 by the FX3/FX3P leaf [11]; EVPN-VXLAN is Cisco's stated direction
  (Nexus One) [15]; per-rack failure domain; 25/100G growth path; the FEX "one
  pair" simplicity is reproduced by config templates + fabric automation, and the
  parent single-point-of-failure disappears.

**Option B — 9300-FX2/FX3-as-FEX (port extension with current hardware)**
- Suitability: **Always unsuitable as an access-layer strategy (niche OOB/iLO
  style port extension only).**
- Evaluation — fails both criteria: it cannot maintain the current design (a full
  EVPN-capable leaf demoted to a remote line card [5], [9]) and cannot fully
  benefit from the new architecture — the parent 9300 carries only a handful of
  40/100G fabric (NIF) ports (6 QSFP28 on the C93180YC-FX3) [5], capping how many
  FEX devices can attach and the uplink bandwidth available to them; AA
  dual-homing as a FEX device is not clearly documented [9]; and it hangs off the
  very C93180YC-FX3 that replaces the C2348UPQ FEX [5], [11].

Note: a collapsed two-switch EVPN pair (two fixed 9300s) is deliberately not
listed — it cannot replace an N7K-7710-class modular core (a significant downgrade
in capacity and radix), and in the scenario of more than a few racks or FEXes per
pair, two fixed switches cannot serve the access ports anyway.

Cross-cutting migration blockers (apply to A): **vPC peer-link sizing** and
**FCoE/DCB behavior** on the cutover; the FEX access layer must be physically
replaced by leaves on any path that leaves the N7K train.

Net: Option A is the only path that is both available and fully aligned with the
new architecture; the 9500-as-FEX-parent path is not an option at all (FEX vPC
not supported with N9500 parents [18]; the 9300-as-FEX attaches to 9300 parents
only [5]); and Option B (FX3-as-FEX) is always unsuitable. That is the strong
support for **"never propose this stack for a new build."**

## Relationship to other files

- [nexus-hardware.md](nexus-hardware.md) — the platform models, port
  counts, NX-OS trains, and EOL/lifecycle data for this architecture.
- [../../techniques/core-agg-access.md](../../techniques/core-agg-access.md) — the
  generic three-tier vs. collapsed-core model this design instantiates; L2/L3
  boundary placement is the key decision.
- [../../techniques/spine-leaf-clos.md](../../techniques/spine-leaf-clos.md) — the
  modern topology that replaces the FEX tree.
- [../../techniques/vxlan.md](../../techniques/vxlan.md) /
  [../../techniques/evpn.md](../../techniques/evpn.md) — the data/control plane of
  the successor fabric; a FEX can't be a VTEP.
- [aci.md](aci.md) / [nxos-vxlan.md](nxos-vxlan.md) /
  [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md) — the two successor fabric options
  and the Nexus One convergence.

## References

[1] "Cisco Nexus 2000 Series Fabric Extenders Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/data_sheet_c78-507093.html (accessed 2026-08-13).

[2] "Configuring Virtual Port Channels," Cisco Nexus 5000 Series NX-OS Layer 2 Switching Configuration Guide, Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus5000/sw/layer2/b_Cisco_Nexus_5000_Series_NX-OS_/b_Cisco_Nexus_5000_Series_NX-OS__chapter_01000.html (accessed 2026-08-13).

[3] "Cisco Nexus 7000 Series Virtual Device Context Configuration Guide 6.x," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/sw/nx-os/virtual_device_context/configuration/guide/b-7k-Cisco-Nexus-7000-Series-NX-OS-Virtual-Device-Context-Configuration-Guide.html (accessed 2026-08-13).

[4] "Configuring Basic OTV Features," Cisco Nexus 7000 Series NX-OS OTV Configuration Guide 8.x, Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus7000/sw/otv/config/cisco_nexus7000_otv_config_guide_8x/configuring_basic_otv_features.html (accessed 2026-08-13).

[5] "Nexus 9000 Series Switch FEX Support" (FEX support matrix), Cisco, revised 2026-07-16. [Online]. Available: https://www.cisco.com/c/dam/en/us/td/docs/Website/datacenter/fexmatrix/fexmatrix.html — N2K FEX supported only through NX-OS 10.5(x), not from 10.6(3)F; ACI notes (no dual-homed FEX in ACI; N2K models dropped from ACI 6.1(1)); FEX scale (6 AA-mode on NFE-base ToR, 16 on LSE-base ToR).

[6] "Configuring Tenant Routed Multicast," Cisco Nexus 9000 Series NX-OS VXLAN Configuration Guide, Release 7.x. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/vxlan/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_7x_chapter_01101.html — "With TRM enabled, FEX is not supported"; "Multicast Source/Receiver behind FEX is not supported."

[7] "Cisco N9300-FX3 Series Switches Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/datasheet-c78-744052.html — flexible forwarding tables up to 2M shared entries on FX3 (accessed 2026-08-13).

[8] "Cisco Nexus 2000 Series NX-OS Fabric Extender Configuration Guide for Cisco Nexus 9000 Series Switches, Release 10.6(x) — Overview," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/fex/cisco-nexus-2000-series-nx-os-fabric-extender-configuration-guide-for-cisco-nexus-9000-series-switches--release-106x/m-overview.html — FEX feature still documented on the 10.6 train (accessed 2026-08-13).

[9] "Configuring the Fabric Extender," Cisco Nexus 2000 Series NX-OS Fabric Extender Configuration Guide for Cisco Nexus 9000 Series Switches, Release 10.6(x). [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/fex/cisco-nexus-2000-series-nx-os-fabric-extender-configuration-guide-for-cisco-nexus-9000-series-switches--release-106x/m-configuring-fex.html — dual-homed (AA) FEX topology per parent: 9300/9300-EX from 7.0(3)I5(2); C9336C-FX2, C93240YC-FX2, C93360YC-FX2, C93216TC-FX2 from 9.3(5); C93180YC-FX3S from 9.3(7); "The Cisco Nexus 9300-FX2 and FX3 switches are supported on the ST and the AA FEX modes" — read as parent capability; FX3-as-FEX-device AA dual-homing not clearly documented (accessed 2026-08-13).

[10] "Cisco Nexus 2300 Platform Fabric Extenders Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/datasheet-c78-731663.html — describes the Nexus 2300 platform as "the successors to the industry's widely adopted Cisco Nexus 2000 Series Fabric Extenders" (accessed 2026-08-13).

[11] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 2248TP GE, Cisco Nexus 2348UPQ 10GE and Cisco Nexus 2348TQ 10GE Fabric Extenders," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/nexus-2248tp-ge-2348upq-10ge-2348tq-10ge-fabric-extenders-eol.html — 1:1 replacement mapping to 9300 leaves (accessed 2026-08-13).

[12] "Cisco Nexus 9000 Series NX-OS Release Notes, Release 10.6(3)F," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/release-notes/cisco-nexus-9000-nxos-release-notes-1063F.html — N2K FEX models (incl. N2K-C2348UPQ, N2K-C2348TQ) no longer supported from 10.6(3)F (accessed 2026-08-13).

[13] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 7700 Switches," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-7000-series-switches/nexus-7700-switches-eol.html — replacement: Nexus 9500 and 9800 series (accessed 2026-08-13).

[14] "Cisco Nexus 7000 Series NX-OS Release Notes, Release 8.4," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus7000/sw/release/notes/cisco_nexus7000_release_notes_84.html — FEX supported with Nexus F4-Series 30-port 100G modules (N77-F430CQ-36) in 40G mode from 8.4(1) (accessed 2026-08-13).

[15] "Unifying the Data Center with Cisco Nexus One: The Network That Works for You," Cisco Blogs, November 2025. [Online]. Available: https://blogs.cisco.com/datacenter/unifying-the-data-center-with-cisco-nexus-one-the-network-that-works-for-you (accessed 2026-08-13).

[16] "Cisco Nexus 9800 Series Switches White Paper," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/nexus-9800-series-switches-wp.html (accessed 2026-08-13).

[17] "Introduction to Cisco Programmable Fabric," Cisco Programmable Fabric with VXLAN BGP EVPN Configuration Guide, Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/pf/configuration/guide/b-pf-configuration/Introduction-to-Cisco-Programmable-Fabric.html — VXLAN BGP EVPN on Nexus 2000/5000/7000/9000; N7K/7700 as leaf/VTEP with FEX host-interface ports (accessed 2026-08-13).

[18] "Validate Nexus 2000 Fabric Extenders Supported/Unsupported Topologies," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/support/docs/switches/nexus-2000-series-fabric-extenders/200363-nexus-2000-fabric-extenders-supported-un.html — "FEX vPC is not supported between any model of FEX and the Cisco Nexus 9500 platform switches as the parent switches" (accessed 2026-08-13).

[19] "Cisco Application Centric Infrastructure (ACI) Design Guide," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-application-centric-infrastructure-design-guide.html — "You can connect fabric extenders (FEXes) to the Cisco ACI leaf switches; the main purpose of doing so should be to simplify migration from an existing network with fabric extenders" (accessed 2026-08-13).
