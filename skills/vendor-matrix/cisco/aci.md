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

### NX-OS-style CLI configuration mode removed in 6.1(2)

From APIC **6.1(2)** (6.1(2f) available Dec. 4, 2024; 6.1(2g) Dec. 13, 2024 [30]),
the configuration mode **and the `show running-config`
command** of the APIC NX-OS-style CLI are no longer supported; EXEC mode and the
UNIX CLI remain [29]. A configuration-gathering plan for a fabric on 6.1(2) or later
cannot rely on `show running-config` output from the APIC; on earlier releases it is
still available. Ask for the APIC version before choosing the collection method.

The replacement is a **configuration export policy**: Admin > Import/Export > Export
Policies > Create Configuration Export Policy, written to a remote location
(FTP/SCP/SFTP) or kept as a snapshot on the controller, in JSON or XML [31]. Since
4.1(1) a read-only user can trigger it. Secure properties follow the fabric-wide AES
setting: with AES on they are exported encrypted, and with AES off they are left out of
the file entirely [31]. A file sent to a third party for design work therefore needs no
passphrase and no change to the AES setting.

**What the export contains**: the **user-configurable managed-object trees** from all
32 shards, one file per shard, packed as a tar.gz. An empty **Target DN** exports
everything; a target narrows it to `infra`, `fabric`, or one tenant [31]. So a full
export carries the tenant policy (VRFs, BDs and their settings, subnets, EPGs, uSeg
EPGs and ESGs, contracts, L3Outs with their peers and protocols), access policies, and
fabric policies. It does not carry anything the fabric learns or measures at run time
(endpoints, learned routes, neighbor tables, running versions), nor anything about
non-ACI devices beyond the ACI-side configuration toward them; those need a separate
request.

**Endpoint list (host IP/MAC to leaf port)** is run-time data, so it comes from the
EXEC-mode `show endpoints` command (variants per leaf interface, port-channel, and vPC)
[33]. The newest command reference that lists it is 6.0(x); no 6.1(2)-or-later
command reference was found, so its presence after 6.1(2) rests on the statement that
EXEC mode remains [29] — confirm on the live APIC. The endpoint object class is
`fvCEp` [34], which the UNIX shell can read with `moquery` when the NX-OS-style command
is unavailable.

## iVXLAN encapsulation

iVXLAN is ACI's proprietary VXLAN variant. Its encapsulation and header field
inventory — the RFC 7348 baseline, the absence of any IETF specification, and
the VXLAN-GBP comparison — are documented once in
[techniques/vxlan.md](../../techniques/vxlan.md) (see **Cross-vendor /
variants**), with the sources cited there. What stays here is ACI-specific
behaviour: FTAG/GIPo multicast trees, the per-BD proxy/flood switch, and glean
processing below.

Two facts worth carrying into capture analysis: the packet is VXLAN on the
outside, so MTU and ECMP reasoning are unchanged; and the policy tag is ACI's
own, so a standards-based VTEP will not interpret it.

## BUM and unknown-unicast forwarding (FTAG trees and BD GIPo)

This is the mechanism behind "unknown unicast is flooded as multicast" in ACI.
Cisco's vocabulary is **FTAG (Forwarding Tag) tree** and **BD GIPo** (Group IP
Outer, shown as `bcastP` on the `fvBD` object [10]). The FTAG is not a separate
header field — it is encoded in the encapsulated packet's destination multicast
address [16].

This section covers how the fabric **forwards** multi-destination traffic. What
it does when the destination is unknown to COOP — gleaning — builds on the same
machinery and is covered in **Silent host detection** below.

### Tree mechanics

- Everything in the fabric is VXLAN-encapsulated, and **all multi-destination
  traffic** from endpoints — broadcast, multicast, and unknown unicast when
  flooding is enabled — is carried through the fabric as **encapsulated IP
  multicast** [16].
- The **ingress leaf assigns the FTAG** when it forwards the frame to the
  spine; spine and transit leaves then forward on the FTAG ID [16].
- **One forwarding tree per FTAG ID**, and **between any two nodes only one
  link forwards per FTAG**. That is what makes the trees loop-free. Parallel
  equal-cost links are exploited by giving different FTAGs different links, so
  more FTAG trees means better multi-destination load spreading [16].
- The fabric supports **up to 12 FTAGs**. Trees are rooted on spines and the
  roots are chosen by the APIC during bring-up, where **multiple roots can sit
  on one spine** (so "one spine = one FTAG" is wrong). Root placement is
  **configuration-driven and is not re-rooted on run-time events such as a
  spine failure**; the trees are recalculated on any topology change, and an
  administrator can re-anchor FTAGs when spines are added or removed [16].
- The **BD GIPo** is the multicast group its flooded traffic is sent to. The
  address APIC displays is a **/28 network address** (last four bits zero); the
  FTAG occupies those four bits on the wire, which is how the destination
  selects one of **16 possible trees** (the fabric supports up to 12) [11],
  [20]. Allocation and membership are in the next subsection.
- The FTAG ID is chosen by a **payload hash (documented range 0–12)**, so the
  value is unpredictable and varies per flow even for the same ingress leaf and
  BD GIPo. That variability is the load-balancing mechanism, not a per-BD
  constant [17].

So the FTAG count is a **BUM load-spreading dimension**, not a per-BD setting:
the tree set is fabric-wide and APIC-configured, and the per-flow hash decides
which tree a given frame rides.

### GIPo allocation and group membership

Allocation is **implicit — there is no user-sized multicast pool**. APIC derives
GIPos from configuration: **one GIPo for the VRF and one GIPo for every BD under
that VRF**, and a GIPo **may be shared between multiple BDs or between multiple
VRFs, but never between a VRF and a BD**. IS-IS was extended to build trees for
the VRF and BD GIPos as well as handling the VRF group [20].

Which traffic uses which group [20]:

| Traffic | BD without multicast routing | PIM/PIM6-enabled BD |
|---|---|---|
| Broadcast | BD GIPo | BD GIPo |
| Unknown-unicast flood | BD GIPo | BD GIPo |
| Multicast | BD GIPo | **VRF GIPo** (L2 and L3) |

So enabling tenant routed multicast moves tenant **multicast** traffic onto the
VRF GIPo, while broadcast and unknown-unicast flooding stay on the BD GIPo
[20]. What moves is only the **outer transport group**: the tenant's own
multicast group address stays in the inner packet, and which host ports receive
the stream is still decided per BD by IGMP snooping (enabled by default in ACI)
[17], [20]. VRF-group membership is VRF-wide — every leaf where the VRF is
deployed [21] — so the transport copy reaches more leaves than a BD group would,
and the egress leaf prunes with its snooping state. A receiver in another BD
consumes the stream only if L3 multicast routing forwards it there; the choice
of GIPo does not create that reachability by itself.

**Which leaves join a BD's group.** The BD GIPo is programmed on the leaves
where that BD is deployed; other leaves can hold a **TRANSIT** entry and forward
toward the deployed leaves without decapsulating. `show isis internal mcast
routes gipo` labels each group `[LOCAL]` (deployed here) or `[TRANSIT]`
(pass-through) [17]. In practice a BD is deployed on a leaf when at least one
EPG of that BD has a binding there — static path binding, VMM/domain
association, or the peer of a vPC pair — and Cisco describes the flood as
reaching "all the nodes where a bridge domain is deployed" [15]. The VRF GIPo
follows the same rule one level up: it is programmed on all leaf switches where
the VRF is deployed, and TRM multicast is received by all of them [21].

**Two different address roles — and why they do not collide.** A leaf's **TEP**
is a **unicast** address from the TEP pool (default `10.0.0.0/16`, infra VRF),
while a **GIPo** is a **multicast destination** in the outer IP header — never
an address assigned to a leaf interface [20], [24]. The GIPo pool is a fabric
setup parameter, not a per-BD choice: APIC asks for it at bring-up, defaults to
**225.0.0.0/15**, and constrains it to **225.0.0.0/15 – 231.254.0.0/15 with
prefix length 15** (128k addresses), so the pool always sits in multicast space,
separate from unicast pools [24]. A leaf "joining" a group is therefore routing
state — a `[LOCAL]` or `[TRANSIT]` GIPo entry — not an interface address [17].

Practical rules:

- Keep the GIPo pool distinct from the TEP pool, infra/management addressing,
  and routed space. The address families do not overlap by design, and the
  setup-validated range keeps the pool in multicast space [24].
- In **Multi-Pod**, the IPN's PIM **bidir** range must include the fabric's GIPo
  pool (default `225.0.0.0/15`) **and** `239.255.255.240/28` for glean, or BUM
  and glean stop crossing pods [25].
- Many leaves joining one group is normal, not a conflict: the VNID inside the
  encapsulation identifies the BD/VRF, and APIC may even share one GIPo across
  BDs [20].
- The same GIPo may be reused across **Multi-Site** sites — identical group
  addresses on two sites are not a conflict [24].
- A tenant multicast group (inner) can numerically match a GIPo (outer) without
  a protocol conflict, because they are different headers; keep them distinct
  in capture filters and monitoring so the two layers are not confused.

### When a GIPo is shared

Cisco documents that sharing **can** happen but not what triggers it: "any given
GIPo might be shared between multiple BDs or multiple VRFs, but not a
combination of VRFs and BDs. APIC will be required to ascertain this" [20].
There is **no user-facing knob**, so sharing is never a design action — you
cannot request, size, or prevent it, and it should not be planned around.

Why it is harmless: the outer group is only the delivery mechanism, while the
inner VNID identifies the segment, so the receiving leaf forwards per VNID.
Sharing therefore does not leak one BD's flood into another; the group is a bus,
the VNID is the address [16], [20].

The trigger is undocumented. The likely drivers — an identical deployment
footprint (same member leaves, so delivery is unchanged) and conservation or
reuse of the multicast address space — are unconfirmed.

Operational consequences:

- Do not use `bcastP` as a BD key in monitoring or tooling — two BDs showing the
  same GIPo is legal, not a fault [20].
- `show isis internal mcast routes gipo` lists the group once; its `[LOCAL]`
  leaves are the union of the sharing BDs'/VRFs' deployments [17].

### Proxy or flood is a per-BD setting

| L2 Unknown Unicast mode | Behavior | GIPo / FTAG tree? |
|---|---|---|
| **Hardware Proxy** (Cisco's "optimized mode") | Frames are sent to the **spine-proxy anycast VTEP**; the spine looks the destination MAC up in **COOP**, and a miss is dropped | No |
| **Flood** | Frames are flooded **over the multicast tree of the bridge domain (GIPo)** | Yes |

Proxy mode and gleaning are adjacent but distinct: proxy lookup decides the fate
of the data frame, while gleaning is triggered by an ARP request or a routed
packet and is covered in **Silent host detection** below [10].

Changing a BD between the two modes **bounces traffic** on the interfaces
attached to that BD's EPGs, so schedule it rather than treating it as a live
tweak [15]. Cisco's guidance is not "always flood": the best-practices summary
recommends **Flood** only when **unicast routing is disabled**, or when **L2 is
extended through non-ACI switches** (for example during a migration) [18].

**The published default is contradictory — verify it per BD instead of quoting
one.** The 6.2(x) Fundamentals storm-control text states that BD Layer 2
unknown-unicast flooding "is enabled by default within the BD but can be
disabled by an administrator," while the same release's Layer 2 guide calls
hardware-proxy the optimized mode and the best-practices summary treats
flooding as the exception [15], [16], [18]. Read the value rather than assuming
it:

```
moquery -c fvBD -f 'fv.BD.name=="<bd>"' | grep -E "unkMacUcastAct|bcastP|multiDstPktAct"
```

`unkMacUcastAct` is `proxy` or `flood` [10]. The GUI location is
Tenant > Networking > Bridge Domains > Policy > General > L2 Unknown Unicast
[18].

### Multiple EPGs in one BD

The FTAG **tree topology** is fabric-wide (the set of up to 12 trees), but the
multicast **group** is per BD — so an EPG never gets a tree of its own. Every
EPG in the same BD shares that BD's GIPo and therefore the same flood scope.
Cisco states the default directly: ACI "uses the bridge domain as the Layer 2
broadcast boundary," each BD can contain multiple EPGs, and "ordinarily ...
broadcast flooding sends traffic to all the EPGs in the bridge domain" [19].

With default settings, multiple EPGs in one BD mean:

- Broadcast, unknown multicast, IP multicast, and — when L2 Unknown Unicast is
  **Flood** — unknown unicast all ride the BD's GIPo and are delivered to every
  EPG's ports in that BD. **Contracts do not scope this:** Cisco notes that
  with several EPGs in one BD, "multicast traffic flood in all EPGs regardless
  of contracts in place between EPGs" [17].
- ARP/GARP follow the same scope when ARP Flooding is enabled, so ARP is
  visible across the EPGs of the BD.
- The blast radius of a broadcast or unknown-unicast storm is the **whole BD**,
  not the EPG. Storm control is applied per port, so it caps ingress rate
  rather than removing the flood domain [16].
- EPGs stay policy containers inside one L2 domain: putting an endpoint in a
  different EPG does not give it a different broadcast or learning domain
  [19].

**To scope flooding to the EPG, use Flood in Encapsulation** — the BD
`Multi Destination Flooding` setting (`multiDstPktAct=encap-flood`, NX-OS-style
CLI `multi-destination encap-flood`) or the per-EPG `Flood in Encapsulation`
setting (`flood-on-encapsulation`). It limits flooding to a single VLAN/VXLAN
encapsulation, and a per-EPG setting takes precedence over the BD setting
[19]. From APIC 3.1(1) on EX/FX-and-later switches, **all** protocols are
flooded in encapsulation (ARP, GARP, and BUM, not just broadcast); from
3.2(5), VXLAN-encapsulated EPGs are supported [19].

| Flood in Encapsulation | Behavior |
|---|---|
| BD on | Flooding scoped to encapsulation for all VLANs/VXLANs in the BD |
| BD off, EPG on | Flooding scoped to encapsulation for that EPG's VLAN/VXLAN only |
| BD off, EPG off (default) | Flooding within the entire BD |

Two constraints matter in design [19]:

- It requires a BD **subnet and IP routing**, because ACI enables **proxy
  ARP** so endpoints in different EPGs/VLANs of the same BD can still reach
  each other at Layer 3 through the pervasive SVI. L2 isolation is the point;
  L3 reachability inside the BD is preserved.
- Service-node EPGs are not scoped the same way: Cisco's own example puts a
  load balancer on its own EPG, notes that "there is no Proxy ARP and flood
  within encapsulation does not take place," and recommends an external switch
  for multi-EPG-per-BD designs.

If you need genuinely separate broadcast domains, **separate BDs** (each with
its own GIPo) are the clean boundary; Flood in Encapsulation is the tool for
keeping one BD while stopping cross-EPG flooding.

### Design consequences

- In **hardware-proxy** mode an unknown MAC is a **drop**, not a flood: a host
  that never transmits is never learned, so its traffic is discarded
  continuously and silently — the failure mode analyzed in
  [silent-host-in-overlays.md](../../scenarios/silent-host-in-overlays.md).
  Switching the BD to flood removes the drop-on-miss step; it does not make a
  silent receiver answer.
- Flooding means the frame is carried on the BD's multicast tree to every leaf
  attached to that tree, rather than resolved to a single egress leaf [15],
  [16]. Storm control only counts L2 unknown unicast when the BD is flooding
  [16].
- FTAG selection is per payload hash, not per BD, so FTAG values cannot be used
  as a tenant/VRF identifier, and one BD's flood traffic spreads across several
  trees [17].
- A GIPo is a transport group, not a BD identifier: APIC may share one GIPo
  across several BDs, or across several VRFs, but not between a BD and a VRF
  [20]. Don't build monitoring or troubleshooting logic that maps one multicast
  group to exactly one BD — the VNID inside the encapsulation still identifies
  the BD.
- This is **not** EVPN head-end replication: an NX-OS/Arista EVPN-VXLAN fabric
  replicates BUM at the ingress VTEP or uses an underlay multicast group per
  BD, with no FTAG concept [12], [16].

## Silent host detection (ARP gleaning / GIPo tree)

The same-subnet and routed-IP trigger cases, the generated ARP's SVI source,
the learning/COOP-report result, and host responses are shared behavior,
described in
[ARP gleaning (ACI COOP)](../../techniques/arp.md#arp-gleaning-aci-coop).
This section keeps only the ACI-specific fabric implementation details.

ACI's intra-pod endpoint directory is **COOP**, not BGP EVPN Type 2: on an
eligible COOP IP miss the spine proxy originates the glean request, carrying
the original packet under custom EtherType **0xfff2** to the reserved glean
group described in the next subsection [10]. In Multi-Pod, BGP EVPN between
spines separately distributes remote-pod endpoint reachability [9], [10].

### The glean group is the System GIPo

`239.255.255.240` is the fabric's **System GIPo**, reserved for glean messages
— the CLI shows it as `System GIPo ... Operational: 239.255.255.240` — not the
BD GIPo and not the individually allocated VRF GIPo [10], [17]. Keep the three
apart: the BD/VRF groups and their tree mechanics are in **BUM and
unknown-unicast forwarding** above [20]; this group carries infrastructure
control traffic.

- Glean requests are flooded **fabric-wide** to the group, but only egress
  leaves that have the destination subnet deployed act on them: they generate
  an ARP from the BD subnet IP. A BD with unicast routing disabled therefore
  cannot resolve a silent endpoint this way [10].
- The base is a /28 (`239.255.255.240/28`), so the FTAG is added into the last
  nibble exactly as for any other GIPo — the capture below shows the wire
  destination as `.241`, i.e. base plus FTAG 1 [22].
- VRF multicast used for tenant routed multicast is a separate feature; see
  [11], [20].

The current Fundamentals guide describes multicast/FTAG forwarding but does
not specify a distinct per-VRF glean tree or the complete glean packet format.
Use the packet-level troubleshooting source [10] for the reserved group and
subnet-based ARP-generation test, rather than deriving those details from the
TRM chapter [11].

**Address-space status.** None of this is a registered allocation.
`239.255.255.240/28` sits inside the **administratively scoped block**
239.0.0.0/8, which RFC 3171 describes as "for local use within a domain" and
for which "no IANA assignment policy is required"; RFC 2365 further defines
239.255.0.0/16 as the IPv4 **Local Scope**, whose traffic "must not be
forwarded across any link for which a scoped boundary is defined" [26], [27].
The IANA registry lists 239/8 as a single block and assigns no sub-range for
ACI [28]. So Cisco's "reserved" is a **vendor convention** honoured inside the
ACI fabric — plus, in Multi-Pod, a configuration requirement on the IPN's bidir
range — not an address the registry protects.

Two consequences:

- Other vendors cannot be expected to avoid the /28 on the strength of a
  standard. The avoidance mechanism is the **operator's domain address plan**
  and RFC 2365 scope boundaries: list `239.255.255.240/28` in the LLD as
  "ACI fabric-internal control group — do not assign", and include it in the
  IPN's bidir range [25]. No configuration knob for the group is documented,
  so it cannot be moved.
- The default GIPo pool has a different status worth knowing: `225.0.0.0/15`
  lies inside the block RFC 3171 lists as **RESERVED**
  (225.0.0.0–231.255.255.255), and its §11 says applications "MUST NOT use
  addressing in the IANA reserved blocks" [27]. Treat GIPo as strictly
  fabric/IPN-internal and never leak or route it into shared networks.

### Glean packet on the wire

Cisco's own glean capture (`tcpdump` on the CPU pseudo-interface, decoded with
`knet_parser.py`) shows, outermost to innermost [22]:

| Layer | Sample contents |
|---|---|
| Outer Ethernet / 802.1Q | dst `0100.5e7f.fff1`, VLAN 2, CoS 5 |
| Outer IPv4 | src = originating TEP (`10.0.116.64` in the sample), dst **239.255.255.241** |
| Outer UDP | dst port **48879**, labelled `ivxlan` in the decode (standard VXLAN is 4789) |
| ACI iVXLAN header | 24-bit **VNID** (`0x2b0000`), 2-byte **PcTag/sClass** (`0x5c0`), flags byte (`dl:1`, source/destination policy-applied bits) |
| Inner Ethernet | dst `ffff.ffff.ffff`, EtherType **0xfff2 (aci-glean)** |
| Inner packet | the original trigger, preserved — here `172.16.1.1 > 172.16.2.2` ICMP echo |

Note the outer group: **.241 = the reserved base .240 plus FTAG 1** — the glean
uses the same FTAG-in-the-last-nibble scheme as any other GIPo, so the base is a
/28 and the wire destination varies within it [22].

**Does it carry the BD?** It carries the **VNID**, which is the forwarding
context: the **BD VNID for bridged traffic** and the **VRF's L3 VNID for routed
traffic**, since ACI assigns one L3 VNID per tenant VRF and, at the egress leaf,
routes from that L3 VNID to the egress subnet's VNID [23]. The sample VNID
(`0x2b0000`) sits in the `0x2xxxxx` range the same deck shows for VRF VNIDs and
the captured flow is routed, which is consistent with an L3 VNID; the deck does
not label the field, so that mapping is inferred from the flow type rather than
documented per case [22].

There is **no separate BD field on the wire**. For a routed glean the egress leaf
matches the destination IP against the BD subnets it has deployed — the event log
reads `Address in PSVI subnet or special VIP` / `Dst IP is in BD subnet` — which
is exactly why only subnet-owning leaves respond [10]. For a same-subnet,
ARP-triggered glean the VNID would be the BD VNID; that follows from the L2
forwarding model but is **not** shown in the available captures [22], [23].

Switch-internal headers carry more than the wire does: a capture on the CPU
pseudo-interface shows an `ieth` header with `bd:0x120e`, `outer_bd:0x27` and
`sup_code: ISTACK_SUP_CODE_SPINE_GLEAN(0x21)`. Those are internal ASIC/CPU
metadata, not fabric fields. In practice, `tcpdump -xxxvei kpm_inb ether proto
0xfff2` is the quick way to see gleans, and `knet_parser.py` decodes them [22].

Decode order at the egress leaf, and what each field can and cannot tell it:

1. **Outer IP destination** = the glean group (`239.255.255.240/28` + FTAG) —
   this only gets the packet onto the fabric's multicast tree, so every member
   switch receives it. It says nothing about which BD or VRF.
2. **VXLAN (iVXLAN) VNID** — the tenant context: the **BD VNID** for bridged
   traffic, the **VRF's L3 VNID** for routed traffic [23].
3. **Inner EtherType `0xfff2`** — this is what marks the payload as a **glean**
   rather than tenant data. The VNID alone does not say "glean"; a normal
   VXLAN-encapsulated tenant frame differs only here (and in being punted to
   the CPU instead of bridged to ports).
4. **Inner destination IP vs locally deployed subnets** — only for a routed
   glean, this is what selects the BD whose SVI sources the ARP [10].

So "the leaf reads its BD from the header" holds for a bridged glean (VNID is
the BD VNID) but not for a routed one, where VNID gives the VRF and the BD comes
from step 4. Two practical corollaries: a generic VXLAN decoder will not
interpret the payload without the custom EtherType (hence `knet_parser.py`), and
the fact that a leaf can receive the packet says nothing about whether it will
act on it — membership in the group is fabric-wide, action is subnet-local.

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
Multi-Pod, the IPN must carry the reserved glean multicast group defined above
[10].

### Source and version notes

Doc 222179's overview describes routed-IP gleaning while its "Use Case 2"
different-BD example says gleaning is not relevant. The wording is unresolved;
no known-destination assumption should be inferred [9], [13], [14].

The endpoint-learning white paper was rechecked on **2026-10-16**. Although its
page update is June 9, 2026, it explicitly scopes feature coverage to **5.2(1g)**.
It therefore does not establish an introduction in 1.0(1e), or unchanged behavior
through 6.2(2). Those historical/current-release assertions remain unverified [9].
The 6.2(x) Fundamentals guide confirms current distributed-gateway and FTAG
architecture; it is not proof that every historical glean detail is unchanged
[12].

## Multi-Pod: the Inter-Pod Network (IPN)

The IPN is **not a leaf or a spine of the ACI fabric**. It is the routed
infrastructure that joins the pods: Cisco describes it as "connecting the different
ACI Pods … an extension of the ACI fabric underlay infrastructure" [14].

- **Any device that meets the requirements can be the IPN.** Cisco recommends
  standalone Cisco Nexus 9200 or Nexus 9300 second-generation (EX or newer) switches,
  as those are the platforms most often deployed and validated [14]. IPN devices are
  configured outside APIC — the white paper explicitly leaves IPN configuration out of
  scope — so they are not fabric nodes with a leaf/spine role.
- **Control plane:** each pod's spines establish **OSPF** peerings with the directly
  connected IPN devices and advertise the local pod's TEP-pool prefix; the IPNs install
  equal-cost routes for every pod's TEP pool, and the prefixes received for remote pods
  are redistributed into the pod's IS-IS so leaves can reach them [14]. Only a few
  spine loopback host routes go into the IPN; leaf loopbacks never do, which keeps the
  IPN routing table small [14].
- **Multicast requirement:** the IPN must carry the fabric's GIPo range and the reserved
  glean group with PIM **bidir** — see the GIPo rules above [25].
- **It can be a generic L3 service:** as long as the requirements are met, an MPLS
  network or other routed infrastructure can act as the IPN [14].
- **From APIC 5.2(3) the IPN can be removed** for small deployments: *Multi-Pod Spines
  Back-to-Back* connects the spines of two pods directly, with no external devices to
  configure [14].

For figure work this means the IPN must not be drawn or coloured as a leaf unless the
platform's own documentation makes it one: in ACI it is a separate routed domain, while
in Huawei CloudFabric the IPN switches are fabric leaf switches with a special role — see
[the Digital Map POC record](../pocs/2026-11-digital-map-multivendor-dc.md).

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

## Advertise Host Routes

A per-BD option that makes border leaves advertise endpoint /32 and /128 routes out of
an L3Out, so traffic enters at the pod where the endpoint lives [32]:

- **Requirements**: the BD is associated with the L3Out (or an explicit route map
  matches the BD subnets), the BD subnet is **Advertised Externally**, and a contract
  exists between the BD's EPG and the L3Out's external EPG. Without the contract the
  border leaf installs neither the subnet nor the host routes. Gen 2 or later leaves
  (EX/FX/FX2) [32].
- **Pod scope**: a border leaf advertises only endpoints learned in its own pod, never
  between pods or sites; on an endpoint move the fabric withdraws the route in the old
  pod and advertises it in the new one [32]. This is the Multi-Pod ingress-alignment
  tool referred to in
  [multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md#cross-cutting-judgment).
- **Side effects**: host routes carry the VRF transit route tag, which external routers
  must preserve; a custom route-map tag can no longer be set on the BD subnet; enabling
  it marks the BD subnet public, so a rogue endpoint is advertised too [32].

A migration that keeps pod-local ingress must reproduce this on the target fabric, and
the external routers' policy that depends on the /32s must be carried across.

## ACI Border Gateway (Heterogeneous Fabric Interconnect)

ACI 6.1(x) introduced the **ACI Border Gateway (BGW)** — dedicated Nexus 9000
FX2/FX2P/GX/GX2+ leaf nodes that bridge ACI's internal COOP control plane to
external MP-BGP EVPN [8]. This is the mechanism for connecting an ACI fabric to
any standards-compliant VXLAN EVPN fabric, including NX-OS EVPN-VXLAN Multi-Site,
Arista, Juniper, and **Huawei CloudFabric** (see
[huawei/cloudfabric.md](../huawei/cloudfabric.md#dci-and-cross-vendor-interconnect)).

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

- **Huawei CloudFabric**: See [huawei/cloudfabric.md](../huawei/cloudfabric.md#dci-and-cross-vendor-interconnect)
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

[12] "Forwarding Within the ACI Fabric," Cisco Application Centric
Infrastructure Fundamentals, Release 6.2(x), updated Mar. 25, 2026. [Online].
Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/aci-fundamentals/cisco-aci-fundamentals-62x/fundamentals-62x.html
— verify "Layer 3 VNIDs Facilitate Transporting Inter-subnet Tenant Traffic"
and "Multicast Tree Topology": distributed gateway, FTAG assignment in the
multicast destination address, and configurable roots with multiple tree roots
possible on one spine. Rechecked Oct. 16, 2026.

[13] S. Garg, "Understand ARP Flooding and ARP Gleaning in ACI," Cisco TAC,
Doc ID 222179, updated July 23, 2024. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/technical-details/222179-understand-arp-flooding-and-arp-gleaning.html
— verify "Understanding ARP Flooding," use cases 3–5, and "Understanding ARP
Gleaning," requirements and both use cases. Rechecked Oct. 16, 2026.
The final example's explanation conflicts with the overview if treated as
a general rule; its intended endpoint-resolution assumption is unconfirmed.
Both gleaning workflow diagrams were visually inspected on recheck.
No specific current software release is stated for these workflows.

[14] "ACI Multi-Pod White Paper," Cisco, updated May 9, 2022, discussion
around Figures 35–36 in "Inter-Pods VXLAN Data Plane." [Online]. Available:
https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-737855.html
— independent definition of ACI ARP gleaning as fabric-generated ARP from
the BD IP to resolve an unknown endpoint, and, in "Inter-Pod Connectivity Deployment
Considerations" and "IPN Control Plane," the definition and control-plane role of the
Inter-Pod Network (IPN). Rechecked Oct. 16, 2026 for terminology and Nov. 7, 2026 for the
IPN sections; not a blanket validation of current-release implementation details.

[15] "Bridge Domains and Subnets," Cisco APIC Layer 2 Networking Configuration
Guide, Release 6.2(x), updated July 7, 2026. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l2-configuration/cisco-apic-layer-2-networking-configuration-guide-62x/bridging-62x/bridge-domain-subnets.html
— verify "Bridge domain options" and the packet-behavior table: L2 Unknown
Unicast is Flood or Hardware Proxy; in flood mode L2 unknown unicast is flooded
over the multicast tree of the bridge domain (GIPo); optimized mode =
hardware-proxy, where frames go to the spine-proxy anycast VTEP address;
switching flood to hw-proxy is disruptive to traffic in the BD. Checked 2026-10-19.

[16] "Forwarding Within the ACI Fabric," Cisco ACI Fundamentals, Release
6.2(x), updated Mar. 25, 2026 — "Multicast Tree Topology" and "Traffic storm
control" sections. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/aci-fundamentals/cisco-aci-fundamentals-62x/fundamentals-62x.html
— verify "Multicast Tree Topology": ingress leaf assigns the FTAG and encodes
it in the destination multicast address; one tree per FTAG ID; only one link
forwards per FTAG between any two nodes; up to 12 FTAGs; roots APIC-configured
during bring-up, multiple roots possible on one spine, not re-rooted on
run-time events such as a spine failure, trees recalculated on topology change.
Also verify "Traffic storm control": the statement that BD Layer 2
unknown-unicast flooding "is enabled by default within the BD but can be
disabled by an administrator," and that storm control covers L2 unknown unicast
only when that flooding is enabled. Checked 2026-10-19. The default statement
conflicts with [15] and [18].

[17] "Configure the L2 Multicast in ACI," Cisco Support, Doc ID 217712.
[Online]. Available:
https://www.cisco.com/c/en/us/support/docs/software/aci-data-center/217712-configure-the-l2-multicast-in-aci.html
— verify the verification section: FTAG IDs assigned by the payload hash
algorithm (0 to 12), value unpredictable and not the same even for the same
leaf and destination BD GIPo; the GIPo's low four bits select the tree; `show
isis internal mcast routes gipo`. Also verify the Background Information
statement that with multiple EPGs sharing one BD, L2 multicast floods in all
EPGs regardless of contracts. Checked 2026-10-19. Lab scope: Release 4.2(7q)
on N9K-C93180YC-FX; CLI field names are version-scoped.

[18] "Cisco ACI Best Practices Quick Summary," Cisco — "L2 Unknown Unicast"
section. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-aci-best-practices-quick-summary.html
— L2 Unknown Unicast decides between flooding frames for an unknown MAC and
sending them to a spine for COOP lookup; best practice is Flood when unicast
routing is disabled or when L2 is extended through non-ACI switches; GUI path
Tenant > Networking > Bridge Domains > Policy > General. Checked 2026-10-19.

[19] "Flood in Encapsulation for All Protocols and Proxy ARP Across
Encapsulations," Cisco APIC Layer 2 Networking Configuration Guide, Release
6.2(x), updated July 7, 2026. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l2-configuration/cisco-apic-layer-2-networking-configuration-guide-62x/bridging-62x/flood-in-encapsulation-for-all-protocols.html
— verify: ACI uses the BD as the L2 broadcast boundary; a BD can contain
multiple EPGs and "ordinarily ... broadcast flooding sends traffic to all the
EPGs in the bridge domain"; flood in encapsulation limits flooding to a single
encapsulation and enables proxy ARP between EPGs of the same BD; requires a BD
subnet and IP routing; from APIC 3.1(1) on EX/FX-and-later all protocols
(ARP, GARP, BUM) are flooded in encapsulation; VXLAN-encapsulated EPGs
supported from 3.2(5); EPG-level setting takes precedence over BD-level, with
the four-way behavior matrix (Table 1); GUI paths
BD Policy > General > Multi Destination Flooding and EPG Policy > General >
Flood in Encapsulation; NX-OS-style CLI `multi-destination encap-flood` (BD)
and `flood-on-encapsulation` (EPG); the service-node/load-balancer example
where proxy ARP and flood in encapsulation do not take place. Checked 2026-10-19.

[20] "VRF GIPo Allocation," Cisco APIC Layer 3 Networking Configuration Guide,
Release 6.2(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-62x/ip-multicast-layer3-config-62x/allocating-vrf-gipo.html
— verify: one GIPo for the VRF and one for every BD under it; GIPo sharing
allowed between multiple BDs or multiple VRFs but not a mix; APIC ascertains
the allocation and IS-IS builds the GIPo trees; the GIPo usage table
(broadcast and unknown-unicast flood always use the BD GIPo; multicast uses
the VRF GIPo once PIM/PIM6 is enabled on the BD); the displayed address is
always a /28 network address with the last four bits zero, and the wire
destination inside that /28 selects one of 16 FTAG trees. Checked 2026-10-19.

[21] "Tenant Routed Multicast," Cisco APIC Layer 3 Networking Configuration
Guide, Release 6.2(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-62x/ip-multicast-layer3-config-62x/l3-multicast.html
— verify "Traffic forwarding differences": the VRF GIPo is programmed on all
leaf switches where the VRF is deployed, TRM packets are received by all of
them, and remote leaf switches use unicast head-end replication instead.
Checked 2026-10-19.

[22] J. Young, "ACI Technical Leader," Cisco Live EMEA 2023, BRKDCN-3900 —
slides "Overlay iVXLAN" (15), "Capturing a Glean with Tcpdump" (36), and
"Layer 3 Unicast – Glean Scenario" (38). [Online]. Available:
https://www.ciscolive.com/c/dam/r/ciscolive/emea/docs/2023/pdf/BRKDCN-3900.pdf
— verify the iVXLAN header layout (VNID 3 bytes, PcTag/sClass 2 bytes, flags
byte with bit 4 source-policy applied, bit 5 destination-policy applied, bit 7
don't-learn); the glean capture (outer dst 239.255.255.241, outer UDP 48879,
VNID 0x2b0000, inner EtherType 0xfff2 aci-glean, preserved inner ICMP, ieth
fields bd/outer_bd and ISTACK_SUP_CODE_SPINE_GLEAN); the kpm_inb tcpdump filter
and knet_parser.py decode; and the egress-leaf event log lines "Received pkt
Fabric-Glean: 1" and "Address in PSVI subnet or special VIP." Checked 2026-10-19.
The 2025 edition carries the same slide:
https://www.ciscolive.com/c/dam/r/ciscolive/emea/docs/2025/pdf/BRKDCN-3900.pdf
Conference deck: slide numbers may shift between editions.

[23] "Layer 3 VNIDs Facilitate Transporting Inter-subnet Tenant Traffic,"
Cisco APIC Layer 3 Networking Configuration Guide, Release 6.2(x). [Online].
Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-62x/aci-forwarding-layer3-config-62x/l3-vnids-facilitate-transport-intersubnet-tenant-traffic.html
— verify: "For each tenant VRF, ACI assigns a single L3 VNID. Traffic is
transported across the fabric according to the L3 VNID, and at the egress leaf
switch, ACI routes the packet from the L3 VNID to the VNID of the egress
subnet." Checked 2026-10-19.

[24] "Initial Setup," Cisco APIC Getting Started Guide, Release 6.1(x).
[Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/getting-started/cisco-apic-getting-started-guide-61x/initial-setup-60x.html
— verify the setup table rows: "IP address pool for bridge domain multicast
address (GIPo) … 225.0.0.0/15. Valid range: 225.0.0.0/15 to 231.254.0.0/15,
prefixlen must be 15 (128k IPs)," and the note that the GIPo address can be the
same across Multi-Site sites; and "IP address pool for tunnel endpoint
addresses … 10.0.0.0/16 … for the infrastructure VRF only." Checked 2026-10-19
(6.1(x) edition; confirm the prompt and defaults in the target release).

[25] "Configure Multi-Pod Provisioning," Cisco APIC Layer 3 Networking
Configuration Guide, Release 6.2(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-62x/multipod-layer3-config-62x/configure-multi-pod-provisioning.html
— verify the IPN steps: enable PIM; "Add bridge domain GIPO range as PIM
Bidirectional (bidir) group range (default is 225.0.0.0/15)"; "Add
239.255.255.240/28 as PIM bidir group range"; enable PIM and IGMP on the
interfaces connected to all spines. Checked 2026-10-19.

[26] D. Meyer, "Administratively Scoped IP Multicast," BCP 23, RFC 2365,
July 1998. [Online]. Available:
https://www.rfc-editor.org/rfc/rfc2365.txt — §4 defines the administratively
scoped space as 239.0.0.0–239.255.255.255; §6.1 defines 239.255.0.0/16 as the
IPv4 Local Scope and requires that scoped traffic not be forwarded across a
scope boundary. Checked 2026-10-19.

[27] Z. Albanna, K. Almeroth, D. Meyer, and M. Schipper, "IANA Guidelines for
IPv4 Multicast Address Assignments," BCP 51, RFC 3171, August 2001. [Online].
Available: https://www.rfc-editor.org/rfc/rfc3171.txt — §2 table lists
225.0.0.0–231.255.255.255 as RESERVED and 239/8 as the Administratively Scoped
Block; §9 says 239/8 addresses "are for local use within a domain" and that
"no IANA assignment policy is required"; §11 says applications "MUST NOT use
addressing in the IANA reserved blocks." Checked 2026-10-19.

[28] "IPv4 Multicast Address Space Registry," Internet Assigned Numbers
Authority. [Online]. Available:
https://www.iana.org/assignments/multicast-addresses/ — lists
225.0.0.0–231.255.255.255 as RESERVED and 239.0.0.0–239.255.255.255 as a single
Administratively Scoped block, with no individual entry for
239.255.255.240/28. Checked 2026-10-19.

[29] "Cisco ACI Releases Changes in Behavior," Cisco, ACI release 6.1(2), Table 15
"Cisco APIC release 6.1(2) changes in behavior," Deprecated Features row. [Online].
Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/all/cisco-aci-releases-changes-in-behavior.html
— verify: "The configuration mode and the show running-config command of the Cisco
APIC NX-OS-style CLI is no longer supported. Other functionality on the APIC CLI
such as the EXEC mode and UNIX CLI are still available." The same 6.1(2) cut-off
is stated in "Using the APIC CLI," Cisco APIC NX-OS Style CLI Configuration Guide,
Release 4.2(x) and Later. Checked 2026-11-06 (page revision dated Sep. 9, 2026).

[30] "Cisco Application Policy Infrastructure Controller Release Notes, Release 6.1(2),"
Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/release-notes/cisco-apic-release-notes-612.html
— verify the revision table: "December 4, 2024 — Release 6.1(2f) became available";
"December 13, 2024 — Release 6.1(2g) became available." Checked 2026-11-06.

[31] "Cisco ACI Configuration Files: Import and Export," Cisco knowledge base article.
[Online]. Available:
https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/kb/b_KB_Using_Import_Export_to_Recover_Config_States.html
— verify "Configuring an Export Policy Using the GUI" (Export Policies > Create
Configuration Export Policy; read-only users can trigger exports, added in 4.1(1)),
"Configuring a Remote Location" (FTP/SCP/SFTP), the JSON/XML format choice and the
Snapshot option, "Configuration File Encryption" (secure properties are omitted from
an export when AES encryption is off), and "Configuration Export to Controller" (exports
the user-configurable MO trees from all 32 shards as a tar.gz; empty targetDn means
everything; NX-OS-style `target [infra | fabric | tenant-name]`). Checked 2026-11-06; the article carries no
per-release scope, so confirm the GUI path on the customer's 6.1(x)+ release.

[32] "Advertise host routes," Cisco APIC Layer 3 Networking Configuration Guide,
Release 6.2(x), Routed Connectivity to External Networks. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l3-configuration/cisco-apic-layer-3-networking-configuration-guide-62x/g_routed_connectivity_to_external_networks/advertise-host-routes.html
— verify "Host route advertisement requirements," "Supported switches," "Pod and site
advertisement behavior," and "Shared services and route limitations." Checked
2026-11-06.

[33] "S Commands," Cisco APIC NX-OS Style CLI Command Reference, Release 6.0(x),
updated Feb. 10, 2026. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/command-reference/601/Cisco-APIC-NXOS-CLI-Command-Reference-60x/m_s_cmds.html
— verify the "show endpoints," "show endpoints leaf interface ethernet," "show endpoints
leaf interface port-channel," and "show endpoints vpc" entries (Command Mode: exec).
Checked 2026-11-06. No 6.1(2)-or-later command reference located; the 6.1(x) PDF
(first published 2024-10-25) predates 6.1(2).

[34] "Endpoint Security Groups," Cisco APIC Security Configuration Guide, Release 6.1(x).
[Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/security-configuration/cisco-apic-security-configuration-guide-61x/endpoint-security-groups-61x.html
— verify the statement that "the objects representing endpoints (fvCEp, fvIp) are
dynamically created and deleted based on the endpoint learning status." Checked
2026-11-06 (search-result excerpt; section not read in full).
