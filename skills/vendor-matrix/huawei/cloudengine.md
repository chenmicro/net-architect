# Huawei CloudEngine

**Scope: DPCF supported models.** Every model covered by this file is one Huawei
documents for DPCF in V300R026C00 [1], [2]:

- **CE6800**: CE6855-48T8CQ, CE6855-48XS8CQ, CE6863E-48S8CQ, CE6885, CE6885-T, CE6885H,
  CE6885L, CE6885-LL (standard forwarding mode), CE6885-SAN.
- **CE8800**: CE8851-32CQ4BQ, CE8855, CE8855-48CD8DQ, CE8855H, CE8855H-SAN, CE8856,
  CE8865, CE8865-SAN, CE8875, CE8885.
- **CE9800**: CE9855, CE9865.
- **CE16800**: X4, X8, X16, and CE16804/CE16808/CE16816 with J series cards.

Three of them are compared below: CE8865-4C, its storage-network twin CE8865-SAN-4C, and
the CE16800-X4 chassis. Earlier releases appear only in
[Version line](#version-line-v300), which exists to say which release is current.

The device layer of the data center domain: CloudEngine switches execute what
[CloudFabric](cloudfabric.md) plans and provisions, and can also run without a
controller as manually configured EVPN-VXLAN. This file records what the platforms
and releases can do. Protocol behavior lives in the
[technique files](../../techniques/). See the [Huawei hub](huawei.md) for VRP and
other product lines.

## Role and capabilities

- **CloudEngine (CE series)**: Huawei's data-center switching line — spine-leaf/Clos
  fabrics, EVPN-VXLAN, and RoCEv2 lossless tuning with deep buffers and 400GE ports —
  the default choice for
  [techniques/spine-leaf-clos.md](../../techniques/spine-leaf-clos.md),
  [vxlan.md](../../techniques/vxlan.md), [evpn.md](../../techniques/evpn.md), and
  [ai-gpu-fabric.md](../../techniques/ai-gpu-fabric.md). Huawei's VXLAN header
  extensions — GBP-based microsegmentation and the patented group/application
  identifiers — are documented in
  [techniques/vxlan.md](../../techniques/vxlan.md) (§Cross-vendor / variants), not
  duplicated here.
- **AI-fabric positioning**: Huawei markets this line directly against
  Nvidia/Mellanox-centric and Arista/Cisco offers for RoCEv2 AI fabrics, which is worth
  surfacing in AI/GPU fabric vendor comparisons rather than only in general DC ones.

## Version line: V300

- All CloudEngine switches in scope here ship on **V300** (**V300R026C00**, Sep. 2026,
  for CE9800/8800/6800 [1]; **V300R025C10**, ~2025; also V300R024C00, 2024; V300R023C00,
  2023; V300R022C00, 2022 — see version-mapping page [3] for the full compatibility
  matrix). The version format is `V<major>R<year>C<build>` — e.g. R025 = release for
  2025 [4].
  - The line is still VRP-based — Huawei's own Common Criteria cert describes it as
    "CE16800&CE8800&CE6800 Series Switches running VRP software V300R02" [5].
- The VRP software version bundled with V300 host software is **VRP V800**
  (e.g. V300R022C00 ships VRP V800R022C05; V300R021C10 ships VRP V800R021C04) [3].
- Newer V300 releases add hardware support, deeper EVPN-VXLAN scale, and
  AI-fabric-specific capabilities (enhanced RoCEv2 tuning, larger forwarding tables)
  within the same config model, so VRP skills carry across the release line.
- Delta documentation accompanies the release line: the V300R024C00 set covers
  commands, traps, MIBs, YANG models, and telemetry [6]. A CLI fact — whether a
  command exists, and what it defaults to — is therefore only valid for the
  release it was read from; record that release next to the fact.
- **CE16800 has its own library**: V300R026C00, Issue 01, September 2026 [2]. The
  CE9800/8800/6800 library does not cover it, so any CE16800 claim needs [2] or the
  chassis-specific documentation.

## Model feature support

Huawei sells the same box switch twice: a standard model for the general DC fabric and a
`-SAN` model positioned for the NVMe over RoCE storage network (its Xinghe NoF+ solution).
Port counts match line for line. Across the 163 features that V300R026C00 documents with a
"Configuration Precautions" hardware table [1], [2], exactly two differ:

| Feature | CE8865-4C | CE8865-SAN-4C | CE16800-X4 | Licence |
|---|---|---|---|---|
| iNOF — zone sync, plug-and-play, host notification; carries RPFR, hard zoning, zone isolation | No | Yes | Yes | CE-LIC-iNOF |
| Anti-locking PFC (`abs-pfc`) — lossless over DCI links longer than 10 km | No | Yes | Yes | CE-LIC-ABS |

- **The SAN model is a superset, not a variant.** IFIT, service telemetry, DPFR/DPCF,
  rPFC, AI ECN, PFC deadlock prevention, NPCC, MACsec, buffer optimisation, and the whole
  routing, switching, multicast and QoS set are documented identically on both, so a SAN
  box deploys as an ordinary leaf or spine with no functional loss. The reverse does not
  hold: no licence level adds iNOF or anti-locking PFC to a standard box.
- **Licence is the second gate.** Both differences above are licensed (`CE-LIC-iNOF`,
  `CE-LIC-ABS`), and so are some of the shared features, so a supported feature without its
  licence changes nothing in a BOM.
- **The lossless set is mostly unlicensed, with one exception.** On the CE6885H
  Configuration Precautions pages, AI ECN is under licence control (`CE-LIC-AFRD`), while
  congestion management, buffer optimisation, and PFC deadlock prevention are not [1]. Check
  each feature's own precautions page rather than assuming a lossless feature is free: the
  deadlock-prevention page also limits the feature to known unicast RoCE traffic, and
  congestion management collects drop statistics for four priorities only (default 0–3).
- **Long-distance buffer work is headroom-based.** These models split buffer by chip,
  interface, and queue, so distance is sized with the headroom pool plus the
  distance-based check.

Where the chassis leads:

- **Documented for the CE16800-X4 and not for the boxes**: DIM, Synchronization Ethernet.
- **Documented for the chassis with no box precautions page**: Intelligent Traffic
  Analysis, Intra-chassis High Reliability, NSR. An absent page rather than a proven
  restriction.

### Lossless and DCB feature set

The lossless toolkit is CloudEngine platform machinery, not a SAN-model feature: standard
models run it too, and the SAN models add iNOF and anti-locking PFC on top (previous
section). All of it is documented as chapters of **Intelligent Lossless Network
Configuration** [1], [2]:

| Feature | What it does |
|---|---|
| iLossless (PFC + AI ECN) | PFC pauses one priority hop by hop; AI ECN adapts the congestion marking to the traffic. Together they make RoCEv2 lossless without a credit protocol |
| PFC deadlock prevention | Identifies the flows that can cause a PFC deadlock and changes their queue priority, so two devices cannot pause each other indefinitely |
| rPFC | Keeps PFC at the network edge: the destination switch tells the source switch to throttle, so PFC frames do not spread through the fabric |

- The buffer split is above; the long-distance arithmetic that spends it is in
  [nof-plus.md](nof-plus.md#buffer-ecn-and-shaping).
- Each feature carries its own precautions page, and they interact — check those before
  stacking several on one interface [1], [2].

### DPCF and DPFR

- Both sit under Data Plane Fault Awareness and are licensed separately
  (`CE-LIC-DPFR`, `CE-LIC-DPCF`).
- DPCF's configuration chapter carries its own model list rather than inheriting DPFR's;
  all three models here are on it, and on the chassis it needs the X4/X8/X16, or J series
  cards on the older CE16800 chassis [1], [2].
- DPCF is not a SAN-model privilege: the standard twin carries it too.
- **Limits** [1], [2]: IPv4 unicast TCP only, with hash-seed re-marking extending to IPv6
  TCP under VXLAN; no detection when the TCP reserved bits are non-zero; non-fragmented
  packets only; needs redundant ECMP or Eth-Trunk paths to recover into; pauses detection
  above 90% CPU until it falls to 75%; co-deployment with IFIT degrades awareness and
  convergence, and IFIT wins when the two are deployed independently.

## References

[1] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation,"
Huawei, V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login
required). Verify in:
the library title and issue metadata. Confirmed Oct. 31, 2026.

[2] "CloudEngine 16800 Series Switches Product Documentation," Huawei, V300R026C00,
Issue 01, September 2026 (HedEx library EDOC1100611763, login required). Cited for the
per-feature "Configuration Precautions" hardware tables (iNOF, anti-locking PFC, buffer
optimisation, data plane fault awareness, service telemetry) and the
CE16800-X4/-X8/-X16 chassis and card list. Verify in: the library title and issue
metadata at support.huawei.com HedEx, `docid=EDOC1100611763`. Confirmed Nov. 2, 2026.

[3] "CloudEngine Switches Software Versions," Huawei Support. [Online]. Available: https://info.support.huawei.com/network/ptmngsys/Web/DC/en/version-mapping.html

[4] "CloudEngine 16800 V300R025C10 Log Reference," Huawei Support, updated April 2026. [Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100561851/bbf994b3

[5] "Huawei CE16800&CE8800&CE6800 Series Switches running VRP software V300R02," Common Criteria Portal, certification document. [Online]. Available: https://www.commoncriteriaportal.org/files/epfiles/huawei-ce16800ce8800ce6800-series-switches-running-vrp-software-v300r02.pdf

[6] "CloudEngine 16800, 9800, 8800, and 6800 V300R024C00 Command, Trap, MIB, YANG, and Telemetry Delta Information," Huawei Support, 2024. [Online]. Available: https://support.huawei.com/enterprise/en/switches/cloudengine-58-68-78-88-98-pid-252837181
— cited for the existence and scope of per-release delta documentation, not for
any specific command or default. Not re-verified Oct. 16, 2026: support.huawei.com
was unreachable from this environment (robots policy/HTTP 403).
Re-confirm the page and its release scope when the site is reachable.
