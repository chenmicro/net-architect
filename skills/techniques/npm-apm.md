# NPM/APM Correlation

Network Performance Monitoring and Application Performance Monitoring answer
different questions but often need to be interpreted together. NPM can show
whether a device, link, or path is healthy. APM can show whether a service,
component, or user transaction is healthy. Neither result should be treated as
proof of the other layer without a defined measurement boundary.

This file is the bridge between the atomic technique files:

- [npm.md](npm.md) defines network, device, flow, packet, and active-measurement
  evidence.
- [apm.md](apm.md) defines application, runtime, client, and wire-data evidence.
- This file defines the identity, clock, topology, and correlation conditions
  needed to compare those sources.

## Correlation model

| Operational question | Evidence to combine | Result that can be defended |
|---|---|---|
| Is the user unable to reach the service? | RUM/synthetic result plus active path or service measurement | Client or probe reachability failure, with a defined test boundary |
| Is delay in the network or inside the service? | Network request/response or segment timing plus application span/log timing | A decomposition of observed delay, subject to synchronized clocks and matching transactions |
| Which network segment affects a transaction? | Packet observations at ordered points plus a stable transaction/flow identity | Per-segment or fault-domain hypothesis, if capture coverage and correlation are complete |
| Is the application slow for all users or only a path/community? | Application service metrics plus client, path, and location dimensions | Scope of impact; not automatically root cause |
| Did security or traffic change precede the incident? | Flow/security event timeline plus NPM/APM timestamps | Correlated incident context, not proof of causation without supporting evidence |

The IETF describes Operations, Administration, and Maintenance (OAM) as a
toolset for fault detection, fault isolation, and performance measurement across
protocol layers [1]. In a design, state which OAM, NPM, packet, APM, or client
measurement supplies each part of the conclusion.

## Cross-vendor / variants

The following combinations are common, but they are not interchangeable:

| Combination | Strength | Main correlation risk |
|---|---|---|
| Flow analytics + agent-based APM | Broad traffic context plus code/runtime detail | Flow records may not identify the same request represented by an application span |
| Packet analysis + wire-data APM | Network timing and protocol evidence without changing hosts | Encryption, capture loss, NAT, load balancing, and unsupported protocols can break transaction joining |
| Active probes + agent-based APM | Independent path baseline plus application cause | The probe may not reproduce the user's route, traffic class, or request behavior |
| RUM/synthetic + NPM/APM | User impact connected to service and path evidence | Browser, network, and backend clocks and identifiers may not align |
| Multiple mirror points + any APM source | More coverage for service-path analysis | More points increase duplication and identity problems unless the same exchange is joined correctly |

Use [../vendor-matrix/ibm.md](../vendor-matrix/ibm.md) for IBM QFlow and Instana
boundaries, [../vendor-matrix/netis.md](../vendor-matrix/netis.md) for Netis
wire-data and network-performance claims, [../vendor-matrix/dynatrace.md](../vendor-matrix/dynatrace.md)
for the instrumented APM baseline, and
[../vendor-matrix/netscout.md](../vendor-matrix/netscout.md) for the
network-derived APM baseline.

## Design considerations

### Establish a shared identity

To correlate an application event with network observations, define the
strongest identity available at every layer:

- an application trace/span or business-transaction identifier;
- a protocol request identifier, where the protocol exposes one;
- a five-tuple plus direction, transport sequence/acknowledgement evidence,
  and timestamps for packet-level joining; or
- a flow key and time window when no stronger identity exists.

A flow key alone may merge multiple requests in a persistent connection or
split one logical transaction into multiple records. State the confidence of
any conclusion based on a weaker identity.

### Synchronize clocks and define boundaries

Record the clock source, timestamp location, accuracy, time zone handling, and
measurement direction for each source. Define whether a value starts at the
client, ingress interface, proxy, service, database, or response egress. A
difference between two timestamps is not meaningful until those boundaries are
known.

For any multi-point design, document:

- the ordered capture points and the traffic direction at each;
- NAT, load-balancer, firewall, tunnel, overlay, and asymmetric-routing
  transformations;
- duplicate detection, packet reordering, retransmission, and stream
  reassembly rules;
- capture-loss counters and the distinction between sensor loss and network
  loss; and
- retention sufficient to re-check the conclusion.

More mirror points increase possible coverage, but do not automatically create
hop-by-hop latency, per-segment loss, or fault localization. A product that
deduplicates or recombines records may improve a consolidated view without
calculating synchronized path performance.

### Treat metric names as hypotheses

- **Latency** may mean RTT, one-way delay, request/response time, flow duration,
  service processing time, or a vendor-specific time delta.
- **Loss** may mean missing probe replies, missing packet sequence numbers,
  missing exporter records, application errors, or capture loss.
- **Jitter** means delay variation; it is not synonymous with a broad spread of
  flow durations.
- **Application response time** may be measured from a network exchange, an
  application span, a browser event, or a synthetic script.

Record the formula, source, direction, sampling, aggregation interval,
identity, and confidence for every metric in a design or POC report.

### Minimum joint POC

- Run one known transaction through at least two observation points and verify
  that the same exchange is joined rather than counted twice.
- Compare a network timing, an application span or log, and a client/probe
  result for the same time window.
- Introduce a controlled network delay, retransmission, loss, congestion, or
  server-side pause and check whether each source attributes the effect to the
  correct layer.
- Test asymmetric routing, NAT, load balancing, VXLAN/GRE/ERSPAN, non-standard
  ports, encrypted traffic, persistent connections, and asynchronous calls.
- Record throughput, packet/flow limits, agent/instrumentation coverage,
  retention, capture loss, licensing, and behavior when capacity is exceeded.

## Relationship to other techniques

- [npm.md](npm.md) — NPM evidence models, conventional SolarWinds baseline,
  device/path selection, and capture placement.
- [apm.md](apm.md) — APM taxonomy, host-agent/application-instrumentation versus
  network-derived selection, and Dynatrace/NETSCOUT reference roles.
- [management-plane.md](management-plane.md) — NTP, syslog, SPAN/TAP, and
  management telemetry affect correlation confidence.
- [sla-policies.md](sla-policies.md) — active probes and service-level policy
  consume performance measurements but do not define their evidence.
- [qos.md](qos.md) — congestion and queuing are common causes of network delay,
  loss, or jitter seen alongside application symptoms.
- [overlay-architecture.md](overlay-architecture.md), [vxlan.md](vxlan.md),
  and [evpn.md](evpn.md) — overlays, VTEPs, asymmetric paths, and tenant
  boundaries complicate identity and capture placement.

## References

[1] T. Mizrahi, N. Sprecher, E. Bellagamba, and Y. Weingarten, "An Overview of
    Operations, Administration, and Maintenance (OAM) Tools," IETF RFC 7276,
    June 2014. [Online]. Available:
    https://www.rfc-editor.org/rfc/rfc7276.html
    — Non-changeable informational RFC; covers data-plane OAM, fault detection,
    fault isolation, performance monitoring, and loss/delay measurement.
