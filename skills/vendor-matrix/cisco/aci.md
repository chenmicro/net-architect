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

ACI's endpoint-learning model is data-plane-driven: a leaf learns a MAC/IP only when
it sees traffic *from* that host. A device that silently listens and never initiates
traffic (a BMS that only responds to requests, a printer, a legacy sensor) never gets
learned — until the fabric actively probes for it [9].

### How the fabric detects a silent host

When a leaf receives traffic destined for an unknown MAC or IP, it forwards it to a
spine for proxy lookup. The spine consults **COOP** (Council of Oracle Protocol),
the fabric-wide endpoint database. If the destination is not in COOP — i.e., the
fabric has never seen this host anywhere — the spine triggers **ARP gleaning** (also
called silent-host detection) [9].

The mechanism in detail, for the most common case (L3 routed traffic to an unknown IP
within an ACI subnet):

1. **Ingress leaf**: Packet arrives for IP X. The leaf has no local or remote
   endpoint for X. It routes the packet to the spine proxy address (pervasive
   static route in the VRF — `*via <spine-proxy-IP>` in `show ip route`).
2. **Spine COOP lookup**: The spine checks its COOP database for IP X. COOP is the
   IS-IS-synchronised, distributed endpoint repository that every spine maintains
   a full copy of. If the IP is *not* present, the spine cannot forward the packet
   — so it triggers gleaning.
3. **Glean packet to the VRF-GIPo tree**: The spine encapsulates a special glean
   message into VXLAN using the VRF's VNID and sends it to the reserved multicast
   group **239.255.255.240** — the VRF-level GIPo address [10]. This multicast
   group reaches every leaf that has an interface in that VRF (the **VRF-GIPo
   tree**) [11].
4. **Leaf ARP generation**: The leaf that owns the BD SVI (pervasive gateway) IP
   for the target subnet receives the glean packet and generates an ARP request
   sourced from the SVI IP, targeting the unknown host IP. This ARP is flooded
   (or unicast-routed, depending on BD config) to every front-panel port in the
   bridge domain.
5. **Silent host responds**: The silent BMS receives the ARP, replies, and the
   fabric learns the endpoint. Subsequent traffic uses the learned EP entry.

### The two multicast trees (GIPo) and FTAG trees

ANC maintains two overlay multicast trees per tenant construct [11]:

| Tree | Scope | Multicast group | Used for |
|---|---|---|---|
| **BD-GIPo** | Per Bridge Domain | Auto-assigned from the BD's multicast pool | L2 BUM (broadcast, unknown-unicast, multicast); L3 ARP flooding within a BD |
| **VRF-GIPo** | Per VRF | Auto-assigned; glean uses 239.255.255.240 | L3 glean packets; TRM (Tenant Routed Multicast) replication |

Both trees are **head-end replication** trees: the source (spine or first-hop leaf)
replicates to the FTAG tree's leaf membership list — there is no PIM in the underlay
for overlay BUM (PIM is only used at the border for TRM or across the IPN in
Multi-Pod) [11].

#### FTAG (Forwarding Tag) trees — the lower-level forwarding construct

FTAG trees are ACI's load-balancing multicast forwarding mechanism that the GIPo
trees ride on. GIPo addresses answer *where* (which BD/VRF scope); FTAG trees answer
*how* (which spine replicates, which path it takes) [12]:

- ACI creates multiple FTAG trees per fabric — roughly **one root tree per spine**
  (a fabric with 4 spines has 4 FTAG root trees, numbered e.g. 0–3 and 5–8) [13].
  IS-IS builds and maintains these trees.
- **Why multiple trees**: without load-balancing, every BUM packet would pin to a
  single spine, wasting the other spines' bandwidth. With FTAG, different traffic
  flows hash to different spines.
- **Ingress leaf hashing**: when a leaf needs to forward BUM traffic (ARP flood, L2
  unknown unicast flood, or a glean packet), it hashes the inner packet headers
  (src/dst IP, src/dst MAC, etc.) and assigns an **FTAG number**. The FTAG
  number determines *which spine* is the root of that tree — and therefore which
  spine performs replication to all other leaves [12].
- **Spine replication**: the spine that is the root for that FTAG receives the
  VXLAN-encapsulated frame, replicates it to every leaf that is a member of that
  FTAG tree (which is all leaves that participate in the same BD/VRF), and sends
  each copy. The other spines are not involved for this particular BUM flow [13].
- **FTAG Transit trees** handle the reverse direction (leaf-to-spine), ensuring the
  ingress leaf's packet reaches the correct root spine without loops.

The hierarchy: **FTAG tree** (IS-IS-built forwarding construct, per-spine load
balancing) → **GIPo address** (multicast destination IP in the VXLAN outer header,
carrying the BD/VRF VNID for scope isolation). Every BUM or glean packet carries
both: an FTAG number that picks the spine, and a GIPo address that identifies the
BD or VRF [12], [13].

In the gleaning pipeline from the [section above](#how-the-fabric-detects-a-silent-host),
step 3 — "the spine sends a glean packet to 239.255.255.240" — means the spine
replicates the glean VXLAN packet using the VRF's FTAG root tree, addressed to the
VRF-GIPo multicast group. Every leaf in that VRF's FTAG tree receives it [10].

### L2 silent-host considerations

For *switched* (L2, intra-subnet) traffic to a silent host, the BD's **L2 Unknown
Unicast** setting matters [9]:
- **Flood**: The frame is flooded over the BD-GIPo tree to all leaves in the BD.
  The silent host receives the frame and responds — learned.
- **Hardware-Proxy** (default): The leaf sends the frame to the spine for COOP
  lookup. If the MAC is unknown, the spine drops it (no gleaning for L2 MACs).
  Enable ARP flooding in the BD to trigger gleaning instead, since the ARP request
  then hits the L3 gleaning path even for intra-subnet traffic [9].

### Requirements

All gleaning mechanisms require [9], [10]:
- **Unicast Routing** enabled on the Bridge Domain
- A **subnet** configured under the BD (so the fabric knows which leaf's SVI is
  authoritative for the target IP range)

### Version note

Silent host detection / ARP gleaning has been present since ACI 1.0(1e) and is
unchanged through 6.2(2) — it's a design constant, not version-gated [9].

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
[huawei.md](../../vendor-matrix/huawei.md#cross-vendor-interconnect-huawei-cloudfabric-%E2%86%94-cisco-aci)).

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

[9] "ACI Fabric Endpoint Learning White Paper," Cisco, Release 5.2(1g). [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-739989.html — covers silent host detection, ARP gleaning, L2 Unknown Unicast options, and endpoint aging. Section "Silent hosts considerations." Last confirmed Aug 2026.

[10] "Troubleshoot ACI Intra-Fabric Forwarding — MultiPod Forwarding," Cisco Support, Doc ID 218013. [Online]. Available: https://www.cisco.com/c/en/us/support/docs/cloud-systems-management/application-policy-infrastructure-controller-apic/218013-troubleshoot-aci-intra-fabric-forwarding.html — COOP database lookup, glean packet to 239.255.255.240 over VRF VNID, pervasive static route. Last confirmed Aug 2026.

[11] "IP Multicast," Cisco APIC Layer 3 Networking Configuration Guide, Release 5.0(x).
[Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/5-x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-50x/m_ip_multicast_v2.html
— VRF GIPo as fabric interface tunnel destination; "When the VXLAN packet is sent in
the fabric, the destination multicast GIPo address will be an address within this /28
block and is used to select one of 16 FTAG trees"; COOP repo synchronization for
PIM on bootup. Last confirmed Aug 2026.

[12] "ACI Fundamentals — Forwarding Within the ACI Fabric," Cisco, Release 3.x and earlier. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/1-x/aci-fundamentals/b_ACI-Fundamentals/b_ACI-Fundamentals_chapter_010010.html — "The ACI fabric uses Forwarding Tag (FTAG) trees to load balance multi-destination traffic. All multi-destination traffic is forwarded in the form of encapsulated IP multicast traffic within the fabric." Last confirmed Aug 2026.

[13] "Configure the L2 Multicast in ACI," Cisco Support, Doc ID 217712. [Online]. Available: https://www.cisco.com/c/en/us/support/docs/software/aci-data-center/217712-configure-the-l2-multicast-in-aci.html — FTAG tree for L2 traffic, spine replication, relationship to IS-IS. Last confirmed Aug 2026.