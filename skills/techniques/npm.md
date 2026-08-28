# Network Performance Monitoring (NPM)

Network Performance Monitoring asks whether the network, its devices, and its
paths are healthy, available, and meeting performance targets. It is distinct
from Application Performance Monitoring, which asks whether software services
and user transactions are healthy. The distinction matters when selecting
telemetry, placing sensors, and deciding what a product result actually proves.

IBM describes network monitoring as collecting traffic and performance data,
building topology and traffic-flow visibility, and alerting on health or
threshold problems. It distinguishes SNMP-based, flow-based, and active network
monitoring; active solutions can measure reachability, round-trip time,
bandwidth, packet loss, and link utilization [1]. A product that only indexes
flow records should not automatically receive credit for all of those
capabilities.

## NPM scope and typical functions

An NPM implementation may combine several data sources:

- **Device and interface telemetry** — reachability, interface counters,
  errors, discards, utilization, CPU, memory, queue state, and environmental
  health. SNMP, streaming telemetry, APIs, and vendor-specific sensors are
  common sources.
- **Flow telemetry** — conversations summarized by source/destination, ports,
  protocol, bytes, packets, and time. Flow records scale well across a large
  network, but summarize traffic rather than preserve every packet.
- **Passive packet observation** — SPAN, ERSPAN, TAP, network packet broker, or
  inline sensor feeds used to calculate TCP behavior, application protocol
  fields, and packet-level evidence when the capture is complete enough.
- **Active measurement** — probes such as IP ping, traceroute, BFD, OWAMP, or
  TWAMP that test reachability, delay, loss, and sometimes delay variation. The
  IETF describes OAM as a toolset for fault detection, isolation, and
  performance measurement across protocol layers, including packet-loss and
  packet-delay measurement [2].
- **Analytics and operations** — topology/dependency views, utilization and
  capacity trends, thresholds, baselines, anomaly detection, SLA/SLO reporting,
  alert routing, and fault-domain or path localization.

## Evidence models

The evidence source determines what an NPM result can prove:

| Technique | Primary evidence | Good for | Main limitation |
|---|---|---|---|
| Device/interface telemetry | Counters and state from network devices | Link health, utilization, errors, queues, and device resource health | Usually does not identify an individual transaction or prove end-to-end path behavior |
| Flow telemetry | Summarized conversations and exporter metadata | Traffic inventory, top talkers, application/port visibility, security correlation, and historical volume | Usually cannot prove data-plane packet loss, jitter, one-way delay, or the responsible hop |
| Passive packet analysis | Observed packet sequence and protocol payload | TCP retransmissions, handshake behavior, protocol timing, packet evidence, and application decoding | Requires correct placement, sufficient capture fidelity, reassembly, retention, and handling of encryption |
| Active probes/OAM | Packets deliberately sent and measured | Reachability, RTT, loss, path checks, service-level baselines, and fault detection | Measures the probe path and traffic class; it may not reproduce real user behavior |

The same metric name can have different evidence quality. A flow record's
start/end timestamps and byte counters can establish that a session existed and
how long the collector observed it; they do not by themselves prove round-trip
time, one-way delay, packet loss, jitter, or the hop where a problem occurred.
Those claims require an appropriate measurement method and a defined
measurement boundary.

## Cross-vendor / variants

Classify a product by its evidence and measurement boundary, not by the
marketing label:

| Product posture | Typical output | Interpret carefully |
|---|---|---|
| Flow-centric NPM | Conversations, application identity, volume, timing, and exporter health | Strong traffic inventory; limited direct proof of packet/path performance |
| Packet-centric NPM | TCP/application behavior, packet loss or retransmission evidence, and packet drill-down | Stronger fault isolation; capture placement, loss, storage, and encryption are material |
| Active NPM/OAM | Probe reachability, RTT/delay, loss, jitter, and path behavior | Define probe source, destination, traffic class, frequency, and whether the result is one-way or round-trip |
| Device-centric NPM | Interface, device, topology, capacity, and infrastructure health | Does not automatically show application transaction behavior or user experience |

### Reference baseline: SolarWinds NPM

SolarWinds Network Performance Monitor (NPM) is the reference baseline for
conventional device- and path-oriented NPM. Its official documentation describes
multi-vendor device monitoring, interface and hardware health, topology
discovery, response-time and packet-loss metrics, and NetPath hop-by-hop path
analysis [3], [4].

Use this baseline to test whether another product provides conventional NPM
functions. Product edition, deployment model, licensing, retention, and metric
semantics still require confirmation for a target design. SolarWinds NPM is not
the APM baseline; application depth belongs in [apm.md](apm.md).

For the products in this library, QFlow is evaluated primarily as a
flow/security analytics component in [ibm.md](../vendor-matrix/ibm.md), while
Netis is evaluated as a packet/service/path-oriented NPM candidate in
[netis.md](../vendor-matrix/netis.md). Those classifications do not transfer
capabilities from one product or module to another.

## Design considerations

### Select by required proof

Translate the requirement into the evidence needed before selecting a tool:

1. **Is the endpoint or path reachable?** Use active probes or an equivalent
   continuity measurement.
2. **Where is delay or loss introduced?** Use measurements at defined endpoints
   or synchronized packet observations that can compare the same traffic across
   points.
3. **Is the network or the application responsible?** Combine NPM/path evidence
   with application transaction or runtime evidence; see [apm.md](apm.md).
4. **Which traffic is abnormal or risky?** Flow and security analytics may be
   sufficient, even when they are not a performance-monitoring substitute.

### Capture placement and multiple observation points

SPAN/TAP points increase visibility, but they do not automatically create path
analytics. Define every capture point's direction and topology, including NAT,
load balancing, tunnels, overlays, and asymmetric routing. Record capture-loss
counters and distinguish sensor loss from network loss. For correlation of the
same exchange across points, use the identity, clock, deduplication, and
reassembly requirements in [npm-apm.md](npm-apm.md).

### Treat metric names as hypotheses until their calculation is known

- **Latency** may mean RTT, one-way delay, request/response time, flow duration,
  or a vendor-specific time delta.
- **Loss** may mean missing probe replies, missing packet sequence numbers,
  missing exporter records, or capture loss.
- **Jitter** means delay variation; it is not synonymous with a broad spread of
  flow durations.
- **Path performance** requires a defined source, destination, direction,
  traffic class, sampling interval, and aggregation method.

Record the formula, source, direction, sampling, aggregation interval, and
confidence for each metric in a design or POC report.

### Minimum NPM POC

- Test a known path from a defined source to a defined destination and record
  the measurement boundary.
- Introduce a controlled delay, loss, retransmission, congestion, or interface
  error and check whether the tool localizes the fault to the correct segment or
  layer.
- Test asymmetric routing, NAT, load balancing, VXLAN/GRE/ERSPAN,
  non-standard ports, and encrypted traffic where relevant.
- Verify capture loss, packet/flow limits, retention, licensing, and behavior
  when capacity is exceeded.
- Compare the tool's result with an independent device counter, packet capture,
  or active probe before treating it as authoritative.

## Relationship to other techniques

- [apm.md](apm.md) — application transactions, runtime state, code-level
  diagnosis, and the agent/instrumentation versus wire-data distinction.
- [npm-apm.md](npm-apm.md) — shared NPM/APM identity, clock, topology, and
  multi-point correlation.
- [management-plane.md](management-plane.md) — SNMP/telemetry, NTP, syslog,
  and SPAN/TAP are common NPM data sources; time synchronization and mirror
  design directly affect measurement confidence.
- [sla-policies.md](sla-policies.md) — BFD, active probes, and app-aware routing
  turn performance measurements into path-selection or service-level policy.
- [qos.md](qos.md) — queuing, congestion, DSCP, ECN, and buffer behavior are
  common causes of delay, loss, and jitter.
- [overlay-architecture.md](overlay-architecture.md), [vxlan.md](vxlan.md),
  and [evpn.md](evpn.md) — tunnels, VTEPs, asymmetric paths, and tenant
  boundaries complicate capture placement and identity across points.

## References

[1] IBM, "What is network monitoring?" IBM Think, updated June 22, 2026.
    [Online]. Available: https://www.ibm.com/think/topics/network-monitoring
    — Changeable source; verify the current page and update date before relying
    on product-taxonomy wording. Last confirmed: August 28, 2026.

[2] T. Mizrahi, N. Sprecher, E. Bellagamba, and Y. Weingarten, "An Overview of
    Operations, Administration, and Maintenance (OAM) Tools," IETF RFC 7276,
    June 2014. [Online]. Available:
    https://www.rfc-editor.org/rfc/rfc7276.html
    — Non-changeable informational RFC; covers data-plane OAM, performance
    monitoring, loss/delay measurement, and the IP Ping/Traceroute/BFD/OWAMP/
    TWAMP tool families.

[3] SolarWinds, "Network Performance Monitor Administrator Guide," official
    product documentation. [Online]. Available:
    https://documentation.solarwinds.com/en/success_center/npm/content/npm_administrator_guide.htm
    — Changeable vendor documentation; verify current device/interface health,
    topology, NetPath, polling, supported integrations, and deployment/licensing
    scope. Last confirmed: August 28, 2026.

[4] SolarWinds, "Network Performance Monitor," official product page. [Online].
    Available: https://www.solarwinds.com/network-performance-monitor
    — Changeable vendor source; verify current claims for response time, packet
    loss, NetPath hop-by-hop analysis, PerfStack correlation, and capacity
    planning. Last confirmed: August 28, 2026.
