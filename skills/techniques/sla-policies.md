# SLA Policies / App-Aware Routing

- SD-WAN's routing decision is per-application (or per-traffic-class), not just
  per-destination-prefix like traditional routing — the same destination can be
  reached over different transports (MPLS, broadband, LTE/5G) depending on which
  app is generating the traffic and what SLA class it's assigned.
- **SLA classes** are defined in terms of measured path characteristics — loss,
  latency, jitter — against thresholds appropriate to the app (e.g. voice/video
  need tight jitter/loss bounds, bulk data transfer tolerates much looser ones).
  The design work is setting realistic, app-appropriate thresholds, not copying
  defaults across every app.
- **BFD** (or vendor-equivalent, e.g. Cisco's BFD-based "vSmart" health checks) on
  each transport gives sub-second path-quality detection so app-aware routing can
  fail traffic over to a compliant path before the user notices degradation —
  this active probing is what differentiates SD-WAN's failover from static routing
  with a longer IGP/BGP convergence timer.
- Circuit diversity matters as much as the policy: app-aware routing can't route
  around a shared failure domain (e.g. two "diverse" broadband circuits from the
  same last-mile provider, or transports sharing a common upstream). Ask about
  actual carrier/path diversity before promising an SLA class is protected.
