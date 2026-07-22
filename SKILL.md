---
name: net-architect
description: Use this skill for network architecture and design questions — data center fabric (spine-leaf, EVPN-VXLAN, AI/GPU fabrics), campus networking (wired/wireless, NAC), SD-WAN/SASE, or WAN/MPLS/segment-routing design — and whenever a specific vendor's platform, OS, or product line (Cisco, Arista, Juniper, Huawei) needs to be evaluated or compared, or current information needs to be pulled from the web: an IETF RFC/draft, a vendor's own spec sheet/datasheet, or a general web search to locate one. Triggers on requests to design, review, size, or compare enterprise/service-provider network topologies, or to pick a vendor/platform for one.
---

# net-architect

A reference library plus a pure-retrieval MCP tool for network architecture and
solution-design work, organized so an agent loads only the knowledge relevant to the
task at hand and only reaches for live retrieval when static knowledge isn't enough.
This is a specialist/architect toolset — it brings external specifications and vendor
documentation into context; it does not touch live infrastructure. `doc-fetcher` has no
offline mode or bundled copies: every call is a live outbound HTTPS fetch against the
IETF or a vendor's own site, so it needs internet access to function, and it fails
outright (rather than silently falling back to a stale answer) if that access isn't
available — see [README.md](README.md#network-access) for the specific hosts involved.

## How to use this skill

1. **Check whether the request matches a known deployment scenario** in
   [skills/scenarios/](skills/scenarios/) before reading technique files piecemeal —
   a scenario file names which technique/vendor files a given end-to-end ask draws
   on, in what order, plus cross-cutting judgment that only exists at the
   intersection of those files. Most requests won't match a canned scenario; that's
   fine, fall through to step 2.

   | Scenario | File | Composes |
   |---|---|---|
   | AI/GPU training cluster buildout | [skills/scenarios/ai-gpu-training-cluster.md](skills/scenarios/ai-gpu-training-cluster.md) | ai-gpu-fabric.md, spine-leaf-clos.md, vendor-matrix (buffer/ASIC) |
   | Campus refresh with WAN edge modernization | [skills/scenarios/campus-wan-edge-refresh.md](skills/scenarios/campus-wan-edge-refresh.md) | core-agg-access.md, wireless.md, nac.md, poe.md, mpls.md or overlay-architecture.md |
   | Multi-site SD-WAN + SASE rollout | [skills/scenarios/sdwan-sase-rollout.md](skills/scenarios/sdwan-sase-rollout.md) | overlay-architecture.md, dia-local-breakout.md, sla-policies.md, sase.md, nac.md, mpls.md/bgp.md (if migrating off MPLS) |
   | Multi-site DC with cross-site workload mobility | [skills/scenarios/multi-site-workload-mobility.md](skills/scenarios/multi-site-workload-mobility.md) | spine-leaf-clos.md, evpn.md, multi-tenancy.md, vendor-matrix/cisco/aci.md (PBR anchoring — the concrete mechanism; NX-OS-native equivalent not yet documented) |

2. **Identify the technique(s)** the request touches and read the matching file(s) in
   [skills/techniques/](skills/techniques/) before proposing a design. Most real
   requests span more than one technique (e.g. a campus refresh that also touches the
   WAN edge) — read all that apply; there's no domain grouping to load wholesale, each
   file is a single atomic technique.

   | Technique | File | Covers |
   |---|---|---|
   | Spine-Leaf (Clos) Fabric | [skills/techniques/spine-leaf-clos.md](skills/techniques/spine-leaf-clos.md) | Clos topology, oversubscription, ECMP/hashing, BGP underlay rationale |
   | VXLAN | [skills/techniques/vxlan.md](skills/techniques/vxlan.md) | Data-plane encapsulation, VTEPs, VNI |
   | EVPN | [skills/techniques/evpn.md](skills/techniques/evpn.md) | BGP control plane for VXLAN, route types 1-5, anycast gateway, EVPN-MH multi-homing |
   | Multi-Tenancy (DC) | [skills/techniques/multi-tenancy.md](skills/techniques/multi-tenancy.md) | VRF-lite, route-target import/export, VNI numbering |
   | AI/GPU Fabric | [skills/techniques/ai-gpu-fabric.md](skills/techniques/ai-gpu-fabric.md) | RoCEv2, lossless Ethernet (PFC/ECN/DCQCN), rail-optimized topology, InfiniBand vs. Ethernet |
   | Core/Aggregation/Access | [skills/techniques/core-agg-access.md](skills/techniques/core-agg-access.md) | Three-tier vs. collapsed-core, L2/L3 boundary placement, redundancy |
   | Wireless | [skills/techniques/wireless.md](skills/techniques/wireless.md) | WLC architecture, AP density, RF planning, Wi-Fi 6E/7 |
   | NAC | [skills/techniques/nac.md](skills/techniques/nac.md) | 802.1X, MAB, dynamic VLAN/RADIUS, SGT/TrustSec |
   | PoE | [skills/techniques/poe.md](skills/techniques/poe.md) | Power budgeting, 802.3af/at/bt, cable-length derating |
   | SD-WAN Overlay Architecture | [skills/techniques/overlay-architecture.md](skills/techniques/overlay-architecture.md) | Controller/orchestrator model, IPsec overlay, topology choice |
   | DIA / Local Breakout | [skills/techniques/dia-local-breakout.md](skills/techniques/dia-local-breakout.md) | Local internet egress, security tradeoff, traffic steering |
   | SLA Policies | [skills/techniques/sla-policies.md](skills/techniques/sla-policies.md) | App-aware routing, SLA classes, BFD, circuit diversity |
   | SASE | [skills/techniques/sase.md](skills/techniques/sase.md) | SSE convergence, ZTNA, single-vendor vs. best-of-breed |
   | MPLS | [skills/techniques/mpls.md](skills/techniques/mpls.md) | LDP/RSVP-TE, L3VPN (RFC 4364), L2VPN (VPWS/VPLS) |
   | Segment Routing | [skills/techniques/segment-routing.md](skills/techniques/segment-routing.md) | SR-MPLS/SRv6, SR-TE policies, flex-algo |
   | BGP | [skills/techniques/bgp.md](skills/techniques/bgp.md) | eBGP/iBGP, route reflectors, confederations, communities, peering hygiene — shared by any technique above that rides on BGP |

3. **If the request names or implies a vendor** (or asks you to choose one), read the
   matching file in [skills/vendor-matrix/](skills/vendor-matrix/) to ground
   recommendations in that vendor's actual product lines, OS, and silicon rather than
   generic claims.

   | Vendor | File | Covers |
   |---|---|---|
   | Cisco | [skills/vendor-matrix/cisco/cisco.md](skills/vendor-matrix/cisco/cisco.md) | Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS. Links out to [aci.md](skills/vendor-matrix/cisco/aci.md) (APIC/ACI) and [nxos-vxlan.md](skills/vendor-matrix/cisco/nxos-vxlan.md) (NX-OS-native EVPN-VXLAN) — two distinct, non-interoperable DC fabric solutions, each with its own release history — plus [aci-vs-nxos-vxlan.md](skills/vendor-matrix/cisco/aci-vs-nxos-vxlan.md) for the head-to-head comparison |
   | Arista | [skills/vendor-matrix/arista.md](skills/vendor-matrix/arista.md) | EOS/SysDB, CloudVision, Broadcom merchant silicon, low-latency (7130) |
   | Juniper | [skills/vendor-matrix/juniper.md](skills/vendor-matrix/juniper.md) | JVDs, Junos/Junos Evolved, Mist AI, MX vs PTX |
   | Huawei | [skills/vendor-matrix/huawei.md](skills/vendor-matrix/huawei.md) | VRP, CloudEngine vs NetEngine, iMaster NCE |

4. **When comparing vendors for the same design**, read all relevant vendor files rather
   than relying on memory — the files capture platform-specific naming and constraints
   that generic knowledge tends to blur together (e.g. EVPN feature parity, ASIC buffer
   architecture, licensing model).

5. **When a design claim hinges on a specific RFC or draft** (normative behavior, MUST/
   SHOULD language, whether a route type or extension is standards-track or still a
   draft), use the `doc-fetcher` MCP tool's `fetch_rfc` / `fetch_draft` / `search_ietf`
   (see [mcp/doc-fetcher/](mcp/doc-fetcher/)) instead of relying on memory for the text
   — RFC numbers and draft status are exactly the kind of detail that's cheap to get
   wrong from recall and cheap to verify live.

6. **When a design claim hinges on current vendor specifics** (exact port speeds/
   counts on a specific SKU, ASIC buffer size, EVPN feature support matrix, licensing
   tier) that go beyond what [skills/vendor-matrix/](skills/vendor-matrix/) captures,
   or that may have changed since it was written, pull the vendor's own current
   documentation with `doc-fetcher` rather than guessing at current-generation
   numbers — vendor hardware specs move faster than this repo does. If the exact
   datasheet/spec-sheet URL isn't already known, use `search_web` first to find it
   (e.g. `"Arista 7800R4 datasheet"`), then `fetch_doc` on the URL it returns to
   actually read it — `search_web` only returns titles/URLs/snippets, not full
   document text.

7. **Design output should state assumptions explicitly**: scale (endpoint/port count,
   east-west vs north-south ratio), oversubscription tolerance, resiliency target
   (N+1 vs N+2, dual-homing), and budget/licensing constraints. The `skills/` files
   describe the design space, not a specific customer's constraints — ask if they're
   not given and materially change the recommendation. `doc-fetcher` fills gaps in
   external reference material, not in customer-specific requirements.

## Repo layout

```
net-architect/
├── SKILL.md                 # Root entry point & design decision logic
├── skills/
│   ├── scenarios/           # Cross-technique composition (which techniques + in what order)
│   │   ├── ai-gpu-training-cluster.md
│   │   ├── campus-wan-edge-refresh.md
│   │   ├── sdwan-sase-rollout.md
│   │   └── multi-site-workload-mobility.md
│   ├── techniques/          # Atomic, one file per technique (flat, no domain grouping)
│   │   ├── spine-leaf-clos.md
│   │   ├── vxlan.md
│   │   ├── evpn.md
│   │   ├── multi-tenancy.md
│   │   ├── ai-gpu-fabric.md
│   │   ├── core-agg-access.md
│   │   ├── wireless.md
│   │   ├── nac.md
│   │   ├── poe.md
│   │   ├── overlay-architecture.md
│   │   ├── dia-local-breakout.md
│   │   ├── sla-policies.md
│   │   ├── sase.md
│   │   ├── mpls.md
│   │   ├── segment-routing.md
│   │   └── bgp.md
│   └── vendor-matrix/       # Platform specs, ASICs, & capabilities
│       ├── cisco/           # Split into a hub + per-solution files (see Maintenance)
│       │   ├── cisco.md     # Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS
│       │   ├── aci.md       # ACI/APIC: architecture, release history, Multi-Site PBR/NAT case
│       │   ├── nxos-vxlan.md # NX-OS-native EVPN-VXLAN: architecture, release history
│       │   └── aci-vs-nxos-vxlan.md # Head-to-head comparison + judgment call
│       ├── arista.md
│       ├── juniper.md
│       └── huawei.md
└── mcp/
    └── doc-fetcher/         # Pure retrieval tool (IETF RFCs, web search, vendor spec sheets)
        ├── index.ts
        └── package.json
```

## Maintenance

- Each technique/vendor file should stay narrowly scoped to its table row above and
  cover exactly one technique — if a file grows to cover a second, distinct technique
  (the original problem this rule exists to prevent: VXLAN and EVPN used to be one
  section), split it into its own file rather than let it re-merge. When new material
  doesn't fit an existing file (e.g. a new technique, or a new vendor), add a file and
  a row rather than overloading an existing one — that's what keeps per-request
  loading cheap.
- The same splitting rule applies to vendor files when a single vendor's coverage
  grows to span genuinely distinct, non-interoperable solutions (e.g. Cisco ACI vs.
  NX-OS-native EVPN-VXLAN — same vendor, same problem space, but different
  architectures, release cadences, and operational models). When that happens,
  turn the vendor file into a subfolder: a hub file (kept at the vendor's own name,
  e.g. `cisco/cisco.md`) holding cross-cutting/general vendor knowledge, plus one
  file per solution that the hub links out to. Only split when a real second
  solution is confirmed (same rule as new technique/vendor files below) — don't
  pre-create subfolders for vendors that don't need one yet.
- When new knowledge is pulled from the web (via `doc-fetcher` or general web
  search) rather than derived from this repo's existing material, record the
  source: add a `[ref](<url>)` link immediately after the specific sentence or
  table cell that claim supports — not a bibliography dumped at the end of the
  file. This keeps each claim independently verifiable and lets a stale fact be
  spotted (and re-checked) at the point it's used, rather than requiring a reader
  to cross-reference a detached source list.
- `doc-fetcher` stays a thin, pure-retrieval tool (fetch and normalize to text) — design
  judgment stays in this skill's prose, not in the tool. It has no write path and should
  never grow one; this repo targets solution design, not Day-2 operations, so anything
  that would touch a live device belongs in a different tool/repo entirely.
- When a query falls outside this skill's current coverage (a technique, vendor, or
  design pattern with no matching file, or a file that turns out to be missing the
  relevant detail), only update the skill once the question has actually been
  resolved (not while still open or uncertain) and only if it's genuinely network
  architecture/design related — confirm both with the user before writing anything.
  Once confirmed, add or extend the relevant file and, for a new technique/vendor,
  add its row to the tables above — so the same gap doesn't have to be rediscovered
  on the next query. This same rule covers [skills/scenarios/](skills/scenarios/):
  add a scenario file only once a real cross-technique request has been confirmed
  solved and confirmed network-related, same double-check with the user. Keep
  scenario files thin — composition (which technique/vendor files, in what order)
  and cross-cutting judgment that only exists at the intersection, never a copy of
  technique content. A technique (EVPN, BGP, SASE, ...) is used across many
  scenarios and, sometimes, by other technique files too (e.g. `spine-leaf-clos.md`
  and `evpn.md` both link to `bgp.md` rather than re-explaining it); it must stay
  written once, in its own file under [skills/techniques/](skills/techniques/), with
  everything else linking to it.

## Commit policy

- Commit author identity must come from the active `git config` (`git config
  user.name` / `git config user.email` — repo-local config takes precedence over
  global) at the time of the commit. Never source author name/email from any other
  signal (session/environment metadata, chat context, memory, a contributor list, or
  guesswork) — those can silently diverge from the config that will actually stamp the
  commit. If `git config` has no name/email set (locally or globally), stop and ask
  rather than filling one in from elsewhere.
- Commit messages must conform to the [Conventional Commits](https://www.conventionalcommits.org/)
  specification and must carry a `Signed-off-by` trailer (i.e., committed with `git
  commit --signoff`), attributed to the identity resolved from the active `git config`
  per the rule above rather than entered independently.
