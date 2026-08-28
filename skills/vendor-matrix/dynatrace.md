# Dynatrace

## Application Performance Monitoring baseline

Dynatrace is the reference vendor for the **host-agent and application-
instrumented APM** category in this library. It is selected as a capability
baseline, not as a claim that its current platform is limited to APM.

Dynatrace's current Full-Stack Monitoring documentation explicitly describes
APM as including distributed tracing, code-level visibility, CPU profiling,
memory profiling, and deep process monitoring for hosts and containers [1].

## Collection and analysis model

Use the OneAgent-based deployment as the default baseline when the customer can
install software on the host, VM, container, or supported runtime. Dynatrace
also documents OpenTelemetry traces and metrics as supported collection paths,
so “host agent required” must be recorded as the default reference mode rather
than an unconditional product limitation [1].

This distinction is important in a comparison:

- **OneAgent mode** represents vendor-agent APM with host/process/runtime
  context and deep diagnostics.
- **OpenTelemetry mode** represents application-instrumented or collector-based
  telemetry and must be evaluated for its actual coverage and enrichment.
- **RUM/frontend mode** adds client-side evidence; it is not a substitute for
  backend instrumentation.

## APM capability profile

| Capability | Baseline interpretation | Evidence to verify in a POC |
|---|---|---|
| Service performance | Request count, failure count, and response-time metrics are documented as service metrics [1] | Metric formula, aggregation, sampling, and treatment of asynchronous or retried work |
| Distributed tracing | Trace data from OneAgent and OpenTelemetry is supported [1] | Context propagation, sampling, retention, cross-service joins, and collector-loss behavior |
| Code and runtime diagnosis | Code-level visibility plus CPU, memory, and thread profiling are documented [1] | Supported languages, profiling depth, overhead, permissions, and production safety |
| Service topology | Application/service relationships and dependency context are part of the full-stack model [1] | Discovery under proxies, service meshes, load balancers, ephemeral containers, and partial instrumentation |
| Frontend-to-backend analysis | RUM can be linked to backend traces from OneAgent or OpenTelemetry; Dynatrace documents slow user-action analysis, frontend errors caused by backend failures, and topology through intermediaries [2] | Browser coverage, `Server-Timing` or equivalent linking, mobile behavior, and clock/identity alignment |

## Cross-vendor / variants

Dynatrace should be compared with the collection model required by the design:

| Comparison category | Dynatrace role | Do not infer |
|---|---|---|
| Host-agent APM | Primary reference implementation | That every deployment requires OneAgent; OpenTelemetry paths exist |
| Application-instrumented APM | Supported alternate model | That OTel alone supplies vendor-specific host, code, or profiling context |
| Network-derived APM | Complementary, not equivalent | That OneAgent can be replaced by packet visibility when code/runtime evidence is required |
| NPM/path monitoring | Separate technique | That APM response time proves interface health, packet loss, jitter, or hop localization |

Dynatrace is therefore the appropriate baseline for asking, “What additional
evidence becomes available when instrumentation is allowed?” It is not the
baseline for asking, “What can be learned without touching application hosts?”
For that question, use [netscout.md](netscout.md) and the network-derived APM
guidance in [../techniques/apm.md](../techniques/apm.md).

## Design considerations

- Record whether the proposal uses OneAgent, OpenTelemetry SDK/auto-
  instrumentation, a collector, a browser/mobile tag, or a combination.
- Identify every uninstrumented service, proxy, database, queue, external API,
  and cloud boundary; a partial trace is not a complete transaction.
- Validate supported language/runtime versions, container or serverless
  deployment requirements, privileges, network egress, proxy behavior, and
  upgrade procedure.
- Measure agent or instrumentation overhead and test the behavior when the
  collector, backend, or trace budget is unavailable.
- Separate application response time, server processing time, database time,
  network wait, and browser time instead of treating them as one latency value.
- Confirm retention, sampling, high-cardinality limits, profile availability,
  and licensing for the target scale; the current Dynatrace documentation
  exposes consumption and trace-volume rules that must be checked against the
  selected subscription [1].

### Market context

Dynatrace's own July 2023 announcement reported that Gartner named Dynatrace a
Leader in the 2023 Magic Quadrant for Application Performance Monitoring and
Observability [3]. Treat that as vendor-reported market context, not as the
definition of APM capability and not as evidence that a current broad
Observability Platforms ranking is an APM taxonomy.

## Relationship to other techniques

- [../techniques/apm.md](../techniques/apm.md) — APM taxonomy, collection-model
  selection, and the neutral comparison boundary.
- [../techniques/npm.md](../techniques/npm.md) — network/device/path evidence
  that Dynatrace does not automatically provide through APM alone.
- [../techniques/npm-apm.md](../techniques/npm-apm.md) — shared identity, clock,
  topology, and multi-point correlation with NPM or packet tools.
- [../vendor-matrix/ibm.md](ibm.md) — IBM Instana is a separate IBM APM
  reference and is not used as the neutral baseline for QFlow.
- [../vendor-matrix/netis.md](netis.md) — Netis provides a network-derived APM
  candidate for no-application-host-instrumentation scenarios.

## References

[1] Dynatrace, "Understand and manage your consumption of Full-Stack Monitoring
    (DPS)," Dynatrace Documentation, updated June 9, 2026. [Online]. Available:
    https://docs.dynatrace.com/docs/license/capabilities/app-infra-observability/full-stack-monitoring
    — Changeable vendor documentation; verify current APM capabilities,
    OneAgent/OpenTelemetry collection paths, supported runtimes, profiling,
    trace/metric behavior, and licensing boundaries. Last confirmed:
    August 28, 2026.

[2] Dynatrace, "Analyze performance from frontend to backend," Dynatrace
    Documentation, published May 7, 2026. [Online]. Available:
    https://docs.dynatrace.com/docs/observe/digital-experience/rum/analyze-and-alert/analyze-frontend-to-backend
    — Changeable vendor documentation; verify current RUM, OneAgent,
    OpenTelemetry, Server-Timing, intermediary, and frontend/backend-linking
    requirements. Last confirmed: August 28, 2026.

[3] Dynatrace, "Dynatrace: Furthest for Vision and Highest in Execution," press
    release, July 10, 2023. [Online]. Available:
    https://www.dynatrace.com/news/press-release/dynatrace-named-a-leader-in-2023-gartner-magic-quadrant-for-apm-and-observability/
    — Vendor-reported Gartner context; verify the underlying Gartner report,
    title, date, scope, and access conditions before making an independent
    market-ranking claim. Last confirmed: August 28, 2026.
