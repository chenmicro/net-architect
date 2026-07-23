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

**Workflow**: Start with the static library ([scenarios/](skills/scenarios/) →
[techniques/](skills/techniques/) → [vendor-matrix/](skills/vendor-matrix/)). When the
library doesn't cover a claim, fetch live (steps 4–5). **Write every new fact back into
the matching file immediately** — the library grows with each query so the next one
doesn't need to re-fetch the same fact.

**Source annotations** (applies to all files in this repo): every fact pulled from an
external source must carry an IEEE-style numbered citation in square brackets at the
point of use — e.g., `[1]`, `[2]` — with a corresponding `## References` section at
the end of the file listing the full source details in order of first appearance. Never
delete or renumber an existing citation; new sources get the next available number.

### 1. Scenarios (optional shortcut)

Check whether the request matches a known deployment scenario before reading
technique files piecemeal. A scenario file names which technique/vendor files a
given end-to-end ask draws on, in what order, plus cross-cutting judgment that only
exists at the intersection of those files. Most requests won't match; fall through
to step 2.

| Scenario | File | Composes |
|---|---|---|
| AI/GPU training cluster buildout | [skills/scenarios/ai-gpu-training-cluster.md](skills/scenarios/ai-gpu-training-cluster.md) | ai-gpu-fabric.md, spine-leaf-clos.md, vendor-matrix (buffer/ASIC) |
| Campus refresh with WAN edge modernization | [skills/scenarios/campus-wan-edge-refresh.md](skills/scenarios/campus-wan-edge-refresh.md) | core-agg-access.md, wireless.md, nac.md, poe.md, mpls.md or overlay-architecture.md |
| Multi-site SD-WAN + SASE rollout | [skills/scenarios/sdwan-sase-rollout.md](skills/scenarios/sdwan-sase-rollout.md) | overlay-architecture.md, dia-local-breakout.md, sla-policies.md, sase.md, nac.md, mpls.md/bgp.md (if migrating off MPLS) |
| Multi-site DC with cross-site workload mobility | [skills/scenarios/multi-site-workload-mobility.md](skills/scenarios/multi-site-workload-mobility.md) | spine-leaf-clos.md, evpn.md, multi-tenancy.md, vendor-matrix/cisco/aci.md (PBR — no confirmed fix on Multi-Site's documented architecture) and nxos-epbr.md (single-service-object ePBR pattern) |

> **Don't pre-create scenario files.** Add a scenario only after a real
> cross-technique request has been confirmed solved and confirmed network-related
> (double-check with the user). Keep scenario files thin — composition + cross-cutting
> judgment, never a copy of technique content.

### 2. Techniques

Identify the technique(s) the request touches and read the matching file(s) before
proposing a design. Most real requests span more than one technique — read all that
apply. Each file is a single atomic technique.

| Technique | File | Covers |
|---|---|---|
| Spine-Leaf (Clos) Fabric | [skills/techniques/spine-leaf-clos.md](skills/techniques/spine-leaf-clos.md) | Clos topology, oversubscription, ECMP/hashing, BGP underlay rationale |
| VXLAN | [skills/techniques/vxlan.md](skills/techniques/vxlan.md) | Data-plane encapsulation, VTEPs, VNI |
| EVPN | [skills/techniques/evpn.md](skills/techniques/evpn.md) | BGP control plane for VXLAN, route types 1-5, anycast gateway, EVPN-MH multi-homing |
| Multi-Tenancy (DC) | [skills/techniques/multi-tenancy.md](skills/techniques/multi-tenancy.md) | VRF-lite, route-target import/export, VNI numbering |
| RoCE | [skills/techniques/roce.md](skills/techniques/roce.md) | RDMA over Ethernet, RoCEv2 encapsulation, lossless Ethernet (PFC/ECN/DCQCN), iWARP vs. InfiniBand, packet format, Verbs operations |
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

**Writing back to techniques:**
- Fetched knowledge goes into the matching technique file, not left in chat context.
- **One file per technique.** If a file grows to cover a second distinct technique,
  split it. If new material doesn't fit any existing file, add one + a row above —
  but only after the question is resolved and you've confirmed with the user it's
  genuinely network architecture/design related.
- A technique used across many scenarios (e.g. BGP) stays written once, in its own
  file, with everything else linking to it.

### 3. Vendors

If the request names or implies a vendor (or asks you to choose one), read the
matching vendor file(s) to ground recommendations in actual product lines, OS, and
silicon. When comparing vendors, read all relevant files — platform-specific
naming and constraints vary.

| Vendor | File | Covers |
|---|---|---|
| Cisco | [skills/vendor-matrix/cisco/cisco.md](skills/vendor-matrix/cisco/cisco.md) | Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS. Links out to [aci.md](skills/vendor-matrix/cisco/aci.md) (APIC/ACI), [nxos-vxlan.md](skills/vendor-matrix/cisco/nxos-vxlan.md) (NX-OS-native EVPN-VXLAN), [aci-vs-nxos-vxlan.md](skills/vendor-matrix/cisco/aci-vs-nxos-vxlan.md) (head-to-head), [nxos-epbr.md](skills/vendor-matrix/cisco/nxos-epbr.md) (ePBR), [nxos-gpo.md](skills/vendor-matrix/cisco/nxos-gpo.md) (GPO) |
| Arista | [skills/vendor-matrix/arista.md](skills/vendor-matrix/arista.md) | EOS/SysDB, CloudVision, Broadcom merchant silicon, low-latency (7130) |
| Juniper | [skills/vendor-matrix/juniper.md](skills/vendor-matrix/juniper.md) | JVDs, Junos/Junos Evolved, Mist AI, MX vs PTX |
| Huawei | [skills/vendor-matrix/huawei.md](skills/vendor-matrix/huawei.md) | VRP, CloudEngine vs NetEngine, iMaster NCE |

**Writing back to vendors:**
- **Splitting**: when a vendor's coverage spans genuinely distinct, non-interoperable
  solutions (e.g. Cisco ACI vs. NX-OS-native EVPN-VXLAN), create a subfolder with a
  hub file (`cisco/cisco.md`) and one file per solution. Only split when a real
  second solution is confirmed — don't pre-create subfolders. The objective test: if
  the vendor ships a feature under its own separately-versioned Configuration/Solution
  Guide, it gets its own file here.

### 4. Fetch RFCs and IETF drafts

When a design claim hinges on a specific RFC or draft (normative behavior,
MUST/SHOULD language, whether an extension is standards-track or still a draft),
use `doc-fetcher`'s `fetch_rfc` / `fetch_draft` / `search_ietf` (see
[mcp/doc-fetcher/](mcp/doc-fetcher/)) instead of relying on memory. RFC numbers
and draft status are cheap to get wrong from recall and cheap to verify live.

### 5. Fetch current vendor documentation

When a claim depends on specifics that go beyond what [skills/vendor-matrix/](skills/vendor-matrix/)
captures, or that may have changed (port speeds/counts, ASIC buffer size, feature
support matrix, licensing tier), pull the vendor's own current documentation.

| Resource type | Tool | Notes |
|---|---|---|
| **Known URL** (HTML page) | `mcp-server-fetch` `fetch` | Preferred. Handles HTML→markdown, robots.txt, redirects. No per-query cost. |
| **Unknown URL** (need to discover) | `doc-fetcher` `search_web` | Discovery only (Brave Search, has a quota). Fetch the result URLs with `mcp-server-fetch` — never rely on snippets alone. |
| **PDF or non-HTML** | `doc-fetcher` `fetch_doc` | Only when `mcp-server-fetch` can't handle the format. |
| **IETF RFC/draft** | `doc-fetcher` `fetch_rfc` / `fetch_draft` / `search_ietf` | See step 4. |

### 6. Design output

State assumptions explicitly: scale (endpoint/port count, east-west vs north-south
ratio), oversubscription tolerance, resiliency target (N+1 vs N+2, dual-homing),
budget/licensing constraints. The `skills/` files describe the design space, not a
specific customer's constraints — ask if they're not given and materially change
the recommendation.

## Boundaries

- `doc-fetcher` is pure retrieval (fetch and normalize to text). Design judgment
  stays in this skill's prose, not in the tool. It has no write path — this repo
  targets solution design, not Day-2 operations. Anything that would touch a live
  device belongs in a different tool/repo.
- Never write new files while a question is still open or uncertain. Confirm with
  the user both that the issue is resolved and that it's genuinely network
  architecture/design related before adding a file or a table row.

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
│   │   ├── roce.md
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
│       ├── cisco/           # Hub + per-solution files for distinct products
│       │   ├── cisco.md     # Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS
│       │   ├── aci.md       # ACI/APIC: architecture, release history, Multi-Site PBR/NAT case
│       │   ├── nxos-vxlan.md # NX-OS-native EVPN-VXLAN: architecture, release history
│       │   ├── nxos-epbr.md # ePBR (own Config Guide, not a VXLAN feature): L4-7 redirect
│       │   ├── nxos-gpo.md  # GPO (own whitepaper, unratified IETF drafts): tag-based microsegmentation
│       │   └── aci-vs-nxos-vxlan.md # Head-to-head comparison + judgment call
│       ├── arista.md
│       ├── juniper.md
│       └── huawei.md
└── mcp/
    └── doc-fetcher/         # Pure retrieval tool (IETF RFCs, web search, vendor spec sheets)
        ├── index.ts
        └── package.json
```

## Commit policy

- Commit author identity must come from the active `git config` (`git config
  user.name` / `git config user.email` — repo-local config takes precedence over
  global) at the time of the commit. Never source author name/email from any other
  signal (session/environment metadata, chat context, memory, or guesswork). If
  `git config` has no name/email set (locally or globally), stop and ask rather
  than filling one in from elsewhere.
- Every commit must carry a `Co-authored-by` trailer identifying the LLM that
  performed the write, and a `Signed-off-by` trailer attributed to the author
  identity resolved from the active `git config`.
- Commit messages must conform to the [Conventional Commits](https://www.conventionalcommits.org/)
  specification.
