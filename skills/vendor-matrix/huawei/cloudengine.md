# Huawei CloudEngine

The device layer of the data center domain: CloudEngine switches execute what
[CloudFabric](cloudfabric.md) plans and provisions, and can also run without a
controller as manually configured EVPN-VXLAN. This file records what the platforms
and releases can do. Protocol behavior lives in the
[technique files](../../techniques/). See the [Huawei hub](huawei.md) for VRP and
other product lines.

## Role and capabilities

- **CloudEngine (CE series)**: Huawei's data-center switching line —
  spine-leaf/Clos fabrics, EVPN-VXLAN, and (on current-generation platforms)
  AI/GPU-fabric-oriented features (RoCEv2 lossless tuning, deep buffers,
  high-radix 400G/800G) — the default choice for
  [techniques/spine-leaf-clos.md](../../techniques/spine-leaf-clos.md),
  [vxlan.md](../../techniques/vxlan.md), [evpn.md](../../techniques/evpn.md), and
  [ai-gpu-fabric.md](../../techniques/ai-gpu-fabric.md). Huawei's VXLAN header
  extensions — GBP-based microsegmentation and the patented group/application
  identifiers — are documented in
  [techniques/vxlan.md](../../techniques/vxlan.md) (§Cross-vendor / variants), not
  duplicated here.
- Huawei has invested heavily in RoCEv2-based AI fabric positioning
  (competing directly with Nvidia/Mellanox-centric and Arista/Cisco AI-fabric
  offers) on current CloudEngine hardware — relevant to surface specifically
  in AI/GPU fabric vendor comparisons, not just general DC fabric ones.

## Version line: V300 (current), V200 (legacy)

- Current-generation CloudEngine switches (CE16800, CE8800, CE6800 series)
  ship on **V300** (**V300R026C00**, Sep. 2026, for CE9800/8800/6800 [1]; **V300R025C10**, ~2025; also V300R024C00, 2024;
  V300R023C00, 2023; V300R022C00, 2022 — see version-mapping page [2] for
  the full compatibility matrix). The version format is
  `V<major>R<year>C<build>` — e.g. R025 = release for 2025 [3].
  The V300 line is still VRP-based — Huawei's own Common Criteria cert
  describes it as "CE16800&CE8800&CE6800 Series Switches running VRP software
  V300R02" [4]. Earlier CloudEngine releases used V200 (V200R020C10 / V200R019C10).
- The VRP software version bundled with V300 host software is **VRP V800**
  (e.g. V300R022C00 ships VRP V800R022C05; V300R021C10 ships VRP V800R021C04) [2].
- V300 is functionally similar in CLI structure to V200 but adds newer hardware
  support, deeper EVPN-VXLAN scale, and AI-fabric-specific capabilities
  (enhanced RoCEv2 tuning, larger forwarding tables). Overall config model and
  operator knowledge transfer from V200 to V300 are straightforward — the same
  VRP skills apply.
- Delta documentation accompanies the release line: the V300R024C00 set covers
  commands, traps, MIBs, YANG models, and telemetry [5]. A CLI fact — whether a
  command exists, and what it defaults to — is therefore only valid for the
  release it was read from; record that release next to the fact.

## References

[1] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation,"
Huawei, V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login required). Verify in:
the library title and issue metadata. Confirmed Oct. 31, 2026.

[2] "CloudEngine Switches Software Versions," Huawei Support. [Online]. Available: https://info.support.huawei.com/network/ptmngsys/Web/DC/en/version-mapping.html

[3] "CloudEngine 16800 V300R025C10 Log Reference," Huawei Support, updated April 2026. [Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100561851/bbf994b3

[4] "Huawei CE16800&CE8800&CE6800 Series Switches running VRP software V300R02," Common Criteria Portal, certification document. [Online]. Available: https://www.commoncriteriaportal.org/files/epfiles/huawei-ce16800ce8800ce6800-series-switches-running-vrp-software-v300r02.pdf

[5] "CloudEngine 16800, 9800, 8800, and 6800 V300R024C00 Command, Trap, MIB, YANG, and Telemetry Delta Information," Huawei Support, 2024. [Online]. Available: https://support.huawei.com/enterprise/en/switches/cloudengine-58-68-78-88-98-pid-252837181
— cited for the existence and scope of per-release delta documentation, not for
any specific command or default. Not re-verified Oct. 16, 2026: support.huawei.com
was unreachable from this environment (robots policy/HTTP 403).
Re-confirm the page and its release scope when the site is reachable.
