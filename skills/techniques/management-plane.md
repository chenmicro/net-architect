# Management Plane — Discovery, AAA, Telemetry

This file covers the protocols that operate the network itself rather than forwarding
traffic: neighbor discovery, management authentication, monitoring/telemetry, and
time synchronization. They're not architectural techniques in the same weight class
as BGP or EVPN, but they surface as cross-vendor mismatches in every multi-vendor
design and need explicit alignment.

## Cross-vendor / variants

### Discovery: CDP vs. LLDP

| | Cisco | Huawei | Standard? |
|---|---|---|---|
| Default protocol | **CDP** (Cisco Discovery Protocol, proprietary) | **LLDP** (IEEE 802.1AB) [1] | LLDP is standard |
| Cross-vendor | CDP doesn't exist on non-Cisco gear; Cisco also supports LLDP | LLDP works across all vendors | Use LLDP |

Both sides must run **LLDP** on inter-switch links for neighbor discovery. CDP is
Cisco-only and won't be understood by the Huawei/Arista/Juniper side.

### AAA: TACACS+ vs. RADIUS

| | Cisco | Huawei |
|---|---|---|
| Management authentication | TACACS+ widely used (Cisco-proprietary) + RADIUS | RADIUS (standard); limited TACACS+ support on some platforms |
| Per-command authorization | TACACS+ is a Cisco hallmark | RADIUS-based; per-command authorization scope differs |
| 802.1X / NAC | RADIUS (both) | RADIUS (see [nac.md](nac.md)) |

**RADIUS** is the common authentication protocol across vendors for both management
login and 802.1X ([nac.md](nac.md)). TACACS+ is Cisco-specific — if the existing
auth infrastructure is Cisco TACACS+, the non-Cisco side will need RADIUS or a
separate AAA path. For a greenfield multi-vendor deployment, pick RADIUS from the
start and avoid the TACACS+ migration problem.

### SNMP / telemetry

| Area | Cisco | Huawei |
|---|---|---|
| MIB trees | Cisco-proprietary MIBs for platform-specific data | Huawei-proprietary MIBs |
| Trap formatting | Cisco-specific trap OIDs and varbind structure | Huawei-specific trap OIDs and structure |
| Model-driven telemetry | YANG/gNMI on NX-OS, IOS-XE | NETCONF/YANG on VRP |
| Polling defaults | Varies by platform | Varies by platform |

MIB trees differ per vendor — a Cisco OID query to a Huawei switch returns
garbage or an empty response. Trap formatting, syslog severity levels, and
default polling intervals vary. A monitoring system (SolarWinds, PRTG,
Observium, Zabbix) needs **separate device profiles per vendor** — the protocol
plumbing (SNMPv3, syslog, gNMI) is standard but the data models are not.

### Port mirroring (SPAN vs. port-mirror)

Cisco calls it **SPAN/RSPAN/ERSPAN**; Huawei calls it **port mirroring /
remote mirroring**. The function (copy packets from one port to another for
analysis) is the same, but:

- CLI syntax differs completely
- ERSPAN encapsulation details (GRE header version, session-ID encoding)
  differ — ERSPAN interop between Cisco and Huawei is not guaranteed and
  should be tested before depending on it
- Decapsulation at the collector/tool side requires matching the source
  vendor's ERSPAN format

### NTP / time synchronization

NTP is standard (RFC 5905) [2] and works across both vendors without interop issues.
Alignment checklist for cross-vendor designs:

- **Version**: same NTP version (v3 or v4) on both sides
- **Stratum**: same master/stratum hierarchy — pick the same upstream NTP
  source(s)
- **Authentication**: if NTP authentication is enabled, keys and key IDs must
  match
- **Source interface**: use loopback as the NTP source on both sides for
  consistent source IP reachability

### Syslog

Syslog is standard (RFC 5424) [3] and works across both vendors. Alignment:

- **Facility**: same syslog facility for forwarded messages
- **Severity threshold**: same minimum severity level (e.g., `informational` or
  `warning`) for forwarding to the collector
- **Timestamp format**: same timestamp format (ISO 8601 preferred, but both
  vendors default to a different local format — configure explicitly)
- **Source interface**: use loopback as the source for consistent source IP in
  syslog messages

## Design considerations

- **Discovery**: always enable LLDP on inter-switch links in multi-vendor
  environments — CDP is Cisco-only and won't be understood by non-Cisco
  neighbors.
- **AAA**: choose RADIUS for multi-vendor deployments. TACACS+ is
  Cisco-proprietary and has limited support on Huawei platforms. Use the
  same AAA server(s) for both management login and 802.1X NAC.
- **SNMP/telemetry**: monitoring systems need separate device profiles per
  vendor — MIB trees, trap OIDs, and polling defaults differ. For model-driven
  telemetry, align on a common transport (gNMI or NETCONF/YANG) and confirm
  YANG model support on both sides before committing.
- **Port mirroring**: CLI syntax differs completely between vendors; ERSPAN
  interop is not guaranteed — test before depending on it for production
  packet capture.
- **NTP**: standard protocol (RFC 5905), no interop issues. Align version
  (v3/v4), use the same upstream source(s), configure loopback as source
  interface, and match authentication keys if enabled.
- **Syslog**: standard protocol (RFC 5424), no interop issues. Align facility,
  severity threshold, timestamp format (prefer ISO 8601), and use loopback as
  source interface.

## Relationship to other techniques

- [nac.md](nac.md) — RADIUS is the common protocol for both management AAA and
  802.1X; TACACS+ is Cisco-only and irrelevant in multi-vendor NAC designs.
- [stp.md](stp.md) — LLDP is the cross-vendor discovery protocol for STP
  topology visibility; CDP-only Cisco switches lose neighbor visibility on
  multi-vendor links without LLDP.

## References

[1] IEEE 802.1AB-2016, "IEEE Standard for Local and Metropolitan Area
    Networks — Station and Media Access Control Connectivity Discovery."

[2] D. Mills, U. Delaware, J. Martin, Ed., "Network Time Protocol Version 4:
    Protocol and Algorithms Specification," RFC 5905, June 2010.
    [Online]. Available: https://www.rfc-editor.org/rfc/rfc5905

[3] R. Gerhards, "The Syslog Protocol," RFC 5424, March 2009.
    [Online]. Available: https://www.rfc-editor.org/rfc/rfc5424
