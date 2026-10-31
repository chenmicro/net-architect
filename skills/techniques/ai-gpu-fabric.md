# AI/GPU Fabric

GPU-to-GPU traffic (RDMA, typically **RoCEv2** — RDMA over Converged Ethernet) is
loss-intolerant in a way general compute traffic isn't: a single dropped packet stalls
a collective operation (all-reduce, all-to-all) across the whole job, not just one
flow. This is the central design driver.

## Lossless Ethernet

**Lossless Ethernet** is achieved via:

- **PFC** (Priority Flow Control, 802.1Qbb) — pauses specific traffic classes
  hop-by-hop rather than the whole link, but is prone to head-of-line blocking
  and, misconfigured, PFC storms/deadlock across the fabric.
- **ECN** (Explicit Congestion Notification) + **DCQCN** — marks packets before
  buffers fill so senders back off proactively, reducing reliance on PFC as the
  only congestion signal. Tuning ECN thresholds and DCQCN parameters (Kmin/Kmax,
  Alpha) is a real, fabric-specific exercise, not a default-and-forget setting.

## Rail-optimized topology

GPU NICs are connected such that each "rail" (e.g. NIC 0 across all nodes) lands on a
common leaf, minimizing the number of hops and spine traversals for collective
communication patterns — this is a deliberate deviation from generic spine-leaf
cabling (see [spine-leaf-clos.md](spine-leaf-clos.md)), driven by how NCCL/collective
libraries schedule traffic.

## Network scale load balancing (NSLB)

Hash-based ECMP distributes AI training traffic unevenly, because a few elephant flows
can land on the same path. Huawei's documentation describes two failure modes [1]:

- **Local conflict**: multiple flows are hashed to the same uplink of a ToR switch,
  congesting that uplink.
- **Global conflict**: flows destined for different ports on the same ToR are hashed
  to the same spine, congesting the spine's downlink. Each switch decides alone, so
  distributed decision-making cannot eliminate this case.

NSLB addresses this by collecting the topology and computing paths centrally [1]:

- **Static**: inter-device links are numbered and ports are assigned to rail groups
  from the physical topology, with no compute-platform integration.
- **Dynamic**: the controller learns when AI tasks start and stop, computes paths
  between NICs for each task, and delivers the result to leaf nodes as a flow matrix.

## Cross-vendor / variants

- **InfiniBand vs. Ethernet**: IB still leads on out-of-box lossless behavior and
  adaptive routing maturity for the largest training clusters; RoCEv2 Ethernet has
  closed much of the gap and wins on operational commonality with the rest of the
  DC estate, multi-vendor interoperability, and cost at scale. This is a live
  tradeoff, not a settled one — ask about existing operational expertise and
  cluster size before defaulting to either.
- **Huawei NSLB**: iMaster NCE-Fabric offers static NSLB and dynamic NSLB-DP [1]. Dynamic
  mode gets task information from the compute side, and its supported operators are
  written around HCCL.

## Design considerations

- Non-blocking (1:1) fabric is the norm for training clusters — oversubscription
  directly throttles collective-op completion time, unlike general compute where
  it's a cost/performance tradeoff.
- 400G/800G leaf uplinks and spine interconnects are now standard for large training
  clusters; buffer depth and switch ASIC architecture (shared vs. per-port buffers)
  matter more here than in general-purpose DC design — see vendor-matrix for
  silicon-specific buffer behavior.
- Controller-computed NSLB adds a dependency between network and compute operations.
  Static mode avoids it; dynamic mode needs the compute platform integrated [1].

## Relationship to other techniques

- [roce.md](roce.md) — RoCEv2 encapsulation and the lossless mechanisms used here.
- [spine-leaf-clos.md](spine-leaf-clos.md) — the generic Clos and ECMP design that
  rail-optimized cabling and NSLB depart from.

## References

[1] "iMaster NCE-Fabric Product Documentation," Huawei, V100R025C00, Issue 04,
Jun. 30, 2026 (HedEx library EDOC1100509727, login required). Verify in: Getting Started > Functions >
AI Digital Map > AI Network Turbo; Digital Map Usage Guide > Fundamentals > Digital Map
Capabilities; Getting Started > Key Specifications > AI Digital MAP Restrictions and
Limitations. Confirmed Oct. 31, 2026.
