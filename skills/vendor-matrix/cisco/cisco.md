# Cisco

## CVDs (Cisco Validated Designs)

- CVDs are Cisco's published, tested reference architectures for a given use case
  (campus, DC fabric, SD-WAN, etc.) — treat them as a strong starting point and a
  way to sanity-check a design against what Cisco has actually tested at scale,
  not as a substitute for sizing to the customer's real numbers.
- They're most useful for validating component compatibility (which platform/OS
  version combinations are tested together) and for borrowing scale/timer
  guidance (e.g. max APs per WLC, max leafs per spine pair) rather than for
  novel or edge-case designs, which often fall outside what a CVD covers.
- SD-Access (fabric-based campus, built on CVD guidance) is Cisco's routed-access/
  overlay campus architecture — relevant whenever a campus design question leans
  toward "routed access + segmentation via SGT" rather than traditional
  three-tier (see [techniques/core-agg-access.md](../../techniques/core-agg-access.md)
  and [techniques/nac.md](../../techniques/nac.md)).

## Silicon One

- Cisco's custom, merchant-silicon-competing ASIC family, used across both
  service-provider routing (8000 series) and, increasingly, DC switching — a
  departure from Cisco's historical practice of separate custom ASICs per product
  line (e.g. UADP for Catalyst, Cloud Scale for Nexus).
- The pitch is a unified silicon/software base spanning routing and switching, so
  features and forwarding behavior converge across what used to be very different
  platforms — worth checking current-generation Nexus/Catalyst hardware for
  whether it's Silicon One-based or legacy ASIC, since it affects feature parity
  and buffer/telemetry capabilities relevant to AI fabric and DC design.

## Catalyst vs. Nexus

- **Catalyst** is the campus/enterprise-access product line — IOS-XE based,
  optimized for port density, PoE, wireless integration (WLC/Mobility Express),
  and NAC/802.1X feature depth. Default choice for
  [techniques/core-agg-access.md](../../techniques/core-agg-access.md),
  [wireless.md](../../techniques/wireless.md), [nac.md](../../techniques/nac.md), and
  [poe.md](../../techniques/poe.md).
- **Nexus** is the data-center switching line — NX-OS based, optimized for
  low-latency, high-radix spine-leaf fabrics, VXLAN/EVPN, and DC-specific
  telemetry (e.g. buffer/queue visibility for AI fabric tuning). Default choice for
  [techniques/spine-leaf-clos.md](../../techniques/spine-leaf-clos.md),
  [vxlan.md](../../techniques/vxlan.md), [evpn.md](../../techniques/evpn.md), and
  [ai-gpu-fabric.md](../../techniques/ai-gpu-fabric.md).
- Using Catalyst gear in a DC fabric role (or vice versa) is usually a sign the
  design inherited the wrong product line rather than a deliberate choice — flag
  it if seen, since feature sets (EVPN maturity, buffer architecture, PoE) diverge
  meaningfully between the lines.

## IOS-XE vs. NX-OS

- **IOS-XE**: the modern, Linux-based successor to classic IOS, used across
  Catalyst (campus) and ISR/ASR (routing/WAN edge) — one control-plane OS across
  a broad hardware range, with model-driven telemetry (YANG/NETCONF/gNMI)
  layered on top of traditional CLI.
- **NX-OS**: Nexus's OS, purpose-built for DC switching workloads — has native
  strengths in VXLAN/EVPN configuration model, VDC/multi-tenancy at the OS level,
  and DC-specific automation hooks (NX-API). Not the same OS lineage as IOS-XE,
  so config syntax and automation tooling don't transfer directly between them —
  plan operational training/tooling per platform, not as one Cisco skillset.

## DC fabric: ACI vs. NX-OS-native EVPN-VXLAN

Two distinct, non-interoperable solutions for the same DC fabric role, each with
its own release cadence and architecture — this is why each gets its own file
rather than being a paragraph here.

- **[ACI](aci.md)** (Application Centric Infrastructure) is Cisco's SDN/policy-
  controller overlay for Nexus DC fabrics (APIC as the controller) — a declarative,
  application-profile-based policy model (EPGs/contracts) trading some flexibility
  for centralized management.
- **[NX-OS-native EVPN-VXLAN](nxos-vxlan.md)** is the standards-based (RFC 7432/
  8365), box-by-box BGP EVPN control plane over VXLAN — see
  [techniques/vxlan.md](../../techniques/vxlan.md) and
  [techniques/evpn.md](../../techniques/evpn.md) for the vendor-neutral mechanics
  either solution rides on. Its microsegmentation feature,
  **[GPO](nxos-gpo.md)** (Group Policy Option), gets its own file — it has its
  own dedicated whitepaper, and unlike the RFC 7432/8365 baseline it rides on,
  GPO itself is based on still-unratified IETF drafts.
- Relevant whenever a DC design question is really "should the fabric be
  controller-managed" rather than just "what topology" — this is a real fork in
  the road, not a minor implementation detail, since operational model,
  multi-vendor interop, and lock-in profile differ substantially between them.
  See **[aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md)** for the full head-to-head
  comparison, judgment call, and the 2026 Cisco convergence ("Nexus One") update.

## Nexus hardware (platform models, specs & lifecycle)

Nexus switch hardware across the portfolio — models, port counts, NX-OS trains,
and lifecycle/EOL data, including the current Nexus 9500 entry and the 7-5-2-era
platforms (N7K/N5K/N2K): [nexus-hardware.md](nexus-hardware.md).

## Classic DC three-tier — Nexus "7-5-2" (N7K / N5K / N2K)

The pre-VXLAN/EVPN data center stack (N7K core + N5K aggregation + N2K FEX
access). **Obsolete for new builds** — the successor is Nexus 9000 spine-leaf
with EVPN-VXLAN (ACI or NX-OS-native; see the DC fabric section above). Still
widely deployed, but retired piece-by-piece by official signals: N2K FEX EOL
(official replacement = 9300 leaf), N2K FEX dropped from NX-OS 10.6(3)F, N7700
EOL (replacement = Nexus 9500/9800). The FEX access model cannot be continued on
any current platform.

- **Design, limitations, upgrade path** (options A/B, operating premise):
  [nexus-752-architecture.md](nexus-752-architecture.md)
  (platform hardware and EOL data for these platforms: see the Nexus hardware
  section above)

