# POC: Huawei DSVPN hub with Cisco DMVPN spokes, and DMVPN↔SD-WAN reachability through a dual-ISP hub site

> Based on product documentation, not lab-tested.

## Background

- **Date**: 2026-11
- **Why it matters**: neither Cisco nor Huawei documents a Cisco DMVPN spoke registering with a
  Huawei DSVPN hub. Both implement RFC 2332 NHRP over mGRE, but they differ in defaults,
  authentication encoding and OSPF behaviour ([nhrp.md](../techniques/nhrp.md#cross-vendor--variants),
  [ospf-isis.md](../techniques/ospf-isis.md#cross-vendor--variants)). The hub site also
  hosts a Huawei SD-WAN hub, and the two overlays must reach each other. Every site, hub and
  spokes, connects to the same two MPLS networks: MPLS1 from ISP1 and MPLS2 from ISP2.
  There's no Internet in the design. At the hub, both hubs share the two provider links, each terminated on the
  aggregation switch in its own VRF.
- **Is it possible?** Yes, in principle, if the common subset below is used:
  - IKEv2,
  - ESP in transport mode,
  - explicit OSPF network type, timers and MTU,
  - hub-and-spoke only, so the NHRP redirect/shortcut exchange is never used.

  Another team has reported basic interoperation working, but left no record of what it
  covered. This POC defines "basic" and tests where it ends
  ([Shared feature set](#shared-feature-set)).

  Traffic between the overlays isn't an interop question. Each hub sees the other overlay's
  sites on its **LAN side**, and the AGG and OSPF route between them (Routing design below).
- **Scope**:
  - **In:**
    - IPv4 only, in the underlay and the overlays;
    - one Huawei AR as DSVPN hub;
    - two Cisco IOS XE routers as DMVPN spokes, hub-and-spoke only;
    - one Huawei AR as SD-WAN hub with two SD-WAN spokes, managed by NCE-Campus;
    - one L3 AGG switch holding ISP1 and ISP2 in separate VRFs;
    - OSPF as the routing protocol on the DMVPN overlay and the hub-site LAN.
  - **Out:**
    - spoke-to-spoke tunnels (not required);
    - IKEv1 (excluded: outdated and a security risk; the Huawei hub also needs an extra
      feature package for it [1]);
    - NAT-traversed spokes, IPv6, multicast traffic and multicast routing over the overlays
      (multicast mapping is configured only so OSPF hellos reach the hub), and a second hub of
      either kind.
- **Versions**:
  - DSVPN hub: V600R025C00SPC100, the release in hand.
  - SD-WAN CPEs: per the V100R026C00 version mapping.
  - iMaster NCE-Campus: V300R026C00, solution V100R026C00 [2].
  - Cisco spokes: IOS XE 26.2.1, the current release (31 Aug 2026) [8].
- **Documentation basis**:
  - Huawei: the V600R026C00 AR library [1] and the V100R026C00 solution library [2].
  - Cisco: no IOS XE 26.x router configuration guide for DMVPN or NHRP had been published
    on 2026-11-23. The 17.x router guides [3]–[7] are the latest, and every Cisco command
    here is re-checked on 26.2.1.
  - A difference from the documentation found in the lab is recorded inline.
- **Scenario**: none.

### Shared feature set

"Basic" interoperation means a Cisco spoke registers with the Huawei hub, forms OSPF over
mGRE, and passes traffic under IKEv2: the rows marked Yes in the **Basic?**
column.

| Feature | Cisco DMVPN | Huawei DSVPN | Shared? | Basic? | Tested in |
|---|---|---|---|---|---|
| mGRE encapsulation | `tunnel mode gre multipoint` [5] | `tunnel-protocol gre p2mp` [1] | Yes; on the wire it's plain GRE ([gre.md](../techniques/gre.md#mgre-multipoint-gre)) | Yes | TC-02 |
| NHRP registration (spoke → hub) | `ip nhrp map`, `ip nhrp map multicast`, `ip nhrp nhs` [5] | Hub accepts registrations; `nhrp entry multicast dynamic` [1] | Yes, RFC 2332 types 3/4 | Yes | TC-02, TC-10 |
| NHRP extensions | Responder Address, Transit NHS, Authentication, NAT (type 9) [3] | Not documented | Check in TC-02. Under RFC 2332, a request carrying an unrecognised compulsory extension (C=1) is in error and the responder returns Error Indication code 1 (Unrecognized Extension) | Yes | TC-02 |
| GRE key | Must match in one DMVPN; required when two tunnels share a source [3], [5] | Optional; must match or be absent on both ends [1] | Yes | Yes | TC-02, TC-09 |
| Hold time / registration | `ip nhrp holdtime`, `ip nhrp registration timeout` [3] | Hub `nhrp entry holdtime` [1] | Set explicitly | Yes | TC-10 |
| NHRP authentication | Cleartext string [3] | Plaintext without `hash`; hashed forms (MD5, SHA-1, SHA2 HMAC) and a "standard" option [1] | Plaintext only; Cisco has no hashed form | No | TC-09 |
| Purge / Error Indication (types 5–7) | Purge Request / Reply supported [3] | Not documented | Check in TC-12; affects recovery time only | No | TC-12 |
| Spoke-to-spoke (redirect / shortcut) | Phase 2/3 [3], [4] | Non-shortcut / shortcut [1] | **Not used** | No | TC-05 (confirms absence) |
| IKEv2 with PSK, unknown peers | Wildcard keyring [6], [7] | IKE peer without remote address in an IPsec profile; IKEv2 by default [1] | Yes | Yes | TC-03 |
| IPsec mode | Transport recommended [5] | Default **tunnel**; `encapsulation-mode transport` [1] | Yes, once Huawei is set to transport | Yes | TC-03 |
| OSPF on mGRE | Point-to-multipoint; filter /32s [5]. Hellos need `ip nhrp map multicast <hub NBMA>` [5] | `ospf network-type p2mp` in every DSVPN example [1]; hellos need `nhrp entry multicast dynamic` [1] | Yes, with explicit timers and MTU. Multicast mapping is configured for OSPF hellos only; multicast isn't tested otherwise | Yes | TC-04 |
| Front-door VRF | `tunnel vrf` [6] | `source vpn-instance` [1] | Hub side only (Huawei) | Yes | TC-01, TC-02 |

### Design decisions

| Area | Decision | Why |
|---|---|---|
| Topology | Hub-and-spoke only: no `nhrp redirect` on the hub, no shortcut on the spokes | No spoke-to-spoke requirement. OSPF P2MP makes the hub the next hop for everything, so spokes never send Resolution Requests ([nhrp.md](../techniques/nhrp.md#operation)) |
| ISPs | Two MPLS networks at every site, MPLS1 (ISP1) and MPLS2 (ISP2); no Internet. Two DMVPN clouds on the DSVPN hub: Tunnel10 over ISP1, Tunnel20 over ISP2. Each Cisco spoke sources Tunnel10 from its ISP1 link and Tunnel20 from its ISP2 link. Two WAN links on the SD-WAN hub and on each SD-WAN spoke | One cloud per ISP keeps each failure domain separate; OSPF cost picks the primary |
| Routing | OSPF throughout. DMVPN overlay in area 1, DSVPN hub as ABR. Hub-site LAN (AGG VRF `corp`) in area 0. SD-WAN hub runs NCE LAN-side OSPF in area 0 | User decision. One IGP lets the two overlays learn each other without redistribution on the DSVPN hub. The SD-WAN hub does the only BGP↔OSPF exchange, which NCE manages [2] |
| Area 1 type | Normal area, no default route into it | The spokes' routes to the hub WAN subnets must stay pointed at their providers: a default via the tunnel would pull the tunnel's own underlay into it (recursive routing, [gre.md](../techniques/gre.md#design-considerations)). A stub area would inject exactly that default |
| Summaries | DSVPN hub `abr-summary 10.11.0.0 255.255.0.0` (area 1 → area 0). SD-WAN hub overlay route summarization 10.21.0.0/16 (externals into OSPF) [2] | One route per overlay crosses the AGG; spoke flaps stay inside their own overlay |
| OSPF on the tunnels | P2MP on both ends; hello 10 s / dead 40 s set explicitly; `ospf mtu-enable` on the hub | Huawei P2MP defaults are 30/120 s [1], so set both ends. Huawei sends MTU 0 in DD packets by default, which can make a non-Huawei neighbour drop LSUs [1], [2] |
| IKE / IPsec | IKEv2 only, PSK; AES-256-CBC / SHA2-256 / DH 14; ESP transport | User decision on IKEv2. Transport is Cisco's DMVPN recommendation [5] and used in Huawei's cross-network DSVPN example [1]. Cisco warns against wildcard PSKs in production: move to certificates after the POC [5] |
| GRE keys | Tunnel10 key 101, Tunnel20 key 102, on hub and spokes | Each spoke tunnel has its own source, so Cisco doesn't require unique keys here [3]. Separate keys still keep a packet from one cloud from landing on the other cloud's tunnel |
| Hold time | 600 s everywhere; Cisco registration timeout 200 s | Defaults differ (Huawei 7200 s; Cisco documents 7200 s and 600 s) [1], [3] |
| Underlay | Per provider: a /30 MPLS access link to the AGG in VRF `ispN` and to every spoke, plus a hub subnet the provider routes to the AGG's /30 address. Each hub uses three physical ports to the AGG: MPLS1 and MPLS2 WAN ports in matching VPN instances, and a LAN port in `corp`. Spokes route each hub subnet via the matching provider | Access links are /30, so the hubs' WAN addresses come from a separate subnet the provider must route. The two provider networks aren't connected, so each tunnel must leave by its own provider's link |

## Test environment

### Topology

[Figure 1 — POC topology: every site has an MPLS link to each of the same two providers; at the hub site the DSVPN hub and the SD-WAN hub share both through the AGG](2026-11-dsvpn-hub-dmvpn-spokes-sdwan-fig1.drawio)

Each Cisco spoke has two mGRE tunnels to the DSVPN hub: Tunnel10 from its ISP1 link to the
hub's ISP1 address, and Tunnel20 from its ISP2 link to the hub's ISP2 address. The figure
draws them as one line per spoke. Each hub uses three separate physical ports to the AGG,
one per kind of link: MPLS1 (`isp1`), MPLS2 (`isp2`) and LAN (`corp`). NCE-Campus manages
the SD-WAN hub and spokes and has no data-plane link.

### Device list

| Role | Vendor | Model | Software version |
|---|---|---|---|
| DSVPN hub | Huawei | AR6710-H (AR6710-H4T4X2Y7). DSVPN is licensed and model-limited; this model is in the DSVPN model list [1] | V600R025C00SPC100 |
| DMVPN spoke ×2 | Cisco | Any mainstream IOS XE access router, for example Catalyst 8200 / 8300 edge [8] | IOS XE 26.2.1 |
| SD-WAN hub | Huawei | AR6710-H (AR6710-H4T4X2Y7); in the SD-WAN EVPN model list [1] | Per V100R026C00 version mapping |
| SD-WAN spoke ×2 | Huawei | AR5710-H4T4N2X; in the SD-WAN EVPN model list [1] | Per V100R026C00 version mapping |
| Controller | Huawei | iMaster NCE-Campus | V300R026C00 (solution V100R026C00) [2] |
| Aggregation | Any | Any L3 switch with VRFs and OSPF in a VRF, for example a Huawei S5755-H | — |
| ISP1, ISP2 MPLS emulation | any | One PE router per provider, with a /30 to the AGG and to every spoke, and a static route to its hub subnet | — |

### Network plan

WAN addresses are documentation ranges (RFC 5737); replace them with the provider-assigned
values.

**Underlay, per provider: MPLS1 (ISP1) and MPLS2 (ISP2).** The provider assigns each /30 access link and also routes
the hub subnet to the AGG's /30 address. That static route is a request to the provider and
must be in place before TC-01.

| Item | ISP1 (AGG VRF `isp1`) | ISP2 (AGG VRF `isp2`) |
|---|---|---|
| ISP ↔ AGG link | 198.51.100.0/30: ISP .1, AGG .2 | 198.51.100.4/30: ISP .5, AGG .6 |
| Hub subnet, routed by the ISP to the AGG | 203.0.113.0/29 → next hop 198.51.100.2 | 203.0.113.16/29 → next hop 198.51.100.6 |
| AGG VLANIF (hub subnet gateway) | 203.0.113.1 | 203.0.113.17 |
| DSVPN hub WAN (own physical port, VPN instance) | 203.0.113.2 (`isp1`) | 203.0.113.18 (`isp2`) |
| SD-WAN hub WAN link (own physical port, own underlay VPN set by NCE [2]) | 203.0.113.3 | 203.0.113.19 |
| AGG default route in the VRF | 0.0.0.0/0 → 198.51.100.1 | 0.0.0.0/0 → 198.51.100.5 |
| DMVPN Spoke1 access link | 192.0.2.0/30: PE .1, spoke .2 | 192.0.2.128/30: PE .129, spoke .130 |
| DMVPN Spoke2 access link | 192.0.2.4/30: PE .5, spoke .6 | 192.0.2.132/30: PE .133, spoke .134 |
| SD-WAN Spoke1 access link | 192.0.2.8/30: PE .9, spoke .10 | 192.0.2.136/30: PE .137, spoke .138 |
| SD-WAN Spoke2 access link | 192.0.2.12/30: PE .13, spoke .14 | 192.0.2.140/30: PE .141, spoke .142 |
| DMVPN spoke route to the hub subnet | 203.0.113.0/29 → PE .1 / .5 | 203.0.113.16/29 → PE .129 / .133 |

**DMVPN overlay.**

| Item | Value |
|---|---|
| Tunnel sources | Tunnel10: the ISP1 link (Spoke1 192.0.2.2, Spoke2 192.0.2.6). Tunnel20: the ISP2 link (Spoke1 192.0.2.130, Spoke2 192.0.2.134) |
| Cloud 1, Tunnel10 (via ISP1) | 172.16.1.0/24: hub .1, Spoke1 .2, Spoke2 .3; GRE key 101; OSPF cost 10 |
| Cloud 2, Tunnel20 (via ISP2) | 172.16.2.0/24: hub .1, Spoke1 .2, Spoke2 .3; GRE key 102; OSPF cost 100 |
| Tunnel IP MTU / TCP MSS | 1400 / 1360 on every mGRE interface |
| Hold time / registration timeout | 600 s / 200 s |
| IKEv2 | AES-256-CBC, SHA2-256 integrity and PRF, DH 14, PSK |
| ESP | AES-256-CBC + SHA2-256, transport |

**Hub-site LAN and OSPF.**

| Item | Value |
|---|---|
| AGG ↔ DSVPN hub (VRF `corp`, area 0, own physical port) | 10.0.0.0/30: AGG .1, hub .2 |
| AGG ↔ SD-WAN hub (VRF `corp`, area 0, own physical port) | 10.0.0.4/30: AGG .5, hub .6 |
| DC subnets (area 0) | 10.1.0.0/16 |
| DMVPN spoke LANs (area 1) | 10.11.1.0/24, 10.11.2.0/24 → ABR summary 10.11.0.0/16 |
| SD-WAN spoke LANs (EVPN; externals in OSPF) | 10.21.1.0/24, 10.21.2.0/24 → summary 10.21.0.0/16 |
| OSPF process IDs | DSVPN hub 1; AGG one process in VRF `corp`; SD-WAN hub overlay LAN-side process in 1–20000, e.g. 100 [2] |
| Router IDs | DSVPN hub 10.255.0.1, AGG 10.255.0.2, SD-WAN hub 10.255.0.3, Spoke1 10.255.1.1, Spoke2 10.255.1.2 |
| OSPF hello / dead on tunnels | 10 s / 40 s on both ends |

#### Routing design: each overlay is on the other hub's LAN side

Each hub has three sides:

| | DSVPN hub | SD-WAN hub |
|---|---|---|
| **WAN side** (underlay) | WAN interfaces on two dedicated physical ports, in VPN instances `isp1` / `isp2` → AGG VRFs `isp1` / `isp2` → ISPs. Carries only encrypted GRE to the DMVPN spokes | WAN links on two dedicated physical ports. As standard in the solution, NCE puts each WAN interface in its own underlay VPN (VRF), apart from the control VPN (RR session) and the service VPN (LAN) [2] → the same AGG VRFs → ISPs. Carries only SD-WAN tunnels (GRE + IPsec) to the SD-WAN spokes [1] |
| **Overlay side** (its own sites) | mGRE Tunnel10/20, OSPF area 1: the DMVPN spokes | SD-WAN EVPN in the VN: the SD-WAN spokes, routes via the RR [1] |
| **LAN side** | Area 0 link to AGG VRF `corp`. Behind it: the DC **and the SD-WAN sites** | NCE LAN-side OSPF to AGG VRF `corp`. Behind it: the DC **and the DMVPN sites** |

The two overlays never touch each other's underlay or control plane. They exchange routes
only through OSPF in AGG VRF `corp`, and only the SD-WAN hub converts between protocols.

**DMVPN sites → SD-WAN sites (route flow):**
1. Spoke1/Spoke2 advertise 10.11.x.0/24 in area 1 over both tunnels.
2. The DSVPN hub (ABR) summarises them as 10.11.0.0/16 into area 0.
3. The AGG floods the summary to the SD-WAN hub.
4. The SD-WAN hub's LAN-side OSPF imports it into BGP ("bidirectional route import between
   BGP and LAN OSPF", which must stay enabled [2]). It is then advertised as an EVPN IP prefix
   route to the RR, which reflects it to the SD-WAN spokes [1].

**SD-WAN sites → DMVPN sites:**
1. The SD-WAN spokes' 10.21.x.0/24 reach the SD-WAN hub as EVPN routes [1].
2. The SD-WAN hub redistributes them into OSPF as one external summary, 10.21.0.0/16, with a
   local tag (NCE requires a tag on routing policies [2]).
3. The AGG floods it in area 0. The DSVPN hub floods it into area 1, a normal area, so
   type-5 LSAs pass.
4. The spokes install 10.21.0.0/16 via 172.16.1.1 on Tunnel10 (cost 10), with Tunnel20 as
   backup.

**Packet walk, DMVPN Spoke1 host → SD-WAN Spoke1 host:**
1. Spoke1 matches 10.21.0.0/16 via 172.16.1.1 on Tunnel10. It encapsulates in GRE (key 101)
   to 203.0.113.2, applies ESP in transport mode, and sends to ISP1.
2. ISP1 routes 203.0.113.0/29 to the AGG; AGG VRF `isp1` delivers it to the DSVPN hub WAN.
3. The DSVPN hub decrypts and decapsulates, then routes the inner packet in its public
   instance out the LAN link to 10.0.0.1. No redirect is sent: the packet leaves on the LAN
   side, not back into the overlay
   ([nhrp.md](../techniques/nhrp.md#design-considerations)).
4. AGG VRF `corp` routes 10.21.0.0/16 to 10.0.0.6.
5. The SD-WAN hub looks up the VN's EVPN route and sends it over the SD-WAN tunnel to SD-WAN
   Spoke1. The tunnel is GRE with key = VN ID, inside IPsec [1], leaving via AGG VRF `isp1`
   or `isp2`, as NCE steering decides.

The return path is the mirror image.

**Loop and leak controls:**
- VRFs `isp1`/`isp2` and `corp` are never leaked into each other on the AGG.
- No hub advertises its WAN subnets into OSPF.
- Only the SD-WAN hub redistributes, and with a tag. A second SD-WAN hub added later must
  filter on that tag, or LAN routes can loop through the overlay. NCE documents such a
  hub-to-hub leak and its community-based fix [2].

## Test cases

### TC-01: Underlay, ISP routing and VRF separation

**Objective**: each hub is reachable from every spoke over both providers' MPLS networks,
each in its own VRF, and VRF `corp` has no route from either provider VRF.

**Prerequisites**: both ISPs have configured the static route for their hub subnet towards
the AGG's /30 address.

**Procedure**:
1. AGG:
   - VRF `isp1`: the ISP1 /30 and VLANIF 203.0.113.1/29, default route to 198.51.100.1.
   - VRF `isp2`: the ISP2 /30 and VLANIF 203.0.113.17/29, default route to 198.51.100.5.
   - VRF `corp`: both hub LAN links and the DC.
2. DSVPN hub:
   ```
   ip vpn-instance isp1
    ipv4-family
   ip vpn-instance isp2
    ipv4-family
   interface <WAN-ISP1>
    ip binding vpn-instance isp1
    ip address 203.0.113.2 29
   interface <WAN-ISP2>
    ip binding vpn-instance isp2
    ip address 203.0.113.18 29
   ip route-static vpn-instance isp1 0.0.0.0 0 203.0.113.1
   ip route-static vpn-instance isp2 0.0.0.0 0 203.0.113.17
   ```
   `<WAN-ISP1>` and `<WAN-ISP2>` are two separate physical ports, and the LAN link in `corp`
   (TC-04) is a third.
3. SD-WAN hub: create two NCE WAN links (203.0.113.3 on ISP1, 203.0.113.19 on ISP2), as in the
   AR6700V-L POC's TC-03/04 flow. As on the DSVPN hub, use three separate physical ports to
   the AGG: MPLS1 WAN, MPLS2 WAN and the LAN link in `corp`. NCE deploys each WAN interface
   in its own underlay VPN [2]: check with `display ip vpn-instance` that the two WAN
   interfaces sit in different VPN instances, separate from the LAN interface.
4. On the AGG, check that each of the six hub-facing ports sits only in its own VRF.
5. Each DMVPN spoke: a static route to 203.0.113.0/29 via its ISP1 PE and to 203.0.113.16/29
   via its ISP2 PE. Ping 203.0.113.2 sourced from the ISP1 link and 203.0.113.18 from the
   ISP2 link. On the AGG, check that VRF `corp` holds no default route and no 203.0.113.x
   route.

**Expected result**: both hub addresses are reachable from the spokes over the matching ISP;
`corp` holds internal prefixes only.

**If it fails**:
- A hub address is unreachable from outside, but the ISP-side /30 answers: the ISP hasn't
  routed the hub subnet to the AGG.
- `corp` has a default route: leaking on the AGG.

### TC-02: NHRP registration of Cisco spokes on both clouds (no IPsec)

**Objective**: both Cisco spokes register with the Huawei hub on Tunnel10 and Tunnel20.

**Prerequisites**: TC-01 passed; DSVPN licence active on the hub [1].

**Procedure**:
1. Hub. Tunnel20 is the same, with 172.16.2.1, `isp2`, 203.0.113.18 and key 102.
   ```
   nhrp enable
   interface Tunnel10
    ip address 172.16.1.1 24
    tunnel-protocol gre p2mp
    source vpn-instance isp1 203.0.113.2
    gre key simple 101
    nhrp enable
    nhrp entry multicast dynamic
    nhrp entry holdtime 600
   ```
   Set `tunnel-protocol` before anything else: changing it deletes the source and NHRP
   settings [1]. Leave `nhrp redirect` off; it is off by default [1].
2. Spoke1. Spoke2 is the same with .3; Tunnel20 is the same with 172.16.2.x, 203.0.113.18,
   key 102 and the ISP2 link as source.
   ```
   interface Tunnel10
    ip address 172.16.1.2 255.255.255.0
    ip mtu 1400
    ip tcp adjust-mss 1360
    ip nhrp network-id 10
    ip nhrp map 172.16.1.1 203.0.113.2
    ip nhrp map multicast 203.0.113.2
    ip nhrp nhs 172.16.1.1
    ip nhrp holdtime 600
    ip nhrp registration timeout 200
    tunnel source <WAN-ISP1>
    tunnel mode gre multipoint
    tunnel key 101
   ```
3. Capture the registration exchange on the hub, in user view:
   ```
   capture-packet local-host interface <WAN-ISP1> destination file nhrp1.cap packet-len 1500
   ```
   Open `nhrp1.cap` in Wireshark. Above 64 bytes, `packet-len` needs the packet capture
   feature package; the 64-byte default cuts each packet off before the NHRP extensions [1].
   Without the package, mirror the hub's WAN port on the AGG to a capture PC instead.
4. Hub: `display nhrp peer all`. Spokes: `show ip nhrp`, `show ip nhrp nhs detail`.

**Expected result**:
- The hub lists each spoke twice, as Type `registered` with Flag `up`, one entry per tunnel
  interface [1].
- The spokes show both NHSs up.
- The capture shows GRE Protocol Type 0x2001 carrying NHRP types 3/4, with the GRE key
  present ([nhrp.md](../techniques/nhrp.md#packet-format)).
- Registration Replies carry CIE code 0.
- Check the extension part of the NHRP packets in the capture, and record the extension
  types each side sends, in order, with the C bit.

**If it fails**:
- No reply on one cloud: check that the GRE key matches on that cloud, and that the request
  arrived in the right VPN instance. A tunnel source in a VPN instance isn't shown in Huawei's
  DSVPN examples.
- A reply with a non-zero Code: decode it from the capture.
- NHS flapping: Cisco declares an NHS down after three retransmissions (7 s) [3].

### TC-03: IKEv2 / IPsec transport mode on both clouds

**Objective**: every hub–spoke GRE packet, NHRP and OSPF included, is protected by ESP in
transport mode on both clouds.

**Prerequisites**: TC-02 passed.

**Procedure**:
1. Hub:
   ```
   ike proposal 1
    encryption-algorithm aes-256
    authentication-algorithm sha2-256
    dh group14
   ike peer dmvpn
    ike-proposal 1
    pre-shared-key <psk>
   ipsec proposal p1
    transform esp
    encapsulation-mode transport
    esp authentication-algorithm sha2-256
    esp encryption-algorithm aes-256
   ipsec profile dmvpn
    ike-peer dmvpn
    proposal p1
   interface Tunnel10
    ipsec profile dmvpn
   interface Tunnel20
    ipsec profile dmvpn
   ```
   - No `shared`: each tunnel has its own source interface and VPN instance, and `shared` is
     needed only when tunnels share an outbound interface [1].
   - If negotiation in a VPN instance fails, add `sa binding vpn-instance` on the IKE peer:
     Huawei's IPsec-in-VPN-instance example uses it [1], but no DSVPN example does. With two
     VPN instances that means two IKE peers and two profiles.
2. Each spoke:
   ```
   crypto ikev2 proposal P1
    encryption aes-cbc-256
    integrity sha256
    prf sha256
    group 14
   crypto ikev2 policy POL1
    proposal P1
   crypto ikev2 keyring KR
    peer ANY
     address 0.0.0.0 0.0.0.0
     pre-shared-key <psk>
   crypto ikev2 profile DMVPN
    match identity remote address 0.0.0.0
    authentication remote pre-share
    authentication local pre-share
    keyring local KR
   crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
    mode transport
   crypto ipsec profile DMVPN
    set transform-set TS
    set ikev2-profile DMVPN
   interface Tunnel10
    tunnel protection ipsec profile DMVPN
   interface Tunnel20
    tunnel protection ipsec profile DMVPN
   ```
   - Cisco documents the wildcard keyring and the transport transform set [6], [7]. It does
     not document the wildcard form of `match identity remote address`; adjust it to the
     hub's IKE identity if the profile isn't selected.
   - The two spoke tunnels have different sources and destinations, so each gets its own
     IPsec SA without `shared`.
3. Hub: `display ike sa`, `display ipsec sa`; check that `display nhrp peer all` shows
   `Ipsec state: up`. Spokes: `show crypto ikev2 sa`, `show crypto ipsec sa`.

**Expected result**:
- Two IKEv2 SAs per spoke, one per cloud.
- ESP SAs whose flow is GRE (protocol 47) between the WAN addresses, in Transport mode.
  Huawei's own example shows that flow in tunnel mode, its default [1].
- Only ESP on the wire between the hub and the spokes.

**If it fails**:
- Mode mismatch: Huawei left at the default tunnel mode. With IKEv2, every proposal on an
  initiator must use the same mode [1].
- Cisco profile not selected: overlapping profiles mean no profile is selected [7].

### TC-04: OSPF over the DMVPN overlay

**Objective**: full OSPF adjacencies on both clouds, with explicit P2MP, timers and MTU, and
complete LSDB exchange.

**Prerequisites**: TC-03 passed.

**Procedure**:
1. Hub (Tunnel20 is the same, with `ospf cost 100`):
   ```
   ospf 1 router-id 10.255.0.1
    area 0.0.0.1
     network 172.16.1.0 0.0.0.255
     network 172.16.2.0 0.0.0.255
     abr-summary 10.11.0.0 255.255.0.0
   interface Tunnel10
    ospf network-type p2mp
    ospf timer hello 10
    ospf timer dead 40
    ospf mtu-enable
    ospf cost 10
   ```
2. Spokes (Tunnel20 is the same, with `ip ospf cost 100`):
   ```
   router ospf 1
    router-id 10.255.1.1
   interface Tunnel10
    ip ospf 1 area 1
    ip ospf network point-to-multipoint
    ip ospf hello-interval 10
    ip ospf dead-interval 40
    ip ospf cost 10
   interface <LAN>
    ip ospf 1 area 1
   ```
   Never put the WAN interface in OSPF.
3. Cisco recommends blocking the OSPF /32 routes when using point-to-multipoint [5]. Run once
   without a filter and once with an inbound filter for 172.16.0.0/16 /32s on the spokes;
   record whether either affects forwarding.
4. Hub: `display ospf peer`, `display ospf lsdb`, `display ip routing-table protocol ospf`.
   Spokes: `show ip ospf neighbor`, `show ip route ospf`.

**Expected result**:
- Each spoke is FULL with the hub on both tunnels.
- The hub has 10.11.1.0/24 and 10.11.2.0/24 via Tunnel10.
- Spokes have the DC routes and each other's LAN with the hub's tunnel address as next hop,
  preferring Tunnel10.
- MTU check: with `ospf mtu-enable`, a mismatched tunnel MTU keeps the adjacency out of FULL
  [1]. That is intended: fix the MTU, not the check.

**If it fails**:
- No neighbours: check multicast mapping (`nhrp entry multicast dynamic` on the hub [1],
  `ip nhrp map multicast` on spokes [5]), hello/dead values, and network type. Huawei P2MP
  drops hellos whose DR and priority are both non-zero [1].
- FULL, but routes missing: LSUs dropped for MTU. Confirm `ospf mtu-enable` [1], [2].

### TC-05: Hub-and-spoke only — no spoke-to-spoke tunnels

**Objective**: traffic between DMVPN spokes always transits the hub, and no NHRP resolution
takes place.

**Prerequisites**: TC-04 passed.

**Procedure**:
1. Ping and traceroute from 10.11.1.0/24 to 10.11.2.0/24 for several minutes.
2. Spokes: `show ip nhrp` (only the hub entries), `show dmvpn`, `show ip nhrp traffic`
   (resolution counters). Hub: `display nhrp peer all`, `display nhrp statistics`.

**Expected result**:
- The traceroute shows the hub's tunnel address.
- No dynamic spoke entries appear on the spokes, no Resolution Requests are counted, and the
  hub's redirect counters stay at zero.

**If it fails**: if the spokes resolve each other, a route with the other spoke as next hop
exists. Check the OSPF network type: broadcast instead of P2MP keeps the originating spoke as
next hop.

### TC-06: OSPF on the hub-site LAN and route exchange through the SD-WAN hub

**Objective**: the DMVPN summary reaches the SD-WAN spokes, and the SD-WAN summary reaches
the DMVPN spokes, as in the Routing design.

**Prerequisites**: TC-04 passed; SD-WAN hub and spokes online in NCE-Campus V300R026C00 with
one VN.

**Procedure**:
1. AGG, VRF `corp`: OSPF area 0 on 10.0.0.1/30 and 10.0.0.5/30 and the DC.
2. DSVPN hub: area 0 on the LAN link (10.0.0.2/30). Hello and dead must match the AGG.
3. SD-WAN hub, in NCE: **Network Configuration > SD-WAN > Virtual Network > Overlay
   Service**, VN, site, **LAN Route > OSPF > Create** [2]:
   - process 100, router ID 10.255.0.3, area 0 normal;
   - interface toward 10.0.0.5;
   - **Filling MTU** on;
   - **Bidirectional route import between BGP and LAN OSPF** on;
   - **Overlay Route Summarization** 10.21.0.0/16;
   - export and import routing policies with a local tag.
4. Check the tables: AGG `corp`, DSVPN hub, a DMVPN spoke, the SD-WAN hub, and an SD-WAN
   spoke (`display ip routing-table vpn-instance <VN>`).

**Expected result**:
- AGG: 10.11.0.0/16 from the DSVPN hub and 10.21.0.0/16 (external) from the SD-WAN hub.
- DMVPN spokes: 10.21.0.0/16 via the hub on Tunnel10.
- SD-WAN spokes: 10.11.0.0/16 and 10.1.0.0/16 via the SD-WAN hub.
- No specific /24 crosses the AGG.

**If it fails**:
- SD-WAN spokes lack 10.11.0.0/16: bidirectional import is off. With it off, LAN OSPF can't
  advertise to the overlay [2].
- Import policy whitelist without a default-route filter: check what the policy actually
  admits.
- Process ID outside the overlay range: rejected [2].

### TC-07: End-to-end DMVPN site ↔ SD-WAN site traffic

**Objective**: hosts at both kinds of site, and at the DC, reach each other symmetrically
along the packet walk in the Routing design.

**Prerequisites**: TC-06 passed.

**Procedure**:
1. Traffic in both directions: 10.11.1.0/24 ↔ 10.21.1.0/24 and 10.11.2.0/24 ↔ 10.21.2.0/24;
   also each site ↔ 10.1.0.0/16.
2. Traceroute both directions.
3. Capture at the AGG on VRF `corp` (clear text between the hubs) and on VRF `isp1`
   (ESP and SD-WAN tunnels only).

**Expected result**:
- Path: DMVPN spoke → DSVPN hub → AGG `corp` → SD-WAN hub → SD-WAN spoke, and the reverse.
- `corp` carries the user packets in clear text; `isp1` carries only encrypted tunnel
  traffic.
- The DSVPN hub sends no NHRP redirect for these flows.

**If it fails**: asymmetry means another router also advertises 10.21.0.0/16 or 10.11.0.0/16;
compare LSDBs. A loop means a tag filter is missing.

### TC-08: ISP failover

**Objective**: losing either ISP moves each overlay to the other ISP within the OSPF dead
interval (DMVPN) and NCE's link detection (SD-WAN). The VRF separation holds throughout.

**Prerequisites**: TC-07 passed.

**Procedure**:
1. Start continuous pings DMVPN ↔ SD-WAN and DMVPN ↔ DC.
2. Shut the ISP1 link on the AGG. Measure the loss, check that the DMVPN spokes moved to
   Tunnel20, and check the SD-WAN tunnels moved to the ISP2 link.
3. Restore ISP1 and measure the fallback. Repeat with ISP2.
4. Shut only Spoke1's ISP1 link. Spoke1 moves to Tunnel20; Spoke2 stays on Tunnel10.

**Expected result**: DMVPN recovers within about 40 s (the dead interval) and returns to
Tunnel10 after restore. SD-WAN recovers per its link detection. No route leaks into `corp`.

**If it fails**:
- Recovery much slower than 40 s: the hold time on the hub keeps stale NHRP entries. Check
  `display nhrp peer all`.

### TC-09: GRE key and NHRP authentication combinations

**Objective**: confirm which optional NHRP fields the two implementations agree on.

**Prerequisites**: TC-04 passed.

**Procedure**, on Tunnel10 only, checking registration and OSPF after each run:

| Run | GRE key | NHRP auth, hub | NHRP auth, spokes |
|---|---|---|---|
| a (negative) | Hub 101, spokes 999 | none | none |
| b | 101 | `nhrp authentication cipher <str>` (no hash) | `ip nhrp authentication <str>` |
| c | 101 | `nhrp authentication hash sha2-256 cipher <str>` | `ip nhrp authentication <str>` |
| d | 101 | run c + `nhrp authentication standard` | `ip nhrp authentication <str>` |
| e (negative) | 101 | `nhrp authentication cipher <str>` (no hash) | none |
| f (negative) | 101 | none | `ip nhrp authentication <str>` |

Use a string of at most 8 characters, the Huawei plaintext limit [1].

**Expected result**:
- Run a fails silently: GRE packets with a mismatched key are dropped [1], [5].
- Run b passes. In the capture, compare both sides' Authentication extension (type 7). If
  the hub reports the plaintext string as a security risk, that's expected with Cisco
  spokes, not a failure.
- Run c fails: the hub expects a hashed value, and Cisco sends only cleartext [3]. Record
  the hub's log and whether it sends an Error Indication.
- Run d: unknown. Capture the hub's type 7 extension. Expect a failure unless the hub sends
  the string in clear.
- Run e: record whether the hub accepts registrations without an Authentication extension.
- Run f fails on the Cisco side: the hub's replies carry no Authentication extension [3].

**If it fails**: keep the last passing run. IKEv2 provides the real authentication; Cisco
says the NHRP string is not true authentication [3].

### TC-10: NHRP timers and re-registration

**Objective**: mappings age and refresh predictably across vendors.

**Prerequisites**: TC-04 passed.

**Procedure**:
1. Compare the hold time the hub advertises (600 s) with the expiry the spokes show, and the
   reverse.
2. Change Spoke1's ISP1 WAN address. Watch the hub with and without `ip nhrp registration
   no-unique` on Spoke1.
3. Reload the hub and time re-registration and OSPF FULL. Cisco probes the NHS at 1–32 s
   intervals [3].

**Expected result**:
- The hub accepts the new address when no-unique is sent. When it isn't sent, the hub keeps
  the old entry until it ages out [1]. Meanwhile, record the CIE code in its Registration
  Replies to the new address (`show ip nhrp nhs detail`, `debug nhrp`).
- Re-registration completes within one probe cycle of the hub returning.

**If it fails**: record the hold time actually cached and the time to recover.

### TC-11: MTU and MSS

**Objective**: no fragmentation or black-holing for full-size packets on either path.

**Prerequisites**: TC-07 passed.

**Procedure**: from DMVPN spoke hosts, send DF-bit pings of 1300–1500 bytes to an SD-WAN
spoke host and to the DC. Then run a large TCP transfer.

**Expected result**:
- The largest DF ping that passes is the smaller of the DMVPN tunnel MTU (1400) and the
  SD-WAN path MTU.
- TCP negotiates an MSS of 1360 or less.

**If it fails**: lower the tunnel MTU or MSS. Huawei's `tcp adjust-mss` on mGRE acts only on
IPv4 TCP SYN packets [1].

### TC-12: NHRP messages beyond registration (purge and error indication)

**Objective**: find where interoperation stops beyond "basic": Purge (types 5/6) and Error
Indication (type 7) between the Huawei hub and Cisco spokes.

**Prerequisites**: TC-04 passed. Capture GRE on the hub WAN, and run `debug nhrp` on
Spoke1.

**Procedure**, on Tunnel10 only:
1. On Spoke1, `clear ip nhrp`, then `shutdown` Tunnel10. Record whether it sends a Purge or
   Registration Request, and how long the hub keeps Spoke1 in `display nhrp peer all`.
2. Bring Tunnel10 up again. On the hub, run `reset nhrp peer` for Spoke1. Record whether the
   hub sends anything to Spoke1, and how long Spoke1 takes to re-register.
3. Send a Registration Request that the hub must refuse: a protocol address outside
   172.16.1.0/24, from a third test spoke with the same key. Record the reply code, or the
   Error Indication and its code.

**Expected result**:
- Step 1: if Spoke1 sends a Purge Request, record whether the hub answers with a Purge Reply
  and removes the entry at once. Otherwise the entry stays until the hold time (600 s)
  expires.
- Step 2: Spoke1 re-registers within one registration interval and OSPF returns to FULL.
- Step 3: the refusal is a standard RFC 2332 code that `debug nhrp` decodes.

**If it fails**: this is outside "basic" and doesn't block the design. Record the behaviour
as a limitation: hold time and IKE/OSPF dead timers then set how fast failure is detected.

## Issues encountered

None from a lab yet. The issues below are predicted from documentation.

### ISSUE-01: IPsec mode defaults differ

**Found in**: TC-03

**Symptom**: IKEv2 negotiation fails, or SAs come up in tunnel mode.

**Root cause**: Huawei's IPsec proposal defaults to tunnel mode [1]; Cisco DMVPN uses
transport [5], [6].

**Fix**: `encapsulation-mode transport` on the Huawei proposal.

**Verification**: `display ipsec sa` shows Transport.

### ISSUE-02: Huawei sends MTU 0 in OSPF DD packets

**Found in**: TC-04

**Symptom**: the adjacency is FULL, but some routes are missing on the Cisco spokes or on the
hub.

**Root cause**: by default Huawei sends MTU 0 in DD packets and skips the check, so a
non-Huawei neighbour may discard larger LSUs [1], [2].

**Fix**: `ospf mtu-enable` on the hub tunnels, and Filling MTU on in NCE; equal tunnel MTUs.

**Verification**: the LSDBs match on both ends.

### ISSUE-03: OSPF P2MP timer defaults

**Found in**: TC-04

**Symptom**: the adjacency never forms, or flaps.

**Root cause**: Huawei P2MP defaults to hello 30 s / dead 120 s [1]; mismatched timers stop
the adjacency.

**Fix**: hello 10 s / dead 40 s set on both ends.

**Verification**: `display ospf interface` / `show ip ospf interface`.

### ISSUE-04: A spoke tunnel leaves by the wrong provider

**Found in**: TC-01, TC-02

**Symptom**: one cloud doesn't come up on a Cisco spoke, or it fails only after the other
provider's link goes down.

**Root cause**: the two MPLS networks aren't connected. If the spoke reaches a hub subnet
through the other provider (for example via a single default route), that tunnel's packets
never arrive.

**Fix**: a route per hub subnet via the matching provider's PE, and each tunnel sourced from
the matching WAN link.

**Verification**: TC-01 step 4; TC-08.

### ISSUE-05: Default route through the overlay

**Found in**: TC-04, TC-06 (design)

**Symptom**: a spoke loses both tunnels as soon as OSPF converges.

**Root cause**: a default route learned over the tunnel overrides the spoke's WAN routes
that the tunnel depends on (recursive routing,
[gre.md](../techniques/gre.md#design-considerations)).

**Fix**: area 1 stays a normal area. Nothing originates a default route into OSPF towards
area 1.

**Verification**: the spoke's routes to the hub subnets stay via its providers.

### ISSUE-06: Hold-time defaults differ

**Found in**: TC-10

**Symptom**: stale spoke entries on the hub for up to 2 h.

**Root cause**: Huawei defaults to 7200 s [1]; Cisco's guide gives 7200 s and 600 s [3].

**Fix**: 600 s everywhere.

**Verification**: TC-10.

### ISSUE-07: Dynamic-IP spoke rejected after an address change

**Found in**: TC-10

**Symptom**: after a spoke's WAN address changes, it can't register again until the old entry
ages out.

**Root cause**: registrations are unique by default on Huawei [1].

**Fix**: send no-unique from the spokes. It is a Cisco smart default [4]; confirm it with
`show run all`.

**Verification**: TC-10 step 2.

### ISSUE-08: Changing the mGRE source removes IPsec

**Found in**: TC-02, TC-03

**Symptom**: after the hub's tunnel source is edited, tunnels come up unencrypted or not at
all.

**Root cause**: changing `source` deletes the tunnel interface's IPsec configuration [1].

**Fix**: re-apply `ipsec profile`.

**Verification**: `display ipsec sa`.

### ISSUE-09: NCE LAN-side OSPF constraints on the SD-WAN hub

**Found in**: TC-06

**Symptom**: the OSPF configuration is rejected, or LAN routes don't reach the overlay.

**Root cause**:
- In GRE tunnel mode, overlay OSPF process IDs must be 1–20000 [2].
- Turning bidirectional BGP↔LAN OSPF import off stops LAN OSPF from advertising to the
  overlay [2].

**Fix**: process 100; keep the import on.

**Verification**: TC-06.

## Conclusion

- **Feasibility:** TC-02 to TC-04 decide it, so run them first. Because the design is
  hub-and-spoke only, the least documented interop area, the redirect/shortcut exchange, is
  never used.
- **What "basic" means:** registration (types 3/4), IKEv2 transport mode
  and OSPF P2MP, with no NHRP authentication. The other team's result is expected to cover
  this.
- **Beyond "basic":**
  - NHRP authentication works only as plaintext on both ends (TC-09 run b). The Huawei
    hashed forms don't interoperate.
  - Purge and error handling (TC-12) and the unique-address behaviour (TC-10) set
    failure-recovery time, not reachability.
- **DMVPN ↔ SD-WAN:** this is plain OSPF routing between two hubs that each see the other
  overlay on their LAN side. The only protocol conversion is the BGP↔OSPF import on the
  SD-WAN hub, which NCE manages.
- **External dependency:** each MPLS provider must route its hub subnet to the AGG's /30
  address before TC-01.

## References

**Basis.**
- Huawei: the V600R026C00 AR library and the V100R026C00 solution library. The DSVPN hub runs
  V600R025C00SPC100, so each Huawei fact is re-checked on the device.
- Cisco: the 17.x router configuration guides are the latest published for DMVPN and NHRP on
  2026-11-23; the spokes run IOS XE 26.2.1.
- Huawei sources are cited by EDOC ID, per
  [huawei.md](../vendor-matrix/huawei/huawei.md#documentation-sources).
- Protocol background: [nhrp.md](../techniques/nhrp.md), [gre.md](../techniques/gre.md),
  [ospf-isis.md](../techniques/ospf-isis.md).

[1] "NetEngine AR5700, AR6700, and AR8000 Product Documentation," Huawei, V600R026C00, Issue
    01, Sep. 30, 2026. **EDOC1100611044**. Read Nov. 23, 2026. Sections used: DSVPN
    Configuration: Understanding DSVPN; Configuration Precautions for DSVPN; Default
    Settings; Configuring mGRE; Configuring NHRP; Understanding DSVPN over IPsec; Example
    for Configuring DSVPN in Shortcut Mode (OSPF); Example for Configuring DSVPN over IPsec;
    IPsec Configuration: Configuring IKE Negotiation; Example for Configuring IPsec VPN in a
    VPN Instance (`sa binding vpn-instance`); Example for Configuring DSVPN over IPsec
    Tunnels Between the Hub and Spokes Across Different Networks (transport, `shared`, `gre
    key`); SD-WAN EVPN Configuration: Overview, Fundamentals, Establishment of an SD-WAN
    Data Channel, SD-WAN EVPN Data Forwarding, Configuration Precautions; Command Reference:
    source (MGRE Tunnel interface view), gre key, nhrp entry, nhrp entry holdtime, nhrp
    registration no-unique, nhrp entry multicast dynamic, nhrp redirect, nhrp
    authentication, nhrp authentication standard, encapsulation-mode, exchange-mode, ipsec
    profile (Tunnel interface view), ospf network-type, ospf timer hello, ospf timer dead,
    ospf mtu-enable, capture-packet local-host; Packet Capture Configuration: Overview of
    Packet Capture.

[2] "SD-WAN Solution & iMaster NCE-Campus Product Documentation," Huawei, V100R026C00, Issue
    01, Sep. 30, 2026. **EDOC1100613380**. Read Nov. 23, 2026. Sections used: Configuring
    Overlay LAN-side Routes (OSPF or OSPFv3) (process-ID ranges, Filling MTU, bidirectional
    BGP↔LAN OSPF import, overlay route summarization, local tag); Configuring Overlay
    LAN-Side Routes (BGP/BGP4+); FAQ: What Do I Do If LAN-side Traffic of a Hub Site with
    LAN Routes Going Down Is Forwarded to Another Hub Site; Understanding the Solution >
    Knowledge and Concepts > SD-WAN Solution and Architecture > VPN Isolation (underlay,
    control and service VPNs).

[3] "IP Addressing Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Configuring
    NHRP." [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_config-nhrp-0.html
    Read Nov. 23, 2026.

[4] "IP Addressing Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Shortcut
    Switching Enhancements for NHRP in DMVPN Networks" (NHRP smart defaults). [Online].
    Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_nhrp-switch-enhancemts-dmvpn-0.html
    Read Nov. 23, 2026.

[5] "Security and VPN Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Dynamic
    Multipoint VPN" (hub/spoke configuration, NAT-Transparency Aware DMVPN, OSPF
    point-to-multipoint /32 note), updated Jan. 11, 2021. [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m_sec-conn-dmvpn-dmvpn-0.html
    Read Nov. 23, 2026.

[6] "Security and VPN Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "DMVPN Support
    for IWAN" (IKEv2 keyring, transport transform set, `tunnel vrf`, `tunnel protection
    ipsec profile`), updated Jan. 11, 2021. [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m-sec-conn-dmvpn-mtt.html
    Read Nov. 23, 2026.

[7] "Security and VPN Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Configuring
    Internet Key Exchange Version 2" (keyring lookup, wildcard key example, profile
    matching, smart defaults), updated Jan. 11, 2021. [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m_sec-cfg-ikev2-flex.html
    Read Nov. 23, 2026.

[8] "Cisco IOS XE 26.2.1," Cisco support page (release date 31-Aug-2026; release notes for
    Catalyst 8200/8300 Edge Platforms, Release 26.2.x). [Online]. Available:
    https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26-2-1/model.html Read
    Nov. 23, 2026.
