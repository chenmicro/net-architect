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

**POC records** ([pocs/](skills/pocs/)): Operational knowledge captured from real POC
tests — not architectural theory, but what actually broke and how it was fixed.
Consult these when planning a POC for a scenario you've designed, especially for
cross-vendor integrations where config traps are the main risk. Each POC record
ties to the scenario it validates. See
[pocs/README.md](skills/pocs/README.md) for the filing convention.

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

Sources fall into two categories with different handling:

- **Non-changeable** (RFCs, IEEE standards, published journal/conference papers):
  the fact is permanently fixed. Write the relevant detail inline in the technique
  file — a normative requirement, a protocol field definition, a well-known
  constant — so future readers don't need to re-fetch the source. The References
  entry should include the full bibliographic citation plus a URL when available.
  Example: an RFC's normative timer default goes inline; the reference cites the
  RFC number, title, and rfc-editor.org link.

- **Changeable / time-sensitive** (vendor datasheets, product documentation,
  third-party blog/review, vendor compatibility matrix): the fact can go stale
  — a port count, a buffer size, a supported software version, a pricing tier.
  The References entry must record **how to verify** the fact: which vendor
  document, section or chapter name, URL pattern (or search terms), and a
  date/version stamp of when the fact was last confirmed. Prefer the most stable
  URL path available (product-family doc hub over a per-release PDF). Do not
  embed a changeable fact inline as permanent truth without the verification
  path — a stale fact is worse than no fact because it looks authoritative but
  misleads.

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
| Cross-vendor DCI: Cisco ↔ Huawei CloudFabric | [skills/scenarios/cross-vendor-dci-interconnect.md](skills/scenarios/cross-vendor-dci-interconnect.md) | Variant A: vendor-matrix/cisco/aci.md §ACI Border Gateway + vendor-matrix/huawei.md §DCI. Variant B: vendor-matrix/cisco/nxos-vxlan.md §Multi-Site + vendor-matrix/huawei.md. Both: evpn.md, vxlan.md, bgp.md, multi-tenancy.md |

> **Don't pre-create scenario files.** Add a scenario only after a real
> cross-technique request has been confirmed solved and confirmed network-related
> (double-check with the user). Keep scenario files thin — composition + cross-cutting
> judgment, never a copy of technique content.

> **POC records** ([skills/pocs/](skills/pocs/)) are standalone operational knowledge —
> real issues from lab testing, not architectural reference. They cover specific
> integration patterns (e.g. BGP over M-LAG to an external firewall) that may appear
> as sub-components of a larger scenario but are documented separately. Check the
> [POC index](skills/pocs/README.md) to see if a record covers a pattern relevant to
> your current question.

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
| IGP — OSPF & IS-IS | [skills/techniques/ospf-isis.md](skills/techniques/ospf-isis.md) | OSPF vs. IS-IS selection, area/level design, timer tuning, cross-vendor alignment |
| ARP | [skills/techniques/arp.md](skills/techniques/arp.md) | RFC 826 basics, ARP flooding vs. suppression in EVPN/VXLAN fabrics, ARP gleaning (ACI), ARP/MAC timer mismatch, cross-vendor behavior |
| STP | [skills/techniques/stp.md](skills/techniques/stp.md) | PVST+ vs. MSTP vs. RSTP, root bridge placement, cross-vendor STP interop |
| FHRP | [skills/techniques/fhrp.md](skills/techniques/fhrp.md) | VRRP (RFC 5798) vs. HSRP/GLBP, preemption, tracking, anycast gateway as alternative |
| QoS | [skills/techniques/qos.md](skills/techniques/qos.md) | Classification/marking/queuing, trust models, DSCP alignment, DC vs. campus/WAN QoS |
| Management Plane | [skills/techniques/management-plane.md](skills/techniques/management-plane.md) | Discovery (LLDP/CDP), AAA (RADIUS/TACACS+), SNMP/telemetry, port mirroring, NTP/syslog — cross-vendor interop |
**Writing back to techniques:**
- Fetched knowledge goes into the matching technique file, not left in chat context.
- **One file per technique** — protocol architecture, vendor-specific implementation
  differences, interop constraints, and cross-vendor defaults mismatches all live in
  the same technique file. Splitting per-protocol vendor behavior across technique
  and vendor files is the wrong cut: a solution architect researching a multi-vendor
  interconnection consults the technique file first and expects the complete answer
  there, not a cross-reference trail to multiple vendor files.
- If a file grows to cover a second distinct technique, split it. If new material
  doesn't fit any existing file, add one + a row above — but only after the question
  is resolved and you've confirmed with the user it's genuinely network
  architecture/design related.
- A technique used across many scenarios (e.g. BGP) stays written once, in its own
  file, with everything else linking to it.
- **Standard chapter layout** — every technique file should follow a consistent
  section structure so the content is navigable and grep-friendly. Not every file
  needs every section (a protocol with no vendor variants skips Cross-vendor), but
  heading names must match exactly across files for searchability:

  ```
  # [Technique Name]
  [Overview — what it does, why it matters in design conversations]
  ## [Concept section(s)] — as needed per technique
  ## Cross-vendor / variants
  [Vendor implementation comparison table or prose, proprietary vs. open, interop constraints]
  ## Design considerations
  [Decision points, common pitfalls, default behaviors]
  ## Relationship to other techniques
  [Cross-links to related technique files with one-line notes on how they interact]
  ## References
  [Numbered citations, IEEE-style, ordered by first appearance]
  ```

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
| Extreme Networks | [skills/vendor-matrix/extreme-networks.md](skills/vendor-matrix/extreme-networks.md) | Universal Hardware, Switch Engine / Fabric Engine (VOSS/SPBm), SLX data center, ExtremeCloud IQ, Extreme Fabric |

**Writing back to vendors:**
- **Splitting**: when a vendor's coverage spans genuinely distinct, non-interoperable
  solutions (e.g. Cisco ACI vs. NX-OS-native EVPN-VXLAN), create a subfolder with a
  hub file (`cisco/cisco.md`) and one file per solution. Only split when a real
  second solution is confirmed — don't pre-create subfolders. The objective test: if
  the vendor ships a feature under its own separately-versioned Configuration/Solution
  Guide, it gets its own file here.
- **Version scope**: always reference the current/latest-version documentation and
  CLI for the product line in question. Older versions may differ in features, command
  names, or defaults. A fact confirmed only against a legacy-version doc is
  **unverified** until confirmed against the current version's documentation or a
  live CLI. Per-product-line version details (which version is current, which is EOL)
  live in the vendor file's version section, never duplicated here.

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
│   ├── pocs/               # POC test findings, config traps, and operational lessons
│   │   └── README.md       # Index — what each POC record covers
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
│   │   ├── bgp.md
│   │   ├── ospf-isis.md
│   │   ├── stp.md
│   │   ├── fhrp.md
│   │   ├── qos.md
│   │   └── management-plane.md
│   └── vendor-matrix/       # Platform specs, ASICs, & capabilities
│       ├── cisco/           # Hub + per-solution files for distinct products
│       │   ├── cisco.md     # Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS
│       │   ├── aci.md       # ACI/APIC: architecture, release history, Multi-Site PBR/NAT case
│       │   ├── nxos-vxlan.md # NX-OS-native EVPN-VXLAN: architecture, release history
│       │   ├── nxos-epbr.md # ePBR (own Config Guide, not a VXLAN feature): L4-7 redirect
│       │   ├── nxos-gpo.md  # GPO (own whitepaper, unratified IETF drafts): tag-based microsegmentation
│       │   └── aci-vs-nxos-vxlan.md # Head-to-head comparison + judgment call
│       ├── arista.md
│       ├── extreme-networks.md
│       ├── juniper.md
│       └── huawei.md
└── mcp/
    └── doc-fetcher/         # Pure retrieval tool (IETF RFCs, web search, vendor spec sheets)
        ├── index.ts
        └── package.json
```

## Agent behavior

### MCP server bootstrap

When this skill is loaded, the agent must first read `.mcp.json` and verify every
listed MCP server is installed and its tools are reachable. For each server that is
missing or unreachable:

1. Attempt to install it (e.g., `npm install` in the server's directory, or `uv tool install`
   for Python-based servers).
2. If installation succeeds, re-verify the tools are available.
3. If installation fails, surface the failure to the user immediately — do not silently
   skip the fetch step. The user must be told which server failed and what was attempted.

- **Do not update dependencies.** Never run `npm update`, `pip install --upgrade`, or any
  command that modifies `package-lock.json`, `pnpm-lock.yaml`, `Pipfile`, `Cargo.lock`, or
  equivalent lock/dependency files. The agent must only install missing MCP servers from
  `.mcp.json`, not alter existing dependency versions.

### Minimizing manual intervention

- **No pagers, no prompts.** Every git command must bypass interactive
  pagers and confirmations. Always use `git --no-pager` (or set
  `GIT_PAGER=cat`) for commands that would launch a pager (log, diff, show,
  blame). Pipe output to `cat` or redirect to a file when the tool doesn't
  support `--no-pager`. Never issue a command that pauses for user input —
  the agent must read all output programmatically without the user having to
  press tab, down, or q.
- **No heredocs, herestrings, or interactive shell constructs.** The
  `execute_command` tool runs commands programmatically — heredocs
  (`<<EOF` / `<<-EOF`), herestrings (`<<<`), and any construct that causes
  the shell to prompt for continuation input (`dquote>`, `heredoc>`,
  `quote>`) will freeze the terminal. Use `write_to_file` to write content
  to a file and then reference the file path in the command. For short
  inline content, pipe via `printf` or `echo` instead.
- **Write back immediately.** After every external fetch (RFC, draft, vendor
  doc, web search result), write the new fact into the matching skill file
  before proposing the design. Do not accumulate facts in chat context — the
  library must grow with each query so the next one doesn't re-fetch the same
  information. **Keep changes uncommitted** — the user reviews and commits.
- **List changes on startup.** At the beginning of each session, run
  `git diff --stat` and `git diff` to show all uncommitted changes from prior
  sessions so the user knows what's pending review.
- **Resolve before creating.** Never create a new technique, scenario, or
  vendor file while a question is still open or uncertain. Confirm with the
  user both that the issue is resolved and that it's genuinely network
  architecture/design related before adding a file or a table row.
- **Don't ask what you can infer.** When the user gives a design request,
  extract all implied constraints (scale, vendor, topology) from the request
  itself before asking for clarifications. Only prompt the user when a missing
  parameter materially changes the recommendation — and when you do ask, make
  it a single consolidated question, not a back-and-forth.
- **Verify heading conformance.** Before editing any file under
  `skills/techniques/`, confirm the file contains the four mandatory `## `
  headings from the [standard chapter layout](#2-techniques) above. The
  heading names must match exactly — no synonyms, no rewording. A file may
  have additional `## ` concept sections above these four, but all four must
  be present and named exactly as in the template. If any is missing or
  renamed, fix it.
- **One turn, one deliverable.** When the user asks a design question, produce
  a complete answer (design rationale, vendor recommendation if applicable,
  citations) in a single response. Don't drip-feed partial answers across
  multiple turns unless the user explicitly asks for iteration.

### Branch policy

- **Never commit to `main`.** The `main` branch is protected — only the repo
  maintainer merges into it (via PR or locally), never the agent.
- The agent works on a branch named by the `BRANCH_NAME` variable in `.env`.
- **If `BRANCH_NAME` is unset or empty**, the agent must generate a UUID, write
  the first 8 hex characters to `.env` as `BRANCH_NAME=agents/<short-uuid>`,
  and reload the env before proceeding.
- The agent must ensure its branch exists locally: `git checkout -b "$BRANCH_NAME"`
  if it doesn't already exist.
- Before each session, sync from main: `git fetch origin && git merge origin/main`
  (or rebase) to stay current.

### Commit policy

The agent does not commit autonomously — all file edits are left uncommitted
unless the user explicitly asks. When asked to commit, the agent follows:

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
- **Use `.git/COMMIT_MSG` for multi-line messages.** Never pass a multi-line
  commit message with `git commit -m` — shell quoting fails on mixed quotes and
  special characters. Heredocs are also prohibited (see [No heredocs](#minimizing-manual-intervention)
  above). Instead, write the message to `.git/COMMIT_MSG` using
  `write_to_file` (VS Code excludes `.git/` from file watchers, so no save
  prompt) and commit with `git commit -F .git/COMMIT_MSG`. Single-line messages
  are safe with `-m`. Do not use `/tmp/` paths — they trigger VS Code save
  prompts.
