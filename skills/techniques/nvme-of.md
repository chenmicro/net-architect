# NVMe over Fabrics (NoF)

- NVMe over Fabrics (NVMe-oF, also written NoF) carries the NVMe storage protocol over
  a network instead of the local PCIe bus, so a host can reach a remote all-flash array
  with NVMe semantics [1].
- NoF is a layer above the fabric. It binds NVMe to an underlying transport. The
  transport, not NoF, decides whether the network is lossless and how congestion is
  controlled:
  - **RDMA**: see [roce.md](roce.md).
  - **TCP**
  - **Fibre Channel (FC)**: see [fibre-channel.md](fibre-channel.md).
- Design conversations about NoF are usually about one choice: keep the storage area
  network (SAN) on FC, or move it onto lossless Ethernet (NVMe over RoCEv2) that is
  converged with the compute network.

## Specification structure

- The NVM Express specification set separates protocol from transport [1]:
  - The **NVMe Base** specification defines how host software talks to an NVM
    subsystem over memory-based and message-based transports.
  - **Command set** specifications extend it, for example the NVM, ZNS, and KV
    command sets.
  - **Transport** specifications bind NVMe to one transport. NVM Express publishes
    transport specifications for PCIe, RDMA, and TCP.
- The FC binding is defined by the FC standards body, INCITS T11, not by NVM Express
  (FC-NVMe and FC-NVMe-2; see [fibre-channel.md](fibre-channel.md#cross-vendor--variants)).
- The stand-alone NVMe-oF specification is obsolete. Its content was folded into the
  Base and Transport specifications, and NVM Express keeps it only as a historical
  reference [1].
- The current set is NVMe 2.4, released 2026-08-04 [1].

## Cross-vendor / variants

### Transport comparison

| | NVMe/FC | NVMe/RoCEv2 | NVMe/TCP |
|---|---|---|---|
| Fabric | Dedicated FC SAN | Lossless Ethernet: PFC + ECN, see [roce.md](roce.md) | Any IP network, lossy |
| Flow control | Proactive, credit-based: the sender is limited by the receiver's buffers ([fibre-channel.md](fibre-channel.md#flow-control)) | Reactive: PFC pause and ECN-driven source rate reduction ([roce.md](roce.md)) | TCP congestion control |
| Host and target NIC | FC HBA | RDMA-capable (RoCEv2) NIC on both host and storage controller, because both ends implement the RDMA transport [1] | Standard NIC |
| Network technology stack | Separate from the IP network | Converges with the compute and service networks on Ethernet | Converges with the IP network |

### FC as the baseline

FC is a separate ecosystem with its own frame format, credit-based flow control, and
fabric services (name server, zoning, RSCN). Its current speeds, distance, and vendor
features are in [fibre-channel.md](fibre-channel.md). When comparing NoF transports,
use current FC (64G or 128G) as the baseline.

### How open are FC and RoCE?

Both are consensus standards that anyone may implement, and neither charges users a
fee to run the protocol. Neither specification is free to read.

| | FC (incl. NVMe/FC) | RoCE (incl. NVMe/RoCE) |
|---|---|---|
| Standards body | INCITS T11, accredited by ANSI ([fibre-channel.md](fibre-channel.md#standards-access)) | InfiniBand Trade Association (IBTA). RoCE is defined in the InfiniBand Architecture specification [3] |
| Getting the specification | Published standards are bought; drafts are free only during public review ([fibre-channel.md](fibre-channel.md#standards-access)) | Members download it; non-members contact IBTA administration [3] |
| Host software | FC is included in Linux distributions ([fibre-channel.md](fibre-channel.md#standards-access)) | Standard Linux RDMA stack (rdma-core), see [roce.md](roce.md) |
| Network hardware | Dedicated FC switches and HBAs | Any Ethernet switch that supports the lossless features (PFC, ECN), and RoCEv2 NICs |

- **Where the practical difference lies**: the ecosystem, not the openness of the
  standard.
  - An FC SAN needs FC-specific switches and HBAs, from a small set of vendors.
  - RoCE runs on general-purpose Ethernet switches and NICs, which gives more sourcing
    choice and more price competition.
- **Standard NoF carries no vendor tie.**
  - NVMe over RoCEv2 with standard PFC (802.1Qbb) and ECN (RFC 3168) runs between any
    compliant host, switch, and array. See [roce.md](roce.md).
  - Vendor congestion tuning that stays inside one switch interoperates, because
    hosts only see standard ECN marks.
- **Vendor extensions add features but reintroduce a tie.**
  - FC's equivalents (zoning, name server, RSCN) are part of the FC standards
    ([fibre-channel.md](fibre-channel.md#addressing-login-and-fabric-services)).
  - The Ethernet extensions that provide zoning, plug-and-play, and fast fault
    notification are vendor-specific.
- **The design choice**:
  - **Standard NoF**: buy from any vendor, and accept manual zoning and multi-second
    failover.
  - **NoF with a vendor extension**: get FC-like plug-and-play and fast failover, but
    commit to that vendor's switches, and sometimes its arrays.
  - **FC**: get both standard zoning and fast failover, on a dedicated fabric.

## Design considerations

- **Dual independent planes**:
  - Centralized-storage SANs run two physically independent planes (A and B).
  - Hosts and arrays attach to both planes, and host multipathing software handles
    failover.
  - Leaf switches are neither stacked nor M-LAG paired, and host and array ports are
    not bonded. Each port has its own IP address on one plane.
  - This mirrors dual-fabric FC SAN design
    ([fibre-channel.md](fibre-channel.md#design-considerations)). It keeps the planes'
    failure domains separate and needs no M-LAG peer link.
- **Multipathing is the failover mechanism**:
  - A host sees its own NIC go down at once.
  - It does not see a fault elsewhere on the path: a storage port, a switch-to-switch
    link, or a switch. Standard NVMe-oF detects those by keep-alive timeout.
  - **Linux NVMe host driver defaults** [2]:
    - keep-alive timeout: 5 s;
    - I/O timeout: 30 s;
    - reconnect delay: 10 s;
    - controller-loss timeout: 600 s;
    - fast I/O fail: disabled.
  - These defaults give failover in seconds, not milliseconds. Tune `keep_alive_tmo`
    and `fast_io_fail_tmo` per connection to shorten it [2].
  - Without a network-assisted notification, budget for a multi-second I/O stall on
    faults the host cannot see.
- **ECMP reconvergence hits RDMA hard**:
  - Packets in flight on a failed spine-leaf link are lost until routing reconverges.
  - RoCE's simple retransmission (Go-Back-N, see [roce.md](roce.md)) recovers only
    after its timeout, so a short network outage becomes a longer I/O stall.
  - Fast link-failure detection (BFD) and data-plane fast reroute reduce this.
- **Access control without FC zoning**:
  - Ethernet has no standard equivalent of FC zoning and the name server.
  - In a standard NoF SAN, isolation comes from VLAN or VRF segmentation plus host
    access lists on the array. Some vendors add zoning as an extension.
- **Distance**: the buffer, not the bandwidth, sets the limit on a long link.
  - Whatever the mechanism, something has to hold the data in flight while the sender
    waits for feedback: the bandwidth-delay product, `B × RTT`. The round trip in glass
    is about 10 µs per km (light travels at about 2 × 10^8 m/s in fibre), so a
    100 Gbit/s link over 100 km has a BDP of about 12.5 MB.
  - Each lossless mechanism needs a different multiple of it, and fails differently
    when it has less:

    | Mechanism | Buffer to hold a link at full rate | When it falls short |
    |---|---|---|
    | FC buffer-to-buffer credits ([fibre-channel.md](fibre-channel.md#flow-control)) | ≈ B × RTT: one credit per frame in flight | The sender stalls waiting for credits: lower throughput, never a dropped frame, no retransmission |
    | Traditional PFC (802.1Qbb, see [roce.md](roce.md)) | ≈ 2 × B × RTT: one RTT for the pause to reach the sender, plus one RTT of data already on the wire | The headroom fills before the pause lands: drops, then RDMA retransmission |
    | Credit-style pacing for PFC (vendor long-distance modes) | ≈ B × RTT, about half the traditional PFC budget | Still PFC rather than a credit gate, so short headroom drops frames like traditional PFC |

  - **What the comparison means**: over the same distance and rate, lossless Ethernet
    needs about twice the buffer of an FC SAN, and a vendor's credit-style pacing brings
    it back to about parity. Huawei's Xinghe NoF+ implements the third row; the detail
    belongs in the Huawei vendor file, not here.
  - **The failure mode matters more than the multiplier**: FC degrades to slower,
    lossless Ethernet degrades to loss. A link that is over-distance for its credits
    under-runs; a link that is over-distance for its PFC headroom drops, and the RDMA
    recovery timeout then turns each drop into a stall.
  - Size the buffer on DCI switches for the link's real distance
    ([roce.md](roce.md)), and check the vendor's per-model distance × bandwidth limit
    rather than assuming the switch's buffer pool is the only constraint.
  - FC solves the same problem with buffer-to-buffer credits
    ([fibre-channel.md](fibre-channel.md#flow-control)).
- **Greenfield bias**:
  - NVMe/RoCE needs RoCE NICs in both servers and storage controllers.
  - Migrating an existing FC estate therefore means replacing host adapters and array
    front-end cards, not only switches.
- **Compare like with like**: benchmark NVMe/RoCE against current FC (64G or 128G),
  not 16G or 32G FC (see [fibre-channel.md](fibre-channel.md#speeds)).

## Relationship to other techniques

- [fibre-channel.md](fibre-channel.md): the FC transport under NVMe/FC, and the
  incumbent SAN that NVMe/RoCE is compared against.
- [roce.md](roce.md): the RDMA transport under NVMe/RoCE. PFC, ECN/DCQCN, and
  deadlock handling are specified there.
- [ai-gpu-fabric.md](ai-gpu-fabric.md): uses the same lossless-Ethernet toolkit, but
  storage SANs use dual independent planes rather than rail-optimized topologies.
- [spine-leaf-clos.md](spine-leaf-clos.md): a NoF storage plane is a small IP Clos
  with a routed underlay.
- [qos.md](qos.md): the lossless class for RoCEv2 must be marked consistently (802.1p
  or DSCP) from host to array.

## References

[1] "NVMe Set of Specifications Overview," NVM Express. [Online]. Available: https://nvmexpress.org/specifications/ (last confirmed 2026-11-02; NVMe 2.4 set)

[2] Linux kernel NVMe host driver, torvalds/linux at commit 6628e7d4c6b25c8d18f1345e3a20d21829aae7e4: drivers/nvme/host/nvme.h (NVME_DEFAULT_KATO), drivers/nvme/host/core.c (io_timeout, admin_timeout), drivers/nvme/host/fabrics.h (NVMF_DEF_RECONNECT_DELAY, NVMF_DEF_CTRL_LOSS_TMO, NVMF_DEF_FAIL_FAST_TMO), drivers/nvme/host/fabrics.c. [Online]. Available: https://github.com/torvalds/linux/tree/master/drivers/nvme/host (last confirmed 2026-11-02)

[3] "IBTA Specification," InfiniBand Trade Association. [Online]. Available: https://infinibandta.org/ibta-specification/ (RoCE defined within the InfiniBand Architecture specification; members download, non-members contact IBTA administration; last confirmed 2026-11-02)
