# Cisco ACI (APIC)

- ACI (Application Centric Infrastructure) is Cisco's SDN/policy-controller
  overlay for Nexus DC fabrics — APIC is the controller, EPGs/contracts are the
  declarative, application-profile-based policy model. See [cisco.md](cisco.md)
  for how this fits against [NX-OS-native EVPN-VXLAN](nxos-vxlan.md), and
  [techniques/evpn.md](../../techniques/evpn.md) /
  [techniques/vxlan.md](../../techniques/vxlan.md) for the underlying
  control/data plane ACI's fabric rides on.

## Release history

| Version | Year | Architecturally significant changes |
|---|---|---|
| 1.x | 2014 | First GA (1.0(1e), Aug 2014) — centralized APIC cluster, EPG/contract policy model, single-pod only [1]. |
| 2.x | 2016–17 | **Multi-Pod**: one APIC cluster spanning multiple pods over a routed inter-pod network (IPN) [2]. |
| 3.x | 2017 | **Multi-Site** — independent APIC fabric domains stitched via MP-BGP EVPN + Multi-Site Orchestrator; 3.1 added **Remote Leaf** [3]. |
| 4.x | 2018–19 | **Cloud APIC** / "ACI Anywhere" — hybrid extension to AWS (4.1), then Azure (4.2); 4.2 became a designated long-lived release [4]. |
| 5.x | 2020–21 | APIC-over-L3 (no L2 adjacency required for spine/APIC), rogue-endpoint detection; 5.2 was the other long-lived release, deepened Nexus Dashboard consolidation (MSO, Nexus Insights, Network Assurance Engine) [5]. |
| 6.x | 2023–2026 | Long-lived-release model retired starting 6.0; 6.1 added standards-based EVPN remote-leaf resiliency (replacing a Cisco-proprietary protocol) and ACI↔non-ACI VXLAN-EVPN interop ("Policy Extension"); **6.2 (latest, 6.2(2), ~Jul 2026)** adds hybrid physical/virtual APIC clusters, a hardened cluster-upgrade workflow, and expanded GPO flexibility [6]. |

Latest release: **APIC 6.2(2)** (~Jul 2026). No newer long-lived-release line
exists — 4.2(x) and 5.2(x) remain the only two in ACI's history [6].

See **[aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md)** for the head-to-head
comparison against NX-OS-native EVPN-VXLAN, including the 2026 Cisco
convergence ("Nexus One") update relevant to new builds.

## Silent host detection (ARP gleaning / GIPo tree)

The same-subnet and routed-IP trigger cases, the generated ARP's SVI source,
the learning/COOP-report result, and host responses are shared behavior,
described in
[ARP gleaning (ACI COOP)](../../techniques/arp.md#arp-gleaning-aci-coop).
This section keeps only the ACI-specific fabric implementation details.

ACI's intra-pod endpoint directory is **COOP**, not BGP EVPN Type 2: on an
eligible COOP IP miss the spine proxy originates the glean request, carrying
the original packet under custom EtherType **0xfff2** to the reserved glean
group defined below [10]. In Multi-Pod, BGP EVPN between spines separately
distributes remote-pod endpoint reachability [9], [10].

Doc 222179's overview describes routed-IP gleaning, while its "Use Case 2"
different-BD example says gleaning is not relevant. The available text does
not resolve this wording difference; do not infer an unstated known-destination
assumption [9], [15], [16].

### Glean multicast, BD GIPo, and FTAG trees

Keep three constructs separate:

- **BD GIPo** is the multicast destination allocated to a bridge domain for
  traffic flooded within that BD [10].
- **239.255.255.240** is the reserved destination for fabric glean messages;
  it is not the BD's ordinary GIPo or an individually allocated per-VRF group
  [10]. VRF multicast used for tenant routed multicast is a separate feature
  described in [11].
- **FTAG trees** provide the fabric forwarding paths for multi-destination
  traffic, carried inside the fabric as encapsulated IP multicast [12], [13].
  Cisco's 6.2(x) Fundamentals guide says the ingress leaf assigns an
  FTAG, encoded as part of the destination multicast address. The APIC selects
  tree roots; multiple roots can be on one spine. Do not assume one FTAG per
  spine, a unique tree per VRF, or equate this with EVPN unicast head-end
  replication [14].

The current Fundamentals guide describes multicast/FTAG forwarding but does
not specify a distinct per-VRF glean tree or the complete glean packet format.
Use the packet-level troubleshooting source [10] for the reserved group and
subnet-based ARP-generation test, rather than deriving those details from the
TRM chapter [11].

### Discovery versus host tracking

COOP-miss gleaning discovers an **unknown** IP in response to traffic. Host
Tracking is a separate retention function for **already learned local IP
endpoints**: the endpoint-learning white paper describes ARP checks at 75% of
the configured retention interval when no source traffic has been observed.
It does not perform this IP tracking for MAC-only local endpoints or remote
endpoint caches [9]. Do not describe traffic-triggered gleaning as a periodic
subnet scan.

### Requirements

The BD unicast-routing and deployed-subnet requirements for each trigger case
are listed in [arp.md](../../techniques/arp.md#arp-gleaning-aci-coop). For
Multi-Pod, the IPN must carry the reserved glean multicast group defined in
the GIPo/FTAG subsection above [10].

### Version note

The endpoint-learning white paper was rechecked on **2026-10-16**. Although its
page update is June 9, 2026, it explicitly scopes feature coverage to **5.2(1g)**.
It therefore does not establish an introduction in 1.0(1e), or unchanged behavior
through 6.2(2). Those historical/current-release assertions remain unverified [9].
The 6.2(x) Fundamentals guide confirms current distributed-gateway and FTAG
architecture; it is not proof that every historical glean detail is unchanged
[14].

## Multi-Site: stretched workload with per-site NAT

Instance of the general
[multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md)
scenario: two ACI fabrics (one per DC), a shared/stretched private-IP subnet so
workloads can migrate between sites, but each site owns a **distinct** public
IP range behind its own independent NAT firewall. A workload can end up
physically hosted at a site other than the one whose public IP/firewall a
client used to reach it — and because NAT requires the return packet to hit
the *exact* device holding the translation entry (stricter than plain
stateful-firewall symmetry — a non-SYN, non-matching segment is dropped by the
implicit stateful check), the wrong firewall can't substitute even if it runs
an identical security policy [7].

**Correction: ACI Multi-Site's documented PBR architecture does not have a
fix for this scenario.** An earlier version of this file claimed a
single-Destination-Group pinning pattern (anchor PBR to one named firewall,
configured identically at every leaf regardless of site) solved this —
that claim doesn't hold up against Cisco's own Multi-Site service-node paper
and has been retracted. Here's why, and what the real options are.

**What the paper's PBR mechanism actually guarantees.** Cisco's stated scope
for this entire document is deliberate and narrow:

> "As of Cisco ACI Release 6.0(5), the recommended option for integrating
> L4–L7 services into a Cisco ACI Multi-Site architecture calls for the
> deployment of independent service nodes in each site... The focus in this
> document, therefore, will be exclusively on this deployment model."
>
> "This model mandates that symmetric traffic flows through the service
> nodes be maintained, because **the connection state is not synchronized
> between independent service nodes deployed in different sites**."

Every PBR use case the paper documents (EPG-to-L3Out compute-leaf
enforcement, EPG-to-EPG provider-leaf anchoring, vzAny-to-vzAny/-to-EPG/
-to-L3Out) is engineered around one guarantee: **flow symmetry** — the *same*
firewall handles both directions of a *given* flow, by resolving to **"the
local active firewall node"** relative to wherever the endpoint currently is.
That guarantee is unconditionally correct when the two sites' firewalls are
interchangeable (same policy, no unique state) — but nowhere in the document
is there a mechanism for redirecting to a **specific, named, non-local**
firewall that overrides that local resolution. "Local" is the answer PBR
always computes; there's no override.

**Why that breaks this scenario specifically.** Each site here owns a
*distinct* public IP range with its own **independent, unsynchronized** NAT
firewall — exactly the "connection state is not synchronized" case the paper
flags. If the workload migrates to DC2 mid-session, its return traffic hits
DC2's compute leaf, which — per the paper's own design, correctly and as
intended — redirects to **DC2's own local firewall (FW2)**. FW2 never
created the translation entry; only FW1 (DC1) did. There's no PBR knob in
this architecture to force it to FW1 instead — the "single Destination
Group, same target everywhere" pattern previously claimed here isn't
something this document (or the general EPG-to-L3Out/EPG-to-EPG mechanics
elsewhere in it) actually supports.

**The one model in this same paper that would sidestep the problem** is an
**active/standby firewall pair *stretched* across sites** — one logical
device (not independent per-site instances), so "local" trivially resolves
to the same thing everywhere since there's no second instance to
mis-resolve to. But Cisco explicitly flags this **"Limited support,"** not
the recommended architecture, and adds:

> "Cisco ACI Multi-Pod remains the recommended architectural approach for
> the deployment of active/standby service-node pairs across data
> centers."

i.e. Cisco's own guidance is to use a *different* fabric architecture
(Multi-Pod, not Multi-Site) if a stretched active/standby pair is a hard
requirement — not to force it onto Multi-Site's independent-node model [7].

**Net**: on ACI Multi-Site with independent per-site firewalls (the
documented, recommended design), this scenario has **no confirmed PBR-based
fix**. The viable paths are the ones already covered generically in
[multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md):
Option 1 (SNAT, sacrificing client-IP visibility), the architectural fix
(don't let NAT'd tiers migrate independently of their public IP), a NAT
platform with cross-site state sync, or — if a stretched active/standby pair
is genuinely required — reconsidering ACI Multi-Pod instead of Multi-Site for
this fabric.

## ACI Border Gateway (Heterogeneous Fabric Interconnect)

ACI 6.1(x) introduced the **ACI Border Gateway (BGW)** — dedicated Nexus 9000
FX2/FX2P/GX/GX2+ leaf nodes that bridge ACI's internal COOP control plane to
external MP-BGP EVPN [8]. This is the mechanism for connecting an ACI fabric to
any standards-compliant VXLAN EVPN fabric, including NX-OS EVPN-VXLAN Multi-Site,
Arista, Juniper, and **Huawei CloudFabric** (see
[huawei.md](../../vendor-matrix/huawei.md#dci-and-cross-vendor-interconnect)).

This is part of Cisco's broader **Nexus ONE Fabric Experience** convergence
initiative (see [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md) §2026 convergence
note) — decoupling "controller-managed experience" from "Cisco-only fabric" by
letting ACI interoperate with external EVPN fabrics via standards-based BGP.

### BGW architecture summary

- **Hardware**: Dedicated Nexus 9000 leaf nodes (FX2/FX2P/GX/GX2+) configured
as BGWs, connected to the Inter-Site Network (ISN) via downlinks in an Infra
L3Out (not fabric links like Multi-Pod) [8].
- **Addressing**:
  - **MS-Int-VIP** — anycast IP shared by all ACI BGWs in a fabric; source IP
    for traffic received from the ISN and re-encapsulated into the ACI fabric.
  - **MS-Ext-VIP** — anycast IP (per-pod) advertised as EVPN next-hop for
    Type-2/Type-5 routes toward the external fabric.
  - **PIP** — unique physical IP per BGW node; source IP for traffic sent
    toward the external fabric.
- **Underlay**: eBGP between ACI BGW PIPs and external BGW interfaces, routed
through the ISN. `disable-peer-as-check` required on ISN routers when ACI BGWs
in the same AS peer across it [8].
- **Overlay**: Full-mesh MP-BGP EVPN sessions between each ACI BGW and each
external BGW. ACI BGWs also run local iBGP EVPN among themselves for DF
election on BUM forwarding.

### Supported topologies (by release)

| Release | ACI side | External side |
|---|---|---|
| 6.1(1) | Single ACI fabric (or Multi-Pod) | VXLAN EVPN site(s) |
| 6.1(4) (planned) | Independent ACI fabrics (no Multi-Site) | VXLAN EVPN Multi-Site domain |
| Future | ACI Multi-Site (via NDO) | VXLAN EVPN Multi-Site domain |

### Limitations for ACI BGW

- **VNI namespace**: Symmetric only until 6.1(4)+ (external VNIs must match
APIC-assigned VNIDs). 6.1(4) adds centralized normalization (ACI BGW
translates); distributed normalization is future [8].
- **ACI Multi-Site**: Not supported for BGW interconnect yet.
- **Multicast**: L2 multicast forwarded as BUM; L3 multicast **not supported**
across domains.
- **IGMP snooping**: Not supported across domains.
- **One management plane per fabric**: Nexus Dashboard management of the
external fabric is not yet GA — APIC manages the ACI fabric, the external
vendor's controller manages its own.

### Policy enforcement across fabrics

- **6.1(1)**: VRF unenforced — L2/L3 forwarding only, no ACI contract
to external traffic [8].
- **6.1(2)**: VRF "Policy Enforced" mode — ACI BGW classifies incoming
traffic to ESGs based on MAC, L2 VNI, or IP subnet [8].
- **6.1(4)** (planned): End-to-end SG-Tag in EVPN routes — ACI maps
external endpoints to ESGs via tag; external fabric maps ACI endpoints
via tag. Cross-fabric microsegmentation becomes possible [8].

### External fabric references

- **Huawei CloudFabric**: See [huawei.md](../../vendor-matrix/huawei.md#dci-and-cross-vendor-interconnect)
  for the Huawei-side DCI architecture (Segment VXLAN on CloudEngine gateways).
- **Any standards-based VXLAN EVPN fabric** (NX-OS EVPN-VXLAN Multi-Site,
  Arista, Juniper): the same ACI BGW architecture above applies unchanged —
  the ACI BGW peers via MP-BGP EVPN with the external fabric's border
  gateways. Only the external-side BGW configuration and VNI namespace
  coordination differ per vendor.

## References

[1] "Cisco APIC Release Notes, Release 1.0(1e)," Cisco, August 2014. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/1-x/release/notes/apic_rn_101.html

[2] "Cisco APIC Layer 3 Configuration Guide — Multi-Pod," Cisco, Release 2.x. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/2-x/L3_config/b_Cisco_APIC_Layer_3_Configuration_Guide/b_Cisco_APIC_Layer_3_Configuration_Guide_chapter_010011.html

[3] "Cisco ACI Multi-Site Architecture White Paper," Cisco, 2017. [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-740861.html

[4] "Cisco Cloud APIC for Azure Installation Guide, Release 4.2(x)," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/cloud-apic/4-x/install/Cisco-Cloud-APIC-Installation-Guide-Azure-42x/Cisco-Cloud-APIC-Installation-Guide-42x_chapter_01.html

[5] "Cisco ACI Long-Lived Release 5.2(x)," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/long-lived-release/aci-long-lived-release-5-2-x.html

[6] "Cisco APIC Release Notes, Release 6.2(2)," Cisco, July 2026. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/release-notes/cisco-apic-release-notes-622.html

[7] "Cisco ACI Multi-Site and Service Node Integration White Paper," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-743107.html

[8] T. Kishida, "Deployment of VXLAN EVPN Gateways with Cisco ACI for the Interconnection of Heterogeneous Data Center Fabrics," Cisco Live EMEA 2025, BRKDCN-2634.

[9] "Cisco ACI Fabric Endpoint Learning White Paper," Cisco, updated June 9, 2026; stated feature scope through Release 5.2(1g). [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/networking/cloud-networking/application-centric-infrastructure/fabric-endpoint-learning-wp.html — verify sections "Silent hosts considerations," "Local endpoints and remote endpoints," and "Aging of endpoints." Distinguishes routed-IP gleaning, flooded ARP, target-IP lookup with ARP Flooding disabled, and L2 unknown-unicast drop. Rechecked Oct. 16, 2026; page date does not extend stated release scope.

[10] "Troubleshoot ACI Intra-Fabric Forwarding — MultiPod Forwarding," Cisco Support, Doc ID 218013. [Online]. Available: https://www.cisco.com/c/en/us/support/docs/cloud-systems-management/application-policy-infrastructure-controller-apic/218013-troubleshoot-aci-intra-fabric-forwarding.html — verify "Proxied requests where the EP is not in COOP," "Glean ARP verification," and "Other possible causes": custom EtherType 0xfff2, reserved group 239.255.255.240, responding leaves with the destination subnet deployed, and Multi-Pod IPN multicast requirements. Rechecked Oct. 16, 2026.

[11] "IP Multicast," Cisco APIC Layer 3 Networking Configuration Guide, Release 5.0(x).
[Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/5-x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-50x/m_ip_multicast_v2.html
— VRF GIPo as fabric interface tunnel destination; "When the VXLAN packet is sent in
the fabric, the destination multicast GIPo address will be an address within this /28
block and is used to select one of 16 FTAG trees"; COOP repo synchronization for
PIM on bootup. Last confirmed Aug 2026.

[12] "ACI Fundamentals — Forwarding Within the ACI Fabric," Cisco, Release 3.x and earlier. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/1-x/aci-fundamentals/b_ACI-Fundamentals/b_ACI-Fundamentals_chapter_010010.html — "The ACI fabric uses Forwarding Tag (FTAG) trees to load balance multi-destination traffic. All multi-destination traffic is forwarded in the form of encapsulated IP multicast traffic within the fabric." Last confirmed Aug 2026.

[13] "Configure the L2 Multicast in ACI," Cisco Support, Doc ID 217712. [Online]. Available: https://www.cisco.com/c/en/us/support/docs/software/aci-data-center/217712-configure-the-l2-multicast-in-aci.html — FTAG tree for L2 traffic, spine replication, relationship to IS-IS. Last confirmed Aug 2026.

[14] "Forwarding Within the ACI Fabric," Cisco Application Centric
Infrastructure Fundamentals, Release 6.2(x), updated Mar. 25, 2026. [Online].
Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/aci-fundamentals/cisco-aci-fundamentals-62x/fundamentals-62x.html
— verify "Layer 3 VNIDs Facilitate Transporting Inter-subnet Tenant Traffic"
and "Multicast Tree Topology": distributed gateway, FTAG assignment in the
multicast destination address, and configurable roots with multiple tree roots
possible on one spine. Rechecked Oct. 16, 2026.

[15] S. Garg, "Understand ARP Flooding and ARP Gleaning in ACI," Cisco TAC,
Doc ID 222179, updated July 23, 2024. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/technical-details/222179-understand-arp-flooding-and-arp-gleaning.html
— verify "Understanding ARP Flooding," use cases 3–5, and "Understanding ARP
Gleaning," requirements and both use cases. Rechecked Oct. 16, 2026.
The final example's explanation conflicts with the overview if treated as
a general rule; its intended endpoint-resolution assumption is unconfirmed.
Both gleaning workflow diagrams were visually inspected on recheck.
No specific current software release is stated for these workflows.

[16] "ACI Multi-Pod White Paper," Cisco, updated May 9, 2022, discussion
around Figures 35–36 in "Inter-Pods VXLAN Data Plane." [Online]. Available:
https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-737855.html
— independent definition of ACI ARP gleaning as fabric-generated ARP from
the BD IP to resolve an unknown endpoint. Rechecked Oct. 16, 2026 for
terminology; not a blanket validation of current-release implementation details.
