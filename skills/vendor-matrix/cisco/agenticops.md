# Cisco AgenticOps

- **Definition.** AgenticOps is Cisco's agent-first IT operating model: AI agents
  that sense, reason, and act across network, security, and observability
  operations, with human oversight. It is positioned against AIOps, which stops
  at alerts and recommendations [1]. Cisco's summary contrast: "AIOps helped you
  see problems. AgenticOps helps you solve them" [1].
- **Name.** "Ops" denotes operations, following the AIOps / NetOps / SecOps /
  DevOps convention: the ongoing discipline of running the estate — monitoring,
  triage, incident response, change, remediation, lifecycle — rather than a
  feature. The qualifier moved from "AI" (analytics over operations) to
  "agentic" (agents performing operations), which is why Cisco frames it as an
  operating model rather than a product.
- **Scope.** The model spans campus/branch/industrial, data center, service
  provider, security, and observability, with its own solution hub rather than a
  single product or OS release [2]. Capabilities ship on different timelines per
  domain (see Release history). In scope it resembles [ACI](aci.md) or
  [NX-OS EVPN-VXLAN](nxos-vxlan.md) — an operating model selected as a whole —
  more than a switch feature that is enabled.
- **Proprietary model, open integration.** AgenticOps itself is Cisco's design
  and is not interoperable as a technique. Its interfaces are open: MCP for
  agent-to-tool and data access, A2A for agent-to-agent handoff [3]. The
  distinction matters in design reviews: the integration surface is standard,
  the reasoning and governance layer is not.
- **Boundary.** This file records what Cisco ships, how it is wired, and the
  constraints it imposes on a design. It is not an operations runbook.

## Reference architecture

### Layers

The architecture is described in three layers, from the agent outward [1]:

- **Agents** — role-scoped software entities (monitoring, diagnostic,
  remediation, learning) that plan, sequence tasks, call tools, and adapt. Cisco
  defines five attributes for reliable enterprise agents: identity and context,
  reasoning, scale, security (policy, permission, audit), and operational
  efficiency [1].
- **Agentic layer** — coordinates multiple agents: decomposes tasks, parallelises
  work, reconciles conflicting results, and maintains shared context [1].
- **Orchestration layer** — enforces ordering and policy guardrails ("gather
  telemetry before diagnostics", "validate before remediation"), and can use
  models to interpret operator intent and emit reasoning traces. MCP sits inside
  this layer as the standard mechanism for tool and data access [1].

### Components

Cisco Cloud Control is the platform: one login, one inventory, one topology,
with correlated events across products [8]. Three agentic experiences are built
on it — **AI Canvas** (shared operator/agent workspace), **AI Assistant**
(natural-language entry point), and **Cloud Control Studio** (third-party tool
connection and custom agent construction) [8].

AI Canvas draws context from the native Cisco estate, third-party tools connected
through native integrations or open MCP, and custom agents built in Cloud Control
Studio, and preserves that context across shifts and escalations [9].

The **Cisco Deep Network Model** is the domain-specific LLM behind the reasoning:
trained on more than 40M tokens with 3,000+ expert-annotated reasoning traces,
reinforced with reinforcement learning, chain-of-thought, and test-time scaling.
Cisco claims up to 20% more accurate reasoning than leading general-purpose
models on troubleshooting, configuration, and automation [10][11]; the disclosed
benchmark is narrow (see Open challenges). Delivery is Cisco-hosted, not
customer-deployable (see Deployment and hosting).

| Component | Role |
|---|---|
| Cisco Cloud Control | Cross-portfolio platform: identity, telemetry, policy, inventory, topology [8] |
| AI Canvas | Shared workspace where humans and agents investigate and resolve [8][9] |
| AI Assistant | Natural-language front end, embedded in AI Canvas and product UIs [9][11] |
| Cloud Control Studio | Custom agents and third-party tool connection [8] |
| Deep Network Model | Domain-tuned reasoning model [10] |
| Agentic Workflows | Deterministic, reusable automations the agents execute [5][6] |
| Agentic Actions | Governance surface: see, approve, audit, and bound agent activity [6] |
| Ambient agents | Always-on agents that investigate without a prompt [6] |
| Cisco Digital Twin | Pre-production simulation of changes and blast radius [6] |
| Experience Metrics | User-experience indicators such as Time to Connect, Capacity, Roaming [5][6] |
| ThousandEyes / Splunk / Intersight | Telemetry and verification inputs [1][6][9] |

## Operating model

### The Agentic Loop

Every autonomous action is structured through five stages, powered by Experience
Metrics, Deep Reasoning, Digital Twin, and Agentic Workflows [6]:

| Stage | What happens | Backing capability |
|---|---|---|
| **Sense** | Detects signals, clusters related events, filters noise, and prioritises. Worked example: when 20 access points reboot at once, the agent correlates reboot timestamps against upstream switch data through topology and treats it as one switch fault rather than 20 tickets | Experience Metrics, telemetry [6] |
| **Diagnose** | Reasons over telemetry, topology, and configuration; evaluates several hypotheses simultaneously before naming a root cause | Deep Reasoning [6] |
| **Remediate** | Prepares the next best action, presents the evidence, and routes the action through the controls that apply to that action type | Agentic Workflows, Agentic Actions [6] |
| **Validate** | Risk-tiered. Low-risk actions may be pre-approved; topology changes, security policy changes, and large-scale configuration pushes can be simulated against a Digital Twin for expected impact and blast radius | Cisco Digital Twin [6] |
| **Deploy** | Executes per operator policy, then verifies that the *experience* recovered — the loop closes on ThousandEyes synthetic testing and Experience Metrics, not on infrastructure reporting healthy | ThousandEyes, Experience Metrics [6] |

### Autonomy and governance

- **Agentic Actions is the control point**, not the agent. Operators see what the
  agent observed, what it inferred, the supporting evidence, the proposed action,
  whether approval is required, what was executed, and what outcome was
  verified. Every decision carries reasoning, every action an audit trail, and
  anything requiring oversight enters an approvals queue [6].
- Autonomy is set per action type, network domain, and change window, which makes
  rollout incremental rather than all-or-nothing [6].
- Cisco describes three trust properties: **trusted** (40 years of operational
  data), **grounded** (real-time cross-domain data rather than assumptions), and
  **governed** (validated, policy-bound, auditable) [2].
- Reversibility and explainability are stated design commitments; actions are
  described as "explainable, transparent, and reversible" [1].

### AIOps and AgenticOps compared

Cisco's comparison, condensed [1]:

| Dimension | AgenticOps | Traditional AIOps |
|---|---|---|
| Automation | Agents reason, plan, and act across systems | Alerts and recommendations require human follow-up |
| Workflows | Adaptive, end-to-end | Static playbooks and dashboards |
| Reasoning | Decomposes problems and weighs alternatives | Surfaces anomalies, leaves reasoning to humans |
| Identity | Agents have defined roles and responsibilities | No persistent identity |
| Decisioning | Reasoning traces, auditable | Runbooks define fixed responses |
| Determinism | Non-deterministic, context-aware | Deterministic, same output every time |

The determinism row is the one that matters in a design review: the reasoning
layer is deliberately non-deterministic, which is why validation and approval
layers exist.

## Capabilities by domain

Cisco delivers AgenticOps as domain-specific capability bundles rather than a
single feature list. Availability differs per item and is the most perishable
data in this file.

### Campus, branch, and industrial [5]

| Capability | What it does | Availability |
|---|---|---|
| Autonomous troubleshooting | End-to-end agentic investigation across campus/branch/industrial; triages connectivity and experience issues, evaluates multiple hypotheses, executes deterministic remediations described as "CCIE-grade" | Rolling out from Feb 2026 |
| Continuous optimization | Context-aware recommendations, then autonomous tuning of RF, QoS, path, and control planes based on live end-to-end conditions | Rolling out from Feb 2026 |
| Trusted validation | Risk-aware assessment of changes against live topology, configuration, and telemetry, including impact and blast radius; also handles compliance validation | Rolling out from Feb 2026 |
| Experience Metrics | Converts thousands of network signals into user-experience indicators — Time to Connect, Capacity, Roaming | Rolling out from Feb 2026 |
| Agentic Workflow Creation | Builds production-ready, deterministic automations inside AI Assistant from environment conditions | Rolling out from Feb 2026 |

### Wireless [16]

| Capability | What it does | Availability |
|---|---|---|
| AI Packet Analyzer | Converts wireless packet captures, via Proactive PCAP, into contextualised root cause and remediation steps rather than raw capture analysis | Public beta |
| Experience Metrics (wireless) | Plain-English root cause over a unified performance/experience view; time to connect, capacity, coverage, roaming; minute-level granularity; client-side data from Apple, Samsung, Intel, and Zebra without an endpoint agent | Alpha |
| AI Config Recommendation | Predictive configuration guidance from models trained on millions of deployments, combining configuration parameters with client compatibility data | Announced Feb 2026 |
| AP Zero Touch Deployment | Detects a new AP on boot, inherits the configuration and identity of the replaced unit, and assumes its physical location ("spatial intelligence"); deployments shift from weeks to days | Available Feb 2026 |
| Campus Gateway | Cloud-native platform for L3 roaming at scale: CW9800L-MCG added to the existing CW9800H1-MCG | Announced Feb 2026 |

### Data center [5]

Early detection and intelligent event correlation with prescriptive
recommendations, covering traditional and AI workloads, and enhancing Nexus One
observability. Stated availability is controlled availability from June 2026 —
the least mature of the domain bundles.

### Service provider: Crosswork AI [5][17][18]

A multi-agentic framework inside Crosswork Network Automation, in beta [5], with
a first wave of specialised agents:

| Agent capability | What it does |
|---|---|
| Deep network troubleshooting | Reasons through complex issues, evaluates hypotheses, and pinpoints root cause to reduce MTTR [17] |
| Risk factor detection / Toxic Factor Identification | Finds hidden combinations of variables that trigger degradation or multiple failure types before services are affected [17][18] |
| Configuration drift remediation | Detects drift continuously, identifies variance against AI-trained device configurations, and recommends remediation [17][18] |

Framework capabilities include consensus-based decision making and built-in
resiliency aimed at self-healing [18]; data federation across Cisco, customer,
and third-party tools [18]; an agent development kit with agent evaluation and a
knowledge graph [17]; and multi-vendor operation over NETCONF, RESTCONF, TAPI,
OpenConfig, native YANG, and streaming telemetry from gRPC, BGP-LS, and gNMI,
with an open SDK for legacy or proprietary devices [17].

### Security operations: Security Cloud Control [5]

| Capability | What it does | Availability |
|---|---|---|
| Proactive zero-trust recommendations | Analyses firewall traffic, including applications accessed and mode of access, and proposes stronger zero-trust controls executable in one click | GA targeted May 2026 |
| Elephant-flow troubleshooting | Detects performance-impacting elephant flows, performs full-context analysis, and proposes remediation | GA targeted May 2026 |
| Continuous compliance | Continuously evaluates firewall configuration for PCI-DSS deviations and recommends remediation | GA targeted May 2026 |

### Observability: Splunk [5]

AI Agent Monitoring in Splunk Observability Cloud tracks performance, cost,
quality, and behaviour of LLM and agentic applications, visualises agent
workflows, and is slated to integrate with Cisco AI Defense for bias,
hallucination, data-leakage, and prompt-injection risk. Generally available
February 25, 2026.

### Cross-domain surfaces

| Surface | Capability | Notes |
|---|---|---|
| Cisco Cloud Control | One login, one inventory, one topology; correlated events; cross-domain dependency tracing | Platform for all three experiences [8] |
| AI Canvas | Natural-language investigation, agent execution, live charts and topology, shared sessions, context persistence | Three context sources: Cisco estate, third-party via MCP, custom agents [9] |
| AI Assistant | Query and drill-down; configuration guidance, compliance checks, one-click automation; product skills in Meraki and ThousandEyes | Entry point to the agentic system [4][11] |
| Agentic Actions | Approvals queue, audit trail, per-decision reasoning; autonomy scoped by action type, domain, and change window | Governance surface [6] |
| Cisco Digital Twin | Pre-production simulation of proposed changes, impact, and blast radius | Used for higher-risk validation [6] |

## Integration and interoperability

The integration layer determines blast radius and is the primary security scope
of a design.

### MCP attachment model

MCP is vertically oriented: agent to tools and data. It is an open standard, not
a Cisco one, and Cisco's servers implement it against management-platform APIs
[12].

MCP servers attach to network infrastructure, and the attachment point follows
the management model: device by device where the estate is not controller-managed,
or at the platform API where it is (Catalyst Center, Meraki Dashboard, Nexus
Dashboard, Nexus Hyperfabric). This choice sets blast radius — a call against a
platform can affect a fabric; a call against a device affects one device.

### Endpoint inventory and write semantics

| Endpoint | Attaches at | Authorization | Writes | Availability |
|---|---|---|---|---|
| Meraki MCP | Meraki Dashboard API | Enforced by the server: read-only tool surface (`semantic_search`, `execute_api`) | None | Beta; hosted `mcp.meraki.com` or self-hosted OSS; Meraki.com only on hosted, 10 req/s per org [12] |
| Catalyst Center MCP | Catalyst Center API | Delegated to the configured account; the server adds no authorization layer | May include configuration changes | OSS, local, versioned per Catalyst Center release [15] |
| Nexus Dashboard MCP | ND API Gateway | RBAC, tenancy isolation, and authentication enforced at the gateway; tools are GET-only | None | ND 4.3.1+, LAN deployments only [23] |
| Community IOS XE MCP | Device over SSH | The SSH login | Whatever that login permits | Community project, not an official Cisco product [14] |

Cisco documents these endpoints for use by AI Canvas agents; on Nexus One,
agents call the MCP server API on Nexus Dashboard and Nexus Hyperfabric
controllers for diagnostics, triage, and issue resolution [24].

Two consequences follow. First, the official platform endpoints are read-only
wrappers with platform-enforced authorization, while OSS and device-level
endpoints delegate to the account; which model applies has to be established per
endpoint before autonomy is granted (see Security and trust). Second, the number
of MCP servers and their credential scope belong in the design document
alongside firewall rules, because they define what an agent can reach.

### A2A and agent-to-agent interoperability

A2A is horizontally oriented: agent to agent, across vendor boundaries. It runs
on HTTP, Server-Sent Events, and JSON-RPC 2.0; agents publish an Agent Card at
`/.well-known/agent-card.json`; A2A v1.0 added signed cards; authentication uses
OAuth 2.0, API keys, or mTLS rather than a separate trust system [3]. Cisco's
position as of August 2026 is explicit that A2A-mediated handoffs between
production security agents are not yet shipping [3].

## Security and trust

The security model rests on four properties: bounded agent identity, endpoint-level
authorization, an auditable action record, and a defined data-processing boundary.

### Agent identity

Cisco bounds agent actions by policy, permissions, and audit trails [1]. Its A2A
guidance frames agent identity as a privileged-access management problem: extend
existing IAM governance to cover agent service accounts rather than creating a
new category [3]. Design consequences are per-agent credentials distinct from
human accounts, scoped to least privilege, registered in the same AAA/RBAC and
accounting path as people, and revocable. Effective privilege is the union of
every credential an agent can reach; that union, not the model, is the
authorization boundary.

### Authorization

The endpoint table in Integration and interoperability records where enforcement
sits for each MCP endpoint. Two patterns exist: server-side restriction (Meraki's
read-only tool surface; Nexus Dashboard's GET-only tools behind gateway RBAC and
tenancy) and delegation to the backing account (Catalyst Center OSS, which adds
no authorization layer of its own) [12][15][23]. Placement of the server is not
an authorization control; the failure mode is when neither the server nor the
account is scoped.

### Audit and blast radius

Agentic Actions records what the agent observed, inferred, and proposed, whether
approval was required, what executed, and what outcome was verified [6]. Blast
radius follows the attachment point: a platform API endpoint can act across a
fabric, a device-level endpoint only on that device [14][23]. An inventory of MCP
servers and their credential scope therefore belongs in the design document
alongside firewall rules.

### Data processing and residency

Cisco documents AI Canvas as a cloud-hosted platform that requires cloud
connectivity for AI processing, collaboration, and data aggregation, with fully
on-premises or air-gapped deployments "not currently supported or planned" [19].
Cloud Control is generally available in the United States only, with other
regions to follow [20]. An on-premises Catalyst Center does not change the data
path: customer content and systems information are processed and stored primarily
in the United States regardless of customer location, and customer data is not
used to train the model [21]. Local OSS MCP servers can run inside an air-gapped
network and provide tool access, but the reasoning model does not travel with
them [13][15].

## Deployment and hosting

**Summary.** The Deep Network Model is not customer-deployable today. It is
consumed as a Cisco-hosted service through AI Canvas and AI Assistant; no
on-premises or air-gapped distribution of the model is documented.

### Hosting boundary by component

| Component | What it is in Cisco's stack | On-premises today? |
|---|---|---|
| Model (weights and inference) | Cisco Deep Network Model, served by Cisco | **No** — no customer-hosted weights or inference [22] |
| Agent runtime / orchestration | Cloud Control; AI Canvas is the workspace, AI Assistant the entry point | **No** — cloud-hosted, US-only GA [19][20] |
| Tool interface | MCP servers: Meraki, Catalyst Center, Nexus Dashboard, community IOS XE | **Yes** — the only component that can be local or air-gapped [13][15] |
| Data sources | Controllers and telemetry (Catalyst Center, Meraki, Splunk, ThousandEyes) | Yes — typically already are |

### Roadmap status

Press reporting (The Register, 28 July 2026) indicates Cisco plans to make its
networking models available for on-premises use, including on UCS platforms. The
report is not confirmed by a Cisco document and should be treated as roadmap
rather than capability. Separately, third-party commentary describing the model
family in the 8–30B-parameter range and suggesting edge operation does not
describe the platform: a locally runnable model would still require Cloud
Control, AI Canvas, agent orchestration, and tooling. Model hosting and platform
hosting are separate questions.

### Documentation availability

Product documentation is public; a scenario-based deployment guide is not. The
Cisco Cloud Control documentation collection is organized Learn, Get Started,
Use, Applications, Reference [25]. *Get Started* carries the deployment
prerequisites: per-product onboarding (ThousandEyes, Meraki, Catalyst Center,
Intersight, Nexus Dashboard, Nexus Hyperfabric, Splunk Cloud, Catalyst SD-WAN
Manager), supported versions, identity matching between Cloud Control and the
controller, and firewall/FQDN requirements [20]. MCP deployment is documented per
component [12][15][23]. No standalone architecture-level "deployment scenarios"
document — site topologies, sizing, HA, multi-region patterns — was located;
scenario-level guidance should be requested from Cisco rather than assumed.

### Authoritative sources

Cisco Trust Portal offer disclosures (Cisco AI Assistant, Catalyst Center) are
the source of record for processing location and data handling, and Cisco states
they can change; they should be re-checked before committing to a data-residency
design [21].

## Commercial model

**Summary.** At the platform layer AgenticOps is entitlement-based, not a
separately priced SKU. Cisco states that Cloud Control and AI Canvas are included
with eligible Cisco product subscriptions at both Essential and Advantage tiers,
with "no new license and no new cost for eligible customers" [26]; the AI Canvas
product page repeats that it is "included with your eligible Cisco license at no
additional cost" [9]. No public list price exists because there is no standalone
line item.

| Layer | Price model | Status |
|---|---|---|
| Cloud Control and AI Canvas | Included with eligible Cisco subscriptions (Essential, Advantage) — no separate SKU or cost | Stated by Cisco [26][9] |
| Deep Network Model and inference | Not separately priced in public material; consumption bundled into the platform | No public price list [26] |
| MCP servers | No separate charge documented. Meraki MCP (beta) is governed by the MCP Server Terms and API terms [12]; the Nexus Dashboard MCP server is a platform feature from ND 4.3.1 [23] | Not priced separately |
| Security Cloud Control (firewall agentic features) | **Separately licensed**: base tenant subscription (`FWM-BASE`) plus per-device SKUs; the subscription SKU carries no price — pricing is determined by the device SKUs added to it | Ordering guide [27] |

Three properties of the model are worth separating:

- **Tiers gate capability, not seats.** AI Assistant is available at all license
  tiers, but its functions follow the tier of the underlying features it invokes
  [21].
- **The Cloud Control "Licensing" page is not a price list.** It is a
  license-visibility feature that aggregates entitlement, consumption, posture,
  and expiration across Meraki, Duo, Intersight, ThousandEyes, Splunk Cloud,
  Catalyst Center, Nexus Dashboard, Hyperfabric, and Security Cloud Control, and
  exposes purchase records including SKU, quantity, expiration, partner, and
  buying program [28]. It is frequently mistaken for Cloud Control's own
  licensing model.
- **Token metering is unconfirmed.** Third-party reporting describes a three-tier
  model (Essentials, Advantage, Premium) with pools of AI tokens, and separately a
  token allowance with overage charged later. Cisco's own material states two
  tiers at no additional cost, and neither third-party claim is confirmed by a
  Cisco document [29][30].

To obtain actual pricing, a Cisco Global Price List or Commerce quote must be
requested through a partner, together with a written definition of which products
and tiers qualify as eligible. That eligibility list, not a Cloud Control SKU,
determines whether a customer pays.

## Adoption and positioning

Adoption data is included as market context; it is not evidence about capability.

A Cisco-announced Omdia study of 1,000 IT and network-operations leaders at
organizations with 500 or more employees (North America, Western Europe,
Asia-Pacific), published 23 September 2026, reports [7]:

- roughly 4,100 monitoring alerts and events per organization per day, more than
  half network-related; clearing that backlog manually would require about 100 IT
  specialists, and nearly half of network alerts are closed without investigation
  [7];
- 95% say existing non-agentic AIOps tools fall short in at least one significant
  area [7];
- 75% have deployed AI for NetOps, 51% run agentic AI that acts in production,
  82% are comfortable letting AI make at least some production network changes
  without prior approval, and 84% expect an AI-led operating model within twelve
  months [7];
- 86% want a single integrated platform rather than another point tool, 69%
  require detailed explainability, and 36% call full observability — tracing,
  summarised rationale, post-action audits — the minimum bar [7].

The figures are directional rather than audited: the study was commissioned in
support of a vendor announcement, the data is self-reported by decision-makers,
and the "100 specialists" figure is a derived estimate. Cisco separately claims
that IT teams face "over 170,000 network alerts per hour" industry-wide, a
marketing figure with no published derivation [11].

## Implications for design

Nine findings follow from the architecture and from what Cisco documents.

**1. The management plane becomes a tier-0 production dependency.** Official MCP
servers front platform APIs — Meraki Dashboard, Catalyst Center, Nexus Dashboard
— so the agent's reach is the platform's reach [12][13][23]. "We can always log
into the controller" was previously a break-glass convenience; it is now also the
path an agent requires to remediate. Out-of-band management, local CLI access,
and controller-independent recovery remain necessary, and a fault inside the
management platform removes agentic remediation by construction.

**2. Telemetry and topology are the input contract.** Reasoning is grounded in
telemetry, topology, configuration context, and Experience Metrics [6]. An estate
that depends on SNMP polling, lacks an authoritative topology model, or runs
stale software presents a thin and partly wrong picture, and a confident wrong
answer is worse than an alert. Model-driven telemetry and current software are
readiness conditions rather than follow-on work; see
[management-plane.md](../../techniques/management-plane.md).

**3. Agent identity is a new identity class.** Cisco bounds actions by policy,
permissions, and audit trails [1], and its A2A guidance treats agent identity as
a privileged-access management problem [3]. Per-agent credentials, least
privilege, registration in the same AAA/RBAC path as people, and revocability are
the design consequences. Effective privilege is the union of every credential an
agent can reach.

**4. Blast radius is set by the endpoint and its credential.** A controller-API
MCP server changes whatever its account can change; the Catalyst Center OSS
server enforces no read-only boundary [15]. A device-level server can do anything
the SSH login permits [14]. The MCP server inventory and credential scope belong
in the design document alongside firewall rules.

**5. Non-determinism must sit behind deterministic controls.** The reasoning layer
is deliberately non-deterministic while runbooks are deterministic [1]. Digital
Twin validation is risk-tiered and covers only changes that can be modelled [6].
Underlay changes, routing policy, and large configuration pushes should retain
template or GitOps idempotency and human approval, so a probabilistic planner is
never the only guardrail. Approval gating by action type and change window is the
documented mechanism [6].

**6. Hosting and sovereignty are per-component decisions.** Cisco's umbrella
statement spans cloud, on-premises, and air-gapped industrial environments [5],
but the documented choices sit at the component level: AI Canvas is cloud-hosted
with no on-premises or air-gapped option [19], while MCP servers can be local
[12][13]. Regulated designs should verify hosting per component rather than
relying on the umbrella statement.

**7. Value scales with Cisco share of the estate.** Enterprise AgenticOps is
grounded in Cisco telemetry — Meraki, ThousandEyes, Splunk, Intersight
[1][2][6] — and the Deep Network Model is trained on Cisco operational data
[10]. Cross-vendor handling is documented for service provider networks through
Crosswork AI, which is in beta [5][17]. Open MCP allows third-party tools to be
attached through Cloud Control Studio and AI Canvas [8][9], but a mostly
non-Cisco estate should expect partial value. The business case should be sized
against the Cisco footprint, not total device count.

**8. Licensing is entitlement-based, with one paid exception.** Cloud Control and
AI Canvas are included with eligible subscriptions at Essential and Advantage
tiers [26]; security-side agentic features fall under Security Cloud Control's
base-subscription-plus-per-device model [27]. Token allowances and overage are
unconfirmed (see Commercial model). Pricing should never be quoted from this file
without a partner quote.

**9. The current fit is bounded.** Use cases that require deterministic,
reproducible action with no reasoning step, closed-loop OT or safety control
without independent validation, and estates with no telemetry baseline are poor
fits. Production SLAs should not depend on capabilities Cisco still labels beta,
controlled availability, or rolling out [5][12].

### Guidance by adoption stage

- **Suitable first scope:** campus and branch assurance — read-only
  investigation, alert correlation, and recommendation inside AI Canvas, with
  approval-gated actions for low-risk changes. Documented maturity is highest
  there (rolling out since February 2026) and the cost of a wrong answer is
  lowest [5].
- **Hold write access** on data-center underlay, routing policy, and security
  policy until telemetry, agent identity, and Digital Twin validation are in
  place and exercised.
- **Treat the platform as an operations-layer multiplier on a Cisco estate**, not
  as a multi-vendor management plane. The underlying fabric decision is covered
  in [aci.md](aci.md), [nxos-vxlan.md](nxos-vxlan.md), and
  [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md).

## Open challenges

- **Announcement dates are targets, not general availability.** The sources carry
  forward-looking disclaimers, and several capabilities were controlled
  availability, beta, or rolling out at announcement [4][5][6][12].
- **The accuracy claim rests on one narrow benchmark.** Cisco describes a
  CCIE-style multiple-choice benchmark on which the model beats general-purpose
  models by up to 20 percent [22]. That measures exam-style question answering,
  not multi-turn troubleshooting against a live network, and no independent
  evaluation is published.
- **Adoption data is vendor-commissioned and self-reported** [7]; it describes
  intent and comfort rather than measured outcomes.
- **A2A is not yet production-real** for agent handoffs [3]; designs that assume
  cross-vendor agent interoperability are building on a roadmap.
- **MCP endpoints have different write semantics.** Meraki's is read-only [12];
  Catalyst Center's is not [15]. Providing an MCP server is not a safety control
  on the latter path.
- **No cross-vendor benchmark is cited here.** Whether Juniper, Arista, or Huawei
  equivalents lead or lag is not established, and should not be asserted without
  a dated source.
- **Cloud-only and US-first.** There is no on-premises or air-gapped AI Canvas,
  and Cloud Control is generally available in the United States only [19][20].
- **Pricing is entitlement-based and partly opaque.** There is no public list
  price, and the token allowance and overage model is unconfirmed [26][30].

## Release history

Availability is Cisco's stated status at announcement, not independently verified
general availability. Every source in this set carries the "products and features
mentioned are still in development… timeline subject to change" disclaimer
[4][5][6].

| Date | Event | Availability as stated |
|---|---|---|
| 2025-06-10 | AgenticOps introduced at Cisco Live San Diego as part of the new secure network architecture; Deep Network Model and AI Canvas announced | Unified management platform available; AI Assistant public beta; AI Canvas "tested with select customers this fall" [4] |
| 2026-02-10 | Expanded across networking, security, and observability (Cisco Live EMEA, Amsterdam) | Campus/branch/industrial capabilities "start rolling out February 2026"; data center "controlled availability in June 2026"; service provider Crosswork AI in beta; Security Cloud Control firewall GA "targeted May 2026"; Splunk AI Agent Monitoring GA February 25 [5] |
| 2026-06 | Cisco Live Las Vegas: Ambient agents, Agentic Actions, and the five-stage Agentic Loop | Announced, no general availability date stated [6] |
| 2026-09-23 | Adoption research published: *The Impact of Agentic AI on Network Operations* (Omdia) | Research, not product [7] |

## Cross-references

- [management-plane.md](../../techniques/management-plane.md) — AAA, telemetry,
  NTP, syslog, and out-of-band management are the substrate. Agents inherit every
  weakness in it; clock skew alone breaks correlation and audit ordering.
- [npm.md](../../techniques/npm.md), [apm.md](../../techniques/apm.md),
  [npm-apm.md](../../techniques/npm-apm.md) — Experience Metrics and ThousandEyes
  are NPM-style evidence, and the identity, clock, and topology correlation
  problem applies one layer up.
- [wireless.md](../../techniques/wireless.md),
  [core-agg-access.md](../../techniques/core-agg-access.md) — campus and branch
  are the most mature AgenticOps scope (RF tuning, Time to Connect, roaming).
- [aci.md](aci.md), [nxos-vxlan.md](nxos-vxlan.md),
  [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md) — data-center AgenticOps is stated
  to enhance Nexus One observability [5]; the fabric decisions it sits on are
  documented there.
- [cisco.md](cisco.md) — portfolio hub.

## References

All sources are **time-sensitive vendor or third-party material** (solution
pages, newsroom posts, product documentation, one community blog, and two press
reports). Each entry gives the section to re-check and the date it was last
confirmed. Reference numbers are stable identifiers retained across restructures,
so they are not in order of first appearance. Cisco pages carry "still in
development… timeline subject to change"
disclaimers; availability and packaging should be re-verified before being
quoted.

[1] "What is agentic operations (AgenticOps)?" Cisco. [Online]. Available:
https://www.cisco.com/site/us/en/learn/topics/artificial-intelligence/what-is-agentic-operations-agenticops.html
Verification: check sections "Agentic and orchestration layers," "The Cisco approach,"
"AgenticOps vs. AIOps," and "Risk and responsibility." Source for the three-layer
model, the five agent attributes, the AIOps comparison table, and the
explainable/transparent/reversible commitment.

[2] "AgenticOps for Enterprise Networking," Cisco solution page. [Online].
Available:
https://www.cisco.com/site/us/en/solutions/artificial-intelligence/agentic-ops/net-ops/index.html
Verification: check the "Trusted AI / Grounded AI / Governed AI" blocks and the
`agentic-ops/` sub-pages (`net-ops`, `cisco-cloud-control`, `ai-canvas`) that
establish this as a solution hub. The page is client-rendered, so framing beyond
those blocks should be verified in a browser.

[3] "A2A and MCP: The Open Protocol Stack Powering the Multi-Agent SOC," Cisco
Blogs (Security), August 2026. [Online]. Available:
https://blogs.cisco.com/security/a2a-mcp-open-protocol-stack-multi-agent-soc
Verification: check "Two protocols, not one" (MCP vertical / A2A horizontal), "How A2A
works" (HTTP + SSE + JSON-RPC 2.0, `/.well-known/agent-card.json`, signed cards
in A2A v1.0, OAuth 2.0/API keys/mTLS), and the statement that A2A handoffs
between production security agents are not shipping yet.

[4] "Cisco Unveils Secure Network Architecture to Accelerate Workplace AI
Transformation," Cisco Newsroom, June 10, 2025. [Online]. Available:
https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2025/m06/cisco-unveils-secure-network-architecture-to-accelerate-workplace-ai-transformation.html
Verification: check "Simplifying Operations with Unified Management and AgenticOps" and
"Availability" (AI Assistant public beta, AI Canvas select customers "this
fall"). This is the launch record for AgenticOps.

[5] "Cisco Expands AgenticOps Innovations Across Portfolio," Cisco Newsroom,
Feb. 10, 2026. [Online]. Available:
https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2026/m02/cisco-expands-agenticops-innovations-across-portfolio.html
Verification: check the per-domain bullets (campus/branch/industrial, data center, service
provider), the stated availability dates (Feb 2026 rollout, DC controlled
availability June 2026, Crosswork AI beta, Security Cloud Control GA targeted
May 2026, Splunk AI Agent Monitoring GA Feb 25), and the closing development
disclaimer. Source for the campus capability list (autonomous troubleshooting,
continuous optimization, trusted validation, Experience Metrics with Time to
Connect / Capacity / Roaming, workflow creation) and for DC/Nexus One
observability.

[6] "From signal to action: The next step in Cisco AgenticOps," Cisco Blogs
(Networking), June 2026 (Cisco Live Las Vegas). [Online]. Available:
https://blogs.cisco.com/networking/from-signal-to-action-the-next-step-in-cisco-agenticops
Verification: check "Agents built for network operations," "Agentic Actions," "The Agentic
Loop," and the per-stage sections "Sense," "Diagnose," "Remediate," "Validate,"
"Deploy." Source for Ambient agents, the five-stage loop, risk-tiered validation,
Digital Twin blast-radius testing, and ThousandEyes/Experience Metrics closure.

[7] "Cisco AI Research: AgenticOps Scaling Quickly in the Enterprise," Cisco
Newsroom, Sept. 23, 2026. [Online]. Available:
https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2026/m09/cisco-ai-research-agenticops-scaling-quickly-in-the-enterprise.html
Study details: Omdia, 1,000 leaders at 500+ employee organizations in NA/WE/APAC.
Verify the "Key Takeaways" and the percentage bullets (75% deployed AI for
NetOps; 51% agentic in production; 80%/24% autonomy comfort; 82% production
changes without prior approval; 84% within 12 months; 86% single platform; 69%
explainability; 36% full-observability minimum). Study PDF:
https://www.cisco.com/c/dam/en/us/solutions/artificial-intelligence/the-impact-of-agentic-ai-on-network-operations.pdf

[8] "Cisco Cloud Control," Cisco solution page. [Online]. Available:
https://www.cisco.com/site/us/en/solutions/artificial-intelligence/agentic-ops/cisco-cloud-control/index.html
Verification: check "One login. One inventory. One topology," "Cross-domain intelligence,"
and "Powering AgenticOps" (the three experiences: AI Canvas, AI Assistant,
Cloud Control Studio).

[9] "Cisco AI Canvas," Cisco solution page. [Online]. Available:
https://www.cisco.com/site/us/en/solutions/artificial-intelligence/agentic-ops/ai-canvas/index.html
Verification: check "One place to ask, investigate, and act" and "Three sources of context.
One reasoning surface" (Cisco products / third-party tools via native
integrations and open MCP connectivity / custom agents from Cloud Control
Studio).

[10] "Meet the Cisco Deep Network Model: Trained by the Experts, Purpose-Built
for the Network," Cisco Blogs (Networking). [Online]. Available:
https://blogs.cisco.com/networking/meet-the-cisco-deep-network-model-trained-by-the-experts-purpose-built-for-the-network
Verification: check "Not Just Another LLM": >40M tokens, 3,000+ expert-annotated reasoning
traces, reinforcement learning, and the "up to 20% more accurate" claim. No
benchmark methodology is published; treat the figure as vendor-reported.

[11] "AgenticOps: How Cisco is Rewiring Network Operations for the AI Age,"
Cisco Blogs (Innovation), 2025. [Online]. Available:
https://blogs.cisco.com/innovation/network-operations-for-the-ai-age
Verification: check "The Complexity Cliff" (the 170,000 alerts/hour figure) and "Cisco AI
Canvas: The Workspace for AgenticOps." Marketing claims; no derivation
published.

[12] "MCP Server — Meraki Dashboard API v1," Cisco Meraki Developer Hub.
[Online]. Available: https://developer.cisco.com/meraki/api-v1/mcp-server/
Verification: check the beta notice, the read-only warning, the deployment comparison
table (Cisco-hosted `https://mcp.meraki.com/mcp` vs local open source; Meraki.com
only on hosted, Federal/GovCloud/localized unsupported), the two-tool surface
(`semantic_search`, `execute_api`), and the rate-limit section (10 requests/s per
organization).

[13] "Build agentic networking experiences with Meraki and Catalyst Center MCP
servers," Cisco Blogs (Developer), Aug. 10, 2026. [Online]. Available:
https://blogs.cisco.com/developer/build-agentic-networking-experiences-with-meraki-and-catalyst-center-mcp-servers
Verification: check "Choosing the right experience: AI Assistant or MCP?" and "Open-source
Catalyst Center MCP: local deployment for controlled environments" (air-gapped
and sovereignty use cases; repositories
`github.com/CiscoDevNet/cisco-meraki-mcp-official` and
`github.com/cisco-en-programmability/catc-mcp-oss`).

[14] "Network MCP Docker Suite: Seven MCP Servers for AI-Driven Network
Operations," Cisco Switzerland Technology Blog. [Online]. Available:
https://gblogs.cisco.com/ch-tech/network-mcp-docker-suite/
Verification: check "The Seven Network MCP Servers" (Meraki, NetBox, Catalyst Center,
IOS XE via SSH, ThousandEyes, ISE, Splunk) and the closing disclaimer that this
is a personal open-source project, **not an official Cisco product**.

[15] "Catalyst Center MCP (OSS)," Cisco DevNet / cisco-en-programmability,
GitHub repository README. [Online]. Available:
https://github.com/cisco-en-programmability/catc-mcp-oss
Verification: check "Before You Start" and "Use a Dedicated, Least-Privilege Account" (the
server adds no authorization layer, does not enforce read-only access, and its
bundled catalog "may include operations that change configuration"), the tool
catalog domains (inventory, device health, wireless experience, software,
compliance), and the requirement to check out the release branch matching the
Catalyst Center version. Local endpoint `/v1/mcp`; binds to `127.0.0.1` in the
examples.

[16] "From Firefighting to Flow: How AgenticOps Transforms Wireless
Operations," Cisco Blogs (Networking), February 2026 (Cisco Live EMEA).
[Online]. Available:
https://blogs.cisco.com/networking/from-firefighting-to-flow-how-agenticops-transforms-wireless-operations
Verification: check "Faster troubleshooting: turning data into decisive action with AI
Packet Analyzer" (public beta, via Proactive PCAP), "Experience-led
troubleshooting with Experience Metrics" (alpha; time to connect, capacity,
coverage, roaming; Apple/Samsung/Intel/Zebra native integrations), "Continuous
optimization: AI Config Recommendation," "AP Zero Touch Deployment" ("available
today"), and "Cisco Campus Gateway" (CW9800L-MCG alongside CW9800H1-MCG).

[17] "The path to autonomous networking: Meet the agents helping win the AIOps
race," Cisco Blogs (Service Provider), 2026 (Cisco Live Las Vegas). [Online].
Available:
https://blogs.cisco.com/sp/netops-at-machine-speed-embracing-a-multi-agentic-framework
Verification: check the three debut agents (deep network troubleshooting, risk factor
detection, configuration drift remediation), the agent development kit (ADK),
agent evaluation, knowledge graph, data federation across Cisco/customer/
third-party sources, and the open interfaces list (NETCONF, RESTCONF, TAPI,
OpenConfig, YANG; gRPC, BGP-LS, gNMI) plus the EANTC 2026 interoperability
showcase reference.

[18] "Cisco Crosswork Network Automation — Multi-Agentic AI Framework
At-a-Glance," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/products/collateral/networking/software/crosswork-network-automation/crosswork-multi-agentic-ai-framework-aag.html
Verification: check "Toxic Factor Identification," "Configuration Drift Detection,"
consensus-based decision making, built-in resiliency/self-healing, data
federation, and the third-party SDK. Collateral page; version/revision may
change without notice.

[19] "Cisco AI Canvas," Cisco one-pager, document code WO-05112026. [Online].
Hosted by Cisco partner TEHNC:
https://www.tehnc.com/1page/CAC.pdf
Source note: Cisco collateral (document WO-05112026), reproduced on a Cisco
partner site rather than cisco.com; confirm against Cisco's published copy before
external quotation. States: "AI Canvas is designed as a cloud-hosted platform and
requires cloud connectivity for core services like AI processing, real-time
collaboration, and data aggregation… Fully on-premises or air-gapped deployments
are not currently supported or planned."

[20] "Cisco Cloud Control — Getting Started," Cisco documentation. [Online].
Available:
https://www.cisco.com/c/en/us/td/docs/ai/cisco-cloud-control/articles/cisco-cloud-control-getting-started.html
Verification: check the note "Cisco Cloud Control is Generally Available in the United
States only. Support for additional regions will be added in future milestones,"
and the Catalyst Center firewall requirements (TCP 443 to `ciscoconnectdna.com`,
`neoffers.cisco.com`, `dnaservices.cisco.com`, `dashboard.meraki.com`,
`api.meraki.com`). Region availability is expected to change — re-check.

[21] "Cisco Catalyst Center AI Assistant," Cisco documentation article.
[Online]. Available:
https://www.cisco.com/c/en/us/td/docs/cloud-systems-management/network-automation-and-management/catalyst-center/articles/cisco-catalyst-center-ai-assistant.html
Verification: check "Where is my data stored and processed when using the AI Assistant?"
(customer content and systems information "primarily processed and stored in the
United States, regardless of your physical location," covering both prompt data
and analyzed deployment data), "Is my data used to train the AI Assistant?" (no),
and the links to the Cisco AI Assistant and Catalyst Center offer disclosures on
the Cisco Trust Portal. The Trust Portal disclosures are the authoritative source
and may be updated.

[22] "Cisco Deep Network Model: Purpose built intelligence for networking,"
Cisco Blogs (AI), February 2026. [Online]. Available:
https://blogs.cisco.com/ai/cisco-deep-network-model-overview
Verification: check the "Analytics Context Engineering (ACE)" and "LAPSE" sections, the
benchmark statement ("CCIE-style multiple choice benchmark… outperforms
general-purpose models by up-to-20 percent"), and "Brought to life in Cisco
products" (delivery through AI Canvas and AI Assistant, no customer-hosted model
distribution described).

[23] "Working with Model Context Protocol (MCP) Server," Cisco Nexus Dashboard,
Release 4.3.1. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/nd/4x/articles-431/working-with-mcp-server.html
Verification: check the "New and changed information" table (MCP server integration from ND
4.3.1), the operational benefits (standardized integration; security boundary
preservation via the Nexus Dashboard API Gateway with RBAC, tenancy isolation,
and authentication policies; stateless architecture with no customer data
stored), "In Nexus Dashboard 4.3.1, MCP server supports only LAN deployments,"
"Read-only operations: The MCP server exposes tools exclusively through GET API
operations," and the supported-tools table. Release-scoped — re-check on later
ND releases.

[24] "Cisco Nexus One, next-generation data center networking architecture,"
Cisco Blogs (Data Center), July 2026. [Online]. Available:
https://blogs.cisco.com/datacenter/cisco-nexus-one-next-generation-data-center-networking-architecture
Verification: check the Cloud Control/AI Canvas section and the statement that AI agents in
AI Canvas use the MCP server API on Nexus One controllers (Nexus Dashboard and
Nexus Hyperfabric) for diagnostics, triage, and issue resolution.

[25] "Cisco Cloud Control Documentation," Cisco documentation collection.
[Online]. Available:
https://www.cisco.com/c/en/us/td/docs/ai/cisco-cloud-control/collections/cisco-cloud-control-documentation.html
Verification: check the collection's five-part organization (Learn, Get Started, Use,
Applications, Reference) and that it is publicly reachable without a support
contract. Doc structure changes between releases; re-check before citing a
specific article.

[26] "Cisco Cloud Control: A New AI Operating Layer for Partners," Cisco Blogs
(Partner), June 2026. [Online]. Available:
https://blogs.cisco.com/partner/cisco-cloud-control-a-new-operating-layer-for-cisco-partners
Verification: check "there is no new license and no new cost for eligible customers"; Cloud
Control "is included with subscription licenses for eligible Cisco products at
both Essential and Advantage tiers"; Controlled Availability June 2026 with a
curated cohort; U.S. availability first with other regions following as
data-sovereignty requirements are completed. This is commercial/partner messaging
and can change — re-check terms at renewal.

[27] "Security Cloud Control Firewall Management Ordering Guide," Cisco.
[Online]. Available:
https://www.cisco.com/c/en/us/products/collateral/security/security-cloud-control/security-cloud-control-firewall-management-og.html
Verification: check "two types of licensing: Base Subscription and per-device licensing.
Both are needed for managing Firewalls"; "There is one subscription SKU for
Firewall Management … (FWM-SEC-SUB). There is no price for the subscription SKU.
Pricing is determined when product SKUs are added and configured"; the optional
logging add-on; and Multicloud Defense's gateway-hour consumption model with
Advantage/Premier tiers. Ordering guides change per release — re-check SKUs.

[28] "Cisco Cloud Control — Licensing," Cisco documentation. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/ai/cisco-cloud-control/articles/cisco-cloud-control-licensing.html
Verification: check that this article describes license *visibility* (aggregating license
data from supported products), the supported-products list, the three supported
licensing models (subscription, on-premises, Meraki co-term), the license
qualifiers (Shared, Reserved, Substitution, Free, Pending, Product Dashboard),
and the Purchases/transactions fields (product number, quantity, expiration,
partner, buying program). It does **not** state Cloud Control's own price — do
not cite it as a price list.

[29] B. Pariseau, "Cisco Cloud Control unites AgenticOps for IT infrastructure,"
TechTarget, June 2, 2026. [Online]. Available:
https://www.techtarget.com/it-infrastructure/news/366643670/Cisco-Cloud-Control-unites-AgenticOps-for-IT-infrastructure
Status: third-party report. Recorded solely for the reported three-tier claim
(Essentials / Advantage / Premium, with token pools), which Cisco documentation
does not corroborate; treat as unconfirmed. The same article states Cloud Control
"replaces the previous Cisco Security Cloud Control," which conflicts with
Security Cloud Control's current ordering guide [27].

[30] "Cisco close to releasing more AI models, this time for deep networking
ops," The Register, July 28, 2026. [Online]. Available:
https://www.theregister.com/networks/2026/07/28/cisco-close-to-releasing-more-ai-models-this-time-for-deep-networking-ops/5279350
Status: not independently confirmed; the publisher restricts automated retrieval.
Recorded solely for the reported claim that subscriptions include a quantity of
tokens with additional tokens charged separately. Not used for any design
conclusion.
