# AI/GPU Training Cluster Buildout

## Composes

1. [skills/techniques/ai-gpu-fabric.md](../techniques/ai-gpu-fabric.md) — RoCEv2/
   lossless Ethernet, rail-optimized topology, non-blocking fabric norm, InfiniBand vs.
   Ethernet tradeoff. This is the primary file; everything else in this scenario
   feeds constraints back into it.
2. [skills/techniques/spine-leaf-clos.md](../techniques/spine-leaf-clos.md) — read
   together with (1), not independently: oversubscription, ECMP/hashing, and spine
   radix all get reinterpreted under the AI-fabric constraints (non-blocking target,
   rail-optimized cabling) rather than the general-purpose defaults that file
   otherwise describes.
3. The relevant [skills/vendor-matrix/](../vendor-matrix/) file, once a vendor is named
   or being evaluated — buffer architecture (shared vs. per-port) and ASIC radix are
   exactly what determines whether the topology from (1)+(2) is actually buildable on
   that platform.

## Cross-cutting judgment

- Rail-optimized topology, non-blocking fabric, and vendor SKU choice are one joint
  decision, not three sequential ones. GPU NIC count per node (rail count) has to be
  reconciled against spine port count *before* a SKU is picked — picking the platform
  first and then discovering it can't deliver the radix the rail layout needs is a
  common, expensive-to-unwind mistake.
- InfiniBand-vs-Ethernet (raised as a live tradeoff in the AI/GPU Fabric section)
  should be decided before fabric sizing, not after — it changes the topology math
  entirely (IB fat-tree conventions vs. Ethernet Clos), not just a component swap
  within the same design.
- Buffer depth and ASIC architecture (vendor-matrix) matter more here than in
  general-purpose DC design because of collective-operation sensitivity to a single
  dropped packet — don't carry over a general-purpose vendor recommendation without
  re-checking its buffer behavior against this workload specifically.

## Questions to ask early

- GPU/node count and NICs-per-GPU (rail count) — this is the number that drives both
  spine radix and leaf port allocation.
- Single large job spanning the whole cluster vs. multi-tenant job scheduling — changes
  whether non-blocking is a hard requirement everywhere or just within job-sized
  partitions.
- Facility power/cooling ceiling — can cap fabric options (port speed, chassis density)
  independent of anything network-specific.
- Existing operational expertise and preference: InfiniBand shop vs. Ethernet/RoCEv2
  shop, and whether multi-vendor interoperability matters for this build.
