# Multi-Site SD-WAN + SASE Rollout

## Composes

1. [skills/techniques/overlay-architecture.md](../techniques/overlay-architecture.md),
   [dia-local-breakout.md](../techniques/dia-local-breakout.md),
   [sla-policies.md](../techniques/sla-policies.md), and [sase.md](../techniques/sase.md)
   — a rollout typically needs all four, since DIA's security tradeoff is exactly what
   SASE exists to close.
2. [skills/techniques/nac.md](../techniques/nac.md) — for identity-based policy
   continuity from the wired/wireless LAN edge through to ZTNA, so the design doesn't
   end up with two disconnected identity systems.
3. [skills/techniques/mpls.md](../techniques/mpls.md) (and
   [bgp.md](../techniques/bgp.md) if BGP peering changes are in scope) — only if
   legacy MPLS is being displaced or is coexisting with the new SD-WAN overlay during
   a migration; skip if this is a greenfield SD-WAN-only build.

## Cross-cutting judgment

- NAC's RADIUS-driven identity ([nac.md](../techniques/nac.md)) and ZTNA's continuous
  identity/posture verification ([sase.md](../techniques/sase.md)) both claim to
  answer "who is this and what can they reach," but they're different systems with
  different trust models. The design needs to state explicitly which one is
  authoritative for which access path — wired/wireless LAN vs. remote/hybrid —
  rather than leaving both partially overlapping and undocumented about which wins
  in a conflict.
- If legacy MPLS coexists with SD-WAN during migration, the SLA/app-aware routing
  policy ([sla-policies.md](../techniques/sla-policies.md)) needs to account for
  both transport types being present simultaneously, including circuit diversity
  checks across the old and new edges — not just among the new SD-WAN transports.
- DIA's security posture question ([dia-local-breakout.md](../techniques/dia-local-breakout.md))
  is answered differently depending on whether SASE/SSE is rolling out in the same
  phase or later — don't recommend broad DIA enablement ahead of the security-stack
  half of the rollout landing.

## Questions to ask early

- Coexistence-vs-cutover timeline with any existing MPLS.
- Single-vendor SASE vs. best-of-breed preference, and existing security vendor
  relationships.
- Remote/hybrid user population size and urgency — drives how much ZTNA displaces
  traditional VPN in this phase vs. a later one.
- Which sites/regions roll out first, and whether the rollout order is driven by
  contract expiration (existing MPLS/circuit terms) or by risk/complexity.
