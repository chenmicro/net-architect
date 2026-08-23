# Spine-Leaf (Clos) Fabric

A spine-leaf fabric is a two-stage Clos topology: every leaf connects to every
spine, with no leaf-to-leaf or spine-to-spine links inside the fabric. This
complete bipartite structure gives any leaf-to-leaf path one spine transit and
makes capacity growth a matter of adding spine paths within the available leaf
and spine radix.

[Figure 1 — Two-spine, four-leaf Clos fabric](spine-leaf-clos-fig1.drawio)

The figure is an atomic schematic rather than a deployment bill of materials.
Its eight links represent complete K(2,4) leaf-to-spine coverage.

## Cross-vendor / variants

The physical Clos structure is vendor-neutral. This library uses `Leaf` because
it identifies the fabric role without implying where the device is installed.
Interoperability depends on the protocols and feature profiles selected for the
underlay and overlay, not the role name.

Large data-center routed fabrics commonly use eBGP in the underlay; RFC 7938
documents this design pattern and its operational considerations [1]. An IGP is
also possible when its flooding, addressing, convergence, and operational model
better match the environment. Align MTU, BFD/timers, ECMP behavior, route policy,
and supported link speeds across vendors.

## Design considerations

- **Oversubscription** is the ratio of aggregate server-facing bandwidth to
  aggregate spine-facing bandwidth on a leaf. Select it from measured east-west
  and north-south demand rather than from a default. Evaluate 1:1 when the
  workload cannot tolerate oversubscription; see
  [ai-gpu-fabric.md](ai-gpu-fabric.md) for workload-specific constraints.
- **ECMP entropy** determines whether the installed paths translate into usable
  capacity. Verify the production hash inputs and test elephant-flow behavior;
  a single large flow can still produce a hot link under static flow hashing.
- **Radix and speed** follow the target rack count, host-facing port demand,
  uplink speed, and oversubscription target. Reserve ports for growth and define
  the failure case before choosing a switch model.
- **Resiliency** requires every leaf to retain an acceptable capacity level after
  a spine or uplink failure. State whether the objective is N+1, N+2, or full
  non-blocking capacity during failure.
- **Cabling coverage** must be mechanically verified: every intended leaf-spine
  pair exists exactly once, with no accidental same-tier link.

## Relationship to other techniques

- [BGP](bgp.md) supplies shared peering mechanics, policy, and session hygiene
  when eBGP is used as the underlay.
- [EVPN](evpn.md) can provide the overlay control plane above the routed fabric.
- [VXLAN](vxlan.md) supplies the overlay data-plane encapsulation carried across
  the underlay.
- [AI/GPU Fabric](ai-gpu-fabric.md) applies Clos design to loss-sensitive,
  high-bandwidth training traffic and may require rail-aware topology choices.

## References

[1] P. Lapukhov, A. Premji, and J. Mitchell, “Use of BGP for Routing in Large-Scale
Data Centers,” RFC 7938, Aug. 2016. https://www.rfc-editor.org/rfc/rfc7938
