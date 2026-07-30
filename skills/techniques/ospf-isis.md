# IGP — OSPF & IS-IS

- The underlay IGP provides reachability between loopbacks (VTEP sources, BGP
  peer endpoints, anycast-gateway addresses) in a routed fabric. Its job is
  fast convergence and ECMP, not path engineering — that belongs above it
  (BGP, SR).
- Both OSPF and IS-IS are link-state protocols with similar convergence
  characteristics; the choice between them in a DC fabric is often driven by
  operational familiarity rather than a technical win, but there are
  differences that matter at scale.

## OSPF

- **Area design**: a single area (area 0, backbone) is the default and correct
  choice for spine-leaf Clos fabrics — the topology is already two-tier, so
  multi-area OSPF adds complexity without benefit. Multi-area design matters
  in campus/distribution layer or WAN aggregation topologies where a
  two-level hierarchy maps to real geographic or administrative boundaries.
- **Link type**: point-to-point (not broadcast) on spine-to-leaf links,
  eliminating DR/BDR election overhead and cutting convergence time — this is
  a one-line config change (`ip ospf network point-to-point` / `ospf
  network-type p2p`) that materially reduces the failure-domain blast radius.
- **Timers**: sub-second hello (1s) and dead-interval (3–4s) plus BFD for
  sub-100ms failure detection. Cisco and Huawei both support BFD on OSPF.
- **Scaling**: OSPF's flooding domain includes every LSA update across the
  entire area — in large fabrics (hundreds of nodes), LSA processing overhead
  becomes the limiting factor. This is why [BGP](bgp.md) is the preferred
  underlay protocol in DC fabrics at scale ([spine-leaf-clos.md](spine-leaf-clos.md)),
  and OSPF/IS-IS serve as the underlay IGP for BGP's next-hop reachability.

## IS-IS

- **Encapsulation**: IS-IS rides directly on L2 (not IP), using CLNS
  addressing — it doesn't share an IP protocol number with any IP-based
  protocol, so it's immune to IP-layer attacks that could target OSPF.
- **Level design**: Level-1 (intra-area, analogous to OSPF non-backbone) and
  Level-2 (backbone). In a spine-leaf fabric, run Level-2 only — the
  topological simplicity doesn't warrant a two-level hierarchy.
- **TLV extensibility**: IS-IS's TLV (Type-Length-Value) structure makes it
  easier to extend with new capabilities (SR, flex-algo) without protocol
  version churn — the TLV is silently ignored by nodes that don't understand
  it. This is why IS-IS is the more common IGP choice in SR/SRv6 designs
  ([segment-routing.md](segment-routing.md)).
- **Timers**: sub-second hello (1s, with sub-second for fast hellos on some
  platforms) and 3× hello for dead-interval. BFD overlay for sub-100ms.

## OSPF vs. IS-IS: when each wins

| Scenario | Recommendation | Why |
|---|---|---|
| Small-to-medium DC fabric (tens of leafs) | Either | Both converge fast enough; operator familiarity should decide |
| Large DC fabric (hundreds of nodes) | IS-IS | TLV extensibility for SR, no IP-layer attack surface, simpler flooding domain management at scale |
| Campus or WAN aggregation | OSPF | Broader operator familiarity, multi-area maps naturally to geographic boundaries |
| Segment Routing deployment | IS-IS | De facto IGP for SR; most vendor SR implementations and documentation assume IS-IS |
| Cross-vendor (Cisco ↔ Huawei) | Either | Both vendors implement both protocols; no interop gap specific to either |
| Extreme Networks (Fabric Engine) | IS-IS | Fabric Engine (VOSS/SPBm) uses IS-IS as its native control plane [1] |

## Cross-vendor / variants

- **Timers must match**: hello/dead intervals, LSA/LSP refresh timers,
  SPF-throttle timers — a mismatch doesn't prevent adjacency, but it can cause
  flapping adjacency if one side declares the neighbor dead before the other
  sends its next hello.
- **Area/Level IDs**: consistent numbering across vendors — Cisco uses
  dotted-decimal for OSPF areas (`area 0.0.0.0`) while Huawei accepts both
  dotted and integer (`area 0`); IS-IS area addresses are hex strings on both.
- **Authentication**: both support MD5 and SHA HMAC; key IDs and key strings
  must match exactly. Cisco defaults to no authentication; Huawei may default
  to no authentication but the CLI syntax differs — configure explicitly on
  both sides rather than relying on defaults.
- **MTU**: OSPF adjacency won't form if interface MTU mismatches between
  neighbors (unless `mtu-ignore` is set) — this is a common first-connect
  failure in cross-vendor links. IS-IS doesn't have this problem since it
  rides on L2.

## Design considerations

- **OSPF vs. IS-IS selection**: see the decision table under [OSPF vs. IS-IS:
  when each wins](#ospf-vs-is-is-when-each-wins). The choice is typically driven
  by operator familiarity for small-to-medium fabrics; IS-IS wins at scale and
  for Segment Routing deployments due to TLV extensibility.
- **Area/level planning**: single-area OSPF or single-level IS-IS is the
  default and correct choice for spine-leaf Clos fabrics — multi-area/level
  design only adds value when the topology maps to real geographic or
  administrative boundaries (campus distribution, WAN aggregation).
- **Point-to-point link type**: always use point-to-point (not broadcast) on
  spine-to-leaf links — eliminates DR/BDR election overhead and speeds up
  adjacency bring-up. Configure explicitly on both sides.
- **BFD**: sub-100ms failure detection via BFD on all fabric links; both Cisco
  and Huawei support BFD on OSPF and IS-IS.

## Relationship to other techniques

- [bgp.md](bgp.md) — BGP is the preferred underlay protocol at fabric scale;
  OSPF/IS-IS provide the IGP reachability that BGP's next-hop resolution depends on.
- [spine-leaf-clos.md](spine-leaf-clos.md) — the spine-leaf topology determines
  the IGP design: single-area/flat (no multi-area needed) and point-to-point links.
- [segment-routing.md](segment-routing.md) — IS-IS is the de facto IGP for SR
  due to TLV extensibility; most SR implementations assume IS-IS.

## References

[1] Extreme Networks, "Fabric Engine (VOSS) — SPBm IS-IS Control Plane."
    *Changeable* — verify at Extreme Networks documentation:
    https://documentation.extremenetworks.com/
    Search for "Fabric Engine" or "SPBm" in current release documentation.
    See [skills/vendor-matrix/extreme-networks.md](../vendor-matrix/extreme-networks.md)
    for full Extreme Fabric details.
    Last confirmed: not fetched — written from architecture knowledge.
