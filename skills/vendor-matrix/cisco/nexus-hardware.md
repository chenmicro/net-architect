# Nexus hardware — platform models, specs & lifecycle

Nexus switch hardware across the portfolio: models, port counts, NX-OS trains, and
lifecycle/EOL data. Currently documents the 7-5-2-era platforms (N7K/N5K/N2K) that
[nexus-752-architecture.md](nexus-752-architecture.md) covers; other Nexus families
(3000, 9000, ...) can be added here as needed. Lifecycle dates recorded 2026-08 —
re-verify current status per PID on Cisco EOX [11] before quoting.

## Nexus 2000/2300 — FEX (access tier)

Fabric extenders: no independent control plane; managed through the parent.
Downlink speeds cap at 10G — **no N2K FEX serves 25G servers** [1].

| Model | Host ports (HIF) | Fabric uplinks (NIF) | Notes |
|---|---|---|---|
| N2K-C2224TP | 24×1G-T | 4×10G | |
| N2K-C2248TP | 48×100M/1G-T | 4×10G | |
| N2K-C2232PP | 32×1/10G SFP+ | 8×10G | |
| N2K-C2232TM-E | 32×1/10G-T | 8×10G (modular) | |
| N2K-C2332TQ | 32×100M/1/10G-T | 4×40G | Nexus 2300 platform |
| N2K-C2348TQ | 48×100M/1/10G-T | 6×40G | Nexus 2300 platform |
| N2K-C2348UPQ | 48×1/10G SFP+ | 6×40G | 2:1 oversubscription at 10G |
| N2K-C2248TP-GE | 48×100M/1G-T | 4×10G | |
| B22 blade FEX | blade slot | 4×10G | HP/Dell/IBM/Fujitsu |

EOL: announcements in waves from 2016 (2224TP/2248TP/2232TM/2248PQ) [3] through
the early 2020s (2232PP/2232TM-E/2332TQ/2348TQ [4]; 2248TP-GE/2348UPQ/2348TQ [5]),
last-order window ending ~2022. **No new FEX hardware exists** — the Nexus 2300
platform ("the successors to the Nexus 2000" [2]) is also EOL. Cisco's 1:1
replacement mapping for the 2248TP-GE/2348UPQ/2348TQ FEX: N2K-C2348UPQ →
N9K-C93180YC-FX3 (48×1/10/25G), N2K-C2348TQ(-E) → N9K-C93108TC-FX3P
(48×10G-T + 6×100G), N2K-C2248TP-E → N9K-C9348GC-FXP (48×100M/1G-T) [5].

Platform notes: Nexus 2300 models support up to **2:1 oversubscription** and carry
a **32 MB shared buffer** [2]. Dual-homing by parent family (Nexus 2300 datasheet):
FEX vPC (dual-homed FEX to a parent vPC pair) is supported on Nexus 7000/7700 (and
5000/6000); on Nexus 9000 only **server vPC** is listed as universally supported —
dual-homed FEX on N9K is per-parent-model and per-release (see
[nexus-752-architecture.md](nexus-752-architecture.md)) [2].

## Nexus 5000/5500/5600/6000 (aggregation tier)

- Fixed aggregation switches (5000, 5500, 5600, 6000 series) running NX-OS; L2
  aggregation, vPC pairs, FCoE/NPV.
- Family EOL: end-of-sale announced 2021-04, last order **2021-05-05**; support
  (incl. vulnerability/security extension) through **2026-05-31**; several PIDs
  have no replacement product [6].

## Nexus 7000/7700 (core tier)

- Chassis: N7K-C7010, N7K-C7018 (EOL: last order **2022-02-28** [7]); N7702,
  N7706, **N7710**, N7718 (N7700 family EOL: last order **2023-10-12**, replacement
  = **Nexus 9500 and 9800 series** [8]).
- Line cards: M1/M2/M3 (1/10/40/100G, VDC/MPLS-capable), F1/F2/F3 (high-density
  10/40G), F4 (100G, e.g. N77-F430CQ-36).
- FEX-parent capability: supported on F3 and F4 modules (F4 in 40G mode from
  NX-OS 8.4(1)) [9]. The N7K NX-OS train is 8.4 — the 10.6(3)F FEX drop applies to
  the N9K NX-OS train only [10].
- OTV for L2 DCI [12]; VDC; MPLS.
- On **Nexus 9500** (the EOL-listed replacement for the 7700): the FEX matrix's
  9500 table lists only legacy PQ/PX **line cards** as parents — N9K-X9564TX,
  X9432PQ, X9464PX, X9536PQ, X9564PX, X9636PQ — and its own note states "The
  switches and linecards that are excluded from this table do not support FEX in
  NX-OS Mode." Modern 9500 line cards (X9700-EX/FX/GX) are spine roles, not FEX
  parents [13]. The FX3 replacement models named in the FEX EOL bulletin
  (N9K-C93180YC-FX3, N9K-C93108TC-FX3P) are **9300-format fixed leaves** — they
  appear as parent columns only in the 9300 table, not the 9500 table; on an N9500
  spine they attach as normal access switches, not as FEXes [5], [13].

EOL status of the six 9500 FEX-capable line cards (recorded 2026-08 — verify per
PID on EOX [11]):

| Line card | End of Sale | Last Date of Support | Cisco replacement |
|---|---|---|---|
| N9K-X9536PQ | 2018-02-09 | 2023-02-28 | N9K-X9732C-EX (not FEX-capable) |
| N9K-X9564TX | 2018-05-12 | 2023-05-31 | N9K-X9464TX2 (not FEX-capable) |
| N9K-X9564PX | 2018-05-12 | 2023-05-31 | N9K-X97160YC-EX (not FEX-capable) |
| N9K-X9636PQ | 2018-05-12 | 2023-05-31 | N9K-X9732C-EX (not FEX-capable) |
| N9K-X9432PQ | 2020-11-27 | 2025-11-30 | N9K-X9736C-FX / X9736Q-FX (not FEX-capable) |
| N9K-X9464PX | 2020-11-27 | 2025-11-30 | N9K-X97160YC-EX (not FEX-capable) |

Net: **all six are past end-of-sale (2018/2020) and past end-of-support (2023/
2025)** — and Cisco's official replacements (EX/FX line cards) are not in the FEX
matrix's 9500 table at all, i.e. they do not support FEX. The "N9500 as FEX
parent" path is closed even with refurbished hardware [14]–[19].

## Nexus 9500 (modular spine / core)

The modular spine/core platform and the EOL-listed replacement for the N7700 [8].
Runs NX-OS (classic mode) or ACI (ACI mode). Current-generation product — no
chassis EOL as of 2026-08; re-verify per PID on EOX [11].

- **Chassis**: N9K-C9504 (4-slot), N9K-C9508 (8-slot), N9K-C9516 (16-slot);
  internal Clos fabric over rear-mounted fabric modules (C9504-FM/C9508-FM/
  C9516-FM; FM-S for the X9432C-S, FM-E/E2 for cloud-scale cards, FM-R for
  R-series) — line-card traffic is load-balanced across all fabric modules and
  survives a fabric-module loss at reduced capacity; chassis bandwidth up to
  172.8 Tbps [20], [21].
- **Supervisors**: N9K-SUP-A (EOL, last order 2020-11-27 [24]), N9K-SUP-A+,
  N9K-SUP-B, N9K-SUP-B+ [20].
- **Line cards** (three generations):
  - *Classic*: X9432PQ (32×40G), X9536PQ/X9636PQ/X9736PQ (36×40G), X9464PX/
    X9564PX (48×1/10G + 4×40G), X9564TX/X9464TX2 (48×10G-T + 4×40G), X9432C-S
    (32×100G). **These are the only 9500 line cards that support FEX** — and only
    the six classic PQ/PX cards (X9432PQ, X9464PX, X9536PQ, X9564PX, X9564TX,
    X9636PQ) appear in the FEX matrix's 9500 table; X9464TX2 and X9736PQ do not
    [13], [21]. All six are EOL and past end-of-support (see the EOL table above)
    [14]–[19].
  - *Cloud-scale EX/FX/GX* (X9700-EX/FX/GX, with FM-E/E2): current generation,
    1/10/25/40/50/100G — **not FEX-capable** [22].
  - *R-series* (X9624D-R2, X9636C-RX, X9636C-R, X9636Q-R, with FM-R): high-density
    100/40G with deep buffers for the 9504/9508 — not FEX-capable [23].
- **FEX capability bottom line**: FEX is possible only on the six classic PQ/PX
  cards, all now past end-of-support; every current line card and every official
  replacement for the classic cards is excluded from the FEX matrix ("The switches
  and linecards that are excluded from this table do not support FEX in NX-OS
  Mode") [13]. The N9500 cannot host a FEX in any buildable 2026 configuration —
  FX3/9300 leaves attach to it as normal access switches (L3/EVPN), not as FEXes.
  A 9300-in-FEX-mode device is a 9300-parent feature only — it does not appear in
  the matrix's 9500 table, so it cannot attach to an N9500 either [13].

## Lifecycle summary

| Family | Last order | Last support (typical) | Replacement |
|---|---|---|---|
| Nexus 5000/5500/5600/6000 | **2021-05-05** [6] | **2026-05-31** (vuln/security ext.) | N9K |
| Nexus 2000/2300 FEX | ~2022 (waves from 2016) [3][4][5] | per model | **9300 leaves** (1:1 mapping) [5] |
| N7K-C7018 | **2022-02-28** [7] | per EOL bulletin | N9500/N9800 |
| N7700 (incl. N7710) | **2023-10-12** [8] | ~2028 (verify per PID on EOX) | **N9500/N9800** [8] |

## References

[1] "Cisco Nexus 2000 Series Fabric Extenders Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/data_sheet_c78-507093.html (accessed 2026-08-13).

[2] "Cisco Nexus 2300 Platform Fabric Extenders Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/datasheet-c78-731663.html (accessed 2026-08-13).

[3] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 2224TP, 2248TP, 2232TM, and 2248PQ Fabric Extenders," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/eos-eol-notice-c51-736205.html (accessed 2026-08-13).

[4] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 2232PP, 2232TM-E, 2332TQ, 2348TQ Fabric Extenders," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/eos-eol-notice-c51-742812.html (accessed 2026-08-13).

[5] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 2248TP GE, Cisco Nexus 2348UPQ 10GE and Cisco Nexus 2348TQ 10GE Fabric Extenders," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-2000-series-fabric-extenders/nexus-2248tp-ge-2348upq-10ge-2348tq-10ge-fabric-extenders-eol.html — 1:1 replacement mapping to 9300 leaves (accessed 2026-08-13).

[6] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 5500, 5600 and 6000 NX-OS 7.3 all versions," Cisco, 2021. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-5000-series-switches/eos-eol-notice-c51-743752.html (accessed 2026-08-13).

[7] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus N7K-C7018 Switches," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-7000-series-switches/eos-eol-notice-c51-2357752.html (accessed 2026-08-13).

[8] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 7700 Switches," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-7000-series-switches/nexus-7700-switches-eol.html — replacement: Nexus 9500 and 9800 series (accessed 2026-08-13).

[9] "Cisco Nexus 7000 Series NX-OS Release Notes, Release 8.4," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus7000/sw/release/notes/cisco_nexus7000_release_notes_84.html (accessed 2026-08-13).

[10] "Cisco Nexus 9000 Series NX-OS Release Notes, Release 10.6(3)F," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/release-notes/cisco-nexus-9000-nxos-release-notes-1063F.html (accessed 2026-08-13).

[11] Cisco End-of-Life policy and EOX search tool. [Online]. Available: https://www.cisco.com/c/en/us/products/eos-eol-policy.html (accessed 2026-08-13).

[12] "Configuring Basic OTV Features," Cisco Nexus 7000 Series NX-OS OTV Configuration Guide 8.x, Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus7000/sw/otv/config/cisco_nexus7000_otv_config_guide_8x/configuring_basic_otv_features.html (accessed 2026-08-13).

[13] "Nexus 9000 Series Switch FEX Support" (FEX support matrix), Cisco, revised 2026-07-16. [Online]. Available: https://www.cisco.com/c/dam/en/us/td/docs/Website/datacenter/fexmatrix/fexmatrix.html — 9300 table (FX3 fixed models as parents) vs 9500 table (legacy PQ/PX line cards only: X9564TX, X9432PQ, X9464PX, X9536PQ, X9564PX, X9636PQ); "The switches and linecards that are excluded from this table do not support FEX in NX-OS Mode."

[14] "End-of-Sale and End-of-Life Announcement for the Cisco N9K-X9564TX Linecard On Cisco Nexus 9500" (EOL11903), Cisco, 2017 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-739496.html (accessed 2026-08-13).

[15] "End-of-Sale and End-of-Life Announcement for the Cisco N9K-X9564PX Linecard On Cisco Nexus 9500" (EOL11904), Cisco, 2017 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-739497.html (accessed 2026-08-13).

[16] "End-of-Sale and End-of-Life Announcement for the Cisco N9K-X9536PQ Linecard On Cisco Nexus 9500" (EOL11902), Cisco, 2017 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-739495.html (accessed 2026-08-13).

[17] "End-of-Sale and End-of-Life Announcement for the Cisco N9K-X9636PQ Linecard On Cisco Nexus 9500" (EOL11905), Cisco, 2017 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-739498.html (accessed 2026-08-13).

[18] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 9500 32p 40G QSFP aggregation line card - N9K-X9432PQ" (EOL13403), Cisco, 2020 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-743851.html (accessed 2026-08-13).

[19] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 9500 48p 1/10G SFP+ plus 4p QSFP line card - N9K-X9464PX" (EOL13402), Cisco, 2020 (amended). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-743849.html (accessed 2026-08-13).

[20] "Cisco Nexus 9500 Series Switches Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/datasheet-c78-729404.html (accessed 2026-08-13).

[21] "Cisco Nexus 9500 Classic Line Cards and Fabric Modules Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/datasheet-c78-741336.html (accessed 2026-08-13).

[22] "Cisco Nexus 9500 Cloud-Scale Line Cards and Fabric Modules Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/datasheet-c78-736677.html (accessed 2026-08-13).

[23] "Cisco Nexus 9500 R-Series Line Cards and Fabric Modules Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/datasheet-c78-738321.html (accessed 2026-08-13).

[24] "End-of-Sale and End-of-Life Announcement for the Cisco Nexus 9500 4-Core/4-Thread Supervisor - N9K-SUP-A," Cisco, 2020. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/eos-eol-notice-c51-743848.html (accessed 2026-08-13).
