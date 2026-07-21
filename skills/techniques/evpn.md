# EVPN

- EVPN (BGP address-family, RFC 7432) is the control plane for [vxlan.md](vxlan.md)'s
  data plane, replacing flood-and-learn with MAC/IP advertisement via BGP. This
  eliminates unknown-unicast flooding for known hosts and gives ARP suppression at
  the ingress VTEP. It rides on ordinary BGP sessions — see [bgp.md](bgp.md) for
  eBGP/iBGP and route-reflector mechanics; a common pattern is an eBGP-only
  underlay ([spine-leaf-clos.md](spine-leaf-clos.md)) carrying a separate iBGP+
  route-reflector overlay just for the EVPN address family, since the overlay
  doesn't need the same one-AS-per-node scheme the underlay does.
- Route types that matter in design conversations:
  - **Type 1** (Ethernet Auto-Discovery, "A-D") — advertised per-ES and per-EVI.
    The per-ES route is what a leaf withdraws on link/NVE failure, triggering mass
    withdrawal (fast convergence) at every remote VTEP with one route pull instead
    of a per-MAC update; the per-EVI route is what drives Aliasing/Backup Path, so
    remote VTEPs load-balance across every leaf on a multi-homed ES instead of
    pinning to whichever one first learned a given MAC.
  - **Type 2** (MAC/IP advertisement) — host reachability, the bread and butter route.
  - **Type 3** (Inclusive Multicast) — builds the BUM (broadcast/unknown-unicast/
    multicast) replication tree per VNI; ingress replication is the common choice
    over PIM in the underlay to avoid multicast state.
  - **Type 4** (Ethernet Segment route) — auto-discovers which leaves share an ESI
    and drives Designated Forwarder (DF) election, so exactly one leaf forwards BUM
    traffic for a given segment/VLAN when a device is multi-homed active-active.
  - **Type 5** (IP Prefix) — inter-subnet/inter-VRF route advertisement, used for
    route summarization and connecting to L3 ([multi-tenancy.md](multi-tenancy.md),
    DCI) without stretching L2.
- **Anycast gateway**: the same gateway IP/MAC is configured on every leaf, so a host's
  default gateway is always local regardless of which leaf it's attached to — this is
  what makes VM/workload mobility across the fabric transparent to the host.
- **Multi-homing**: EVPN Multihoming (EVPN-MH, ESI-based, RFC 8365) is the modern,
  vendor-interoperable way to dual-home a server or downstream switch to two leaves
  with active-active forwarding, replacing proprietary MLAG/vPC pairs at the
  server-facing edge. Note EVPN-MH and vPC/MLAG are not directly interoperable —
  pick one per fabric generation, don't mix at the same tier.
  - Split-horizon (loop prevention for BUM traffic on an all-active ES) can't reuse
    MPLS-EVPN's ESI-label trick here — VXLAN has no label stack to carry it. RFC 8365
    §8.3.1 instead uses **Local Bias**: every VTEP tracks which peer VTEPs share an
    ESI with it and filters BUM traffic sourced from those peers' tunnel IPs, so a
    frame never loops back out the same segment it entered.
