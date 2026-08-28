# Netis

## Product family and naming

Netis is a product family rather than a one-to-one equivalent of QFlow. Its
official solutions page currently positions three relevant products together:

- **BPC — Business Performance Center**: packet-based transaction analysis,
  real service mapping, and evidence for RCA without application changes;
- **NPM — Network Performance Manager**: unified network-performance visibility
  and alerting across WAN, LAN, data-center, and hybrid environments; and
- **Netis 42**: AI-assisted fault diagnosis, correlation, summarization, and
  operational guidance [1].

Netis also describes transaction-level application performance monitoring and
transaction-link tracing in its hybrid-observability material [4]. In this
library, **Netis APM** is a capability label for the application/business-
performance function represented primarily by BPC and related observability
modules. It is not an assertion that the current English catalog exposes a
standalone SKU named exactly “Netis APM.” Confirm the commercial product,
version, module, and license in the proposal or current datasheet.

## Collection and analysis model

Netis presents an out-of-band, agentless collection model: mirrored traffic from
SPAN, ERSPAN, NPB, or TAP sources and flow sources is collected, service
relationships and paths are mapped, and the resulting evidence is correlated for
diagnosis [1]. This design is relevant where application code cannot be changed
or agents are not acceptable.

The advertised workflow is **collect → map → diagnose → act**. The public
solution material associates it with packet-level evidence, transaction detail,
SLA and anomaly monitoring, REST APIs, and integration into operations workflows [1].
These statements describe the vendor’s intended capability; actual depth
depends on capture fidelity, supported protocols, topology, retention, and the
licensed modules.

## Netis NPM capability profile

Netis positions NPM around network-performance visibility and alerting across
WAN/LAN/data-center/hybrid environments [1]. Its data-center and service-assurance
materials describe a broader packet- and path-oriented profile, including:

- path latency and loss analysis, link and service-path views, and multi-layer
  fault localization;
- transport/application behavior such as retransmissions, slow flows, and
  protocol-level service delays;
- underlay/overlay and data-center visibility, including microburst or
  congestion-oriented analysis where the relevant data source is available; and
- packet evidence, historical backtracking, and cross-segment or hop-by-hop RCA
  as advertised outcomes [2], [3].

The current DCN solution page specifically describes real-time east-west and
north-south visibility across ToR, leaf-spine, and overlay locations; packet-
precision microburst and latency analytics; full raw-packet capture for
historical backtracking; and visibility points placed at key data-center
locations [2]. These are useful design signals, not a substitute for checking
the deployed sensor topology and licensed feature set.

This is substantially closer to a full NPM/service-assurance function than a
flow-only security collector. The claims remain **vendor-stated**: validate the
metric formula, sensor placement, supported encapsulations, packet-rate limit,
retention, and license for the target deployment.

Netis's telecom page gives a concrete example of the intended depth: session,
API, and business-level observability; service-delay, retransmission, error,
and slow-API/HTTP-flow monitoring; Backbone/DCN congestion and latency
analytics; end-to-end path correlation; and raw-packet replay for RCA [3].
Treat these as scope indicators to map to an actual Netis edition and capture
architecture.

## Netis APM capability profile

Netis's hybrid-observability material explicitly describes transaction-level
application performance monitoring, transaction-level network performance
monitoring, non-intrusive collection without application modification,
transaction-link tracing, and database-performance monitoring [4]. Its
telecom/service-assurance material further advertises traffic, application, and
database observability; HTTP, SQL, DNS, and TLS decoding; and end-to-end path or
service correlation [3].

The same hybrid page presents the collection as full-volume raw business-network
data, with cross-cloud/on-premises transaction-link tracing and reconstructed
user-business behavior; it also lists adaptive microservice monitoring and
transaction-level APM/NPM as application scenarios [4]. These claims should be
validated for the target cloud, protocol, encryption, and transaction-identity
conditions.

That makes Netis APM a **wire-data or network-derived APM** capability: it can
follow and analyze transactions observed on the network and correlate them to
service paths without code changes. It should not automatically be treated as a
replacement for agent-based APM where the requirement is browser RUM,
synthetic-user journeys, stack traces, exception objects, code-level profiling,
garbage-collection state, or arbitrary in-process runtime metrics. Those
boundaries follow from the data source and must be tested against the exact
Netis module and protocol coverage.

## Netis 42 and packet evidence

Netis 42 is positioned as a separate AI diagnosis product. The official product
page describes PCAP analysis, multi-segment correlation, packet-level evidence,
multi-protocol parsing, and AI-assisted diagnosis [5]. Treat it as an analysis
and diagnosis component in the Netis family, not as evidence that every NPM or
APM deployment includes full packet capture or AI diagnosis by default.

The product page also says NETIS 42 can consume PCAP files from third-party
capture and NPM tools, compare multiple capture files, surface sample packets,
and export standardized diagnosis reports [5]. That makes it a possible
post-capture analysis layer in a heterogeneous NPM design, subject to PCAP
completeness and the product’s supported parsing rules.

## Cross-product view

| Requirement | Netis capability to evaluate | Important boundary |
|---|---|---|
| Network health, performance baselines, and alerting | NPM | Confirm device/interface telemetry versus mirrored-traffic analytics and active-probe support |
| Transaction and service-performance analysis without code changes | BPC / Netis APM capability | Confirm protocol/database coverage, transaction identity, encryption handling, and licensing |
| Packet-level diagnosis and multi-segment correlation | Netis 42 and the relevant NPM/BPC data path | Confirm whether raw packets are retained, searchable, and available for the required history |
| AI-assisted cross-domain RCA | Netis 42 and solution integrations | Treat AI output as a hypothesis until packet, flow, and transaction evidence supports it |

## Design judgment

- For the NPM requirements in [npm.md](../techniques/npm.md), Netis is
  the closer product-family match when the design needs passive network
  performance, path or service correlation, packet evidence, and multi-point
  analysis.
- Yes, Netis has an APM-level capability in the functional sense: the vendor
  explicitly describes transaction-level application performance monitoring.
  Use “BPC/application-business observability” in a bill of materials until the
  exact commercial SKU and module name are confirmed.
- Netis's advertised agentless wire-data APM, discussed in
  [apm.md](../techniques/apm.md), can complement, but does not necessarily
  replace, instrumented APM. Require a side-by-side test if code, runtime, RUM,
  database-query, or exception depth is a hard requirement.
- Multiple mirror points are useful only if the selected Netis modules can join
  the same transaction or packet across points. Validate clock accuracy,
  asymmetric routing, NAT/load-balancing identity changes, duplication,
  reassembly, capture loss, encryption, and the resulting fault-localization
  output.
- Netis claims should be tracked as vendor-stated and edition-dependent until
  confirmed in a current technical datasheet and a POC using the customer’s
  traffic mix and throughput.

## References

[1] Netis, "Enterprise AI Observability Platform — Solutions," official product
    site. [Online]. Available: https://www.netis.com/en/solutions
    — Changeable vendor source; verify the current product names, collection
    sources, packet-evidence model, service mapping, alerting, and API claims on
    the current *Solutions* page. Last confirmed: August 28, 2026.

[2] Netis, "Data Center Network Performance Analytics," official product site.
    [Online]. Available: https://www.netis.com/en/solutions/technology/dcn
    — Changeable vendor source; verify current claims for underlay/overlay,
    microbursts, path latency/loss, raw-packet capture, historical backtracking,
    and cross-domain RCA. Last confirmed: August 28, 2026.

[3] Netis, "Telecom Service Assurance Across Backbone and DCN, and CRM/BSS/OSS,"
    official product site. [Online]. Available:
    https://www.netis.com/en/solutions/industry/telecommunication
    — Changeable vendor source; verify current claims for retransmissions,
    service delays, HTTP/SQL/DNS/TLS decoding, database/application visibility,
    and end-to-end path correlation. Last confirmed: August 28, 2026.

[4] Netis, "Hybrid Environment Unified Observability Solution," official
    product site. [Online]. Available:
    https://ai.netis.com.cn/en/solutions/hybrid-observability
    — Changeable vendor source; verify current transaction-level APM/NPM,
    agentless collection, transaction-link tracing, and database-monitoring
    claims, as well as the applicable module and deployment model. Last
    confirmed: August 28, 2026.

[5] Netis, "NETIS 42 AI Packet Diagnosis," official product site. [Online].
    Available: https://www.netis.com/en/products/netis-42
    — Changeable vendor source; verify current PCAP, multi-segment correlation,
    packet-evidence, protocol-parsing, and AI-diagnosis claims. Last confirmed:
    August 28, 2026.
