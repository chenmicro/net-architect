# Cisco NX-OS VXLAN GPO (Group Policy Option)

- GPO is NX-OS's tag-based microsegmentation feature for VXLAN EVPN fabrics —
  classify endpoints/external prefixes into **Security Groups (SGs)**, each
  carrying a 16-bit **Security Group Tag (SGT)**, then permit/deny/redirect
  traffic *between* SGs via **Security Contracts (SGACLs)**, instead of
  VRF/ACL-based segmentation. It ships its **own dedicated whitepaper**
  ("Securing Data Centers with Microsegmentation using VXLAN GPO"), confirmed
  separate from the [VXLAN Configuration Guide](nxos-vxlan.md) — same
  splitting test as [nxos-epbr.md](nxos-epbr.md).
  [ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html)
- **Standards status: not a ratified standard.** Cisco's own framing: *"VXLAN
  GPO implementation on NX-OS is based on standard as per IETF RFC draft EVPN
  Group Policy (draft-lrss-bess-evpn-group-policy-00)... a combination of two
  RFC drafts draft-smith-vxlan-group-policy and
  draft-wlin-bess-group-policy-id-extended-community defining Data Plane and
  Control Plane operations respectively."* All three are **expired individual
  Internet-Drafts** — no RFC stream, no working-group adoption, no intended
  RFC status — confirmed on the IETF Datatracker:
  [draft-smith-vxlan-group-policy](https://datatracker.ietf.org/doc/draft-smith-vxlan-group-policy/)
  (expired 2019, data plane),
  [draft-wlin-bess-group-policy-id-extended-community](https://datatracker.ietf.org/doc/draft-wlin-bess-group-policy-id-extended-community/)
  (expired 2024, control plane),
  [draft-lrss-bess-evpn-group-policy](https://datatracker.ietf.org/doc/draft-lrss-bess-evpn-group-policy/)
  (expired, last updated Dec 2025 — the umbrella doc combining the two).
  Same pattern as vPC and CloudSec in
  [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md#proprietary-tech-inside-nx-os-evpn-vxlan):
  a genuinely open RFC 7432/8365 EVPN-VXLAN baseline with a Cisco-driven,
  not-yet-ratified feature layered on top — belongs in vendor-matrix, not
  [techniques/](../../techniques/), until/unless one of these drafts is
  adopted by a BESS working group and progresses toward RFC.

## Release history

| Version | What changed |
|---|---|
| 10.4(3)F | First introduced — GPO-based segmentation. Platforms: N9300-FX3/GX/GX2A/GX2B. Classification: IPv4/IPv6 connected endpoints/subnets, IPv4/IPv6 external networks, VLAN. |
| 10.5(1)F | GPO-based **service redirection**; new platform (Nexus 9408); new classification criterion (VLAN range). |
| 10.5(2)F | New platforms (9300-FX/FX2/HX); **Route-Inject** (`match external-subnet route-inject`) — lets a Border Leaf locally originate SG-tagged routes per configured classification when the upstream only advertises a default route, so specific external prefixes can still get differentiated policy. |
| 10.5(3)F | GPO support with **MPLS-SR handoff**; new classification criteria (port-VLAN mapping, IP prefix + next-hop, IP prefix + next-hop + encap type). Intra-SG contracts/isolation **not yet supported** as of this release — roadmap item. |
| 10.6(1)F | New classification criterion (port + VLAN); segmentation support with L2 VLAN. |

Scale (per device, per Verified Scalability Guide): 8,000 ESG selectors on all
supported platforms; 64,000 SGACLs on N9300-FX/FX3/GX/GX2B/HX, 32,000 on
N9300-FX2/GX2A and Nexus 9408.
[ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html)

## Constructs

- **Security Group (SG)** — logical container of endpoints (by IPv4/IPv6, MAC,
  port, VLAN, VM attribute) or external prefixes. Same-SG traffic needs no
  contract; cross-SG traffic is governed by SGACLs. An SG may span multiple
  VRFs (route-leaking is a separate, deliberate config step). Two
  classification styles, coexistable in the same fabric: **network-centric/
  macro** (by subnet/VLAN) vs. **host-centric/micro** (by /32 host route or
  port+VLAN).
- **SGT (Security Group Tag)** — 16-bit tag identifying the SG; 0/1/15
  reserved (unclassified default / directly-connected-subnet marker for
  silent-host discovery / auto-assigned by a policy-aware Border Gateway to
  traffic arriving from a policy-unaware Multi-Site fabric). Must be globally
  unique and homogeneously defined across all fabrics in a Multi-Site domain.
- **Traffic Selector** — the "traffic of interest" a contract matches on:
  Ether-Type, L3/L4 protocol, L4 ports.
- **Security Contract (SGACL)** — binds source SG + destination SG + traffic
  selector + action (permit/deny/redirect/log); bidirectional (auto-creates
  the return rule) or unidirectional.
- **VRF Enforcement Mode** — new VRFs default to **Unenforced** (no policy
  applied at all). Must be switched to **Enforced**, in either
  **default-permit** (blacklist) or **default-deny**/zero-trust (whitelist)
  sub-mode. Documented migration path: enable default-permit + `log`, verify
  via `show logging ip access-list cache`, then flip to default-deny in one
  command once validated.
- **Security Group Routing Template** — SGTs ride in the FIB alongside EVPN
  routes; SGACLs are programmed into a **dedicated Policy TCAM**, separate
  from the Classification TCAM used for ACL/NAT/QoS. Cisco calls this out as
  the main scalability differentiator vs. PVLAN/ACL-based segmentation.
  Enabled via `system routing template-security-groups`, which **requires a
  reload** — must be set before `feature security-groups`/SG config.

## Implementation mechanics

- **Policy lookup is always IP-based**, even for bridged (MAC-forwarded)
  flows — an SGT bound to a MAC address is never used for enforcement, only
  the IP-bound SGT is. Direct consequence: **non-IP traffic (STP/LLDP/CDP,
  etc.) cannot currently be governed by GPO at all.**
  [ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html)
- **Control plane**: Group Policy ID rides as a new transitive Opaque BGP
  Extended Community (Type 0x03) on EVPN Type-2 (MAC-IP) and Type-5 (external
  prefix) routes — this is what makes **ingress-VTEP enforcement** possible;
  without it, enforcement could only happen at the egress VTEP, wasting
  fabric bandwidth (worse in Multi-Site).
- **Data plane**: the VXLAN header carries the *source* endpoint's SGT via a
  GBP (Group Based Policy) extension — a backward-compatible reuse of
  reserved header bits: **G bit** (Group Policy ID present), **A bit**
  (Policy Applied — set to 1 once a device has enforced policy, so downstream
  devices don't re-apply it), **D bit** ("Don't Learn" — defined by the spec
  but **not implemented by NX-OS**). Lets the egress VTEP enforce policy
  itself when the ingress VTEP didn't know the destination's SGT (PA bit = 0).
- **Silent hosts**: endpoints that never originate ARP/GARP stay unlearned —
  and even a unicast ARP reply to such a host is normally just forwarded as
  data, not learned. Up to 10.5(3), getting it learned (and thus
  policy-eligible) requires `suppress-arp` on the L2VNI, which makes the leaf
  glean the reply, install a local ARP entry, and generate a Type-2 EVPN
  route.

## Policy enforcement scenarios

- **East-West, single site**: ingress enforcement is preferred (source SGT
  local, destination SGT learned via BGP EVPN); falls back to egress
  enforcement (PA bit = 0) if the destination SGT isn't known at ingress.
- **East-West, Multi-Site**: sites are Policy-Aware (GPO enabled) or
  Policy-Unaware; mixed MSDs are supported for phased rollout.
  - **Policy-Aware ↔ Policy-Aware**: the SGT extended community survives
    Border-Gateway next-hop/RT rewrites end to end; enforcement always
    happens at the **ingress leaf of the originating site**.
  - **Policy-Unaware → Policy-Aware**: the policy-aware site's BGW
    auto-tags all routes from the unaware site with reserved **SGT 15**;
    contracts must explicitly reference SGT 15 to permit that traffic.
    Enforcement point is the ingress leaf (if traffic originates in the
    aware site) or the aware site's BGW (if traffic originates in the
    unaware site).
  - **Gotcha**: the traditional Multi-Site best practice of stretching only
    L3VNI (no L2VNI) on BGWs **breaks GPO's ingress-enforcement optimization**
    — without per-endpoint Type-2 SGT propagation, enforcement gets pushed
    all the way to the destination site's BGW. Cisco's stated fix: configure
    L2VNIs on **all** Multi-Site BGWs regardless of whether L2 is actually
    stretched — an outright requirement (not just an optimization) whenever
    cross-site service redirection/chaining is in play. See
    [nxos-epbr.md](nxos-epbr.md) for the ePBR side of that interaction.
  - [ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html)
- **North-South**: works over IP VRF-Lite or MPLS/MPLS-SR handoff. Since SGT
  exchange is confined to the VXLAN EVPN plane, it can't be exchanged with the
  external network — the Border Leaf must classify and assign an SGT to each
  external prefix as it converts it to a Type-5 route. Enforcement is at the
  ingress leaf (fabric→external) or the Border Leaf (external→fabric).

## Use cases

- **Network segmentation** — uni-/bidirectional app-specific policy,
  independent of where in the fabric an endpoint sits. Explicit non-goal:
  *"GPO per se does not offer specific 'application discovery mapping'
  capabilities"* — the operator must already know which SGs should talk to
  which.
- **Service chaining** — redirect N-S/E-W flows through firewalls/LBs/IDS
  based on SG match criteria; the multi-site version of this is what
  [nxos-epbr.md](nxos-epbr.md)'s GPO-based service chains build on.
- **VRF as a Security Zone** — group a VRF's resources into one SG for a
  second, dynamic layer of isolation on top of VRF-level routing isolation;
  supports quarantining a compromised endpoint into a separate SG without
  moving it to a new VRF.
- **Subnet as a Security Zone** — replaces hairpinning all inter-subnet
  traffic through an external firewall-as-default-gateway (a scaling/latency
  bottleneck) with per-subnet SGs enforced natively at line rate, while still
  selectively redirecting only traffic that needs stateful inspection.
- **Application as a Security Zone** — one SG per application for lateral-
  movement containment, with shared infra (DNS/backup/syslog) in a common SG
  reachable by all; also supports user-group-based access restriction to
  specific application SGs.

[ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html)
