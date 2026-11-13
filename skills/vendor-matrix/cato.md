# Cato Networks

- **Definition.** Cato Networks sells **SASE as a converged, cloud-native service**
  in which the SD-WAN function is a property of Cato's own private backbone rather
  than a standalone product, with the security service edge in the same cloud [1].
- **Name and scope.** "Cato SD-WAN" is therefore a *capability of the platform*, not
  a separate SKU: sites attach through Sockets or vSockets (or IPsec / Cloud
  Interconnect), remote users through ZTNA, and networking and security policy are
  authored in one console, the Cato Management Application (CMA) [2], [1].
- **Two service tiers.** The vendor ships two distinct services from the same
  cloud, and the choice determines what WAN the customer actually ends up with [1].
  This is the first question to settle in any Cato design review: "we're buying
  Cato" is ambiguous until the tier is known.
- **Proprietary platform, standards-based edges.** The overlay is Cato's own (DTLS
  to the PoP), while the attachment and control surfaces are standard: IPsec for
  third-party sites, BGP or static routing toward the Socket, GraphQL for telemetry
  [1], [3], [4].
- **Boundary.** This file records what Cato ships, how it is wired, and the
  constraints it imposes on a design. It is not an operations runbook.

| Service | What Cato supplies | What the customer keeps |
|---|---|---|
| **Cato SASE** | Networking (SD-WAN) **and** security, converged | Nothing — Cato is the WAN |
| **Cato SSE** | Security only, with secure Internet egress | Existing/third-party SD-WAN, integrated over IPsec [1] |

## Reference architecture

### Cato Cloud backbone and PoPs

- The Cato Cloud is a **private global backbone built over tier-1 providers**;
  PoPs are interconnected through it, giving controlled latency and packet
  delivery independent of the public Internet [4].

### PoP footprint

- **91 production PoP locations** are enumerated in Cato's Production PoP Guide,
  counted from its per-region tables on **2026-10-20**: 24 in Asia/Australia/Oceania,
  38 in the Americas, 29 in EMEA [5].
- Treat that as a **floor, not a guarantee**: the guide's downloadable CSV
  "does not include PoP locations that are limited availability or coming soon", and
  new locations are published as *coming soon* before they go live [5]. Marketing
  material cites "85+ PoPs"; the enumeration above is the defensible number.
- **Africa — five locations**: **Lagos (NG)**, Johannesburg (ZA), Cape Town (ZA),
  Nairobi (KE), and Casablanca (MA) [5].
- **Nigeria has a PoP**: **Lagos, NG** is listed in production with the range
  **216.252.185.1 – 216.252.185.254** [5].
- **Two Nigerian ranges with two different jobs** — this reconciles the guide rather
  than exposing a contradiction in substance:
  - **216.252.185.0/24** (published as .1–.254) — the **Lagos PoP** range from the
    per-PoP location table: the **service-bearing** subnet, inside Cato-owned
    **216.252.176.0/20** [5].
  - **85.255.21.144/28** (published as .145–.158) — a **geo-localized** range whose
    "Serviced Through" column names **Paris**: it exists so third-party
    geo-location sees Nigerian addressing. It is *not* a PoP. It sits inside
    Cato-owned **85.255.16.0/20** [5].
- **The guide's wording is stale, not contradictory.** The geo-localized table says
  it applies to countries where "there is no Cato PoP", yet Lagos is listed as a
  production PoP — read that sentence as legacy text predating Lagos going live, and
  read the /28 row as geo-location-only.
- **Reported in design review (2026-10-20): the /28 behaves as a local
  access/ingress path rather than a service PoP.** Vendor documentation does not say
  this; it is operational observation, so confirm with Cato before it drives a
  firewall or routing decision.
- **Design consequence:** allow-list both ranges if you cannot establish which one
  the local ISP path actually uses, and do not infer an exit PoP from either —
  steering is algorithmic.
- **Allow-listing**: the guide publishes the **Cato-owned supernets** for firewall
  ACLs and the **per-PoP ranges** if you pin an exit PoP; the licence group a site
  consumes is determined separately by country allocation [5].

### Edge devices: Sockets and vSockets

- Models [2]: **X1500** (small branches), **X1600 / X1600 LTE** (medium branches;
  LTE adds resiliency and out-of-band connectivity), **X1700** (large sites and
  on-premises data centers), **vSocket** (virtual, for AWS, Azure, GCP, and VMware
  ESXi).
- **Zero-touch provisioning**: all models connect automatically to Cato Cloud for
  provisioning, monitoring, and orchestration with no local configuration, under a
  single management plane (CMA) covering networking and security [2].
- **Managed Socket Upgrade Service**: Cato pushes firmware versions automatically,
  with rollback if an upgrade is found to have issues — the appliance patch cycle
  largely leaves the customer's own change process [2].
- **Connectivity model**: DTLS tunnels to the PoP, then an automatically created
  **logical mesh** between sites, with inter-site permissioning enforced by the
  **WAN firewall**. Encryption is therefore site-to-PoP, not site-to-site [2].
- **Direct site-to-site paths** exist for three specific cases: MPLS interworking,
  redundancy (DTLS between Socket sites over the Internet when Cato Cloud access
  is temporarily unavailable — "WAN Recovery"), and selective exclusion of traffic
  from the Cato Cloud [2].
- **Optimization** applied at the edge: TCP acceleration, packet-loss mitigation
  (TCP packets duplicated across active links; UDP duplicated across active *or
  standby* links), and UDP retransmission for voice/video [2].
- Each Socket also runs a **Next-Gen LAN Firewall** — L3/L4 plus L7 application
  awareness — enforcing policy on LAN-to-WAN, LAN-to-Internet, and VLAN/subnet
  segmentation locally, with policy authored in the CMA and events logged there
  [2].
- **HA options**: multiple active links per Socket (load sharing), active/passive
  link pairs, and **two Sockets in active/standby** for device-level redundancy
  [2].
- **Migration**: a **hybrid WAN** model is supported as either a permanent or a
  transitional state — insert Internet connections alongside MPLS, then move
  traffic class by class via Network Rules (e.g. keep only voice/video on MPLS),
  and optionally terminate existing IPsec tunnels into a PoP during the transition
  [6].

### Transport and steering

- **Secure overlay:** Cato uses **DTLS** (UDP) between site and Cato Cloud
  backbone — UDP for latency-sensitive traffic, encryption for confidentiality
  and integrity across public networks [6].
- **Steering** is the algorithm that decides which of the globally dispersed PoPs
  a Socket connects to. Most sites can reach almost any PoP, subject to limited
  regional/country considerations, with balancing factors for physical and
  logical distance, PoP health and load status, same-country PoPs, and underlay
  connection quality between site and PoP [6].
- **Transport modes** are chosen per traffic class by the centralized **Network
  Rules** policy, which matches on application, source, and destination and also
  selects optimization profiles [6]:
  - Normal — traverses the Cato Cloud and is inspected by the PoP security stack.
  - **Bypass** — local Socket egress via a local underlay connection, outside the
    Cato Cloud. **Not inspected by PoP security engines** [6].
  - **Backhaul** — traffic sent across Cato SD-WAN to an Internet egress point at
    a designated Socket site [6].
  - **Off-cloud** — between Socket sites over an encrypted tunnel across the
    public Internet. **Not inspected by PoP security engines** [6].
- Bypass and off-cloud are the two documented ways to leave the inspected path.
  They are operationally useful and audit-relevant; treat them as exceptions to
  be inventoried, not as routine policy [6].
- **"Local internet breakout" is ambiguous in Cato terms — establish which one is
  meant before answering:**
  - *Egress at the nearest PoP* (the SASE default): Internet-bound traffic goes
    Socket → PoP → Internet and is inspected by the **Internet Firewall** at the PoP.
    The branch is not backhauled to a data centre, so the breakout is local to the
    region — but it **is** inspected [7].
  - *Egress on the site's own WAN link* (**Bypass**): traffic leaves the Socket
    directly, never enters Cato, and is **not inspected** [8].
  - Two further variants complete the set: **Backhaul** moves the Internet egress
    point to another Socket site, and **Off-cloud** keeps site-to-site traffic on the
    public Internet [6].
- **Bypass mechanics to confirm before promising it** [8]: the policy is
  **account-level** and applies to all Socket sites; it matches predefined
  applications, FQDNs/domains, or custom applications plus site/source/destination/
  service; the Socket chooses the WAN port from its own per-second link score unless a
  **Preferred Socket Port** is pinned; bypassed traffic is **excluded from the
  bandwidth licence**; it requires **every** Socket and vSocket site to run
  **v26.0.23517+**; and the default flow timeout is **60 s**, with a WebUI-customised
  value reverting to 60 s after a reboot.
- **Bandwidth Management Profiles** guarantee bandwidth per traffic class. The
  vendor's stated rationale is that ISP policing/shaping cannot be relied on to
  discard the right packets under congestion, so the SD-WAN layer must [6].

## Operating model

### Traffic flow between sites

Three distinct paths exist. **Only one of them is the default**, and it is not
direct.

#### 1. Via the Cato Cloud — the default for all site-to-site traffic

1. Source host sends to Socket A's LAN range (native, VLAN, or routed) [9], [10].
2. Socket A evaluates the Network Rules policy. Simple rules are evaluated on the
   Socket; rules containing applications, app categories, services, custom apps,
   or domain/FQDN objects are "complex" and must be sent to the PoP for the Socket
   to identify the correct rule (this is what enables TCP proxy) [11].
3. Socket A encapsulates the packet in a **DTLS** tunnel to its PoP — chosen by
   steering, not by the administrator [6].
4. The PoP applies the security stack, and the **WAN Firewall** enforces what is
   allowed between sites. The WAN Firewall is a *PoP* function, not a Socket
   function — see §Where enforcement happens.
5. Traffic crosses the **Cato backbone** between PoPs [4].
6. The far PoP sends it down its DTLS tunnel to Socket B, which forwards to the
   destination host [2].

**Consequences to state plainly in a design:** every inter-site flow is inspected,
QoS-managed, and TCP-accelerated, and its latency is *last mile A + backbone +
last mile B*. Cato's own documentation is explicit that by design **all** WAN
traffic — "both site-to-site and inter-VLAN traffic" — goes to the PoP [10]. Same
campus, two VLANs, no WAN involved: still hairpinned to the PoP unless Local
Routing / LAN Firewall policy says otherwise, and then it is no longer inspected
[12].

#### 2. Off-cloud — direct Socket-to-Socket, opt-in

- Configured **per network rule** as the primary transport; Sockets form a **full
  mesh** with each other and send the traffic as **DTLS over the public
  Internet** [11].
- **Not inspected** by the threat-protection engines, and TCP acceleration must be
  disabled for these rules [11].
- **Excluded from the bandwidth license**, but it shares the link's throughput
  ceiling with WAN and bypass traffic [11].
- Limits: **max 3 links** per Socket for off-cloud; **no two sites behind the same
  ISP router** (each site needs a unique public IP); **Alt-WAN cannot be the
  secondary transport** for off-cloud; **FTP passive mode is not supported**;
  complex rules silently fall back to the PoP [11].
- Typical legitimate use: bulk replication/backup between sites in the same region
  where inspection adds nothing [11].

#### 3. WAN Recovery — direct, automatic, outage-only

- **Full mesh DTLS between every pair of Sockets, enabled by default**, with
  keepalives and pre-established tunnels to shorten recovery [13].
- Used when a site **cannot reach the Cato Cloud**; the Socket switches WAN traffic
  onto the direct tunnels and back when the PoP is reachable again [13].
- For large accounts Cato recommends moving from full mesh to **hub & spoke**, to
  cut tunnel and probe count and CPU load [13].
- China Socket sites support off-cloud direct tunnels for intra-China traffic and
  business continuity [13].

Practical reading: **site-to-site traffic is PoP-routed by default; "direct" is
either an explicit per-rule decision (off-cloud) or an outage fallback (WAN
Recovery).** If a customer expects branch-to-branch traffic to stay off the vendor
cloud for cost or privacy reasons, that is an off-cloud design decision with an
inspection consequence — not a default.

### Off-cloud scaling: full mesh by default, hub & spoke at scale

- **The mesh exists even if you never use off-cloud transport.** By default every
  Socket site (except those in China) forms a **full mesh of off-cloud tunnels** for
  WAN Recovery, continuously exchanging reachability probes with every other site
  [14].
- **Consequence for a headquarters/DC Socket:** under full mesh it holds a tunnel to
  *every* branch, so its tunnel count, state table, probe bandwidth and CPU scale
  with **branch count**. In-cloud traffic does not behave this way — all branches are
  multiplexed down one Socket-to-PoP tunnel, so WAN-link count at the hub is
  independent of branch count.
- **Cato's published scale guidance is qualitative, not numeric.** Full mesh is
  described as "suitable for small and medium deployments"; accounts with "hundreds
  or thousands of Socket sites" are advised to move to **hub & spoke**, citing high
  CPU on Sockets (the **X1500** is named explicitly) and bandwidth consumed by
  reachability probes, "especially problematic for sites with limited bandwidth or
  cellular links" [14].
- **Hub & spoke semantics:** hub sites connect to all hubs and spokes; spokes connect
  only to hubs, and spoke routes are not advertised to other spokes. Off-cloud WAN
  Recovery then works **spoke↔hub but not spoke↔spoke** [14].
- **The change is vendor-side:** request it through the Cato account representative;
  Cato applies it in a pre-arranged maintenance window, in phases, and can roll the
  account back to full mesh [14].
- **Hard caps that *are* published:** max **3 links** per Socket for off-cloud
  traffic [15], and site-level HA supports up to **4 tunnels** with recovery
  mechanisms [1]. No maximum site count per hub, and no maximum tunnel count per
  Socket, is published — treat hub sizing as a vendor-confirmed figure.

### Link selection and SLA

- The Socket and the connected PoP operate as one SD-WAN fabric: the Socket
  measures latency, packet loss, jitter, and congestion per WAN link, and the
  PoP validates those measurements against its own backbone-side telemetry
  before acting — dual validation exists specifically to suppress false
  positives from localized anomalies [4].
- Every link gets a **dynamic score updated every few seconds**; paths adjust
  automatically, and **failover requires a minimum number of threshold
  violations** to prevent flapping. Metric weighting favours latency/jitter for
  real-time traffic and packet loss for bulk flows [4].
- **Redundancy is expressed as three deployment types**, and which one is in use
  is a design decision rather than a default [4]:
  - **Active/active** — traffic balanced across both active WAN links on
    real-time scoring; SLA thresholds customizable per account or per site.
  - **Active/passive** — one link carries traffic; the standby is activated when
    performance falls below SLA. Default behaviour is vendor **Smart SLA**, which
    samples every few seconds, aggregates into moving averages, uses synthetic
    probes when there is no user traffic, and is per-site customizable.
  - **Active/passive with last-resort** — a third link (typically cellular) held
    for severe outages; minimal data is sent while passive, and it activates only
    when both active and passive links are unavailable or out of SLA.
- Note the asymmetry: on failover the passive link must initialize, so a brief
  disruption is expected, and recovery back to the primary is automatic [4].
- **XOps** adds an AI-driven operations layer: the Site Operations engine detects
  link instability, BGP disconnects, and site outages, correlates them into
  "stories" on the Stories Workbench, links each to playbooks, and closes them
  automatically after resolution [4].
- Telemetry paths: CMA dashboards (Network > Sites, Site > Network Analytics,
  Sites Overview, Network Overview) plus the **Cato API** — `accountMetrics` for
  historical site↔backbone SLA and `socketPortMetrics` for real-time per-interface
  and per-transport performance — and webhooks for SIEM/collaboration alerts [4].

### Link capacity: how many links a site can have

- Each WAN interface can connect to a **different ISP**, or to **MPLS over the last
  mile** [16].
- Link roles come from **precedence**: same precedence = **active/active** load
  sharing; different precedence = **active/passive**; and Cato documents "**more
  than two links**" as a deployment using two or more precedence levels, with
  **precedence 3 = Last Resort** (typically cellular) to minimise data use [16].
- Active links are treated as one **Multi-Tunnel** — a logical tunnel holding the
  flow state — with flows pinned by **5-tuple stickiness**, so a link failure moves
  flows without breaking them [16].
- Documented ceilings:
  - Site level: Socket/vSocket HA supports **up to 4 tunnels** with recovery
    mechanisms; IPsec sites up to 3 [1].
  - Off-cloud traffic: **max 3 links** per Socket [11].
  - Practical ceiling is the **number of WAN ports on the model**, which varies by
    model and add-on NIC (see §Edge devices and the data sheets in [17]).
- Throughput is shared, not additive: the documented **X1500 maximum is 500 Mbps**,
  and that ceiling covers WAN + off-cloud + bypass combined on the link [11].

- **Per-model ceilings are published, but not as one number.** *Cato Cloud
  Thresholds and Limits* gives an app-mix-dependent table for each Socket model,
  measured at 1,450-byte (LAN) and 1,300-byte (Internet) packets [18]:

  | Model | LAN FW L4 | LAN FW L7 | LAN Threat Prevention | Internet |
  |---|---|---|---|---|
  | X1500A | 960 Mbps | 625 Mbps | 625 Mbps | 435 Mbps |
  | X1500B | 2.0 Gbps | 2.0 Gbps | 1.9 Gbps | 1.5 Gbps |
  | X1500C | 2.0 Gbps | 2.0 Gbps | 2.0 Gbps | 2.0 Gbps |
  | X1600 | 7.87 Gbps | 7.87 Gbps | 3.1 Gbps | 1.88 Gbps |
  | X1700A | 8.5 Gbps | 8.1 Gbps | 8.1 Gbps | 5.33 Gbps |
  | X1700B | 12.4 Gbps | 11.2 Gbps | 10.7 Gbps | 10.2 Gbps |
  | X1700C | 15.4 Gbps | 15.4 Gbps | 15.35 Gbps | 20.0 Gbps |

- **Read that table as inspection-scenario capacity, not "the tunnel speed".** Cato
  separately states site throughput of **up to 10 Gbps for WAN and Internet links** on
  the **X1700B** and Cloud Interconnect — and the X1700C Internet figure of 20 Gbps
  exceeds that sentence, so quote the model row, not the headline [18].
- **vSockets and non-Socket sites** [18]: Azure 1 Gbps on 2 NIC / up to 2 Gbps on
  3 NIC with accelerated networking; GCP up to 2 Gbps; AWS and VMware ESXi
  instance-dependent; IPsec IKEv1/IKEv2 up to 3 Gbps; Cloud Interconnect up to
  10 Gbps.
- **The X1500 "500 Mbps" figure** used elsewhere in Cato's documentation is the
  bandwidth-licence example in the off-cloud article, not this table's measured
  ceiling — don't mix the two in a sizing discussion [15], [18].

## Capabilities by domain

### Site connectivity options

Cato documents three ways to attach a site, and the differences are functional,
not just throughput [1]:

| Criterion | Socket / vSocket | IPsec (third-party appliance) | Cloud Interconnect |
|---|---|---|---|
| Tunnel | DTLS encrypted overlay | IPsec encrypted overlay | Private link, **no encryption** |
| Performance ceiling | Up to 10 Gbps | Up to 3 Gbps | Up to 10 Gbps |
| Analytics | Full monitoring and visibility | **Partial — e.g. no packet-loss visibility** | Partial — no packet-loss visibility |
| QoS | **Upstream and downstream** | **Downstream only** | Downstream only |
| HA | Full — up to 4 tunnels, plus recovery mechanisms | Up to 3 tunnels | Active/passive, 2 links |

Only a Socket/vSocket gets upstream QoS and packet-loss telemetry. IPsec sites
are the classic false economy: cheap to stand up during a migration, and the
missing telemetry never comes back at those sites [1].

### Routing and protocols

#### Routing

- **Static routing and BGP are the documented L3 mechanisms** — there is no IGP
  peer relationship with the Socket. Dynamic routing is **eBGP only**: the Socket
  exchanges routes with routers on its LAN, VLAN, and native ranges, and with
  routers reachable inside IPsec tunnels [3], [19].
- BGP facts that change designs [3], [19]:
  - ASNs must be **private (64,512–65,534)**; Cato's default account ASN is
    **64,515**, and the neighbor must use a different ASN (eBGP only).
  - **No graceful restart**, and route changes initiated by Cato generate no
    events — plan maintenance windows and monitoring accordingly.
  - Defaults: **hold time 60 s, keep-alive 20 s, metric 100**. A hold time of 1–2
    is invalid; mismatched timers negotiate down to the smaller value.
  - **BGP MD5 authentication** (RFC 2385) is supported [19].
  - Per-neighbor advertisement choices: default route (0/0) when the Socket is the
    router's Internet gateway, all account routes, or summary routes. **Hide SNAT**
    can be applied so BGP traffic is translated to the LAN IP.
  - Sessions run over **direct, VLAN, or native ranges**; over routed ranges only
    if every range shares the BGP peer's next hop.
- **No OSPF, IS-IS, or EIGRP support is documented** — a search of the KB document
  index returns no hits for these protocols. Treat the Socket as a static/BGP edge
  speaker, not an IGP neighbor; if a design depends on OSPF adjacency with the
  Socket, get vendor confirmation in writing before relying on it.

#### WAN access

- **PPPoE** is supported per WAN link, configured in the Socket WebUI (account,
  secret, optional service name, static IP, DNS, MTU, VLAN tag); with PPPoE
  selected, the configured DNS fields are ignored [20].
- **WAN VLAN tagging** is supported through a configured VLAN tag per WAN
  interface [20], [21].
- **IPv6-only ISPs** are supported via IPv4-over-IPv6 in three forms — **IPIP6
  Static**, **IPIP6 Auto** (SLAAC or DHCPv6-PD), and **DS-Lite**. Requires
  **Socket v26.0.23517+** and vendor enablement [21]. IPv6 is *transport only*:
  IPv4 is encapsulated to an ISP AFTR/Border Relay and MTU is reduced for the
  headers; the Cato overlay itself stays IPv4 [3], [21].

#### LAN

- **802.1Q VLANs**: the Socket tags packets with the configured VID; any L2 switch
  that supports VLAN tagging works (no L3 switch needed); VIDs must match at both
  ends; a native range bound to a VLAN **drops untagged traffic and traffic with a
  different VID** [9].
- **DHCP**: per native range and per VLAN range, the Socket can use the **account
  default**, a **DHCP Range** (Cato's own DHCP server, with reservations using
  infinite leases), or a **DHCP relay group** to external servers. A relay group
  can hold up to **three** servers and the Socket relays a request to all of them;
  the relay option requires X1500/X1600/X1700 or ESX vSockets at the minimum
  Socket version [22].
- **Local routing** lets the Socket route between local ranges/hosts without
  sending traffic to the Cato Cloud. Under *legacy* Local Routing, locally routed
  traffic is **not inspected and WAN Firewall rules do not apply**; dynamic-PAT NAT
  is configurable inside local routing rules from Socket v13.0 [12]. Cato positions
  the **Next-Gen LAN Firewall** as the successor, and that policy **does** enforce
  on the Socket — L2–L4 by default, L7 where enabled per site (see §Where
  enforcement happens). Do not describe LAN-routed traffic as "uninspected"
  without naming which of the two mechanisms is in use.

### Security enforcement

The three firewall policies are **not in the same place**. This is the distinction
that decides what you lose when traffic stops touching a PoP [7].

| Policy | Enforced on | Traffic it covers |
|---|---|---|
| **WAN Firewall** | **Cato Cloud PoP** | Site-to-site and user-to-site traffic *destined to another Cato Cloud destination* |
| **Internet Firewall** | **Cato Cloud PoP** | Outbound Internet traffic |
| **Next-Gen LAN Firewall** | **Socket** | Traffic where **both** source and destination belong to the same Socket site |

- Cato's PoPs are the **FWaaS enforcement point**: the security stack inspects WAN
  and Internet traffic at the network edge, single-pass (SPACE), alongside the
  IPS/SAM, App Control, TLS-inspection, DLP and anti-malware engines [7].
- The **WAN Firewall** is "part of the Next Gen Firewall (NGFW) that is integrated
  into the Cato Cloud". It is a **whitelist** firewall with a **default ANY-ANY
  block** as the last rule, ordered evaluation, and L7 with user awareness [23].
- The **LAN Firewall runs on the Socket** — that is what lets it segment east-west
  traffic locally: both source and destination belong to the same Socket site, the
  traffic "remains local and isn't sent to the PoP" [7]. L2–L4 by default with L7
  enabled per site, account-level policy with sub-policies/RBAC, Socket v22+ [24].
- **Transport** is a separate decision made by **Network Rules** (the networking
  engine, in the PoP for complex rules), which selects Cato Cloud, Off-cloud, or
  Bypass [15].

## Security and trust

### What bypasses inspection

The enforcement points above do not cover every path; this is the consequence for
the transports that leave them behind.

- **Bypass is stated explicitly:** "Traffic that matches a Bypass policy rule is
  not enforced by Cato firewall policies. Since bypassed traffic is not sent to the
  Cato Cloud, **Internet Firewall and WAN Firewall rules are not applied to it**."
  The Socket still applies bandwidth profiles and QoS upstream; downstream QoS is
  lost because the PoPs are bypassed [8].
- **Off-cloud is the same architectural situation.** The traffic goes
  Socket→Socket over the Internet and never reaches a PoP, and Cato states it is
  "not inspected by the Cato Threat Protection engines" [11]. Because the WAN
  Firewall is a PoP function [7], it cannot evaluate off-cloud flows either — the
  vendor's most explicit wording for that consequence appears on the Bypass page
  [8].
- **What still applies to off-cloud:** the Network Rule that selected the transport
  (plus its secondary-transport choice), DTLS encryption in transit, and
  Socket-side QoS/bandwidth priority [11]. **What you lose:** WAN Firewall policy,
  IPS/SAM, App Control, TLS inspection, DLP, anti-malware — the entire PoP engine
  list [7], [15].
- **So yes:** PoP-based security is unavailable in off-cloud mode. Off-cloud is an
  inspection bypass with a routing label. Use it only where the traffic genuinely
  does not need inspection, and record the exception.
- **Intra-site traffic is the exception that is *not* a gap:** traffic routed
  locally under the Next-Gen LAN Firewall still gets enforced — by the Socket
  (L2–L4 minimum, L7 if enabled), not by the PoP. Only legacy Local Routing left it
  unenforced [12], [24].

### Data plane protection and residency

- **Encryption scope.** Socket-to-PoP tunnels are DTLS; site-to-site traffic is
  decrypted and re-encrypted at the PoPs, so the tunnel is *not* end-to-end between
  branches — a fact that matters when a customer assumes otherwise [1], [2].
- **Address family.** The Cato Cloud overlay and all site addressing are **IPv4**;
  IPv6 appears only as an *access* transport for IPv6-only ISPs (IPIP6, DS-Lite)
  [3], [21].
- **Regulatory data.** Data-residency requirements must be written into the
  contract; PoP selection is algorithmic rather than customer-pinned, so residency
  cannot be inferred from topology.

## Integration and interoperability

- **Third-party attachments.** IPsec is the interoperability path: existing
  firewalls and routers can terminate into a PoP, at the cost of upstream QoS and
  packet-loss telemetry [1]. Cloud Interconnect is a private link with **no
  encryption** [1].
- **Routing interoperability.** The Socket speaks static and **eBGP only** — no
  OSPF, IS-IS, or EIGRP is documented — so an OSPF estate must peer via BGP or
  convert to static/routed ranges [3], [19].
- **Telemetry and automation.** GraphQL APIs (`accountMetrics`, `socketPortMetrics`)
  and webhooks into SIEM/collaboration tooling [4]; policy is authored centrally in
  the CMA and distributed to PoPs and Sockets without local configuration [2].

## Deployment and hosting

### Site topology: what sits in front of and behind the Socket

Three separate questions get conflated here; keep them apart.

1. **Between the Socket and the ISP (WAN side).** Cato's *default* HA deployment
   places **routers between the Socket and the ISP**, and documents that a
   no-router deployment (Socket straight to the PoP) is a customization requiring
   Cato engagement [25]. In practice the Socket's WAN ports connect to an ISP CPE
   or a switch stack and take a DHCP or static address — optionally VLAN-tagged or
   over PPPoE [20], [21].
2. **Between the Socket and the LAN (site side).** No router is required. The
   typical topology is the Socket **replacing the site's existing firewall**, with
   the Socket as L3 gateway and per-VLAN DHCP [26], [10].
3. **If an internal L3 device must stay.** The site can keep its L3 core and give
   the Socket **routed ranges** (static routes toward the internal L3 switch)
   instead of VLAN interfaces. Cato's stated best practice is **VLANs on the
   Socket** for new designs when firewall-as-a-service is the goal, and **routed
   ranges** where the internal switch owns the routing domain [10].

Design consequences to carry into the proposal:

- **All traffic goes to the PoP by default — including inter-VLAN traffic inside
  the same office.** Cato states this explicitly; keeping inter-VLAN traffic local
  requires Local Routing / LAN Firewall policy, and that traffic then loses L7
  inspection [12], [10].
- **A NAT device in front of the Socket is the risk case**, because multi-WAN
  links bind to one logical tunnel via the DTLS source port (see §Deployment
  prerequisites and known limitations).
- **HA mechanics**: active/standby; the standby listens for keepalives on an
  interface designated **LAN & VRRP** or **VRRP**; failover occurs after **three
  seconds** of missed keepalives; the new master sends a **GARP** to speed L2
  convergence; the primary **preempts** back on recovery. A split-brain shows both
  Sockets as Master with keepalive Failed and site HA **NOT READY**. Both Sockets
  must be the same model/type (X1600 + X1700 is not supported), and HA is supported
  for physical sites plus AWS and Azure vSockets [25].

### Prerequisites and known limitations

These are the items that sink cutover dates, so verify them during site survey
rather than at turn-up [27]:

- **Firewall/DNS prerequisites**: outbound **UDP 53, 443, 1337** and **TCP 53,
  443**; resolution of `vpn.catonetworks.net`, the `cc2.*` controllers,
  `steering.catonetworks.com` (and, on firmware v11.x and earlier,
  `c-me.catonetworks.net` / `d-me.catonetworks.net`); **TLS inspection and
  security checks disabled for the Socket IP**; **ICMP permitted** (used for
  last-mile monitoring); NTP for time synchronization [27].
- **NAT can break multi-WAN aggregation.** For a Socket with multiple WAN links,
  a NAT device between Socket and PoP may prevent one or more links from
  connecting. The PoP uses the **source port of each incoming DTLS connection** to
  bind each WAN link to the same logical tunnel, and a NAT device that rewrites
  the source port breaks that binding — surfacing as connectivity problems and an
  HA status of **"Not Ready"** [27].
- **Hardware reliability** (vendor-published): MTBF X1500 ≈ 808,959 h, X1600 ≈
  143,940 h, X1700 ≈ 157,565 h; RMA rate below 0.5% [27].
- **X1700 physical constraints** [26]: **port 1 must be copper RJ45** to establish
  the tunnel to the PoP — fiber-only connectivity is not supported. Only one
  network-card add-on at a time; X1700B/C accept a second 4×10 Gbps fiber card
  (eight 10G fiber ports total), and X1700C supports 2×100 Gbps fiber cards (four
  100G fiber ports total). A newly shipped Socket arrives with the NIC add-on
  uninstalled and must be booted before the add-on is fitted.
- **Licensed bandwidth is a configuration input, not just a commercial one**: WAN
  interface bandwidth in the CMA is set according to the ISP bandwidth *and* the
  license purchased from Cato [26]. Sizing the circuit without sizing the license
  produces a site the platform will not shape correctly.
- **X1600 LTE specifics** [27]: no automatic failover between SIM cards (manual
  only); not supported for sites in China; cannot ping the Local IP of another
  Socket site's native range.
- **Ping behaviour differs by model and source**, which misleads acceptance
  testing: from behind a Socket, only the gateway IP of the source subnet replies;
  from a remote Client, only the native range's local IP replies; for Azure
  vSockets in HA, the floating IP answers all pings [27].

### High availability and software upgrades

- **Two Sockets per site — active/standby only.** Cato's wording is unambiguous: "The
  Sockets operate in HA Active/Standby mode… **Only the Socket with the HA Master
  status handles the traffic**" [25]. There is **no device-level active/active mode**;
  Cato's "active/active" refers to *links inside one Socket*, not to a pair of
  Sockets [16]. Two Sockets therefore buy **availability, not throughput** — aggregate
  site bandwidth still comes from one chassis plus the licence.
- **Vendor-managed upgrades are sequenced around HA** [28]:
  - The **primary upgrades first**; the secondary is upgraded **only after** the
    primary is confirmed stable, and the pair completes **within the maintenance
    window**.
  - For HA sites, only the **primary** joins the initial five-Socket canary group.
  - A Socket that fails to upgrade **rolls back automatically**, and the rollout stops
    for that time zone if a connectivity or stability issue is detected.
  - If the primary hits a critical issue mid-upgrade, the **secondary becomes active
    and does not upgrade** — leaving the pair on different versions.
- **The two published figures measure different things — device downtime vs. service
  impact.** Each Socket takes about **17 minutes** (download, verify, install, fast
  switch, stability check), and Cato puts *service* impact at "**at most a few
  seconds**" during the fast switch [28]. The maintenance-window article's "**can
  result in a few minutes of downtime**" describes the **upgraded device itself**
  being out of service [29], not a few minutes of site-wide outage. Read together:
  the box is busy for minutes, the user-visible interruption is the switch.
- **Whether that becomes site downtime depends on having a peer Socket.** With HA, the
  standby carries traffic while the primary is being upgraded (and the primary carries
  it while the secondary is), so the device's minutes are absorbed and the site sees
  the seconds-long switch. **A single-Socket site has no peer — there the device's
  downtime *is* the site's downtime**, so the conservative "few minutes" figure applies.
  This is the real argument for the HA pair in an upgrade-sensitive design.
- **The window is customer-configurable**: Account > Maintenance Window, applied in
  each site's **local time zone**, with a **48-hour buffer** before the window — a
  release that lands inside that buffer waits for the following week [29].
- **Version skew breaks HA readiness.** If the pair runs different **major** versions,
  site HA status is **Not Ready**; failover still happens, but features added in the
  newer version are missing while the older Socket is active [25], [28].
- **Do not use manual HA failover for maintenance.** Cato states it plainly: "Do not
  use the manual HA failover to perform Socket maintenance — this can create a
  split-brain issue" [30]. The feature (Socket v24+, HA state Ready) exists for
  validation: it takes ~120 s, reports both Sockets as Master with status "Not Ready
  (In HA Failover)", and is reverted from the CMA or by restarting the primary [30].

### Hardware ownership and refresh

**The customer — title transfers on delivery.** The Socket is paid for over the
contract term, but it is not leased in the ownership sense [31]:

- "**Ownership of Cato Socket hardware transfers upon its delivery**," while the
  Socket "operates as an integral component of Cato's subscription-based service"
  — Cato manages the supported hardware lifecycle, including refreshes and
  end-of-support [31].
- **Refreshes are free to the customer**: refreshed Sockets are provided "at no
  additional charge, including shipping", in connection with the existing
  subscription — though Cato notes subscription fees may still change over time
  under market conditions [31].
- **Cato controls the lifecycle calendar**: hardware needing refresh is identified
  at least **90 days** before the Refresh Start Date (usually aligned to renewal);
  the refresh window is **at least 12 months**; EOS is typically announced about
  **four years** ahead; and Cato generally supports a model for **at least seven,
  often up to ten, years** from start of service [31].
- **The customer's obligation is physical**: replacing and installing the Socket at
  the site is the customer's responsibility; Cato initiates the refresh and ships
  the unit. During the refresh window Cato will not ship an old model to replace a
  defective one — the customer must move to the new hardware [31].
- **After replacement** the old Socket stays available for **rollback for 14 days**,
  is then deactivated, and "**You can dispose of the Socket**" [32] — the clearest
  practical confirmation that the asset belongs to the customer.
- Past EOS, Cato will not proactively disconnect a Socket, but provides no
  troubleshooting, replacement, repair, or software/security updates, and
  continues-operation is explicitly a security risk [31]. RMA is always fulfilled
  with the **latest active model**, never an EOS one [31].

**Contract caveat:** the above is a knowledge-base *policy* statement. Title, risk
of loss, and return/disposal obligations are governed by the **MSA and order
form** — confirm there before a procurement decision, and treat the KB policy as
the operational interpretation rather than the contract itself.

### Authoritative sources

- The Cato Knowledge Base on **`knowledge.catonetworks.com`** is the current
  platform; `support.catonetworks.com` stopped being updated for all articles after
  **2026-08-09** [17]. Cite the new platform and re-verify anything read from the old
  one.
- Marketing pages on `catonetworks.com` were unreachable from this environment
  (HTTP 403 / Incapsula), so no claim here rests on them.

## Commercial model

Cato does not publish list prices. The knowledge base documents the **licensing
dimensions** — what is metered and how — while actual pricing lives in the
commercial agreement. Two account models exist, and they behave very differently
[33]:

| | Enforcement Model | Bursting Model |
|---|---|---|
| Which accounts | All accounts until Jan 2027; existing accounts keep their assigned model | New accounts and renewals **from Jan 2027** (Jul 2026 – Jan 2027 could pick either) |
| Site bandwidth | You **define** licensed bandwidth per site | Bandwidth **measured by usage**, compared to a pool |
| Remote users | A ZTNA license **per user** | Measured by usage |

### Enforcement Model (accounts up to and including 2026)

- Bandwidth is licensed **per site** as a fixed **Site license** [34], or drawn from a
  regional **Pooled** license. Both cap the site's **upstream and downstream**
  traffic over the Cato Cloud.
- Sizing rule: the license must match the **higher** of the summed download and the
  summed upload across all active links. A 500 Mbps license means 500 Mbps down
  *and* 500 Mbps up — not 250+250.
- Two site license types: **SASE** (all networking and security features; mandatory
  for Socket/vSocket sites) and **SSE** (security only, no SD-WAN; IPsec sites only).
- Licenses are scoped to **License Groups** (Group 1, Group 2, and stand-alone
  China / Vietnam / Morocco). Capacity cannot move between groups, and pooled
  licenses are not supported in China or Vietnam.
- **Unlicensed sites pass no traffic**, and up to 1,000 unlicensed sites may exist.

### Bursting Model (accounts from 2027)

- Structured in layers: **Base Products** (Bandwidth Pool, ZTNA User) [35] →
  **Premium Security** (Threat Prevention, Advanced TP, Agentic TP, CASB/DLP…) →
  **Insights** → **Services**.
- **Bandwidth Pool** is licensed in **Mbps per region group** and covers Socket,
  vSocket, IPsec, App Connector and Cloud Interconnect; **Socket sites include the
  LAN Firewall service** in the pool licence [36].
- Measurement is **monthly P95 per region group**, and each sample takes the
  **higher of the two directions** — 7 Mbps up with 9 Mbps down measures as 9, not
  16.
- **Socket and IPsec sites in Group 1/Group 2 are *not* bandwidth-enforced per site
  by default**: they can use full last-mile capacity, with aggregate usage measured
  against the pool (per-site enforcement optional). **Cloud Interconnect** is
  fixed-enforcement. **Stand-alone countries** enforce configured per-site capacity.
- Premium Security and Insights are sized **off the Bandwidth Pool / ZTNA capacity
  and "must cover the total licensed capacity"** — so raising bandwidth obliges
  raising the security licences too.

### Is there an extra fee for in-cloud (site-to-site) traffic?

**No per-gigabyte or per-flow charge.** Cato prices **bandwidth capacity**, not
traffic volume, and site-to-site traffic simply consumes that capacity:

- Under Enforcement, inter-site traffic is WAN traffic over the Cato Cloud and is
  capped by the site's licensed bandwidth; there is no separate itemised charge for
  it [34].
- Under Bursting, inter-site traffic contributes to the pool's P95 measurement;
  again no per-GB line item [37].
- **The cost risk sits at the capacity boundary, not in the traffic itself.** If
  measured usage exceeds licensed capacity it becomes **over-usage**, resolved by
  **True-Up** (one-time charge for the over-used month) or **True-Forward** (raise
  capacity for the remainder of the term) — and Premium Security and Insights must
  be increased to match [38].
- **Off-cloud and bypass traffic are excluded from the bandwidth licence**
  [11], [8] — so shifting bulk site-to-site traffic off-cloud genuinely reduces
  licence consumption, at the cost of losing all PoP-based inspection (see §Where
  enforcement happens).
- Capacity is **not fungible across region groups**, and unused capacity cannot be
  transferred to offset over-usage [37], [38].

### Hardware and services

- **Sockets** are "purchased per device via **payments over the term** of the
  contract" — a recurring per-device charge, not a one-off [36].
- **Rack-mount kits** are a **one-time fee**; the X1700 **fiber card** is an add-on
  [36].
- **Services are licensed on different axes** and easy to omit from a quote:
  NOCaaS, ILMM and Hands-Free are **per site**; MDR follows Bandwidth Pool/ZTNA;
  CSE is **per account, monthly**; PSE and TPM are **hour-based**; Gold/Platinum
  Support are **per account relative to total subscription size** [36].

**What this means for a proposal:** recurring cost is driven by (a) Mbps of pool or
site bandwidth per region group, (b) socket count × contract term, (c) security
tier sized to the pool, and (d) optional services licensed per site or per account.
Inter-site traffic volume is *not* a billing line — but sustained peaks above the
pool are, via True-Up or True-Forward.

## Adoption and positioning

### Cross-vendor comparison

Cato should be compared on **where the middle mile comes from**, not on feature
checklists — the comparison that decides most deals is backbone vs.
bring-your-own-transport:

| | Cato (SASE tier) | Appliance-led SD-WAN (Palo Alto, Fortinet, Versa) | Telco-managed / VeloCloud-style overlay |
|---|---|---|---|
| Middle mile | Cato private backbone between PoPs [4] | Public Internet + carrier underlay | Carrier underlay, vendor orchestration |
| Site CPE | Cato Socket / vSocket (vendor-locked) [2] | Vendor NGFW or SD-WAN edge | Vendor edge, often carrier-supplied |
| Security | Same-vendor, in-PoP | Same-vendor, on the CPE | Separate SSE usually required |
| Customer control of path | Low — PoP selection is algorithmic [6] | High — customer sets hubs and policy | Medium |
| Best fit | Many sites, global spread, thin IT, converged mandate | Deep local inspection, existing vendor estate | Incumbent telco relationship |

Interop constraints worth naming in a design document:

- **SSE tier plus third-party SD-WAN** is the only supported way to keep an
  existing SD-WAN, and site connectivity is then IPsec — losing upstream QoS and
  loss telemetry [1].
- **Cloud Interconnect is unencrypted by design** (private link), so encryption,
  if required, is the customer's problem, not the tunnel's [1].
- **Bypass and off-cloud traffic is not inspected** — any claim that "all traffic
  is inspected because we have SASE" must be tested against the rule base [6].

### Design guidance

- **Pick the tier before the topology.** SASE tier means Cato owns SD-WAN and
  security; SSE tier means Cato owns only security and the customer's SD-WAN
  survives on IPsec. This single decision determines the site CPE, the telemetry
  available, and the migration plan [1].
- **Standardize on Socket sites unless there is a hard reason not to.** The
  upgrade path from IPsec to Socket is a hardware project, so IPsec-at-scale is
  usually a decision to be revisited, not a steady state [1], [2].
- **Choose the redundancy model per site role, not globally.** Active/active for
  sites with two genuine circuits and latency-sensitive traffic; active/passive
  where circuits are asymmetric; last-resort cellular where outage cost exceeds
  the data plan — noting the passive link's initialization causes a brief
  disruption on failover [4].
- **Budget for two Sockets at critical sites.** Link redundancy does not survive
  a device failure; device-level HA is a separate active/standby pair [2].
- **Treat licensed bandwidth and circuit bandwidth as one sizing exercise** [26].
- **Plan the uninspected-path inventory** (bypass/off-cloud) as a deliverable of
  the design, not an afterthought — it is the artifact security review will ask
  for [6].
- **Watch the migration clock.** Hybrid WAN is explicitly supported as a
  transitional state [6]; designs that park most traffic on MPLS "temporarily"
  tend to keep paying for both.

## Open challenges

Recorded so the next session doesn't mistake a gap for a fact:

- **Per-model throughput is now sourced, not inferred.** *Cato Cloud Thresholds and
  Limits* publishes per-model figures for LAN Firewall L4/L7, LAN Threat Prevention
  and Internet traffic (§Link capacity) [18]. Two caveats remain: that table is
  app-mix- and packet-size-dependent rather than a single "tunnel speed", and the
  separately stated "up to 10 Gbps for WAN and Internet" ceiling is exceeded by the
  X1700C Internet row — quote the model row. The per-model **data-sheet PDFs** remain
  unreachable from this environment (CDN 404 / marketing 403), so **port counts and
  power figures** still rest on the deployment guides rather than the data sheets.
- **PoP count moves.** The Production PoP Guide enumerated **91** production
  locations on 2026-10-20 (§PoP footprint) [5], while marketing says "85+"; the
  guide's CSV omits limited-availability and coming-soon locations, so neither
  figure is a ceiling. Recount from the guide rather than quoting a press release.
- **Nigeria needs the two-subnet reading, not a vendor fix.** Lagos
  (216.252.185.0/24) is a service-bearing PoP; Nigeria's 85.255.21.144/28 is a
  geo-localized range serviced through Paris [5]. The guide's "no Cato PoP there"
  sentence is stale — the two rows are not competing statements.
- **BFD for BGP neighbors is unverified.** The KB index lists an article titled
  "Configuring BFD for BGP Neighbors", but it was not read in this session — if
  the design needs sub-second BGP failure detection, confirm BFD support and its
  timers with the vendor before promising them.
- **Overlay is IPv4-only; the underlay may not be.** The BGP article lists "The
  Cato Cloud only supports IPv4" under Known Limitations [3] — still true of the
  overlay and of all site addressing. What is newer is the *access network*: Socket
  sites can ride an IPv6-only ISP via IPv4-over-IPv6 (see §Protocols and routing
  support). Do not generalize either statement into the other — an earlier version
  of this file wrongly called the IPv4-only claim stale.
- Re-verify everything above on the same `knowledge.catonetworks.com` platform —
  it replaced `support.catonetworks.com` for all articles after 2026-08-09 [17].

## Release history

Facts already cited above, in the order Cato shipped them; verify against the
current KB before relying on any version number.

| Milestone | What changed |
|---|---|
| Socket v11.x and earlier | Legacy controller domains (`c-me` / `d-me`) required for resolution [27] |
| Socket v13.0 | NAT (dynamic PAT) available inside Local Routing rules [12] |
| Socket v17.0 | BGP sessions withdraw other site ranges when the Socket disconnects, allowing an alternate next hop [3] |
| Socket v22 | Next-Gen LAN Firewall (account-level, L2–L4 default, L7 per site) [24] |
| Socket v26.0.23517 | IPv4-over-IPv6 access (IPIP6 Static/Auto, DS-Lite) and account-level Bypass policy [21], [8] |
| 2026-08-09 | Cato Knowledge Base completes its move to `knowledge.catonetworks.com` [17] |
| 2026-09-22 | Socket prerequisites article adds UDP 1337 and TCP 53 [27] |
| Jan 2027 | Bursting license model becomes the default for new accounts and renewals [33] |

## Cross-references

- [sase.md](../techniques/sase.md): the technique file holds the vendor-neutral
  convergence models; this file is the Cato instance of the backbone-native model.
- [overlay-architecture.md](../techniques/overlay-architecture.md): Cato replaces
  the edge-to-edge overlay with site-to-PoP DTLS tunnels plus vendor transport
  between PoPs.
- [sla-policies.md](../techniques/sla-policies.md): Cato's SLA mechanics (Smart
  SLA, multi-violation failover) are one implementation of app-aware routing
  policy; compare thresholds and measurement points before assuming portability.
- [dia-local-breakout.md](../techniques/dia-local-breakout.md): Bypass and
  Backhaul are Cato's DIA constructs.
- [qos.md](../techniques/qos.md): bandwidth management profiles and the
  upstream/downstream QoS asymmetry between Socket and IPsec sites.
- [mpls.md](../techniques/mpls.md): hybrid-WAN coexistence and MPLS offload.

## References

All Cato references are **changeable** and were confirmed on **2026-10-20**
against the Cato Knowledge Base on its current platform
(`knowledge.catonetworks.com`, which replaced `support.catonetworks.com` for all
articles after **2026-08-09**). Each entry names the section to re-check; if a
URL 404s, search the article title on the current platform.

1. Cato Networks, "Connecting Sites to the Cato Cloud," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/connecting-sites-to-the-cato-cloud
   Verify: "Cato SASE vs SSE Services" and "Overview of Site Types" (the
   capability table: tunnel type, performance, analytics, QoS, HA).
2. Cato Networks, "What are Cato Sockets," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/what-are-cato-sockets
   Verify: "Socket Models and Versions," "Connectivity," "Cloud and SaaS
   Performance," "Socket Next Gen LAN Firewall," "High Availability."
3. Cato Networks, "Using BGP in the Cato Cloud," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/using-bgp-in-the-cato-cloud
   Verify: "Cato's BGP Components," the eBGP/ASN rules, "Known Limitations"
   (IPv4-only, no graceful restart) — and re-check whether OSPF/IS-IS support has
   been added.
4. Cato Networks, "Cato Socket Link SLA Architecture," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/cato-socket-link-sla-architecture
   Verify: "Behavior by Site Deployment Type," "Link SLA Operation and
   Architecture," "Monitoring Link Performance."
5. Cato Networks, "Production PoP Guide," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/production-pop-guide
   Verify: the per-region PoP-location table and Cato-owned IP ranges (needed for
   firewall allow-lists); this is the authoritative current PoP inventory.
6. Cato Networks, "What is Cato SD-WAN," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/what-is-cato-sd-wan
   Verify: "Secure Overlay," "Steering," "Network Rules"
   (bypass/backhaul/off-cloud), "Migrating to Cato SD-WAN."
7. Cato Networks, "What is the Cato Firewall," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/what-is-the-cato-firewall
    Verify: the three-policy table (WAN / Internet / LAN, enforcement point and how
    traffic is processed) and the statement that PoPs are the FWaaS enforcement
    point.
8. Cato Networks, "Bypassing the Cato Cloud (Account Level Policy)," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/bypassing-the-cato-cloud-account-level-policy
    Verify: "Internet Firewall and WAN Firewall rules are not applied" to bypassed
    traffic, the upstream-only QoS statement, the bandwidth-license exclusion, and
    the Socket v26.0.23517+ prerequisite.

9. Cato Networks, "Connecting a Socket to a Switch with VLANs (802.1q)," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/connecting-a-socket-to-a-switch-with-vlans-802-1q
    Verify: VID matching, the drop behaviour for untagged/mismatched traffic, and
    the DHCP range option on a VLAN-tagged native range.
10. Cato Networks, "Socket Best Practice: VLANs vs. Routed Ranges," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/socket-best-practice-vlans-vs-routed-ranges
    Verify: the two supported models (VLAN interfaces vs. routed ranges/static
    routes), the VLAN-first best practice, and the statement that inter-VLAN
    traffic goes to the PoP by default unless local routing is used.

11. Cato Networks, "Routing Traffic to an Off-Cloud Link," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/routing-traffic-to-an-off-cloud-link
    Verify: the off-cloud overview, "Known Limitations" (max 3 links, unique public
    IP per site, Alt-WAN not supported as secondary, FTP passive unsupported), the
    bandwidth-license exclusion and the X1500 500 Mbps example, and the complex-rule
    fallback note.
12. Cato Networks, "Local Routing at the Socket," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/local-routing-at-the-socket
    Verify: the "not inspected / WAN Firewall not applied" statement, the
    v13.0+ requirement for local-routing NAT, and the note that the LAN Firewall
    replaces Local Routing for many customers.
13. Cato Networks, "Socket Site Resiliency with WAN Recovery," *Cato Knowledge
    Base*.
    https://knowledge.catonetworks.com/docs/socket-site-resiliency-with-wan-recovery
    Verify: the full-mesh default and keepalives, the hub & spoke recommendation for
    large accounts, and the China site behaviour.
14. Cato Networks, "Hub & Spoke Off-Cloud Topology for WAN Recovery," *Cato Knowledge
    Base*.
    https://knowledge.catonetworks.com/docs/hub-spoke-off-cloud-topology-for-wan-recovery
    Verify: the default full mesh (except China), the "small and medium deployments"
    vs. "hundreds or thousands of Socket sites" guidance, the X1500 CPU warning, the
    hub/spoke advertisement rules, the loss of spoke↔spoke recovery, and the
    vendor-applied change plus rollback process.
15. Cato Networks, "Understanding Packet Flow with Cato SPACE Architecture," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/understanding-packet-flow-with-cato-space-architecture
    Verify: the list of PoP engines (firewall, network rules/QoS, IPS/SAM, App
    Control, TLS inspection, DLP, anti-malware) and where each phase is evaluated.
16. Cato Networks, "Part 1: The Socket Interfaces and Precedence," *Cato Knowledge
    Base*.
    https://knowledge.catonetworks.com/docs/part-1-the-socket-interfaces-and-precedence
    Verify: the active/active vs. active/passive vs. "more than two links"
    deployment definitions, precedence numbering (1 active, 2 passive, 3 last
    resort), and the Multi-Tunnel / 5-tuple flow-stickiness behaviour.

17. Cato Networks, "Cato Socket Deployment Guides and Data Sheets," *Cato
   Knowledge Base*.
   https://knowledge.catonetworks.com/docs/cato-socket-deployment-guides-and-data-sheets
   Verify: the links to the **X1500, X1600, and X1700 data sheets** — the only
   authoritative source for per-model throughput, port counts, and power. Page
   updated 2026-10-19. If the PDFs are unreachable, request them from the vendor
   rather than quoting reseller figures.
18. Cato Networks, "Cato Cloud Thresholds and Limits," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/cato-cloud-thresholds-and-limits
    Verify: "Supported Throughput for Cato Sites" (the per-model LAN FW L4/L7, LAN
    Threat Prevention and Internet table measured at 1,450/1,300-byte packets), the
    "up to 10 Gbps on X1700B and Cloud Interconnect" statement, the vSocket figures,
    and the IPsec 3 Gbps ceiling. Note the X1700C Internet row (20 Gbps) exceeds the
    10 Gbps sentence — quote the model row.
19. Cato Networks, "Configuring BGP Neighbors for a Cato Socket," *Cato Knowledge
    Base*. https://knowledge.catonetworks.com/docs/configuring-bgp-neighbors-for-a-cato-socket
    Verify: "Advanced BGP Settings" (metric/hold time/keep-alive defaults), MD5
    auth (RFC 2385), advertise/accept options, Hide SNAT, Show BGP Status.
20. Cato Networks, "Using PPPoE with Cato Sockets," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/using-pppoe-with-cato-sockets
    Verify: the PPPoE fields (account, secret, service name, MTU, VLAN tag) and
    the note that DNS fields are ignored when PPPoE is selected.
21. Cato Networks, "Configuring a Socket Site for IPv6-only Internet Connectivity,"
    *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/configuring-a-socket-site-for-ipv6-only-internet-connectivity
    Verify: the three connection types (IPIP6 Static, IPIP6 Auto, DS-Lite), the
    minimum Socket version (v26.0.23517 at time of writing), and that the feature
    is enabled by contacting Cato.
22. Cato Networks, "Configuring Cato as the DHCP Relay," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/configuring-cato-as-the-dhcp-relay
    Verify: the three per-range DHCP options, the three-server relay-group limit,
    and the model/version restriction on the relay option. See also "Configuring
    DHCP Settings" for the Cato DHCP server and reservations.
23. Cato Networks, "What is the Cato WAN Firewall," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/what-is-the-cato-wan-firewall
    Verify: "part of the Next Gen Firewall (NGFW) that is integrated into the Cato
    Cloud", the whitelist approach, the default ANY-ANY block, and L7 with User
    Awareness.
24. Cato Networks, "What is the Socket Next Gen LAN Firewall," *Cato Knowledge
    Base*. https://knowledge.catonetworks.com/docs/what-is-the-socket-next-gen-lan-firewall
    Verify: Socket-side enforcement for same-site traffic, L2–L4 default with L7
    enabled per site, the account-level policy with sub-policies/RBAC, and the
    Socket v22+ requirement.
25. Cato Networks, "What is Socket HA," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/what-is-socket-ha
    Verify: HA supported environments, the same-model/type restriction, keepalive
    interface designation ("LAN & VRRP" / "VRRP"), the 3-second failover, GARP
    behaviour, preemption, split-brain handling, and the statement that the default
    deployment uses routers between the Socket and the ISP.
26. Cato Networks, "Socket X1700 Deployment Guide," *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/socket-x1700-deployment-guide
   Verify: "X1700 Socket Network Card Add-On," the copper-port-1 requirement, and
   the WAN bandwidth step (bandwidth is coupled to the license).
27. Cato Networks, "Cato Socket Connection Prerequisites and Known Limitations,"
   *Cato Knowledge Base*.
   https://knowledge.catonetworks.com/docs/cato-socket-connection-prerequisites-and-known-limitations
   Verify: prerequisites port list, "MTBF Specifications," "Socket Known
   Limitations" (NAT/multi-WAN, ping behaviour, X1600 LTE). The article changelog
   dated 2026-09-22 added UDP 1337 and TCP 53 — check the changelog for later
   changes.
28. Cato Networks, "Understanding Cato's Managed Socket Upgrade Service," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/understanding-cato-s-managed-socket-upgrade-service
    Verify: the gradual roll-out (five-Socket canary per time zone), "Socket HA Upgrade
    Process" (primary first, secondary only after it is stable, pair completes within
    the maintenance window), the 17-minute per-Socket sequence, the "at most a few
    seconds" fast-switch claim, and the version-skew consequences.
29. Cato Networks, "Configuring the Socket Upgrade Maintenance Window," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/configuring-the-socket-upgrade-maintenance-window
    Verify: the account-level window applied in each site's local time zone, the
    48-hour buffer rule, and the "can result in a few minutes of downtime" wording.
    That sentence is about the **upgraded device**, not the site — it is not a conflict
    with the upgrade-service article's "at most a few seconds" *service* impact, but the
    two terms are never defined side by side, so state the scope explicitly when
    quoting either figure.
30. Cato Networks, "Manually Activate Socket HA Failover," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/manually-activate-socket-ha-failover
    Verify: the "Do not use the manual HA failover to perform Socket maintenance"
    warning, the split-brain behaviour it triggers, the Socket v24+ / HA-Ready
    prerequisites, the ~120 s timing, and both revert paths.

    Premium Security and Insights must be increased in step with Base Products.
31. Cato Networks, "Cato Socket Hardware Refresh Policy," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/cato-socket-hardware-refresh-policy
    Verify: the ownership sentence ("ownership … transfers upon its delivery"), the
    no-additional-charge refresh and shipping statement, the 90-day / 12-month /
    4-year / 7-to-10-year lifecycle milestones, the customer-only physical
    replacement, EOS consequences, and the latest-active-model RMA rule.
32. Cato Networks, "Refreshing Cato Socket Hardware," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/refreshing-cato-socket-hardware
    Verify: the refresh workflow (CMA refresh order, shipping details, USB-based
    settings copy, 14-day rollback), the "you can dispose of the Socket" statement,
    and the Socket v26.0+ prerequisite for replacement.
33. Cato Networks, "Identifying Your License Model," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/identifying-your-license-model
    Verify: the Enforcement-vs-Bursting split and the **cutover dates** (Enforcement
    until Jan 2027; Bursting for new accounts and renewals from Jan 2027). This is
    the single most time-sensitive fact in this file — re-check it against the
    current KB before any commercial discussion.
34. Cato Networks, "Managing Site Bandwidth (Enforcement Model License only),"
    *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/managing-site-bandwidth-in-licenses
    Verify: pooled vs. site licenses, the SASE/SSE site-license types, the
    higher-of-total-up-vs-down sizing rule, License Groups and the
    China/Vietnam/Morocco exceptions, and the unlicensed-site behaviour.
35. Cato Networks, "Jan 2027 License Bursting Model," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/jan-2027-license-bursting-model
    Verify: the licensing layers (Base Products, Premium Security, Insights,
    Services) and the description of measured usage.
36. Cato Networks, "Cato Product Catalog (Bursting License Model only)," *Cato
    Knowledge Base*.
    https://knowledge.catonetworks.com/docs/cato-product-catalog-bursting-license
    Verify: SKU descriptions and licensing dimensions (Bandwidth Pool in Mbps per
    region group; Premium Security "must cover the total licensed capacity"; Socket
    "purchased per device via payments over the term"; one-time rack kits; per-site
    vs. per-account vs. hourly services). Page updated 2026-08-31. **No prices are
    published here** — do not infer list pricing from this document.
37. Cato Networks, "Usage Measurement," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/usage-measurement
    Verify: monthly P95 measurement, the higher-of-two-directions sampling rule,
    region-group scoping, the default non-enforcement of per-site bandwidth in
    Group 1/2, fixed enforcement for Cloud Interconnect, and the stand-alone
    country behaviour.
38. Cato Networks, "License Over-Usage," *Cato Knowledge Base*.
    https://knowledge.catonetworks.com/docs/license-over-usage
    Verify: True-Up vs. True-Forward, the co-term requirement, and the rule that

