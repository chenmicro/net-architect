# Juniper

## JVDs (Juniper Validated Designs)

- Juniper's equivalent of a tested reference architecture per use case (DC
  fabric, campus, WAN edge) — same role as Cisco's CVDs: use for
  compatibility/scale sanity-checking, not as a substitute for sizing against
  the actual deployment's numbers.
- JVDs for DC fabric lean heavily on EVPN-VXLAN with Juniper's own
  automation/orchestration layer (historically Apstra, now integrated into
  Juniper's broader AI-Native Networking Platform) — worth checking whether a
  given JVD assumes Apstra-based intent-driven fabric management or a
  manually-configured EVPN-VXLAN build, since the operational model differs
  substantially.

## Junos / Junos Evolved

- **Junos** is Juniper's long-standing, FreeBSD-derived NOS with a consistent
  CLI and configuration model (structured, transactional config with commit/
  rollback) across routing and switching platforms — the commit-confirm/
  rollback model is a genuine operational strength worth calling out in change-
  management-sensitive designs, since a bad config auto-reverts if not
  confirmed within a timer.
- **Junos Evolved** is the Linux-based, containerized re-platforming of Junos
  used on newer high-end platforms (e.g. PTX, some QFX) — same config model and
  CLI experience as classic Junos, but with a Linux-native underlying OS
  enabling better container/microservices packaging of routing protocol
  daemons and third-party app hosting. Check per-platform whether it's classic
  Junos or Junos Evolved, since supported features and third-party app hosting
  capability differ.
- One consistent config/CLI model across the whole portfolio (contrast with
  Cisco's IOS-XE/NX-OS split) is Juniper's traditional differentiator — relevant
  when a design spans multiple Juniper platform families and operational
  consistency across them is a stated goal.

## Mist AI

- Juniper's AI-driven operations layer (from the Mist Systems acquisition),
  originally wireless-focused and now extended across wired/campus and
  increasingly DC — cloud-managed, with a strong emphasis on proactive
  anomaly detection and automated root-cause analysis rather than
  dashboard-and-alert-only monitoring.
- **Marvis** is Mist's virtual network assistant — a conversational/AI
  interface over the collected telemetry, aimed at reducing time-to-root-cause
  for common issues (client connectivity failures, RF problems, DHCP/AAA
  failures) by correlating telemetry automatically rather than requiring an
  engineer to manually cross-reference logs across systems.
- Wireless assurance (SLE — Service Level Expectations — metrics: time-to-
  connect, throughput, roaming, coverage) is Mist's most mature area given its
  origin as a wireless company — a strong fit when a campus wireless design
  explicitly prioritizes measurable, AI-driven assurance over traditional
  WLC dashboards (see [techniques/wireless.md](../techniques/wireless.md)).

## MX vs. PTX

- **MX series**: Juniper's services/edge routing platform — broad feature
  depth for L3VPN/L2VPN, subscriber management, and WAN-edge functions;
  the default choice for a service-provider-edge or enterprise WAN-edge role — see
  [techniques/mpls.md](../techniques/mpls.md).
- **PTX series**: Juniper's core/DC-oriented high-density routing platform —
  optimized for raw throughput and port density (core transit, DC
  interconnect, high-radix DC fabric spine) over the deep services feature set
  MX carries; typically Junos Evolved-based on current generations.
- Choosing between them is a role question, not a raw-performance one: MX
  where rich edge services (VPN termination, subscriber policy) are required,
  PTX where the role is high-throughput transit/core/DCI without that services
  depth — using PTX in an edge-services role (or MX where pure high-radix
  core throughput is the ask) is usually a sign of a role mismatch worth
  flagging.
