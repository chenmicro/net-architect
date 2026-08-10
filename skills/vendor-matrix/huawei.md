# Huawei

## VRP (Versatile Routing Platform)

- Huawei's unified network OS across its routing and switching portfolio —
  broadly analogous in role to Cisco IOS or Juniper Junos: one config
  model/CLI family spanning CloudEngine and NetEngine product lines, which
  simplifies operational training across a mixed Huawei fleet compared to
  vendors that split OS trains by product line.
- VRP's command syntax and structured config model will be unfamiliar to
  Cisco/Juniper-trained operators even though the underlying concepts
  (interfaces, VRFs, routing protocols, ACLs) map directly — factor in
  operator retraining time when a design proposes introducing Huawei gear into
  a previously Cisco/Juniper/Arista-only environment, it's a real but often
  underestimated cost.

### Version line: V300 (current), V200 (legacy)

- Current-generation CloudEngine switches (CE16800, CE8800, CE6800 series)
  ship on **V300** (latest: **V300R025C10**, ~2025; also V300R024C00, 2024;
  V300R023C00, 2023; V300R022C00, 2022 — see version-mapping page [3] for
  the full compatibility matrix). The version format is
  `V<major>R<year>C<build>` — e.g. R025 = release for 2025 [4].
  The V300 line is still VRP-based — Huawei's own Common Criteria cert
  describes it as "CE16800&CE8800&CE6800 Series Switches running VRP software
  V300R02" [2]. Earlier CloudEngine releases used V200 (V200R020C10 / V200R019C10).
- The VRP software version bundled with V300 host software is **VRP V800**
  (e.g. V300R022C00 ships VRP V800R022C05; V300R021C10 ships VRP V800R021C04) [3].
- V300 is functionally similar in CLI structure to V200 but adds newer hardware
  support, deeper EVPN-VXLAN scale, and AI-fabric-specific capabilities
  (enhanced RoCEv2 tuning, larger forwarding tables). Overall config model and
  operator knowledge transfer from V200 to V300 are straightforward — the same
  VRP skills apply.

Current versions per product line (see [SKILL.md](../../SKILL.md#3-vendors) version-scope rule):

| Product line | Current version | Legacy (do not reference) |
|---|---|---|
| CloudEngine (CE series) — data center | V300 (V300R025C10) | V200 |
| S-series — campus | V600 (V600R025C10) | V200 |

Campus and data center product lines run different OS trains — do not conflate
them. V600 on campus S-series is not the same CLI or feature set as V300 on
CloudEngine.

## ARP and silent host handling

Huawei CloudEngine V300 has two complementary mechanisms for learning ARP
entries from silent hosts (hosts that never initiate traffic or send ARP) [6]:

### Reactive: ARP Miss (default, no config)

When routed traffic arrives at a VBDIF/VLANIF for a destination with no ARP
entry, the interface generates an ARP Request automatically. Controlled by
`arp miss disable` / `undo arp miss disable` on the interface — enabled by
default. This is the leaf-local reactive equivalent of ACI's COOP-triggered
gleaning, but without spine involvement or a fabric-wide endpoint database.

### Proactive: ARP smart-discover (disabled by default)

`arp smart-discover enable` in **VLANIF interface view** [6]. The device
sends ARP probe messages to each host on the gateway's network segment at the
configured interval (default 1s, max 128 probes per interval). Existing ARP
entries, device IPs, and VRRP VIPs are excluded. Companion command:
`arp smart-discover interval <interval> count <count>`.

| Feature | Trigger | Default | Notes |
|---|---|---|---|
| ARP Miss | Traffic miss (reactive) | Enabled | Works on VBDIF/VLANIF |
| ARP smart-discover | Periodic timer (proactive) | Disabled | VLANIF only [6]; verify VBDIF availability |
| `arp direct-route enable` | N/A (publishes learned entries) | Disabled | Converts ARP entries to /32 EVPN host routes |

Huawei's doc warns: do not enable smart-discover if hosts send ARP proactively
— it may slow ARP learning. Also, on small network segments the probe volume
can be high, and if a host never responds, probing continues indefinitely [6].

## CloudEngine vs. NetEngine

- **CloudEngine (CE series)**: Huawei's data-center switching line —
  spine-leaf/Clos fabrics, EVPN-VXLAN, and (on current-generation platforms)
  AI/GPU-fabric-oriented features (RoCEv2 lossless tuning, deep buffers,
  high-radix 400G/800G) — the default choice for
  [techniques/spine-leaf-clos.md](../techniques/spine-leaf-clos.md),
  [vxlan.md](../techniques/vxlan.md), [evpn.md](../techniques/evpn.md), and
  [ai-gpu-fabric.md](../techniques/ai-gpu-fabric.md).
- **NetEngine (NE series)**: Huawei's routing line — WAN edge, service-provider
  core, MPLS/SR — the default choice for
  [techniques/mpls.md](../techniques/mpls.md) and
  [segment-routing.md](../techniques/segment-routing.md). Don't conflate the two
  lines by name alone; "NetEngine" routers and "CloudEngine" switches serve
  distinct roles even though both run VRP.
- Huawei has invested heavily in RoCEv2-based AI fabric positioning
  (competing directly with Nvidia/Mellanox-centric and Arista/Cisco AI-fabric
  offers) on current CloudEngine hardware — relevant to surface specifically
  in AI/GPU fabric vendor comparisons, not just general DC fabric ones.

## iMaster NCE

- Huawei's SDN controller / network-cloud-automation platform — spans
  intent-based fabric provisioning, telemetry, and closed-loop automation,
  broadly playing the same role Cisco ACI/APIC or Juniper Apstra play for
  their respective DC fabrics, with additional variants/modules extending into
  campus (NCE-Campus) and WAN (NCE-IP) domains.
- As with ACI vs. NX-OS-native EVPN-VXLAN (see
  [vendor-matrix/cisco/cisco.md](cisco/cisco.md)), whether a Huawei DC design is
  NCE-controller-managed or manually-configured EVPN-VXLAN is a real
  architectural fork affecting operational model and automation capability —
  confirm which is intended rather than assuming a specific one.
- Procurement note relevant to design conversations rather than technical
  ones: Huawei networking equipment is subject to restrictions or outright
  bans in a number of jurisdictions and for certain customer sectors
  (government, critical infrastructure, telecom in several countries) —
  worth flagging early in a vendor-selection conversation rather than
  discovering it after a design is otherwise finalized.

## DCI and cross-vendor interconnect

Huawei CloudFabric's recommended DCI model for interconnecting independent
fabrics is **Segment VXLAN** (as opposed to E2E VXLAN, which assumes a single
iMaster NCE-Fabric domain across all sites) [1]:

- Each CloudFabric is an **independent VXLAN/EVPN domain** with its own
iMaster NCE-Fabric instance
- **CloudEngine DCI gateways** (CE8800 / CE16800 / CE6860 series, any CE
switch with EVPN VXLAN capability at the fabric border) establish MP-BGP
EVPN peering across an Inter-Site Network to the remote fabric's border
gateways
- DCI VXLAN tunnels exist only between the gateways — the internal fabric
VXLAN stays within each DC
- The gateway function is configured on CloudEngine leaf/spine nodes at
the fabric edge; iMaster NCE provisions the DCI VNI stitching

To interconnect Segment VXLAN on CloudFabric with **Cisco ACI**, the ACI
fabric must present an **ACI Border Gateway** (BGW). See
[cisco/aci.md](cisco/aci.md#aci-border-gateway-heterogeneous-fabric-interconnect)
for the full architecture — ACI BGW addressing (MS-Ext-VIP/MS-Int-VIP/PIP),
control plane flow, data plane tunnel stitching, namespace normalization
(ACI 6.1(4)+), and multi-fabric policy enforcement. The CloudFabric side
connects by presenting standard EVPN VXLAN border gateways (above) that
peer with the ACI BGWs via MP-BGP EVPN over an L3 Inter-Site Network. All
ACI-side constraints (VNI namespace, multicast, Multi-Site support) apply
from the Cisco side.

For connecting CloudFabric to other non-Huawei EVPN VXLAN fabrics that
speak MP-BGP EVPN at the border (e.g. Arista, Juniper, NX-OS EVPN-VXLAN),
the same Segment VXLAN model applies with the foreign fabric presenting an
EVPN Multi-Site border gateway.

## References

[1] "What DCI Solutions Are Available? — E2E VXLAN and Segment VXLAN," Huawei Support Encyclopedia. [Online]. Available: https://info.support.huawei.com/info-finder/encyclopedia/en/DCI.html

[2] "Huawei CE16800&CE8800&CE6800 Series Switches running VRP software V300R02," Common Criteria Portal, certification document. [Online]. Available: https://www.commoncriteriaportal.org/files/epfiles/huawei-ce16800ce8800ce6800-series-switches-running-vrp-software-v300r02.pdf

[3] "CloudEngine Switches Software Versions," Huawei Support. [Online]. Available: https://info.support.huawei.com/network/ptmngsys/Web/DC/en/version-mapping.html

[4] "CloudEngine 16800 V300R025C10 Log Reference," Huawei Support, updated April 2026. [Online]. Available: https://support.huawei.com/enterprise/en/doc/EDOC1100561851/bbf994b3

[5] "CloudEngine 16800, 9800, 8800, and 6800 V300R024C00 Command, Trap, MIB, YANG, and Telemetry Delta Information," Huawei Support, 2024. [Online]. Available: https://support.huawei.com/enterprise/en/switches/cloudengine-58-68-78-88-98-pid-252837181

[6] \"ARP Configuration Commands — CloudEngine 9800, 8800, and 6800
V300R024C00 Command Reference,\" Huawei, EDOC1100439391. [Online]. Available:
https://support.huawei.com/enterprise/en/doc/EDOC1100439391/1c40b472/arp-configuration-commands
— `arp smart-discover enable` in VLANIF interface view. Last confirmed Aug 2026.
