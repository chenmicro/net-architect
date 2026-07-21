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
