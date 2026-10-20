# SASE

- **SASE** (Secure Access Service Edge) converges SD-WAN (networking) with a
  security service edge — **SSE**: SWG (Secure Web Gateway), CASB (Cloud Access
  Security Broker), **ZTNA** (Zero Trust Network Access, replacing or
  supplementing traditional VPN for remote/app access), and often DLP/FWaaS —
  delivered as a cloud service rather than boxes at every site.
- The architectural shift is inspection moving from "backhaul to a DC firewall"
  to "steer to the nearest cloud PoP for the security stack, then to destination"
  — this is what makes [dia-local-breakout.md](dia-local-breakout.md) safe to enable
  broadly without a security stack at every branch.
- ZTNA specifically changes the remote-access model: instead of a VPN granting
  network-level access to a segment, ZTNA brokers per-application access after
  continuous identity/posture verification — relevant when a design question is
  "how do remote/hybrid users get to internal apps" rather than just "how do
  branches connect to the WAN." Note this is a different identity system from
  [nac.md](nac.md)'s RADIUS-driven wired/wireless LAN access — a design spanning
  both should state which one is authoritative for which access path.

## Convergence models

The vendor landscape splits on two independent axes, and designs get into
trouble by conflating them:

1. **Single-vendor SASE vs. best-of-breed.** Single-vendor means one vendor for
   both SD-WAN and SSE (Palo Alto Prisma SASE, Fortinet, Versa, Cisco+Umbrella,
   Cato); dual-vendor/best-of-breed pairs an SD-WAN vendor with an SSE vendor
   (e.g. Zscaler or Netskope). Single-vendor simplifies operations and policy
   consistency; best-of-breed can win on point-feature strength — ask about
   existing security vendor relationships before defaulting to either.
2. **Vendor-backbone-native vs. public-internet overlay.** Some SASE services
   carry site-to-site and site-to-cloud traffic over the *vendor's own private
   backbone* between PoPs, rather than tunneling edge-to-edge across the public
   Internet. This changes where the WAN SLA comes from: with a backbone the
   vendor owns the middle mile and can offer controlled latency/loss between
   PoPs; with a pure public-internet overlay the middle mile is best-effort and
   the SLA stops at each edge's own last mile.

### Backbone-native example

Cato Networks is the clearest current example of this model: the SD-WAN function
is a property of Cato's own backbone rather than a standalone product, and the
vendor sells **SASE** (networking and security together) and **SSE** (security
only, with the customer's own SD-WAN attached over IPsec) as two materially
different services from the same cloud [1]. That split is why a backbone-native
vendor has to be qualified by *service tier* before its feature list — the tier,
not the logo, decides the site CPE and what telemetry exists. Product detail —
edge appliance models, site-connection capability tiers, link-SLA behaviour, and
deployment constraints — lives in [cato.md](../vendor-matrix/cato.md), not here.

## Cross-vendor / variants

| Model | Example | Where the middle-mile SLA comes from | Site CPE | Trade-off to flag |
|---|---|---|---|---|
| Backbone-native SASE | Cato (SASE tier) [1], [2] | The vendor, between PoPs | Vendor appliance (Socket/vSocket) | Best middle-mile consistency; CPE, tunnel type and PoP choice are vendor-controlled |
| Appliance-led SASE | Palo Alto Prisma SASE, Fortinet, Versa | Customer-chosen hubs over the public Internet, plus each site's carrier | Vendor NGFW/SD-WAN edge | Policy/security depth on the CPE; middle mile is best-effort |
| SD-WAN + SSE (best-of-breed) | Any SD-WAN + Zscaler/Netskope | The customer's existing WAN/underlay | Existing edge router | Keeps installed SD-WAN; two policy planes, two consoles, and an IPsec-only join |
| No backbone at all | Plain IPsec/DMVPN overlay | Nothing beyond the underlay | Any | Cheapest; no cloud inspection, no steering, no optimization layer |

The last row is included deliberately. Plenty of what is sold as SD-WAN is still a
plain IPsec overlay with a controller in front of it, and the SASE/SSE tier split
above is where the functional difference actually sits — so qualify a vendor on
which row it belongs to before comparing feature lists.

## Design considerations

- **Fix the direction of the dependency before choosing the vendor.** Buy SSE
  first and the SD-WAN half arrives later over whatever join the SSE tier
  exposes — in practice IPsec, which on a backbone-native product means upstream
  QoS and packet-loss telemetry are missing at exactly the sites that SLA-based
  steering depends on [1]. Sequence the two halves so the edge device type
  matches the target state rather than the migration order.
- **Grade sites by attachment method, not by vendor.** Even inside one SASE
  product the attachment decides the outcome: an appliance/vSocket site gets
  upstream and downstream QoS plus loss telemetry, an IPsec site gets
  downstream-only QoS and partial analytics, and a private interconnect may not
  encrypt at all [1]. Carry the attachment type in the site table — a
  "SASE-enabled" site spans several capability tiers, not one.
- **Count the hops that are not inspected.** Every local-breakout, bypass, or
  off-cloud rule moves traffic outside the inspection path. Keep an explicit
  inventory of which traffic classes leave the inspected path and why — this is
  the artifact security review and auditors ask for. Vendor-specific rule types
  are enumerated in the vendor file that defines them, e.g.
  [cato.md](../vendor-matrix/cato.md).
- **Pin the exit-PoP question.** With a backbone the site's PoP is chosen by the
  vendor (proximity, PoP health/load, country, underlay quality) [2]; with an
  appliance-led design the customer picks the regional hub. Data-residency
  constraints must be stated in the contract, not inferred from PoP placement.
- **Quantify last mile, not PoP count.** PoP count is a marketing number; the
  design-relevant question is whether a site has two diverse last-mile paths,
  because every SASE variant can only fail over to a transport that physically
  exists at that site.
- **State ZTNA vs. VPN vs. 802.1X ownership.** Name which system is authoritative
  for which access path (see [nac.md](nac.md)); otherwise two identity systems
  both claim the same users.

## Relationship to other techniques

- [dia-local-breakout.md](dia-local-breakout.md): SASE is what makes broad DIA
  defensible; a backbone-native product's bypass/off-cloud rule types are DIA
  expressed as vendor policy (see [cato.md](../vendor-matrix/cato.md)).
- [overlay-architecture.md](overlay-architecture.md): same controller/data-plane
  split, different middle mile — backbone-native SASE replaces the edge-to-edge
  overlay with site-to-PoP tunnels plus vendor transport between PoPs.
- [sla-policies.md](sla-policies.md): SLA thresholds are only meaningful if the
  measurement point is defined; backbone-native designs measure at the
  Socket/PoP pair, overlay designs measure edge-to-edge.
- [nac.md](nac.md): RADIUS/802.1X LAN access identity vs. ZTNA remote-access
  identity — different trust models, must be explicitly scoped.
- Scenario: [sdwan-sase-rollout.md](../scenarios/sdwan-sase-rollout.md).

## References

Every Cato source used here is **changeable** and was confirmed on **2026-10-20**.
Re-verify against the Cato Knowledge Base on its current platform
(`knowledge.catonetworks.com`, which replaced `support.catonetworks.com` for all
articles after **2026-08-09**) before relying on a detail in a design; if a URL
404s, search the article title on the current platform. Each entry below names the
section to re-check. The full Cato source set — appliance models, site-connection
capability tiers, link-SLA behaviour, deployment constraints — is cited in
[vendor-matrix/cato.md](../vendor-matrix/cato.md), using that file's own numbering.

1. Cato Networks, "Connecting Sites to the Cato Cloud," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/connecting-sites-to-the-cato-cloud
   (confirmed 2026-10-20). Verify: "Cato SASE vs SSE Services" and the
   "Overview of Site Types" comparison table (tunnel type, performance ceiling,
   analytics, QoS direction, HA tunnel counts).
2. Cato Networks, "What is Cato SD-WAN," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/what-is-cato-sd-wan
   (confirmed 2026-10-20). Verify: the "Steering" section.

