# IBM

## QRadar and QFlow

IBM QRadar documentation describes QFlow as the QRadar component that collects
and creates flow information. It is a flow-collection and security-analytics
capability, not a general-purpose NPM platform or a conventional agent-based
APM product [1], [2]. In this library, all conclusions in this file apply to
QFlow/Flow Collector unless a separate QRadar component is named explicitly.

QFlow can receive traffic from packet-based monitoring sources such as SPAN,
ERSPAN, and network TAPs, and can also process external flow sources such as
NetFlow, sFlow, and J-Flow [1], [2], [5]. A packet-based Flow Collector can
identify applications from observed traffic even when they use a non-standard
port, and IBM distinguishes this from an external flow record that may identify
only the port [1].

The resulting flow is a normalized record of network activity between hosts. The
documented fields include source and destination IP addresses and ports,
protocol, flow ID, source-domain information, and flow-source-dependent VLAN or
VXLAN fields. Byte and packet counters and available payload evidence are
aggregated into the record [3]. Long-lived communication is reported in
intervals, so one application session can appear as multiple records with the
same first-packet time and advancing last-packet times [2], [3].

## Application identification and evidence depth

QFlow application determination uses several algorithms: payload application
signatures, state-based decoding, QRadar port mappings, user-defined port
mappings, ICMP protocol mapping, and flow-exporter information [4]. The Flow
Information view exposes which determination algorithm was used, which is useful
when assessing confidence in a non-standard application mapping [4].

QFlow's packet-based source is not a full packet-capture engine. IBM documents a
limited beginning-of-conversation payload capture with an adjustable amount of
content per flow; increasing capture size affects collector-to-processor traffic
and storage [1]. Therefore, QFlow can provide useful application and traffic
evidence without providing the complete historical packet stream required for
arbitrary packet replay or full TCP forensics.

QRadar Network Insights (QNI) is a separate inspection capability. IBM's
application-identification documentation says QNI uses its own inspectors and
detection methods, with QFlow algorithms used only when QNI cannot identify a
specific protocol [4]. Do not credit QNI's deeper inspection levels to QFlow in
a design, comparison, or bill of materials.

## Multiple sources and mirror-point analysis

The QRadar flow pipeline has two relevant multi-source functions:

- **Flow deduplication** removes duplicate flows when multiple Flow Collectors
  send data to Flow Processors.
- **Asymmetric recombination** attempts to combine the two sides of a flow when
  each direction arrives through a different observation path; IBM notes that
  sometimes only one side is present [2].

These functions improve the integrity of a consolidated flow view. They do not,
by themselves, establish synchronized hop-by-hop path measurement. That is an
architectural inference from the documented output: QFlow normalizes and
aggregates flow records, while the documentation does not describe a path model
that compares the same packet or transaction across ordered mirror points [2], [3].

Consequently, multiple mirror points can still be useful for **coverage**—for
example, observing core, DMZ, server, and application-switch traffic—or for
redundant visibility [1]. They should not be installed with the assumption that
QFlow alone will calculate per-segment latency, data-plane packet loss, jitter,
or the hop responsible for a delay. Those requirements belong in an NPM,
packet-analysis, active-measurement, or application-tracing design; see
[npm.md](../techniques/npm.md), [apm.md](../techniques/apm.md), and the
cross-layer guidance in [npm-apm.md](../techniques/npm-apm.md).

IBM documents ERSPAN support in QRadar 7.5.0 Update Package 13 and later for
transporting mirrored traffic over an IP network to a compatible Flow Collector;
the feature is configured in QFlow settings and is disabled by default in that
documentation [5]. ERSPAN extends where a mirror can be delivered. It does not
change the distinction between packet collection and cross-point path
correlation.

## Flow processing, correlation, and capacity boundaries

The Flow Processor performs deduplication, asymmetric recombination, license
throttling, and forwarding. Flow data can then pass through QRadar's Custom
Rules Engine and contribute to an offense when a configured rule matches [2].
This makes QFlow valuable in a SOC for traffic inventory, application identity,
security search, and flow/event correlation; a security offense is not the same
thing as an NPM baseline or an APM transaction trace.

QFlow has explicit capacity behavior. IBM documents that when incoming traffic
exceeds the processable flow capacity, QRadar creates overflow records; excess
flows are not parsed, and the overflow record may retain counters while omitting
source/destination addresses, ports, and payload capture [6]. A design that
depends on application identification or multi-point evidence must therefore
validate flow-per-minute capacity, licensing, processing limits, and what is
lost during overload.

## Design judgment

- Choose QFlow when the primary need is to bring network activity into QRadar
  for traffic search, application recognition, security correlation, and
  incident context.
- Add a dedicated NPM or path-measurement function when the requirement includes
  interface/link health, active reachability, RTT/one-way delay, packet loss,
  jitter, or hop-by-hop localization.
- Add packet analysis or a full packet-capture function when the requirement is
  arbitrary packet replay, detailed TCP forensics, or historical evidence beyond
  the limited QFlow payload sample.
- Add instrumented or wire-data APM when the requirement is end-to-end
  application transactions, database/component timing, exceptions, code-level
  profiling, RUM, or runtime state.
- If QFlow and another performance tool are deployed together, define which
  system owns the authoritative timestamp, alert, transaction identity, and
  retention policy. Validate deduplication and asymmetric routing rather than
  assuming that more collectors automatically produce more accurate metrics.

## Instana APM

IBM Instana Observability is IBM's application performance monitoring product,
not a QFlow mode. IBM's current product page lists Full Stack APM, discovery and
monitoring, logs in context, distributed tracing, analytics, and root-cause
analysis [7]. It also describes transaction tracing across application
components and automatic topology discovery [7].

For this library, classify Instana as an **agent/auto-instrumentation APM
reference** and confirm the exact host agent, runtime auto-instrumentation,
OpenTelemetry, collector, browser, and mobile requirements for the target
deployment. Do not infer those requirements from QFlow's packet-based flow
collection model.

Instana is a valid IBM APM product to record in the vendor matrix, but it is not
the neutral APM baseline for a QFlow comparison: using two products from the
same vendor can blur the boundary the comparison is intended to test. Use
[dynatrace.md](dynatrace.md) for the host-agent APM baseline and
[netscout.md](netscout.md) for the network-derived APM baseline.

## References

[1] IBM, "QRadar Flow Collectors and packet-based sources," IBM QRadar 7.5.0
    documentation. [Online]. Available:
    https://www.ibm.com/docs/en/qsip/7.5.0?topic=sources-qradar-flow-collectors-packet-based
    — Changeable product documentation; verify the current QRadar 7.5
    documentation under *Flow sources* and confirm packet-source behavior,
    application visibility, payload-capture limits, and release scope. Last
    confirmed: August 28, 2026.

[2] IBM, "QRadar Events and Flows," IBM QRadar 7.5.0 documentation. [Online].
    Available: https://www.ibm.com/docs/en/qsip/7.5.0?topic=overview-qradar-events-flows
    — Changeable product documentation; verify the current *Flows* and *Flow
    pipeline* sections for QFlow inputs, normalized flow records, per-minute
    reporting, deduplication, asymmetric recombination, licensing, forwarding,
    and CRE correlation. Last confirmed: August 28, 2026.

[3] IBM, "Flow aggregation," IBM QRadar 7.5.0 documentation. [Online].
    Available: https://www.ibm.com/docs/en/qsip/7.5.0?topic=monitoring-flow-aggregation
    — Changeable product documentation; verify the current field list and
    aggregation interval behavior. Last confirmed: August 28, 2026.

[4] IBM, "Application identification," IBM QRadar 7.6.0 documentation. [Online].
    Available: https://www.ibm.com/docs/en/qsip/7.6.0?topic=monitoring-application-identification
    — Changeable product documentation; verify current QFlow application
    determination algorithms and the distinction from QNI inspectors. Last
    confirmed: August 28, 2026.

[5] IBM, "Flow improvements," IBM QRadar 7.5.0 documentation. [Online].
    Available: https://www.ibm.com/docs/en/qsip/7.5.0?topic=qradar-flow-improvements
    — Changeable release documentation; verify ERSPAN support, the applicable
    Update Package, supported mirror encapsulations, and default configuration
    before deployment. Last confirmed: August 28, 2026.

[6] IBM, "Flow capacity limits and overflow records in IBM QRadar," IBM QRadar
    7.5.0 documentation. [Online]. Available:
    https://www.ibm.com/docs/en/qsip/7.5.0?topic=aggregation-flow-capacity-limits
    — Changeable product documentation; verify current deployment, hardware,
    user, and overflow behavior against the target appliance and license. Last
    confirmed: August 28, 2026.

[7] IBM, "Application Performance Monitoring (APM)," IBM Instana product page.
    [Online]. Available:
    https://www.ibm.com/products/instana/application-performance-monitoring
    — Changeable vendor source; verify current Instana modules, collection and
    auto-instrumentation requirements, supported runtimes, trace semantics,
    retention, and licensing. Last confirmed: August 28, 2026.
