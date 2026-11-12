# Multi-Tenancy (Data Center)

Tenant isolation on a shared fabric: per-tenant VRFs, route-target policy between them,
and how that isolation is carried across the fabric edge.

## VRFs and route targets

- **VRF-lite** (per-tenant VRF on every leaf, redistributed into [evpn.md](evpn.md)
  Type-5) is the standard way to give tenants isolated L3 routing domains on a
  shared fabric.
- **Route-target import/export** controls which VRFs see which Type-5 routes —
  this is how you implement shared-services access (e.g. every tenant VRF imports
  a shared "services" RT for DNS/DHCP/security) without full-mesh route leaking.

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

## Cross-vendor / variants

- **Huawei CloudEngine (V300R026C00)**: a VPN instance's IPv4 address family keeps a
  separate VPN-target list for EVPN routes (`vpn-target … [ import-extcommunity |
  export-extcommunity | both ] evpn`). A received IRB route (EVPN Type-2 with an IP) or
  IP prefix route (Type-5) is added to the VPN instance's routing table when its VPN
  targets match that import list, so importing another VRF's VPN target also imports
  that VRF's host routes. `import route-policy <name> evpn` filters what the address
  family imports from EVPN, with one import policy per address family. A route whose
  address family doesn't match the policy's `if-match` clause is permitted by default,
  so end the policy with a deny node that has no `if-match`, which matches all routes.
  To scope the policy to certain source VRFs or BDs, add `if-match extcommunity-filter`
  with a basic VPN-target filter (`ip extcommunity-filter basic <name> permit rt …`).
  Configure the filter first: referencing a filter that doesn't exist matches all
  routes. Both need an RD
  and `evpn-overlay enable`, and both run only on the listed models, CE6885 included
  [1].

## Design considerations

- VLAN/VNI numbering should be planned per-tenant with headroom — collisions or
  renumbering after onboarding customers is expensive; reserve VNI ranges by
  tenant or function up front.
- Isolation boundary questions to ask early: does a tenant need its own BGP ASN
  for on-prem-to-cloud connectivity, does it need dedicated DCI paths, does it
  have compliance requirements (e.g. PCI) that mandate physical rather than
  logical separation for parts of the fabric.
- **Leaking routes between VRFs keeps their next hop.** A route imported from another
  VRF's VPN target still points at that VRF's VTEP, so traffic follows it directly
  rather than through any device placed between the VRFs. Filter the import when a
  service device must stay in the path.

## Relationship to other techniques

- [evpn.md](evpn.md): the Type-2 and Type-5 routes that VPN targets select
- [vxlan.md](vxlan.md): VNI numbering and the L3VNI each VRF uses
- [mpls.md](mpls.md), [segment-routing.md](segment-routing.md): L3VPN handoff at the edge

## References

[1] "CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation," Huawei,
V300R026C00, Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611778, login required).
Verify in: References > Command Reference > VXLAN > VXLAN Configuration Commands >
vpn-target evpn (VPN instance IPv4 address family view) and import route-policy evpn; and
> IP Routing > Routing Policy Configuration Commands > route-policy, ip extcommunity-filter
basic, and if-match extcommunity-filter. Confirmed Nov. 12, 2026.
