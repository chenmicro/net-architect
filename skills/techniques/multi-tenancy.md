# Multi-Tenancy (Data Center)

- **VRF-lite** (per-tenant VRF on every leaf, redistributed into [evpn.md](evpn.md)
  Type-5) is the standard way to give tenants isolated L3 routing domains on a
  shared fabric.
- **Route-target import/export** controls which VRFs see which Type-5 routes —
  this is how you implement shared-services access (e.g. every tenant VRF imports
  a shared "services" RT for DNS/DHCP/security) without full-mesh route leaking.
- VLAN/VNI numbering should be planned per-tenant with headroom — collisions or
  renumbering after onboarding customers is expensive; reserve VNI ranges by
  tenant or function up front.
- Isolation boundary questions to ask early: does a tenant need its own BGP ASN
  for on-prem-to-cloud connectivity, does it need dedicated DCI paths, does it
  have compliance requirements (e.g. PCI) that mandate physical rather than
  logical separation for parts of the fabric.

## VRF-lite handoff at the fabric edge

Per-tenant isolation inside the fabric (VNIs + EVPN Type-5, above) still has
to survive the handoff to whatever sits outside it — a WAN edge router,
firewall, or upstream router that isn't part of the VXLAN/EVPN domain. Two
ways to carry that isolation across the border, both terminated at the
Border Leaf:

- **VRF-lite handoff**: each tenant VRF gets its own dedicated sub-interface
  (or VLAN) on the physical link to the external router, with plain per-VRF
  BGP/OSPF/static routing on that sub-interface — no MPLS label-switched path
  or VPN-specific signaling involved (it's "lite" precisely because it skips
  RFC 4364 L3VPN machinery). Simplest option when the external network is a
  plain routed WAN edge rather than an MPLS/SR domain, at the cost of one
  sub-interface (and one routing adjacency) per tenant on that link.
- **MPLS/MPLS-SR handoff**: each VRF maps instead to an MPLS VPN label
  (RFC 4364-style L3VPN) over a single link/adjacency to the external router
  — see [mpls.md](mpls.md) and [segment-routing.md](segment-routing.md).
  Preferred when the external network is itself an MPLS/SR domain, since it
  avoids provisioning a sub-interface per tenant and lets the label stack do
  the multiplexing instead.

Which one to use is really "what does the thing on the other side of the
Border Leaf speak" — VRF-lite if it's a router doing plain per-VRF routing,
MPLS/MPLS-SR if it's already an MPLS/SR PE.
