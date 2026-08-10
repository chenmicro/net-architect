# Silent Host Reachability in Overlay Fabrics

## Background

A DC operations team migrates their infrastructure from a legacy L2 access
network (STP-based, flat VLANs) to an EVPN-VXLAN spine-leaf fabric.
Post-migration, the centralized syslog collector — a UDP listener on port 514
that ingests streams from every device in the environment — goes dark. It
never sends a single packet. This is not a host that *happens* to be quiet;
it has no reason to respond to anything. Remote log sources work briefly
while the collector's MAC survives in the leaf's forwarding table from the
migration window, then fail hard when the MAC aging timer expires and the
leaf drops the frames as unknown unicast. ARP broadcasts from neighbors on
the subnet elicit nothing. It is invisible to the control plane by nature,
not by accident.

Before the solution, read the fundamentals:
[arp.md](../techniques/arp.md) (ARP suppression, gleaning, smart-discover,
timer mismatch), [evpn.md](../techniques/evpn.md) (RFC 7432's reactive model,
Type 2 learning, no fabric-side probe), and
[vxlan.md](../techniques/vxlan.md) (BUM path, flood-vs-drop behavior).

## The challenge

EVPN (RFC 7432) learns endpoints reactively from data-plane traffic. There is
no fabric-initiated discovery mechanism — no hello protocol, no periodic
probe, no route type that means "I haven't heard from this host yet." A host
that never emits a frame, ARP reply, or ND solicitation is permanently
invisible to the control plane. The design question is not "which protocol
learns silent hosts" (none do, on their own) but **"which mechanism, at which
layer, is allowed to ask."** The layer choice — L2 unknown-unicast flooding
vs. L3 gateway-driven probe — is the master switch for the entire solution
space.

## The solution

ARP is the one protocol every IP host is obligated to answer (RFC 826), which
is why every fabric-side probe uses ARP. There is no other universal trigger:
ICMP requires a configured IP stack, LLDP is optional, and UDP/TCP ports are
application-specific. ARP sits at the lowest common denominator — if a host
has an IP address, RFC 826 says it must reply to an ARP request for that
address.

But this also defines the solution's upper bound. A host that is ARP-deaf — a
UDP syslog collector that binds a port and never sends, a device with a
hard-coded neighbor table, a powered-off server — defeats every probe. No
protocol-level mechanism works for these; the only option is a static
ARP/MAC entry pinned on the attaching leaf. The rest of the solution space
falls into two tiers: hosts that will answer ARP but never initiate, and hosts
whose senders still ARP for them.

### ACI (Cisco)

ACI uses COOP gleaning: when a spine receives a packet destined for an
unknown endpoint, it sends a glean packet via the VRF's GIPo multicast group
(239.255.255.240) to the leaf that owns the BD's subnet. That leaf's SVI
issues an ARP request. If the host answers, the endpoint is learned and
advertised as a Type 2 route. Gleaning requires unicast routing and a subnet
configured on the BD — without an L3 gateway, there is no SVI to ARP from.
See [aci.md](../vendor-matrix/cisco/aci.md) for COOP/gleaning pipeline,
GIPo/FTAG mechanics, and hardware-proxy behavior.

### Huawei CloudFabric

Huawei provides `arp smart-discover` — a periodic, fabric-side ARP probe
initiated from the VBDIF (anycast gateway interface). Also available: ARP
Miss / broadcast-detect on the VBDIF, which triggers an ARP probe when the
fabric sees a miss. Both are proprietary and require the BD/VNI to have an L3
gateway. See [huawei.md](../vendor-matrix/huawei.md) for platform details.

### Juniper EVPN-VXLAN

Juniper uses `static-mac-ip` entries coupled with ARP/ND probing. The
operator configures a list of silent-host MAC/IP pairs; the leaf periodically
ARPs (or NDs) those addresses and, on reply, advertises a Type 2 route. The
probe interval follows a configurable backoff. Without a configured list,
Juniper has no spontaneous fabric-side discovery. See
[juniper.md](../vendor-matrix/juniper.md) for platform details.

### Standard EVPN (Arista EOS, Cisco NX-OS native, others)

No fabric-initiated probe. The portable workaround is a periodic ARP scan
(nmap, arping) run from a host in each subnet — the scan triggers ARP replies
that the fabric learns as Type 2 routes. The scan interval must be sized
against the MAC aging timer. Timer discipline (MAC aging > ARP aging) is the
cheapest mitigation and applies everywhere. See
[arista.md](../vendor-matrix/arista.md) and
[nxos-vxlan.md](../vendor-matrix/cisco/nxos-vxlan.md) for platform defaults
on unknown-unicast handling.

### ARP-deaf fallback (all vendors)

For hosts that will not answer ARP under any circumstances, static ARP/MAC
entries on the attaching leaf are the only universal option. This applies
regardless of vendor or fabric type, including ACI.

## References

[1] "Silent Hosts in EVPN Fabrics," ipSpace.net, Ivan Pepelnjak, May 2023 —
full citation and timer analysis in [arp.md](../techniques/arp.md) [3].

[2] "ACI Fabric Endpoint Learning White Paper," Cisco — full citation and
COOP/gleaning mechanics in [arp.md](../techniques/arp.md) [2] and
[aci.md](../vendor-matrix/cisco/aci.md) [9].

[3] A. Sajassi et al., "BGP MPLS-Based Ethernet VPN," IETF RFC 7432 — full
citation and route-type analysis in [evpn.md](../techniques/evpn.md) [1].

[4] "IEEE Standard for Local and Metropolitan Area Networks — Bridges and
Bridged Networks," IEEE Std 802.1Q — aging/refresh rules cited in
[arp.md](../techniques/arp.md) [6].
