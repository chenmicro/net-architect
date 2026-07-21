# Segment Routing (SR-MPLS / SRv6)

- SR replaces per-hop signaling (LDP/RSVP-TE state on every transit router, see
  [mpls.md](mpls.md)) with source-routed paths: the ingress node encodes the path
  as a stack of segments (instructions), and transit nodes just forward based on
  the top segment — this removes the per-LSP state problem of RSVP-TE while
  keeping (and extending) traffic-engineering capability.
- **SR-MPLS** reuses the existing MPLS label stack/data plane — segments are MPLS
  labels — so it can be introduced incrementally onto an existing MPLS core with
  no data-plane forklift, which is usually the deciding factor for brownfield
  MPLS networks.
- **SRv6** encodes segments as IPv6 addresses in a Segment Routing Header, native
  to the IPv6 data plane — no MPLS label stack at all. This suits greenfield
  IPv6-native builds or networks wanting to converge on a single IPv6 data plane
  across access/core/services, at the cost of larger packet headers and requiring
  IPv6 and SRv6-capable hardware/software throughout the path.
- **SR-TE policies** express traffic engineering as a set of candidate paths
  (explicit SID lists or constraint-based) bound to a color/intent, computed
  either locally (via IGP/flex-algo) or by a centralized **PCE** (Path Computation
  Element, via PCEP) — the design choice is distributed (simpler, IGP-driven,
  good for well-understood topologies) vs. centralized PCE (better for complex,
  frequently-changing constraints or cross-domain TE).
- Flex-algo is worth calling out separately from generic SR-TE: it lets the IGP
  compute multiple shortest-path topologies against different metrics/constraints
  (e.g. low-latency vs. high-bandwidth) without needing an explicit path or a PCE,
  useful when the TE requirement is "always pick the low-latency path for this
  traffic class" rather than a one-off engineered path.
