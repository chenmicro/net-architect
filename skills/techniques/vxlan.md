# VXLAN

- VXLAN provides the data plane: L2 (and L3) traffic is encapsulated in UDP and
  carried over the IP underlay between **VTEPs** (VXLAN Tunnel Endpoints, usually
  the leaf switches). A **VNI** (VXLAN Network Identifier, 24-bit) maps to a
  bridge domain, giving ~16M logical L2 segments vs. VLAN's 4096.
- VXLAN by itself is data-plane only — it needs a control plane to populate VTEP MAC/
  ARP tables. Flood-and-learn (data-plane learning, no BGP) works but scales poorly
  and floods unknown-unicast/ARP across every VTEP; [evpn.md](evpn.md) is the modern,
  BGP-based control plane that replaces it and is what most current fabric designs
  actually deploy VXLAN with.
- Because the underlay only needs IP reachability between VTEPs, VXLAN rides on the
  same ECMP fabric described in [spine-leaf-clos.md](spine-leaf-clos.md) without any
  VXLAN-specific underlay requirements beyond that.
