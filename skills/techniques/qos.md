# Quality of Service (QoS)

- QoS ensures predictable network behavior for traffic that is
  delay-sensitive (voice, video), loss-sensitive (storage replication,
  financial transactions), or bandwidth-constrained (real-time
  collaboration). In Ethernet/IP networks, QoS operates at Layer 2 (802.1p
  CoS, 3-bit priority in the VLAN tag) and Layer 3 (DSCP, 6-bit
  Differentiated Services Code Point in the IP header).

## The QoS architecture: classification → marking → queuing

1. **Classification**: identify traffic by header fields (L2 CoS, L3
   DSCP/IP-precedence, L4 port, protocol) or by ingress interface/VLAN.
2. **Marking**: write (or rewrite) the CoS/DSCP/MPLS-EXP value so downstream
   devices can act on it without re-classifying. Mark as close to the source
   as possible.
3. **Queuing/scheduling**: map marked traffic to egress queues with
   bandwidth guarantees, priority (strict/low-latency), and congestion
   avoidance (WRED/ECN).

## QoS and cross-vendor interconnection

QoS is not a single protocol — it's a set of behaviors built on IP/Ethernet
fields that are standard, but **the trust model and default behavior differ
by vendor**. When connecting Cisco to Huawei, the two sides can carry each
other's marked traffic correctly, but they won't necessarily *trust* it
out of the box.

### Trust models

| Vendor | Default trust | What it means |
|---|---|---|
| **Cisco** (Catalyst, IOS-XE) | Ports default to **untrusted** | Ingress CoS/DSCP is reset to 0 unless `mls qos trust dscp` or `trust cos` is configured [1]. |
| **Cisco** (Nexus, NX-OS) | Ports default to **trust DSCP** | Nexus switches trust incoming DSCP markings by default (the DC-oriented assumption is that the marking was done at the hypervisor/NIC) [2]. |
| **Huawei** (CloudEngine, VRP) | Ports default to **untrusted** (per-port) but can be set to trust DSCP/802.1p | Similar to Cisco IOS-XE — explicit trust config is needed. |
| **Huawei** (NetEngine, VRP) | Typically **trust DSCP** on routed interfaces | Router behavior — trusting L3 markings is the norm. |

The interop risk: a Cisco Catalyst port (untrusted by default) connected to a
Huawei CE port (also untrusted by default) strips all QoS markings in both
directions — neither side trusts the other's traffic. Fix it by explicitly
configuring `trust dscp` on the inter-switch link on both sides.

### Marking alignment

DSCP values and their intended per-hop behavior (PHB) are standardized
(RFC 2474 [3] / RFC 2475 [4]), but **what each value means** — which traffic
class it maps to —
is organization-specific. A DSCP value of 46 (EF, Expedited Forwarding,
commonly used for voice) maps to the same PHB on Cisco and Huawei, but
Cisco's default queue mapping may differ from Huawei's default.

- The fix is not a protocol change — it's a **documented QoS design**: agree
  on a DSCP-to-queue mapping, configure it explicitly on both sides, and
  validate with `show policy-map interface` during commissioning.

### Congestion management: WRED vs. Tail Drop

Both vendors support WRED (Weighted Random Early Detection) to avoid TCP
global synchronization during congestion. The WRED profile (min/max
thresholds, drop probability) must be aligned if both sides enforce
congestion management on the same flow direction.

## QoS design checklist for cross-vendor links

1. **Trust model**: explicitly configure `trust dscp` on inter-switch
   physical links — don't rely on platform defaults.
2. **DSCP-to-queue mapping**: publish the mapping table (which DSCP values go
   to which queue, which queue gets priority/strict scheduling) and configure
   it identically on both sides.
3. **Ingress marking**: if re-marking happens at the edge (e.g., marking
   traffic from a specific VLAN with a specific DSCP), document where the
   marking occurs — mark once, as close to the source as possible, and let
   downstream devices trust the marking.
4. **Queue depth and buffer**: Cisco and Huawei switches have different
   buffer architectures (shared vs. per-port, deep vs. shallow).
   PFC/ECN-based lossless Ethernet for RoCEv2
   ([roce.md](roce.md), [ai-gpu-fabric.md](ai-gpu-fabric.md)) is a separate
   concern with its own requirements beyond generic QoS.
5. **Voice/video**: EF (DSCP 46) traffic should map to a strict-priority
   (LLQ/Priority Queue) on both sides; AF41 (DSCP 34) for interactive video
   with guaranteed bandwidth — these mappings must match or one side drops
   what the other considers critical.

## QoS in the data center vs. the campus/WAN edge

- **DC fabric**: most east-west traffic is trusted by default (marked by the
  server/hypervisor). QoS is typically simplified to a small number of
  classes (e.g., lossless RoCEv2 class, best-effort, maybe a control-plane
  class) rather than the 8–12 class campus/WAN model.
- **Campus/WAN edge**: more classes (voice, video, transactional data, bulk
  data, scavenger), explicit trust boundaries at access ports, and
  policers/shapers at the WAN edge to match carrier CIR. Cross-vendor QoS
  alignment matters most at the WAN edge handoff.

## Relationship to other techniques

- [roce.md](roce.md) — PFC/ECN-based lossless Ethernet for RoCEv2 is a
  separate QoS class with its own buffer and congestion-control requirements
  beyond generic DSCP-based QoS.
- [ai-gpu-fabric.md](ai-gpu-fabric.md) — AI/GPU fabrics have strict tail-latency
  and loss requirements that drive the QoS design toward a small number of
  carefully-tuned classes.
- [core-agg-access.md](core-agg-access.md) — campus QoS design has more classes
  and explicit trust boundaries at access ports, vs. the simplified DC model.

## References

[1] Cisco, "QoS Trust Behavior on Catalyst Switches," Cisco IOS-XE QoS
    Configuration Guide.
[2] Cisco, "Configuring QoS on Nexus 9000 Series Switches," Cisco NX-OS QoS
    Configuration Guide.

[3] K. Nichols, S. Blake, F. Baker, D. Black, "Definition of the
    Differentiated Services Field (DS Field) in the IPv4 and IPv6 Headers,"
    RFC 2474, December 1998.
    [Online]. Available: https://www.rfc-editor.org/rfc/rfc2474

[4] S. Blake, D. Black, M. Carlson, E. Davies, Z. Wang, W. Weiss,
    "An Architecture for Differentiated Services," RFC 2475, December 1998.
    [Online]. Available: https://www.rfc-editor.org/rfc/rfc2475
