# Wireless

- **WLC** (Wireless LAN Controller) architecture choice: centralized (controller in
  DC/campus core, CAPWAP tunnels from every AP) vs. distributed/cloud-managed
  (control plane in the cloud, local data plane at the AP or a local gateway).
  Centralized gives tighter roaming and policy consistency across a large campus;
  cloud-managed lowers on-prem footprint and suits distributed multi-site orgs
  with no local WAN engineering per site.
- **AP density** is driven by client count and application requirements, not just
  square footage — voice/video and high-density areas (auditoriums, stadiums) need
  a capacity-planning pass (concurrent clients per AP, channel width, contention),
  not just an RF coverage predictive survey. Coverage-only surveys under-provision
  for anything beyond best-effort data.
- **RF planning**: channel plan (20/40/80 MHz — wider channels raise per-client
  throughput but reduce the number of non-overlapping channels available, worsening
  co-channel interference at high AP density), transmit power (lower power + more
  APs generally outperforms fewer APs at high power for capacity-dense designs),
  and band steering (nudging dual-band clients to 5/6 GHz to keep 2.4 GHz for
  legacy/IoT devices that need it).
- Wi-Fi 6E/7 introduces 6 GHz — effectively a clean, less contested band today, but
  its shorter range means it doesn't just add capacity for free, it also changes the
  AP placement/density math versus a 5 GHz-only design.
