# AI/GPU Fabric

- GPU-to-GPU traffic (RDMA, typically **RoCEv2** — RDMA over Converged Ethernet)
  is loss-intolerant in a way general compute traffic isn't: a single dropped
  packet stalls a collective operation (all-reduce, all-to-all) across the whole
  job, not just one flow. This is the central design driver.
- **Lossless Ethernet** is achieved via:
  - **PFC** (Priority Flow Control, 802.1Qbb) — pauses specific traffic classes
    hop-by-hop rather than the whole link, but is prone to head-of-line blocking
    and, misconfigured, PFC storms/deadlock across the fabric.
  - **ECN** (Explicit Congestion Notification) + **DCQCN** — marks packets before
    buffers fill so senders back off proactively, reducing reliance on PFC as the
    only congestion signal. Tuning ECN thresholds and DCQCN parameters (Kmin/Kmax,
    Alpha) is a real, fabric-specific exercise, not a default-and-forget setting.
- **Rail-optimized topology**: GPU NICs are connected such that each "rail" (e.g.
  NIC 0 across all nodes) lands on a common leaf, minimizing the number of hops
  and spine traversals for collective communication patterns — this is a deliberate
  deviation from generic spine-leaf cabling (see [spine-leaf-clos.md](spine-leaf-clos.md)),
  driven by how NCCL/collective libraries schedule traffic.
- Non-blocking (1:1) fabric is the norm for training clusters — oversubscription
  directly throttles collective-op completion time, unlike general compute where
  it's a cost/performance tradeoff.
- 400G/800G leaf uplinks and spine interconnects are now standard for large training
  clusters; buffer depth and switch ASIC architecture (shared vs. per-port buffers)
  matter more here than in general-purpose DC design — see vendor-matrix for
  silicon-specific buffer behavior.
- **InfiniBand vs. Ethernet**: IB still leads on out-of-box lossless behavior and
  adaptive routing maturity for the largest training clusters; RoCEv2 Ethernet has
  closed much of the gap and wins on operational commonality with the rest of the
  DC estate, multi-vendor interoperability, and cost at scale. This is a live
  tradeoff, not a settled one — ask about existing operational expertise and
  cluster size before defaulting to either.
