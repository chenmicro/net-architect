# Spine-Leaf (Clos) Fabric

- Every leaf connects to every spine; no leaf-to-leaf or spine-to-spine links. This
  bounds any endpoint-to-endpoint path to exactly two hops (leaf → spine → leaf) and
  makes bandwidth scaling a matter of adding spines, not redesigning the topology.
- **Oversubscription** is the ratio of downlink (server-facing) to uplink (spine-facing)
  bandwidth on a leaf. 3:1 is common for general-purpose compute; AI/ML and storage
  fabrics increasingly target 1:1 (non-blocking) — see [ai-gpu-fabric.md](ai-gpu-fabric.md).
- **ECMP** across all spine uplinks is what makes the fabric a fabric rather than a
  collection of paths — hashing (typically 5-tuple) must be verified for entropy;
  elephant flows (e.g. single large RDMA transfers) can still land unevenly on
  static hashing and cause hot links.
- **Underlay** is almost always BGP (eBGP, one AS per leaf/spine or per rack) rather
  than an IGP — it scales to thousands of routes and avoids the flooding-domain
  and convergence characteristics of OSPF/IS-IS at fabric scale. RFC 7938 ("Use of
  BGP for Routing in Large-Scale Data Centers") is the reference design. For the
  general eBGP session mechanics and hygiene (filtering, authentication) rather than
  this fabric-specific application, see [bgp.md](bgp.md).
- Fabric size dictates spine count and port speed mix, not the reverse — decide
  target rack count and oversubscription first, then work out spine radix and
  optics.
