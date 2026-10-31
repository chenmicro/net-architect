---
name: net-architect
description: Use for network architecture and design — data center fabric (spine-leaf, EVPN-VXLAN, AI/GPU fabrics), campus (wired/wireless, NAC), SD-WAN/SASE, and WAN/MPLS/segment routing. Use to design, review, size, or compare enterprise or service-provider topologies; to evaluate or pick a vendor or platform (Cisco, Arista, Juniper, Huawei, Extreme Networks, Cato, IBM, Netis, Dynatrace, NETSCOUT); or to look up an IETF RFC/draft or vendor spec sheet.
---

# net-architect

A reference library plus a pure-retrieval MCP tool for network architecture and
solution-design work. Load only the knowledge relevant to the task, and reach for live
retrieval only when static knowledge isn't enough. It brings specifications and vendor
documentation into context; it does not touch live infrastructure. `doc-fetcher` needs
internet access and fails outright without it.

## How to use this skill

**Workflow**: Start with the static library ([scenarios/](skills/scenarios/) →
[techniques/](skills/techniques/) → [vendor-matrix/](skills/vendor-matrix/)). When the
library doesn't cover a claim, fetch live (steps 4–5). Write every new fact back into
the matching file immediately, so the next query doesn't re-fetch it.

**Load on demand:**

- **Before editing anything under `skills/`**, read [docs/authoring.md](docs/authoring.md)
  for citation, file-placement, and splitting rules.
- **Before committing**, read [docs/git-policy.md](docs/git-policy.md).

**POC records** ([skills/pocs/](skills/pocs/)): what actually broke in real tests and
how it was fixed. Consult these when planning a POC, especially for cross-vendor
integrations where config traps are the main risk. See the
[POC index](skills/pocs/README.md).

### 1. Scenarios (optional shortcut)

Check whether the request matches a known deployment scenario before reading
technique files piecemeal. A scenario file names which files a request draws on, in
what order, plus judgment that only exists where they intersect. Most requests won't
match; fall through to step 2.

| Scenario | File | Composes |
|---|---|---|
| AI/GPU training cluster buildout | [ai-gpu-training-cluster.md](skills/scenarios/ai-gpu-training-cluster.md) | ai-gpu-fabric.md, spine-leaf-clos.md, vendor-matrix (buffer/ASIC) |
| Campus refresh with WAN edge modernization | [campus-wan-edge-refresh.md](skills/scenarios/campus-wan-edge-refresh.md) | core-agg-access.md, wireless.md, nac.md, poe.md, mpls.md or overlay-architecture.md |
| Multi-site SD-WAN + SASE rollout | [sdwan-sase-rollout.md](skills/scenarios/sdwan-sase-rollout.md) | overlay-architecture.md, dia-local-breakout.md, sla-policies.md, sase.md, nac.md, mpls.md/bgp.md, vendor-matrix/cato.md |
| Multi-site DC with cross-site workload mobility | [multi-site-workload-mobility.md](skills/scenarios/multi-site-workload-mobility.md) | spine-leaf-clos.md, evpn.md, multi-tenancy.md, cisco/aci.md, cisco/nxos-epbr.md |
| Silent-host reachability in overlay fabrics (L2/bridged) | [silent-host-in-overlays.md](skills/scenarios/silent-host-in-overlays.md) | arp.md, evpn.md, vxlan.md, cisco/aci.md |
| Cross-vendor DCI: Cisco ↔ Huawei CloudFabric | [cross-vendor-dci-interconnect.md](skills/scenarios/cross-vendor-dci-interconnect.md) | cisco/aci.md or cisco/nxos-vxlan.md, huawei.md, evpn.md, vxlan.md, bgp.md, multi-tenancy.md |

### 2. Techniques

Identify the technique(s) the request touches and read the matching file(s) before
proposing a design. Most real requests span more than one technique — read all that
apply. Each file is a single atomic technique.

| Technique | File | Covers |
|---|---|---|
| Spine-Leaf (Clos) Fabric | [spine-leaf-clos.md](skills/techniques/spine-leaf-clos.md) | Clos topology, oversubscription, ECMP/hashing, BGP underlay |
| VXLAN | [vxlan.md](skills/techniques/vxlan.md) | Encapsulation, VTEPs, VNI, RFC 7348, VXLAN-GBP, VXLAN-GPE, ACI iVXLAN |
| EVPN | [evpn.md](skills/techniques/evpn.md) | BGP control plane, route types 1-5, anycast gateway, EVPN-MH |
| Multi-Tenancy (DC) | [multi-tenancy.md](skills/techniques/multi-tenancy.md) | VRF-lite, route-target import/export, VNI numbering |
| RoCE | [roce.md](skills/techniques/roce.md) | RDMA over Ethernet, RoCEv2, PFC/ECN/DCQCN, iWARP vs. InfiniBand, Verbs |
| AI/GPU Fabric | [ai-gpu-fabric.md](skills/techniques/ai-gpu-fabric.md) | Lossless Ethernet, rail-optimized topology, NSLB, InfiniBand vs. Ethernet |
| Core/Aggregation/Access | [core-agg-access.md](skills/techniques/core-agg-access.md) | Three-tier vs. collapsed-core, L2/L3 boundary, redundancy |
| Wireless | [wireless.md](skills/techniques/wireless.md) | WLC architecture, AP density, RF planning, Wi-Fi 6E/7 |
| NAC | [nac.md](skills/techniques/nac.md) | 802.1X, MAB, dynamic VLAN/RADIUS, SGT/TrustSec |
| PoE | [poe.md](skills/techniques/poe.md) | Power budgeting, 802.3af/at/bt, cable-length derating |
| SD-WAN Overlay Architecture | [overlay-architecture.md](skills/techniques/overlay-architecture.md) | Controller/orchestrator model, IPsec overlay, topology choice |
| DIA / Local Breakout | [dia-local-breakout.md](skills/techniques/dia-local-breakout.md) | Local internet egress, security tradeoff, traffic steering |
| SLA Policies | [sla-policies.md](skills/techniques/sla-policies.md) | App-aware routing, SLA classes, BFD, circuit diversity |
| SASE | [sase.md](skills/techniques/sase.md) | SSE convergence, ZTNA, single-vendor vs. best-of-breed |
| MPLS | [mpls.md](skills/techniques/mpls.md) | LDP/RSVP-TE, L3VPN (RFC 4364), L2VPN (VPWS/VPLS) |
| Segment Routing | [segment-routing.md](skills/techniques/segment-routing.md) | SR-MPLS/SRv6, SR-TE policies, flex-algo |
| BGP | [bgp.md](skills/techniques/bgp.md) | eBGP/iBGP, route reflectors, confederations, communities, peering hygiene |
| IGP — OSPF & IS-IS | [ospf-isis.md](skills/techniques/ospf-isis.md) | Selection, area/level design, timers, cross-vendor alignment |
| ARP | [arp.md](skills/techniques/arp.md) | RFC 826, flooding vs. suppression, gleaning, ARP/MAC timer mismatch, Linux neighbor cache |
| STP | [stp.md](skills/techniques/stp.md) | PVST+ vs. MSTP vs. RSTP, root placement, cross-vendor interop |
| FHRP | [fhrp.md](skills/techniques/fhrp.md) | VRRP (RFC 5798) vs. HSRP/GLBP, preemption, tracking, anycast gateway |
| QoS | [qos.md](skills/techniques/qos.md) | Classification/marking/queuing, trust models, DSCP, DC vs. campus/WAN |
| Management Plane | [management-plane.md](skills/techniques/management-plane.md) | LLDP/CDP, RADIUS/TACACS+, SNMP/telemetry, port mirroring, NTP/syslog |
| Network Performance Monitoring (NPM) | [npm.md](skills/techniques/npm.md) | Device, flow, packet, active-probe, and path evidence |
| Application Performance Monitoring (APM) | [apm.md](skills/techniques/apm.md) | Taxonomy, host-agent vs. network-derived collection, selection |
| NPM/APM Correlation | [npm-apm.md](skills/techniques/npm-apm.md) | Shared identity, clocks, topology, multi-point correlation |

### 3. Vendors

If the request names or implies a vendor (or asks you to choose one), read the
matching vendor file(s) to ground recommendations in actual product lines, OS, and
silicon. When comparing vendors, read all relevant files.

Always reference the current-version documentation and CLI for the product line. The
vendor file's version section says which version is current. Treat a fact confirmed
only against a legacy-version doc as unverified.

| Vendor | File | Covers |
|---|---|---|
| Cisco | [cisco/cisco.md](skills/vendor-matrix/cisco/cisco.md) | Hub: CVDs, Silicon One, Catalyst vs Nexus, IOS-XE vs NX-OS; links to ACI, NX-OS VXLAN, GPO, Nexus hardware, 7-5-2, and AgenticOps files. ePBR: [nxos-epbr.md](skills/vendor-matrix/cisco/nxos-epbr.md) |
| Arista | [arista.md](skills/vendor-matrix/arista.md) | EOS/SysDB, CloudVision, Broadcom merchant silicon, low-latency (7130) |
| Juniper | [juniper.md](skills/vendor-matrix/juniper.md) | JVDs, Junos/Junos Evolved, Mist AI, MX vs PTX |
| Huawei | [huawei.md](skills/vendor-matrix/huawei.md) | VRP, CloudEngine vs NetEngine, iMaster NCE |
| Extreme Networks | [extreme-networks.md](skills/vendor-matrix/extreme-networks.md) | Switch Engine / Fabric Engine (VOSS/SPBm), SLX, ExtremeCloud IQ, Extreme Fabric |
| Cato Networks | [cato.md](skills/vendor-matrix/cato.md) | SASE/SSE tiers, backbone and PoPs, Socket/vSocket, link SLA and redundancy |
| IBM | [ibm.md](skills/vendor-matrix/ibm.md) | QRadar QFlow collection, application identification, flow correlation |
| Netis | [netis.md](skills/vendor-matrix/netis.md) | NPM, packet/service observability, BPC/wire-data APM, Netis 42 |
| Dynatrace | [dynatrace.md](skills/vendor-matrix/dynatrace.md) | Host-agent and instrumented APM, OpenTelemetry paths, RUM correlation |
| NETSCOUT | [netscout.md](skills/vendor-matrix/netscout.md) | nGeniusONE network-derived APM, packet-collection architecture |

### 4. Fetch RFCs and IETF drafts

When a design claim hinges on a specific RFC or draft (normative behavior,
MUST/SHOULD language, standards-track vs. draft status), use `doc-fetcher`'s
`fetch_rfc` / `fetch_draft` / `search_ietf` (see [mcp/doc-fetcher/](mcp/doc-fetcher/))
instead of relying on memory. RFC numbers and draft status are cheap to get wrong from
recall and cheap to verify live.

### 5. Fetch current vendor documentation

When a claim depends on specifics that go beyond what
[skills/vendor-matrix/](skills/vendor-matrix/) captures, or that may have changed (port
speeds/counts, ASIC buffer size, feature support matrix, licensing tier), pull the
vendor's own current documentation.

| Resource type | Tool | Notes |
|---|---|---|
| **Known URL** (HTML page) | `mcp-server-fetch` `fetch` | Preferred. Handles HTML→markdown, robots.txt, redirects. No per-query cost. |
| **Unknown URL** (need to discover) | `doc-fetcher` `search_web` | Discovery only (Brave Search, has a quota). Fetch the result URLs with `mcp-server-fetch` — never rely on snippets alone. |
| **PDF or non-HTML** | `doc-fetcher` `fetch_doc` | Only when `mcp-server-fetch` can't handle the format. |
| **IETF RFC/draft** | `doc-fetcher` `fetch_rfc` / `fetch_draft` / `search_ietf` | See step 4. |
| **Huawei product documentation** | Local HedEx library | Do not fetch or search the web for it: it requires login. Read the library the user supplied; if the needed library is missing, ask the user. |

### 6. Design output

State assumptions explicitly: scale (endpoint/port count, east-west vs north-south
ratio), oversubscription tolerance, resiliency target (N+1 vs N+2, dual-homing),
budget/licensing constraints. The `skills/` files describe the design space, not a
specific customer's constraints — ask if they're not given and materially change
the recommendation.

When a design needs a topology figure (read, edit, or create), first apply
[docs/network-topology-figures.md](docs/network-topology-figures.md), then the
implementation adapter [plugins/drawio-mcp.md](plugins/drawio-mcp.md).

## Boundaries

- `doc-fetcher` is pure retrieval (fetch and normalize to text). Design judgment
  stays in this skill's prose, not in the tool. It has no write path — this repo
  targets solution design, not Day-2 operations. Anything that would touch a live
  device belongs in a different tool/repo.

## Repo layout

`skills/` holds the library (`pocs/`, `scenarios/`, `techniques/`, `vendor-matrix/`).
`docs/` holds on-demand guidance, `mcp/doc-fetcher/` the retrieval tool, `tools/` the
draw.io validators, and `plugins/` the draw.io submodule and workflow.

## Agent behavior

### MCP server bootstrap

When this skill is loaded, read `.mcp.json` and verify every listed MCP server is
installed and reachable. If the agent has no MCP support, say so, skip live retrieval,
and work from the library. Otherwise, for each server that isn't available:

1. Attempt to install it (e.g., `npm install` in the server's directory, or
   `uv tool install` for Python-based servers), then re-verify its tools.
2. If installation fails, tell the user which server failed and what was attempted —
   do not silently skip the fetch step.

**Do not update dependencies.** Never run `npm update`, `pip install --upgrade`, or any
command that modifies `package-lock.json`, `pnpm-lock.yaml`, `Pipfile`, `Cargo.lock`, or
equivalent files. Only install servers missing from `.mcp.json`.

### Minimizing manual intervention

- **No pagers, no prompts.** Every git command must bypass interactive pagers and
  confirmations: use `git --no-pager` (or set `GIT_PAGER=cat`), and pipe to `cat` or a
  file when a tool lacks that option. Never issue a command that pauses for user input.
- **No heredocs, herestrings, or interactive shell constructs.** Shell commands run
  programmatically — `<<EOF`, `<<<`, and anything that prompts for continuation
  (`dquote>`, `heredoc>`, `quote>`) will freeze the terminal. Use your file-writing tool
  and reference the file path, or pipe short content via `printf` or `echo`.
- **Write back immediately.** After every external fetch (RFC, draft, vendor doc, web
  search result), write the new fact into the matching skill file before proposing the
  design. **Keep changes uncommitted** — the user reviews and commits.
- **List changes on startup.** At the beginning of each session, run `git diff --stat`
  to show uncommitted changes from prior sessions. Open the full diff only if needed.
- **Don't ask what you can infer.** Extract implied constraints (scale, vendor,
  topology) from the request first. Only prompt when a missing parameter materially
  changes the recommendation, as a single consolidated question.
- **One turn, one deliverable.** Answer a design question completely (rationale, vendor
  recommendation if applicable, citations) in a single response unless the user
  explicitly asks for iteration.

### Branch policy

- **Never commit to `main`.** The `main` branch is protected — only the repo
  maintainer merges into it (via PR or locally), never the agent.
- The agent works on a branch named by the `BRANCH_NAME` variable in `.env`.
- **If `BRANCH_NAME` is unset or empty**, generate a UUID, write the first 8 hex
  characters to `.env` as `BRANCH_NAME=agents/<short-uuid>`, and reload the env.
- Ensure the branch exists locally: `git checkout -b "$BRANCH_NAME"` if it doesn't.
- Before each session, sync from main: `git fetch origin && git merge origin/main`
  (or rebase).
