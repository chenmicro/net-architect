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
  [vendor-matrix/cisco.md](cisco.md)), whether a Huawei DC design is
  NCE-controller-managed or manually-configured EVPN-VXLAN is a real
  architectural fork affecting operational model and automation capability —
  confirm which is intended rather than assuming a specific one.
- Procurement note relevant to design conversations rather than technical
  ones: Huawei networking equipment is subject to restrictions or outright
  bans in a number of jurisdictions and for certain customer sectors
  (government, critical infrastructure, telecom in several countries) —
  worth flagging early in a vendor-selection conversation rather than
  discovering it after a design is otherwise finalized.
