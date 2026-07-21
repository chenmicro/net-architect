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
- Vendor landscape here splits between single-vendor SASE (one vendor for both
  SD-WAN and SSE, e.g. Palo Alto Prisma SASE, Fortinet, Versa, Cisco+Umbrella) and
  dual-vendor/best-of-breed (SD-WAN from one vendor, SSE from another, e.g. via
  Zscaler or Netskope) — single-vendor simplifies operations and policy
  consistency, best-of-breed can win on point-feature strength; ask about existing
  security vendor relationships before defaulting to either.
