# BGP

- **eBGP vs iBGP**: eBGP between autonomous systems (customer-to-provider,
  provider-to-provider, or between distinct network domains internally); iBGP
  within a single AS to carry externally-learned routes consistently across
  internal routers. iBGP's full-mesh requirement (routes learned via iBGP aren't
  re-advertised to other iBGP peers by default) is the reason route reflectors
  exist.
- **Route reflectors** let iBGP scale past a handful of routers by replacing full
  mesh with a hub-and-spoke reflection topology — clients peer only with the
  reflector(s), not each other. Design considerations: reflector placement
  (redundant pairs, not single points of failure), cluster-ID planning to avoid
  loops when using multiple reflector layers, and confirming path diversity isn't
  lost (a reflector by default only reflects its best path — additional
  add-path or diverse-path config may be needed where multiple paths must be
  visible to clients, e.g. for fast reroute).
- **Confederations** are the alternative iBGP-scaling tool, splitting one AS into
  sub-ASes that peer with each other via eBGP-like sessions internally while
  presenting as one AS externally — used less often than route reflectors today,
  but relevant when a network is actually organized into semi-autonomous regions
  that benefit from eBGP-like policy control between them (each sub-AS boundary
  gets its own AS-path/local-pref handling) without full external AS complexity.
- **Communities** (standard, extended, and large) are the mechanism for tagging
  routes with intent that downstream policy acts on — e.g. no-export, region
  tagging, customer/peer/provider classification for a routing policy framework,
  or driving route-target behavior in L3VPN. A BGP design without a documented
  community plan tends to accumulate ad hoc, undocumented policy that's hard to
  safely change later — worth establishing a community scheme early, even for a
  network that's currently small.
- Peering hygiene fundamentals to always check for in a review: max-prefix limits
  on all eBGP sessions, explicit inbound/outbound filtering (prefix-lists or
  AS-path filters, not "accept everything from a trusted peer"), and BGP session
  authentication (MD5 or, preferably, TCP-AO) on external sessions.
- This file covers BGP-the-protocol; domain-specific applications live in their own
  technique files and link back here for the shared mechanics rather than
  re-explaining them: [spine-leaf-clos.md](spine-leaf-clos.md) (DC underlay, one-AS-
  per-node eBGP), [evpn.md](evpn.md) (EVPN overlay, commonly iBGP+route-reflector),
  [mpls.md](mpls.md) (L3VPN's MP-BGP, route-distinguishers/route-targets).
