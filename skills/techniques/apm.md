# Application Performance Monitoring (APM)

Application Performance Monitoring asks whether software services and the user
transactions that depend on them are healthy, available, and meeting experience
targets. It is distinct from Network Performance Monitoring, which focuses on
devices, links, paths, and network traffic. The distinction matters when
selecting telemetry, placing sensors, and deciding what a product result
actually proves.

IBM distinguishes application performance monitoring as continuous collection
of performance data from application performance management as the broader
practice of analyzing the data, troubleshooting issues, and optimizing the
application [1]. In everyday product conversations, APM is used for both; the
scope should therefore be stated explicitly.

## APM scope and typical functions

The five-dimensional taxonomy used here is Gartner's, not an IBM-created model.
Gartner's research described five distinct functional dimensions of APM [2],
and IBM's current explanation summarizes that framework [1]:

1. **End-user or digital-experience monitoring** — real-user monitoring (RUM)
   and synthetic journeys that observe a user or simulate one.
2. **Runtime application architecture discovery** — service, component,
   infrastructure, and dependency relationships as they operate.
3. **User-defined transaction profiling** — following a business transaction
   through the application stack.
4. **Deep-dive component monitoring** — code sections, external calls,
   application servers, database queries, and other components.
5. **Analytics and reporting** — dashboards, trends, alerting, anomaly
   detection, root-cause analysis, and performance optimization.

Typical APM functions include:

- response time, throughput, and error/exception tracking;
- distributed tracing and transaction profiling;
- service, dependency, database, query, and external-call monitoring;
- host, process, runtime, thread, CPU, memory, and garbage-collection metrics;
- code-level profiling and diagnostic context;
- logs in context and business KPIs; and
- alerting, anomaly detection, SLO/SLA reporting, and root-cause analysis.

OpenTelemetry gives the core signals a precise vocabulary: traces describe the
path of a request through an application, metrics are runtime measurements,
logs record events, baggage carries context between signals, and profiles
describe resource usage at code level [3]. OpenTelemetry is an instrumentation
and telemetry framework, not by itself a complete APM product.

## APM collection models

“Agentless” is too broad for solution selection. Record whether software must
be installed on the application host, whether the application must be
instrumented, and which remote collection infrastructure is required:

| Collection model | Application-host change | Typical evidence | Appropriate when | Main limitation |
|---|---|---|---|---|
| Host-agent APM | Vendor agent on a host, VM, container, or runtime | Runtime metrics, spans, exceptions, profiles, service maps, database detail | The host/application environment can be instrumented and code-level diagnosis is required | Requires deployment access, coverage, overhead/privacy controls, and lifecycle management |
| Application instrumentation without a host agent | SDK, library, runtime auto-instrumentation, or application-exported telemetry; a collector may be remote | Traces, metrics, logs, and selected business context | The team can modify the application or runtime but does not want a vendor host agent | Instrumentation still has coverage, version, context-propagation, and collector dependencies |
| Network-derived or wire-data APM | No application-host instrumentation; traffic is observed through TAP/SPAN, packet broker, or network probe | Service-path timing, protocol behavior, client/server relationships, and supported transaction evidence | Hosts cannot be modified, legacy software cannot expose telemetry, or instrumentation is prohibited | No reliable in-process state, exact code line, stack trace, or runtime profile; encryption and capture coverage reduce depth |
| Client-side monitoring | Browser tag, mobile SDK, or external synthetic probe | Page/action timing, user experience, frontend errors, and scripted journeys | The requirement is real-user or synthetic experience | Does not by itself explain backend or network cause |
| Hybrid correlation | Two or more of the above with shared identity and time | Separation of client, network, service, database, and code contributions | Both application responsibility and network/path responsibility must be proven | Requires compatible identity, clocks, topology, retention, and correlation rules |

The categories are not mutually exclusive. A product may support more than one
collection model, and the same product name may cover different modules or
deployment modes. Record the mode actually proposed in the design or bill of
materials.

## Cross-vendor / variants

Classify an APM product by the evidence it collects and the deployment boundary
it requires:

| Product posture | Reference role in this library | What to verify |
|---|---|---|
| Agent-based/instrumented APM | Dynatrace as the host-agent baseline | Supported runtimes, agent placement, OTel alternatives, code/profiling depth, RUM, and licensing/retention boundaries |
| Network-derived/wire-data APM | NETSCOUT nGeniusONE as the network-derived baseline | Packet/probe placement, protocol and transaction coverage, multi-point correlation, encryption handling, and sensor capacity |
| IBM application APM | IBM Instana as an IBM-specific APM example | Exact agent/auto-instrumentation requirements, supported runtimes, and how it is separated from QFlow flow collection |
| Network-derived APM candidate | Netis BPC/application-business observability | Commercial module/SKU, application-host requirement, protocol/database coverage, raw evidence, and multi-point correlation |

### Reference baseline: Dynatrace APM

Dynatrace is the reference baseline for host-agent and application-instrumented
APM. Its current Full-Stack Monitoring documentation explicitly describes APM
as including distributed tracing, code-level visibility, CPU profiling, memory
profiling, and deep process monitoring [4]. It also documents service request
metrics and trace data, as well as OneAgent and OpenTelemetry collection paths [4].

Use Dynatrace as a reference implementation for the evidence available when a
host/runtime agent or equivalent application instrumentation is permitted. It
is not a universal definition of APM and is not the network-derived baseline.
For browser and frontend scope, Dynatrace documents linking RUM data with
backend traces captured by OneAgent or OpenTelemetry, including investigation
of slow user actions, frontend errors caused by backend failures, and topology
through intermediaries [5].

Dynatrace's current product is a broader full-stack observability platform, so
the comparison should select the APM capabilities actually required rather than
credit every platform feature by default. See the vendor record in
[dynatrace.md](../vendor-matrix/dynatrace.md).

### Reference baseline: NETSCOUT nGeniusONE

NETSCOUT nGeniusONE is the reference baseline for network-derived APM or
network/application service assurance. NETSCOUT describes packet-derived Smart
Data from InfiniStreamNG and vSTREAM, application/session analysis, latency,
responsiveness, errors, dependency mapping, and packet-based troubleshooting [6].
Its official data sheet describes multi-segment, hop-by-hop transaction detail [7].

Use this as a **no application-host instrumentation** baseline, not as a claim
that no deployment infrastructure is required. The relevant traffic still has
to reach packet appliances, virtual probes, or other observation points, and
the supported protocol and capture coverage determine the analysis depth. See
the vendor record in [netscout.md](../vendor-matrix/netscout.md).

### IBM Instana and Netis placement

IBM Instana is documented as IBM's application performance monitoring product,
with full-stack APM, discovery, logs in context, distributed tracing, analytics,
and root-cause analysis [8]. It belongs in the agent/instrumented APM family for
this comparison, but is treated as an IBM-specific reference rather than the
neutral baseline because QFlow is also an IBM product. The QFlow boundary and
the exact product-specific collection behavior remain in [ibm.md](../vendor-matrix/ibm.md).

Netis's vendor record describes BPC/application-business observability as a
wire-data or network-derived APM capability. Do not convert its public feature
claims into a guaranteed function of every Netis edition; confirm the module,
deployment model, protocol coverage, transaction identity, and license in the
proposal and POC.

## Design considerations

### Select by deployment constraint and required evidence

Use these questions in a solution request or POC:

1. **Can software be installed on the host, VM, container, or runtime?** If yes,
   evaluate host-agent and application-instrumentation APM. If no, evaluate
   network-derived APM or external client monitoring.
2. **Can the application or runtime be modified?** If yes, an SDK or
   auto-instrumentation path may provide useful traces without a vendor host
   agent. Do not call this fully agentless.
3. **What evidence is required?** Separate code-level, runtime, service,
   protocol, path, database, browser, and business-transaction requirements.
4. **Where can traffic be observed?** For network-derived APM, document TAP,
   SPAN, ERSPAN, packet-broker, sensor, and cloud-visibility coverage before
   promising transaction or path analysis.
5. **Must the same transaction be correlated across multiple points or tools?**
   Define identity, timestamps, topology, direction, NAT/load-balancing
   changes, deduplication, and retention; see [npm-apm.md](npm-apm.md).
6. **What are the blind spots?** Test encryption, unsupported protocols,
   sampling, asymmetric routing, missing packets, overloaded collectors, and
   incomplete instrumentation.

### APM versus NPM boundary

APM response time is not automatically network latency. A browser event,
application span, network request/response delta, and active probe can all be
called “response time” while measuring different boundaries. Record the source,
formula, direction, sampling, aggregation interval, and confidence for every
metric.

Use NPM, packet analysis, or active OAM when the requirement is interface health,
reachability, path delay, data-plane packet loss, jitter, or hop localization.
Use APM when the requirement is application transaction behavior, service or
database responsibility, exceptions, code/runtime state, or user experience.
Use both when the design must distinguish network wait from server processing,
database time, and client-side delay.

### Minimum APM POC

- Trace one known transaction through the client, service, database, and
  external dependency where the selected model claims to support those layers.
- Compare observed timing with server logs, packet timing, or an independent
  active probe to identify what each metric includes.
- For network-derived APM, run the same transaction through at least two
  observation points and verify joining, duplicate handling, clock accuracy,
  and fault localization.
- For agent/instrumented APM, test runtime coverage, sampling, context
  propagation, code-level diagnostics, agent overhead, and behavior during
  upgrades or collector loss.
- Test encrypted traffic, non-standard ports, NAT, load balancing, tunnels,
  asynchronous messaging, and unsupported or partially instrumented services.
- Record throughput, retention, licensing, storage, sensor/agent limits, and
  the behavior when capacity is exceeded.

## Relationship to other techniques

- [npm.md](npm.md) — device, flow, packet, and active network evidence for
  network responsibility and path performance.
- [npm-apm.md](npm-apm.md) — cross-layer identity, clock, topology, and
  multi-point correlation.
- [management-plane.md](management-plane.md) — NTP, syslog, SPAN/TAP, and
  management telemetry affect collection and correlation confidence.
- [qos.md](qos.md) — queuing, congestion, DSCP, ECN, and buffer behavior can
  explain network delay or loss observed alongside an APM transaction.
- [overlay-architecture.md](overlay-architecture.md), [vxlan.md](vxlan.md),
  and [evpn.md](evpn.md) — tunnels, VTEPs, asymmetric paths, and tenant
  boundaries complicate network-derived evidence and transaction identity.
- [../vendor-matrix/ibm.md](../vendor-matrix/ibm.md) — QFlow and Instana are
  separate IBM capabilities with different evidence and deployment boundaries.
- [../vendor-matrix/netis.md](../vendor-matrix/netis.md) — Netis BPC and related
  modules provide the vendor-specific network-derived APM candidate.

## References

[1] IBM, "What Is Application Performance Management (APM)?" IBM Think,
    updated June 22, 2026. [Online]. Available:
    https://www.ibm.com/think/topics/application-performance-management
    — Changeable source; verify IBM's current summary and attribution of the
    Gartner taxonomy and feature descriptions on the page. Last confirmed:
    August 28, 2026.

[2] Gartner, "Keep the Five Functional Dimensions of APM Distinct," Gartner
    Research Note G00206101, September 16, 2010. [Online]. Available:
    https://www.gartner.com/en/documents/1436734
    — Historical Gartner source; the public document path may redirect or
    require access, so verify the title, document ID, date, and five-dimension
    wording against Gartner's current archive or a licensed copy. Last
    confirmed: August 28, 2026.

[3] OpenTelemetry, "Signals," OpenTelemetry Documentation, last modified
    March 10, 2026. [Online]. Available:
    https://opentelemetry.io/docs/concepts/signals/
    — Changeable project documentation; verify current signal status and
    definitions before using profiles or other evolving signal claims. Last
    confirmed: August 28, 2026.

[4] Dynatrace, "Understand and manage your consumption of Full-Stack
    Monitoring (DPS)," Dynatrace Documentation, updated June 9, 2026. [Online].
    Available:
    https://docs.dynatrace.com/docs/license/capabilities/app-infra-observability/full-stack-monitoring
    — Changeable vendor documentation; verify current APM capabilities,
    OneAgent/OpenTelemetry collection paths, supported runtimes, profiling,
    trace/metric behavior, and licensing boundaries. Last confirmed:
    August 28, 2026.

[5] Dynatrace, "Analyze performance from frontend to backend," Dynatrace
    Documentation, published May 7, 2026. [Online]. Available:
    https://docs.dynatrace.com/docs/observe/digital-experience/rum/analyze-and-alert/analyze-frontend-to-backend
    — Changeable vendor documentation; verify current RUM, OneAgent,
    OpenTelemetry, Server-Timing, intermediary, and frontend/backend-linking
    requirements. Last confirmed: August 28, 2026.

[6] NETSCOUT, "IT Troubleshooting Solution - nGeniusONE," official product
    page. [Online]. Available:
    https://www.netscout.com/product/ngeniusone-solution
    — Changeable vendor source; verify current collection components, packet or
    flow coverage, supported protocols, application/session analysis, and
    deployment scope. Last confirmed: August 28, 2026.

[7] NETSCOUT, "nGeniusONE Service Assurance platform," official product data
    sheet, June 2021. [Online]. Available:
    https://www.netscout.com/sites/default/files/2021-06/EPDS_025_EN-2101%20-%20nGeniusONE.pdf
    — Historical vendor document; verify current product names, supported
    multi-segment and hop-by-hop analysis, retention, and licensing before
    using it as a current implementation requirement. Last confirmed:
    August 28, 2026.

[8] IBM, "Application Performance Monitoring (APM)," IBM Instana product page.
    [Online]. Available:
    https://www.ibm.com/products/instana/application-performance-monitoring
    — Changeable vendor source; verify current Instana modules, collection and
    auto-instrumentation requirements, supported runtimes, trace semantics,
    retention, and licensing. Last confirmed: August 28, 2026.
