# MPLS

- MPLS forwards on a label rather than a longest-prefix-match IP lookup at each
  transit hop, which is what enables traffic engineering and VPN services that plain
  IP routing can't express cleanly. Understand it as an enabling data plane for the
  services below, not an end in itself.
- **LDP** (Label Distribution Protocol) distributes labels hop-by-hop following the
  IGP's shortest path — simple, but ties the label-switched path to whatever the
  IGP already computed, with no traffic-engineering control.
- **RSVP-TE** signals explicit-path LSPs with bandwidth reservation and constraints,
  enabling actual traffic engineering (route around a congested or avoided link)
  at the cost of per-LSP state on every transit router — a scaling concern at
  large route/tunnel counts, part of why [segment-routing.md](segment-routing.md)
  has displaced it in newer builds.
- **L3VPN** (RFC 4364, "2547bis"): PE routers hold per-customer VRFs, MP-BGP
  distributes VPN-IPv4/IPv6 routes with route-distinguishers and route-targets
  between PEs, MPLS labels provide the data-plane separation across the shared
  P (provider core) routers. This is the standard model for any-to-any routed
  VPN service across a WAN/service-provider core. See [bgp.md](bgp.md) for the
  route-reflector and community mechanics MP-BGP relies on at scale.
- **L2VPN** (VPWS for point-to-point, VPLS for multipoint L2) extends the same PE/P
  core to deliver Ethernet-like L2 connectivity instead of routed L3 — pick L2VPN
  when the customer needs to run their own routing/L2 adjacency across the WAN
  (e.g. stretching a VLAN or L2 DCI between sites) rather than handing off routes.
