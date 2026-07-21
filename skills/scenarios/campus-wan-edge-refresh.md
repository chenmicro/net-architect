# Campus Refresh with WAN Edge Modernization

## Composes

1. [skills/techniques/core-agg-access.md](../techniques/core-agg-access.md),
   [wireless.md](../techniques/wireless.md), [nac.md](../techniques/nac.md), and
   [poe.md](../techniques/poe.md) — a campus refresh almost always touches all four,
   since core/access hardware age, wireless standard, NAC posture, and PoE budget
   tend to be replaced together rather than piecemeal.
2. [skills/techniques/mpls.md](../techniques/mpls.md) or
   [overlay-architecture.md](../techniques/overlay-architecture.md) for the WAN edge
   itself — which one depends on whether the refresh keeps the existing MPLS edge or
   moves to SD-WAN; read both if that decision isn't made yet.

## Cross-cutting judgment

- Sequencing matters and isn't obvious from any single technique file alone: core/tier
  hardware swap, wireless/NAC rollout, and WAN edge cutover each have their own
  maintenance-window and rollback considerations, and doing them out of order can
  create avoidable double-outages (e.g. swapping the core before NAC is validated in
  monitor mode risks compounding two untested changes in one window).
- PoE budget planning ([poe.md](../techniques/poe.md)) needs to account for the new
  WAN edge closet's power draw too if it's colocated with access switching, not just
  endpoint PoE load — this is a real interaction the file doesn't call out on its own
  since it's written for endpoint-facing budgeting.
- If NAC is being deployed or re-deployed as part of this refresh, its monitor-mode
  rollout ([nac.md](../techniques/nac.md)) should land *before* the WAN edge cutover,
  not after — otherwise a NAC misconfiguration and a WAN edge issue surfacing in the
  same window are much harder to isolate from each other.

## Questions to ask early

- Is the WAN edge decision (stay MPLS vs. move to SD-WAN) already made, or part of the
  scope of this same project?
- Single building/collapsed-core or multi-building/three-tier campus?
- Existing NAC posture: greenfield deployment, or migrating/re-validating an existing
  one?
- Are core/access refresh, wireless refresh, and WAN edge cutover being planned as one
  combined maintenance window or staged separately?
