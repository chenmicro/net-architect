# VXLAN (including ACI iVXLAN)

VXLAN provides the overlay data plane: L2 (and L3) traffic is encapsulated in UDP
and carried over the IP underlay between **VTEPs** (VXLAN Tunnel Endpoints,
usually the leaf switches). A 24-bit **VNI** (VXLAN Network Identifier) maps to a
bridge domain, giving roughly 16 million logical L2 segments against VLAN's 4096
[1].

## Encapsulation and header format

RFC 7348 (Informational) defines the 8-byte header carried between the outer UDP
header and the inner frame [1]:

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |R|R|R|R|I|R|R|R|            Reserved                           |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                VXLAN Network Identifier (VNI) |   Reserved    |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **I** MUST be 1 for a valid VNI. The other seven flag bits ("R") and the
  24-bit and 8-bit reserved fields "MUST be set to zero on transmission and
  ignored on receipt" [1]. That tolerance is the extension point every variant
  in this file relies on.
- Full stack: outer Ethernet (optional 802.1Q) → outer IPv4 → outer UDP
  (destination port 4789, the IANA-assigned VXLAN port [2]) → the 8-byte VXLAN
  header → inner Ethernet → payload [1].
- **Overhead is fixed at 8 bytes**: 50 bytes over IPv4 untagged (14 + 20 + 8 +
  8) and 54 with an 802.1Q tag. Every variant below keeps the same header
  length, so this arithmetic does not change across dialects.
- The underlay only sees the **outer 5-tuple**; ECMP hashes on that, and the
  inner flow is invisible to it.

## Control plane: flood-and-learn vs EVPN

- VXLAN is data-plane only — it needs a control plane to populate VTEP MAC/ARP
  state. **Flood-and-learn** (data-plane learning, no BGP) works but scales
  poorly: unknown unicast and ARP flood to every VTEP in the VNI.
- [evpn.md](evpn.md) is the modern BGP control plane that replaces it — MAC/IP
  advertisement (Type 2), a per-VNI inclusive replication tree (Type 3), and ARP
  suppression at the ingress VTEP — and is what most current fabric designs
  deploy VXLAN with. [bgp.md](bgp.md) covers the session mechanics.
- The underlay only needs IP reachability between VTEPs, so VXLAN rides the same
  ECMP Clos fabric described in [spine-leaf-clos.md](spine-leaf-clos.md) with no
  VXLAN-specific underlay requirement beyond carrying the extra 50/54 bytes.

## Cross-vendor / variants

| Variant | Specification | Header difference | Interoperability |
|---|---|---|---|
| **VXLAN** | RFC 7348, Informational [1] | baseline | any standards VTEP |
| **VXLAN-GBP** | `draft-smith-vxlan-group-policy-05`, expired 2019 [2] | G/D/A flags + 16-bit Group Policy ID, still port 4789 | Cisco NX-OS GPO and other GBP implementations |
| **VXLAN-GPE** | `draft-ietf-nvo3-vxlan-gpe-13`, still an Internet-Draft [3] | next-protocol field for non-Ethernet payloads | draft-stage; check peer support |
| **ACI iVXLAN** | proprietary, no RFC or draft [4] | 24-bit VNID + 2-byte PcTag/sClass + flags; UDP 48879 | not interoperable; terminate at an ACI Border Gateway |
| **Huawei CloudEngine** | GBP draft implementation, plus a patented extension [7], [8] | G bit + 16-bit Group Policy ID (EPG); the patented variant adds group/application IDs | GBP-based; verify per release |

### VXLAN-GBP — policy tag with a presence bit

```
 |G|R|R|R|I|R|R|R|R|D|R|R|A|R|R|R|        Group Policy ID        |
 |          VXLAN Network Identifier (VNI)       |   Reserved    |
```

- **G** (bit 0) = Group Policy ID present, **D** (bit 9) = don't learn, **A**
  (bit 12) = policy already applied (meaningful only when G = 1) [2].
- The 16-bit **Group Policy ID** carries the source TSI group; the VNI stays in
  its standard position and the packet stays on UDP **4789**, relying on RFC
  7348's reserved-bit tolerance for backward compatibility [2].
- Cisco's implementation is **NX-OS GPO**, built on this draft plus two expired
  EVPN companions — see [nxos-gpo.md](../vendor-matrix/cisco/nxos-gpo.md). GPO is
  **not** ACI's scheme; see the next subsection.

### ACI iVXLAN — proprietary dialect

Field inventory from Cisco Live BRKDCN-3900 ("Overlay iVXLAN", the same slide in
the 2023–2025 editions) [5]; Cisco's 6.2(x) configuration guide states only that
the header "includes policy attributes and a 24-bit VNID" and shows a
packet-format figure [6]:

- a 24-bit **VNID** in the VNI-sized field, carrying the BD or VRF context;
- a **2-byte PcTag/sClass** carrying the source EPG's class ID — the field that
  lets every packet be classified without a controller lookup;
- flag bits for **source policy applied**, **destination policy applied**, and
  **don't learn** (the CLI decode prints them as `src_policy`, `dst_policy`,
  `dl`);
- fabric encapsulation on UDP **48879** in the captured sample, not 4789 [5].

**There is no public bit map.** The deck numbers the flags "bit 4 source policy
applied, bit 5 destination policy applied, bit 7 don't learn," which does not
reconcile with RFC 7348's I bit (position 4 in the same MSB-first convention) or
with VXLAN-GBP's G/D/A bits (0/9/12) [1], [2], [5], and no offset table is
published. Consequence: don't hand-write a parser — decode with Cisco's
`knet_parser.py`, or treat the header as opaque.

**Classification.** Structurally iVXLAN is a **dialect of the VXLAN envelope**:
same header length, same outer stack, same 24-bit segment field, so MTU, ECMP,
and underlay reasoning carry over unchanged. It is not an interoperable
extension, for two reasons:

- **No presence bit.** VXLAN-GBP uses G to announce that the Group Policy ID is
  meaningful; the published iVXLAN fields have no equivalent, so a receiver
  cannot distinguish a policy tag from reserved bytes.
- **Different transport.** The sample runs on UDP 48879, so a standards VTEP
  never receives it. Even with the port remapped, RFC 7348 tolerance would
  preserve forwarding while silently discarding the policy — no error, no
  enforcement.

Cross-vendor interop therefore terminates at the **ACI Border Gateway**, which
re-encapsulates to standards-based VXLAN EVPN. ACI-specific mechanics built on
this header — FTAG multicast trees, BD/VRF GIPo allocation, glean packets — are
in [cisco/aci.md](../vendor-matrix/cisco/aci.md).

### Huawei CloudEngine — GBP now, richer header in patent

- **Microsegmentation** is documented as **VXLAN-GBP**: when the **G** flag is 1,
  the 16-bit **Group Policy ID** carries the ID of the EPG the source server
  belongs to, and the destination VTEP enforces policy from it [7]. That is the
  same draft-based scheme as NX-OS GPO, not a Huawei-proprietary layout —
  promising for interop, but confirm per release and platform.
- Huawei has also patented a **richer extension**: a 2-octet **group identifier
  before the VNI**, a 1-octet **application identifier after the VNI**, and
  reserved flag bits repurposed as presence indicators for them [8]. That is a
  superset of GBP, not the same wire format — do not assume a switch uses it
  merely because the patent exists.

### Other implementations

Most other vendor EVPN-VXLAN implementations use the RFC 7348 header; vendor
header extensions are covered in the subsections above (ACI, Huawei), and
deployment-level differences (for example Huawei's Segment VXLAN for DCI) live
in the vendor files:
[arista.md](../vendor-matrix/arista.md),
[juniper.md](../vendor-matrix/juniper.md), [huawei.md](../vendor-matrix/huawei.md),
and [cisco/nxos-vxlan.md](../vendor-matrix/cisco/nxos-vxlan.md).

## Design considerations

- **MTU is variant-independent.** Every dialect keeps the 8-byte header, so the
  encapsulated overhead (50 bytes IPv4 untagged, 54 with 802.1Q) is the same
  whether the fabric runs standard VXLAN, GBP, or ACI iVXLAN. Size the underlay,
  IPN, and ISN for the outer header, not for the dialect.
- **BUM scope is a control-plane property, not VXLAN's.** Flood-and-learn
  replicates to every VTEP in the VNI; EVPN builds a per-VNI inclusive tree with
  Type 3 and prunes with ARP suppression ([evpn.md](evpn.md)). ACI substitutes
  BD/VRF GIPo multicast groups and FTAG trees
  ([cisco/aci.md](../vendor-matrix/cisco/aci.md)).
- **Unknown-unicast handling is separate again.** Whether an unresolved MAC is
  flooded, proxied, or dropped is fabric policy, not encapsulation — see
  [arp.md](arp.md) for ARP and unknown-unicast semantics, and the ACI file for
  the per-BD proxy/flood switch.
- **Filter on the right UDP port.** 4789 is the IANA-assigned VXLAN port [2];
  ACI fabric encapsulation was observed on 48879 [5]. ACLs, firewalls, and IPN
  multicast filters that assume 4789 will silently drop ACI traffic, and vice
  versa.
- **Policy fields do not survive an unaware VTEP.** RFC 7348 requires receivers
  to ignore reserved bits [1], so a GBP tag or iVXLAN PcTag is silently
  discarded rather than rejected. A security model that depends on those fields
  must terminate the encapsulation at a device that implements it.
- **ECMP sees only the outer 5-tuple.** Inner flows sharing an outer header hash
  to the same path, and BUM replication trees are built on outer addresses, not
  per-tenant inner flows.

## Relationship to other techniques

- [evpn.md](evpn.md) — BGP control plane (route types 1–5) that replaces
  flood-and-learn.
- [bgp.md](bgp.md) — session and route-reflector mechanics EVPN rides on.
- [spine-leaf-clos.md](spine-leaf-clos.md) — the underlay, which needs only IP
  reachability between VTEPs.
- [arp.md](arp.md) — ARP flooding/suppression and unknown-unicast behaviour in
  overlays.
- [multi-tenancy.md](multi-tenancy.md) — VNI/VRF/BD and route-target mapping.
- [vendor-matrix/cisco/aci.md](../vendor-matrix/cisco/aci.md) — FTAG trees, GIPo
  allocation, the glean packet, per-BD proxy/flood.
- [vendor-matrix/cisco/nxos-gpo.md](../vendor-matrix/cisco/nxos-gpo.md) — the
  VXLAN-GBP implementation (GPO).
- [vendor-matrix/cisco/nxos-vxlan.md](../vendor-matrix/cisco/nxos-vxlan.md) —
  standards-based EVPN-VXLAN on NX-OS.

## References

[1] R. Mahalingam, D. Dutt, K. Duda, P. Agarwal, L. Kreeger, T. Sridhar,
M. Bursell, and C. Wright, "Virtual eXtensible Local Area Network (VXLAN): A
Framework for Overlaying Virtualized Layer 2 Networks over Layer 3 Networks,"
RFC 7348, August 2014. [Online]. Available:
https://www.rfc-editor.org/rfc/rfc7348.txt — §5 for the header, the I flag, and
the reserved-field rule. Informational RFC.

[2] M. Smith and L. Kreeger, "VXLAN Group Policy Option," IETF Internet-Draft
draft-smith-vxlan-group-policy-05, October 22, 2018; expired April 25, 2019.
[Online]. Available:
https://datatracker.ietf.org/doc/draft-smith-vxlan-group-policy/ — §2.1 Figure 1
and bit definitions (G 0, D 9, A 12), the 16-bit Group Policy ID, and the
port-4789 backward-compatibility argument.

[3] "Generic Protocol Extension for VXLAN (VXLAN-GPE)," IETF Internet-Draft
draft-ietf-nvo3-vxlan-gpe, revision 13 — still an Internet-Draft, not an RFC.
[Online]. Available: https://datatracker.ietf.org/doc/draft-ietf-nvo3-vxlan-gpe/
— recheck revision and status before citing; do not describe it as an RFC.
Checked Oct. 19, 2026.

[4] IETF Datatracker search for the term "ivxlan," returning no RFC or draft
matches. [Online]. Available: https://datatracker.ietf.org/ — absence claim:
re-run the search to re-verify. Checked Oct. 19, 2026.

[5] J. Young, "ACI Technical Leader," Cisco Live EMEA, BRKDCN-3900 — slide
"Overlay iVXLAN." 2025 edition:
https://www.ciscolive.com/c/dam/r/ciscolive/emea/docs/2025/pdf/BRKDCN-3900.pdf
(the 2023 and 2024 editions carry the same slide). Verify the field list (VNID
3 bytes, PcTag/sClass 2 bytes, flags byte with source/destination-policy and
don't-learn bits) and the glean capture showing UDP 48879. Checked Oct. 19,
2026; conference deck, slide numbers may shift.

[6] "VXLAN in ACI," Cisco APIC Layer 2 Networking Configuration Guide, Release
6.2(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l2-configuration/cisco-apic-layer-2-networking-configuration-guide-62x/g_cisco_aci_layer_2_and_layer_3_forwarding/vxlan-in-aci.html
— "policy attributes and a 24-bit VNID, supporting up to 16 million unique
Layer 2 segments," plus Figure 2 "Cisco ACI VXLAN Packet Format" (a figure, with
no offset table). Checked Oct. 19, 2026.

[7] "Understanding Microsegmentation," Huawei CloudEngine 9800, 8800, 6800, and
5800 V200R020C10 Configuration Guide — Security. [Online]. Available:
https://support.huawei.com/enterprise/en/doc/EDOC1100198635/8f515dd/understanding-microsegmentation
— "Group Policy ID field: When the value of the G flag bit is 1, the Group
Policy ID field in the VXLAN packet header carries the ID of an EPG that the
source server belongs to"; destination VTEP enforces GBP. **Not directly
fetched**: support.huawei.com serves `User-agent: * / Disallow: /` in robots.txt,
so this was read only as a search-index excerpt. Confirm manually against the
page, and note the quoted release (V200R020C10) may not be current. Checked
Oct. 19, 2026.

[8] "VXLAN Packet Encapsulation and Policy Execution Method, and VXLAN Device
and System," US11588665B2 (application US20210144028A1), Huawei Technologies
Co., Ltd., priority 2018-07-25, granted 2023-02-21. [Online]. Available:
https://patents.google.com/patent/US20210144028A1/en — verify the Fig. 3
description: a 2-octet group identifier before the VNI, a 1-octet application
identifier after the VNI, and reserved flag bits usable as indicator bits for
their presence; the VXLAN header may omit the group identifier and use that
location as reserved. A patent, not a product specification. Checked Oct. 19,
2026.
