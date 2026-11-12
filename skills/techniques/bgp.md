# BGP

BGP-4 carries reachability between autonomous systems and, with multiprotocol
extensions, the overlay and VPN address families used in DC and WAN designs.

## Protocol mechanics

- **eBGP vs iBGP**: eBGP between autonomous systems (customer-to-provider,
  provider-to-provider, or between distinct network domains internally); iBGP
  within a single AS to carry externally-learned routes consistently across
  internal routers. iBGP's full-mesh requirement (routes learned via iBGP aren't
  re-advertised to other iBGP peers by default) is the reason route reflectors
  exist.
- **AS loop detection**: a route whose AS_PATH contains an AS loop should be
  excluded from route selection. A speaker detects the loop by scanning the full
  AS path for its own AS number. Accepting routes that carry the local AS is
  outside the scope of the BGP-4 specification [1].
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

## Cross-vendor / variants

Because accepting routes that carry the local AS falls outside BGP-4 [1], each
vendor implements it as its own per-peer option. Check the device documentation for
the command and its occurrence limit before relying on it.

- **Cisco Secure Firewall Threat Defense (FTD), FMC 10.x**: by default eBGP advertises
  learned routes back to the same peer, leaving the peer's loop check to discard them.
  A firewall meant to only receive routes therefore needs an explicit outgoing filter.
  The neighbor's AS Override option replaces the originating AS with the sender's AS,
  for discontiguous segments that share an ASN. Neighbor filtering takes incoming and
  outgoing access lists, route maps, prefix lists, and AS-path filters [2].
- **Huawei CloudEngine (V300R026C00)**: BGP selects routes independently of the IP
  routing table and by default advertises every route it selects, active or not.
  `active-route-advertise` limits advertisement to routes active in the IP routing
  table. `routing-table rib-only [ route-policy <name> ]` keeps BGP routes, or only
  those matching the policy, out of the IP routing table. Because the two commands are
  mutually exclusive, a rib-only route is advertised but not used for forwarding [3].
  Communities: a device advertises none to a peer, BGP-EVPN peers included, until
  `peer … advertise-community` is set. So every hop, route reflectors included, needs
  it for a community to survive. `apply community` replaces a route's communities
  unless `additive` is given. With `peer … route-policy … export`, only routes that
  match the policy are advertised, so a tagging policy needs a node that matches
  everything [3].

## Design considerations

- Peering hygiene fundamentals to always check for in a review: max-prefix limits
  on all eBGP sessions, explicit inbound/outbound filtering (prefix-lists or
  AS-path filters, not "accept everything from a trusted peer"), and BGP session
  authentication (MD5 or, preferably, TCP-AO) on external sessions.
- **Sites that share an AS**: when two sites learn each other's routes over eBGP
  through a transit AS, AS loop detection drops them if both sites use the same AS
  [1]. Give each site its own AS, or accept the own-AS exception per peer
  deliberately.

## Relationship to other techniques

This file covers BGP-the-protocol; domain-specific applications live in their own
technique files and link back here for the shared mechanics rather than
re-explaining them:

- [spine-leaf-clos.md](spine-leaf-clos.md): DC underlay, one AS per node with eBGP
- [evpn.md](evpn.md): EVPN overlay, commonly iBGP with route reflectors
- [mpls.md](mpls.md): L3VPN's MP-BGP, route distinguishers and route targets

## References

[1] Y. Rekhter, T. Li, and S. Hares, Eds., "A Border Gateway Protocol 4 (BGP-4),"
RFC 4271, Jan. 2006, §9.1.2. https://www.rfc-editor.org/rfc/rfc4271

[2] "Cisco Secure Firewall Management Center Device Configuration Guide, 10.x," Cisco.
Verify in: Routing > BGP (BGP attributes note; Configure BGP Neighbor Settings).
https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/device-config/100/management-center-device-config-10-0/routing-bgp.html
Confirmed Nov. 12, 2026.

[3] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation," Huawei,
V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login required).
Verify in: References > Command Reference > IP Routing > BGP Configuration Commands >
routing-table rib-only and active-route-advertise (BGP-VPN instance IPv4 address family
view); > VXLAN > VXLAN Configuration Commands > peer advertise-community and peer
route-policy export (BGP-EVPN address family view); > Routing Policy Configuration Commands >
apply community; Configuration > Configuration Guide > IP Routing Configuration > BGP Configuration >
Configuring Active-Route-Advertise > Understanding Active-Route-Advertise. Confirmed Nov.
12, 2026.
