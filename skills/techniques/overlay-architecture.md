# SD-WAN Overlay Architecture

- SD-WAN separates the control plane (orchestrator/controller — e.g. vManage,
  Versa Director, Fortinet FortiManager+FortiGate SD-WAN, Palo Alto Panorama) from
  the data plane (edge devices at each site), letting policy be authored centrally
  and pushed fabric-wide instead of box-by-box CLI changes.
- The overlay itself is typically an **IPsec** (or DTLS/TLS in some vendors' control
  channels) mesh between edges, with tunnel establishment and topology automated by
  the controller rather than hand-built — this is the core value proposition versus
  legacy DMVPN/manual VPN mesh.
- **Topology choice**: full mesh (every site to every site) gives optimal any-to-any
  paths but doesn't scale tunnel/CPU overhead linearly past a few hundred sites;
  hub-and-spoke (or partial/regional mesh) trades some path optimality for
  scalability and simpler policy. Most large deployments land on regional mesh —
  full mesh within a region, hub-and-spoke (via a DC or colo hub) between regions.
- Control-plane resiliency: verify the design accounts for controller/orchestrator
  HA and what happens to existing tunnels and policy enforcement if the controller
  is unreachable — most platforms keep the data plane running on last-known-good
  policy, but confirm this per vendor rather than assuming it.
