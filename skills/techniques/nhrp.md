# NHRP (DMVPN / DSVPN)

- The Next Hop Resolution Protocol maps a protocol address (an overlay tunnel IP or a subnet)
  to an NBMA address (the underlay public IP), so that routers on a non-broadcast
  multi-access network can reach each other directly instead of through intermediate hops
  [1].
- In design work it is the control plane of mGRE ([gre.md](gre.md#mgre-multipoint-gre)) and
  the core of two vendor solutions:
  - **Cisco DMVPN:** mGRE + NHRP + IPsec [3], [5].
  - **Huawei DSVPN:** mGRE + NHRP + an IPsec profile [6].
- Both are hub-and-spoke overlays where spokes, often on dynamic public IPs, register with a
  hub and build direct spoke-to-spoke tunnels on demand.
- The protocol is standard (RFC 2332). The shortcut trigger (the Traffic Indication or
  "Redirect" message) comes from an expired Cisco Internet-Draft [2]. NAT handling and
  authentication encoding are implementation-specific. That split decides what a
  Cisco-to-Huawei mix can rely on.

## Roles and addresses

| Term | Meaning |
|---|---|
| NHS (Next Hop Server) | The hub. Holds the registrations and answers or forwards resolution requests [1], [3] |
| NHC (Next Hop Client) | A spoke. Registers its own mapping and asks for others' [1], [3] |
| Protocol address | Overlay address: the tunnel interface IP, or a subnet behind a spoke [6] |
| NBMA address | Underlay address: the public IP the GRE delivery header is sent to [6] |
| Static mapping | Configured on a spoke for its hub (tunnel IP → public IP) [3], [6] |
| Dynamic mapping | Learned from Registration (on the hub) or Resolution (on spokes) [6] |

## Message types

| `ar$op.type` | Message | Direction and use |
|---|---|---|
| 1 / 2 | Resolution Request / Reply | Spoke asks for a tunnel IP or prefix; the egress node replies with its NBMA address [1], [2] |
| 3 / 4 | Registration Request / Reply | Spoke → hub, carrying its own mapping [1] |
| 5 / 6 | Purge Request / Reply | Invalidates a mapping given out earlier, e.g. when the route behind it changes [1], [4] |
| 7 | Error Indication | Errors such as hop count exceeded [1] |
| 8 | Traffic Indication (traffic code 0 = redirect) | Hub → ingress spoke when it hairpins a packet back into the same overlay; carries the first 64 bytes of that packet [2] |

Type 8 is not in RFC 2332. The draft lists it as an experimental value [2]. Cisco and Huawei
both call it "NHRP redirect" [4], [6].

## Packet format

**Transport.**
- NHRP is carried directly in GRE, with GRE Protocol Type **0x2001**, not over IP or UDP [2],
  [7]. The DMVPN draft requires implementations to support these "L2 NHRP" frames, so that
  packet filters need no NHRP rule [2].
- The value is not an IANA-registered EtherType; Wireshark dissects it as NHRP only inside GRE
  [7].
- Under IPsec, NHRP is encrypted with the data, so on the wire it is just ESP.

```
| IP PubA>PubB proto 47 (or 50 + ESP) | GRE 0x2001 [key] | NHRP fixed (20 B) | mandatory part | extensions |
```

**Fixed header** (RFC 2332 §5.1), common to every type [1]:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            ar$afn             |          ar$pro.type          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          ar$pro.snap                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ar$pro.snap  |   ar$hopcnt   |            ar$pktsz           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           ar$chksum           |            ar$extoff          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| ar$op.version |   ar$op.type  |    ar$shtl    |    ar$sstl    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `ar$afn`: the NBMA address family [1].
- `ar$pro.type`: the protocol type, an EtherType when one exists (0x0800 for IPv4) [1].
- `ar$hopcnt`: decremented by each NHS. At zero, the NHS returns an Error Indication [1].
- `ar$pktsz`: the length excluding link-layer encapsulation [1].
- `ar$chksum`: the IP checksum over the whole NHRP packet [1].
- `ar$extoff`: the offset of the first extension, 0 if there are none [1].
- `ar$op.version`: 1 for NHRP [1].
- `ar$shtl` / `ar$sstl`: the type and length of the source NBMA address and subaddress [1].

**Mandatory part, types 1–6** (§5.2.0.1): a common header followed by zero or more Client
Information Entries (CIEs) [1].

```
| Src Proto Len | Dst Proto Len |            Flags              |
|                         Request ID                            |
|  Source NBMA Address  |  Source NBMA Subaddress (len 0 on IP) |
|  Source Protocol Address                                      |
|  Destination Protocol Address                                 |
--- CIE, repeated ---
|    Code       | Prefix Length |            unused             |
|  Maximum Transmission Unit    |        Holding Time           |
|  Cli Addr T/L | Cli SAddr T/L | Cli Proto Len |  Preference   |
|  Client NBMA Address | Client NBMA Subaddress | Client Protocol Address |
```

| Field | Notes |
|---|---|
| Request ID | Copied into the reply to match it. The same value is reused on retransmission [1] |
| Code | 0 in a reply = ACK, anything else = NAK [1] |
| Prefix Length | Says the answer covers a whole prefix, not one host. DMVPN replies with the prefix the egress node found [1], [2] |
| Holding Time | Seconds the mapping stays valid; 0 on a NAK [1] |
| Preference | Higher wins; equal is a local matter [1]. Cisco uses it for unequal-cost spoke-to-spoke load sharing (`ip nhrp path preference`) [4] |
| Flags, Resolution Request | `Q` (requester is a router), `A` (authoritative answer only), `D`, `U` (uniqueness), `S` [1] |
| Flags, Registration Request | `U`: the registration is unique. A later attempt to bind the same address to another NBMA address is rejected with Code 14 [1] |

**Error Indication (type 7) mandatory part** (§5.2.7). It replaces Flags and Request ID with
an error code and offset, carries no CIEs, and ends with the offending packet [1]:

```
| Src Proto Len | Dst Proto Len |            unused             |
|           Error Code          |         Error Offset          |
| Source NBMA Address | Source NBMA Subaddress | Source Protocol Address |
| Destination Protocol Address (station that sent the bad packet)        |
| Contents of NHRP Packet in error (variable length)                     |
```

- **Source** fields: the station that detected the error.
- **Destination Protocol Address:** the sender of the bad packet.
- **Error Offset:** counted from the start of the fixed header [1].

| Code | Error | When |
|---|---|---|
| 1 | Unrecognized Extension | A responder can't process a compulsory extension. A transit NHS ignores it instead |
| 3 | NHRP Loop Detected | The packet is being forwarded in a loop |
| 6 | Protocol Address Unreachable | The routed path reaches a point where the address of interest is unreachable |
| 7 | Protocol Error | Generic: bad version, protocol type or checksum |
| 8 | NHRP SDU Size Exceeded | The NHRP packet exceeds the NBMA MTU |
| 9 | Invalid Extension | The extension isn't valid for this packet type |
| 10 | Invalid NHRP Resolution Reply Received | A reply arrived for a request the client didn't make |
| 11 | Authentication Failure | The authentication test failed |
| 15 | Hop Count Exceeded | `ar$hopcnt` reached zero |

All codes are from [1].
- An Error Indication is never sent in response to another Error Indication.
- The offending packet is discarded, with at most one Error Indication per packet.
- No extensions may be added.
- An NHS that sees its own addresses as the source of a transiting Error Indication drops it
  silently, because the packet is looping [1].

**Traffic Indication (type 8) mandatory part** [2]. It is modelled on the Error Indication
layout rather than the request/reply one [2]:

```
| Src Proto Len | Dst Proto Len |            unused             |
|        Traffic Code           |            unused             |
| Source NBMA Address | Source NBMA Subaddress | Source Protocol Address |
| Destination Protocol Address (dst IP of the triggering packet)          |
| Contents of the triggering data packet (first 64 bytes)                 |
```

It has no request/reply pair and no CIE [2].

**Extensions** (§5.3): TLVs from `ar$extoff`, ending with Type 0, Length 0 [1].

```
|C|u|        Type               |        Length                 |
|                         Value...                              |
```

- `C` = compulsory: an NHS that doesn't recognise the type treats the request as an error [1].
- An NHS must not reorder extensions [1].

| Type | Extension | Source |
|---|---|---|
| 3 | Responder Address | [1] |
| 4 / 5 | Forward / Reverse Transit NHS Record. Each hub forwarding a Resolution Request appends a forward record; a hub that finds itself already listed drops the request (loop) | [1], [2] |
| 7 | Authentication (compulsory) | [1] |
| 8 | Vendor Private | [1] |
| 9 | Device Capabilities in RFC 2735 (non-compulsory, length 8). Cisco uses the same code for its NAT Address extension (pre-/post-NAT addresses). Wireshark tells them apart by length | [7], [8] |

## Operation

**Registration (always).**
- The spoke has a static mapping for the hub and sends a Registration Request. The hub caches
  tunnel IP → public IP and replies [3], [6].
- Cisco sends registrations every one-third of the hold time, unless
  `ip nhrp registration timeout` is set [3].
- If no reply comes, Cisco retransmits at 1, 2, 4, 8, 16 and 32 s, and declares the NHS down
  after three retransmissions (7 s) [3].
- Huawei registers every `nhrp registration interval`, which can't exceed the hold time [6].

**Spoke-to-spoke without redirect** (Cisco Phase 2, Huawei non-shortcut).
- Routing must give each spoke the remote spoke's **tunnel IP as next hop**, so no
  summarization is possible [3], [6].
- On a mapping miss, the spoke sends a Resolution Request via the hub. The remote spoke
  answers it, and the two build a direct tunnel [3], [6].

**Spoke-to-spoke with redirect** (Cisco Phase 3, Huawei shortcut).
1. Spokes hold only summaries via the hub [4], [6].
2. The hub forwards the first packets and sends a Traffic Indication (redirect) to the source
   spoke [2], [6].
3. The source spoke sends a Resolution Request for the destination. The hub forwards it,
   appending a forward-transit record [2].
4. The egress spoke, the one whose route to the destination leaves the overlay, builds the
   tunnel and IPsec SA towards the requester. It then answers with the whole prefix it
   routes [2].
5. The requester installs that prefix through the new tunnel [2]:
   - Cisco installs an NHRP route (code `H`) or a next-hop override [4]. The shortcut lives
     only while a covering summary route exists ("route watch") [4].
6. The commands:
   - Cisco: `ip nhrp redirect` on the hub, `ip nhrp shortcut` on spokes [4].
   - Huawei: `nhrp redirect` on the hub, `nhrp shortcut` on spokes. Both are off by default.
     A hub with redirect but spokes without shortcut sends a redirect for every packet [6].

| Cisco | Huawei | Routes on spokes | Spoke-to-spoke |
|---|---|---|---|
| Phase 1 | (none) | Via hub | None; hub-and-spoke only [3] |
| Phase 2 | Non-shortcut | Specific, remote spoke as next hop | Resolution triggered by the next hop's missing mapping [3], [6] |
| Phase 3 | Shortcut | Summaries via hub | Triggered by the hub's redirect [4], [6] |

The Phase 2/3 ↔ non-shortcut/shortcut pairing is this library's mapping; neither vendor
documents the other's terms.

**Teardown.**
- Unused spoke-to-spoke mappings expire at the hold time.
- On Cisco, expiry also deletes the IPsec and IKE SAs and sends delete notifications to the
  peer [3]. The hub purges mappings it gave out when the route behind them changes [4].
- Huawei tears down a dynamic mGRE tunnel that has had no traffic for a period [6].

## Cross-vendor / variants

### Departures from RFC 2332

DMVPN and DSVPN are not plain RFC 2332. The table is this library's summary, not a vendor
document. Each cell cites its own source:
- the RFCs [1], [8];
- the expired Internet-Draft by Cisco authors [2];
- Cisco's configuration guides [3], [4];
- Huawei's AR documentation [6];
- Wireshark's decoder [7], which is third-party evidence.

"Wire" rows change what is sent; "local" rows change only how a router uses what it receives.

| Item | Standard (RFC 2332) | Cisco DMVPN | Huawei DSVPN | Interop note |
|---|---|---|---|---|
| Transport (wire) | LLC/SNAP and NLPID encapsulations for ATM, SMDS, Frame Relay and X.25 [1] | NHRP directly in GRE, Protocol Type 0x2001; implementations must support it [2], [7] | NHRP is exchanged over the mGRE tunnel [6]; the GRE Protocol Type isn't documented | 0x2001 isn't an IANA EtherType [7]; confirm Huawei's value in a capture |
| Redirect (wire) | None; RFC 2332 defines types 1–7 [1] | Traffic Indication, type 8, traffic code 0, carrying the first 64 bytes of the hairpinned packet; an experimental value [2]. **The Phase 3 trigger** | "NHRP Redirect" from the hub in shortcut mode [6]; packet format not published | Same name and role; byte compatibility undocumented |
| Who answers a resolution (wire) | Any NHS with authoritative cached information may reply; NHS cache synchronisation assumed [1] | Intermediate hubs should not answer or cache; the **egress node** builds the tunnel, then replies. No reliance on server cache synchronisation [2] | The hub forwards the Resolution Request to the destination spoke, which replies [6] | Same model in both |
| Reply contents (wire) | CIE Prefix Length may describe an equivalence class [1] | The egress node replies with the whole prefix it routes [2]; Cisco installs it as an NHRP route [4] | The documented example installs a /32 `remote-network` entry for the destination host [6] | Prefix granularity differs; check what each side installs |
| NAT (wire) | No NAT handling [1] | Cisco NAT Address extension on type 9, a code RFC 2735 assigned to Device Capabilities [7], [8] | The hub returns the post-NAT address in the Registration Reply; spokes exchange pre- and post-NAT addresses. No extension type documented [6] | Different mechanisms; not expected to interoperate |
| Authentication (wire) | Type 7 extension: SPI, source address, keyed hash over the packet; HMAC-MD5-128 by default [1] | Cleartext string (`ip nhrp authentication`), described as not encrypted [3] | Plaintext without `hash`. With `hash`: SHA2-256/384/512, MD5 or SHA1. `nhrp authentication standard` makes the hashed form "compatible with the standard algorithm" [6] | Neither default is the RFC keyed hash. Plaintext is the likely common ground |
| Installing the result (local) | Cache entry with a holding time [1] | NHRP route or next-hop override, kept only while a covering summary exists ("route watch") [4] | NHRP peer entry of type `remote` / `remote-network` [6] | No wire effect |
| Purge on route change (local use of types 5/6) | Purge messages defined [1] | The hub purges mappings it answered for when the route behind them changes [4] | Not documented | Standard messages; check whether Huawei sends or honours them |
| Path preference (local use of the CIE field) | Preference field; equal values are a local matter [1] | `ip nhrp path preference` for unequal-cost spoke-to-spoke sharing [4] | Not documented | — |
| network-id (local) | Not defined | Local only, not sent [3] | Local only, default 0; NHRP isn't forwarded between interfaces with different IDs [6] | No wire effect |

#### Huawei coverage of the DMVPN draft

The draft [2] is the only written specification of DMVPN behaviour. Huawei never references
it. The table maps each of the draft's behaviours to what Huawei's AR documentation [6]
states:
- **Yes:** documented.
- **Function only:** the behaviour is documented, but not the packet format.
- **Differs:** the documentation shows other behaviour.
- **Not documented.**

| Draft behaviour [2] | Requirement level | Huawei DSVPN [6] | Status |
|---|---|---|---|
| GRE tunnels protected by IPsec; unprotected GRE also supported | MUST / SHOULD | DSVPN with or without an IPsec profile on the mGRE interface | Yes |
| NHRP carried as "L2" frames inside GRE | MUST | NHRP is exchanged over the mGRE tunnel; GRE Protocol Type not stated | Function only |
| Multipoint tunnel interface, registration to the hub | MAY (allowed model) | mGRE interface; spokes register with the hub | Yes |
| Hub sends a Traffic Indication (redirect) carrying the first 64 bytes when it hairpins a packet; spokes accept it | MUST send and accept | Hub `nhrp redirect`, spoke `nhrp shortcut` | Function only |
| Redirects rate-limited | MUST | With redirect on and shortcut off on the spokes, the hub sends a redirect "whenever a data packet is received" | Differs (at least in that case) |
| Ingress spoke sends a Resolution Request for the destination after the redirect | MUST | The source spoke sends a Resolution Request after the redirect | Yes |
| Requests forwarded hop by hop along the routing table, including through hub hierarchies | MUST | Hub forwards to the destination spoke; hierarchical hubs forward spoke hub → HQ hub → spoke hub | Yes |
| Each forwarding hub appends a Forward Transit NHS Record; a hub already listed drops the request | MUST | Not documented | Not documented |
| Intermediate hubs don't cache; no reliance on server cache synchronisation | SHOULD NOT / MUST NOT | Not documented | Not documented |
| Egress node builds the tunnel and SAs, then replies | MUST | The destination spoke replies, and building the mGRE tunnel triggers IPsec; the order isn't stated | Not documented (order) |
| Reply carries the whole routed prefix; providing and receiving aggregated answers | MUST | The documented example installs a /32 `remote-network` entry for the destination host | Differs (as documented) |
| IPv6: second CIE with the egress node's link-local address | SHOULD | Not reviewed | Not documented |
| IKE authentication, X.509 recommended | Recommended | IKEv2 by default; certificate use not reviewed | Yes (IKEv2) |
| Remote-access clients (no LAN behind them) as DMVPN nodes | MUST be possible | DSVPN nodes are hub and spoke routers | Not documented |
| NAT traversal, including a hub behind NAT (§8.8) | MUST | Own mechanism: NAT Server or static NAT only, no PAT, transport mode required when the hub or both spokes are behind NAT | Yes, with restrictions |
| Shortcut used only after its SAs are up (§8.8, 8c) | Stated as met | Not documented | Not documented |

**Reading the table:**
- Huawei documents the same functional model: registration, redirect, resolution forwarded
  through the hub (or a hub hierarchy) to the far spoke, and IPsec on demand.
- What it doesn't document is the wire format and the draft's finer rules: transit records,
  aggregated replies, rate limiting.
- For a Cisco–Huawei mix that uses Phase 3, those gaps are test items, not assumptions.

### Configuration and defaults

| Item | Cisco IOS XE 17 (DMVPN) | Huawei AR V600R026C00 (DSVPN) |
|---|---|---|
| Enable | `ip nhrp network-id` (on by default since 16.3) [5] | `nhrp enable` globally and per interface. Licensed feature [6] |
| network-id | Local only, not sent; may differ between routers [3], [5] | Local only, default 0. NHRP isn't forwarded between mGRE interfaces with different IDs [6] |
| Hub mapping on spoke | `ip nhrp map <hub-tun> <hub-nbma>`, `ip nhrp map multicast <hub-nbma>`, `ip nhrp nhs <hub-tun>` [5] | `nhrp entry <hub-tun> <hub-nbma> register` [6] |
| Multicast to spokes (hub) | `ip nhrp map multicast dynamic` (default since 16.3) [5] | `nhrp entry multicast dynamic`, off by default [6] |
| Hold time | The page gives 7200 s in one passage and "default = 600 seconds" (since 16.2.1) in another. Recommended 300–600 s [3] | `nhrp entry holdtime` 5–31845 s, default 7200 s; the value is sent to the remote end [6] |
| Registration interval | One-third of the hold time, or `ip nhrp registration timeout` [3] | `nhrp registration interval`, default 1800 s, ≤ hold time [6] |
| Uniqueness | `ip nhrp registration no-unique` is a smart default [4] | Unique by default: a spoke whose public IP changes is rejected until its old entry ages out. `nhrp registration no-unique` recommended for LTE spokes [6] |
| Authentication | `ip nhrp authentication <string>`, sent unencrypted [3] | `nhrp authentication [ hash { sha2-256 \| sha2-384 \| sha2-512 \| md5 \| sha1 } ] cipher <string>`, 1–8 characters. Plaintext without `hash`. `nhrp authentication standard` makes the hashed form "compatible with the standard algorithm"; it must match on both ends [6] |
| Redirect / shortcut | `ip nhrp redirect` / `ip nhrp shortcut` [4] | `nhrp redirect` / `nhrp shortcut`, both off [6] |
| NAT | NHRP learns the post-NAT address when IPsec transport mode is used. Every spoke needs a unique post-NAT address. Spokes behind PAT can't reach each other directly [5] | Hub detects NAT and returns the post-NAT address in the Registration Reply; spokes exchange pre- and post-NAT addresses. Same-post-NAT-IP and PAT cases unsupported; NAT devices need NAT Server or static NAT [6] |
| IPsec mode | Transport recommended for DMVPN, required for NAT-aware operation [5] | `encapsulation-mode` default **tunnel** [6]. Transport required when the hub, or two spokes, sit behind different NATs [6] |
| IKE | IKEv1 or IKEv2 | **IKEv2 by default**; IKEv1 needs a separate feature package [6] |
| Interface state | n/a in the sources read | `nhrp tunnel-if-state related` (spoke): mGRE interface goes down when all hubs are down [6] |
| Routing | EIGRP, BGP, OSPF. OSPF point-to-multipoint needs its /32 routes blocked [5] | OSPF (`ospf network-type p2mp` in every example) and BGP [6] |
| Dual / hierarchical hubs | Phase 3 allows hierarchical hubs [4] | Dual hub (active/standby by route preference) and hierarchical hubs: **shortcut mode only** [6] |

**Interop.**
- Neither vendor documents Cisco ↔ Huawei interoperation.
- What both share is the RFC 2332 message set, Traffic Indication type 8 for redirect, and
  NHRP over GRE.
- What is likely to differ:
  - the authentication extension's encoding when Huawei hashes the string,
  - NAT handling (Cisco's type-9 extension vs Huawei's own detection),
  - the IPsec mode defaults.
- Validate each in a POC; see
  [2026-11-dsvpn-hub-dmvpn-spokes-sdwan.md](../pocs/2026-11-dsvpn-hub-dmvpn-spokes-sdwan.md).

## Design considerations

- **Prefer shortcut / Phase 3** where both ends support it. Summaries keep spoke routing
  tables small, and spoke-to-spoke tunnels still form [4], [6].
- **The hub is in the resolution path.** Existing shortcuts keep forwarding while the hub is
  down, but routes learned from the hub disappear, so shortcuts become unusable until they
  expire [3]. Plan two hubs. On Huawei, dual-hub needs shortcut mode [6].
- **Spoke-to-hub-LAN traffic never triggers a redirect.** The hub only redirects when it sends
  a packet back out the same overlay [2], [6]. Traffic to the hub's LAN side, or onward into
  another overlay, stays hub-routed by design.
- **Pin IPsec to transport mode on both ends.** Cisco recommends it [5]. Huawei defaults to
  tunnel [6], and with IKEv2 a mode mismatch fails negotiation or yields an unexpected mode
  ([ipsec.md](ipsec.md#ikev2)).
- **Set hold time and registration interval explicitly** on every node. Defaults differ by
  vendor and even within Cisco's own documentation [3], [6].
- **Rate-limit and protect the hub control plane.** Every spoke registration, resolution and
  redirect is punted to the hub CPU.
- **MTU:** IPv4 delivery header + GRE (4–8 B) + ESP. Set the tunnel IP MTU and TCP MSS on
  every node ([gre.md](gre.md#design-considerations)).

## Relationship to other techniques

- [gre.md](gre.md): mGRE, the encapsulation NHRP resolves addresses for.
- [ipsec.md](ipsec.md): IKEv2 and transport-mode ESP protecting the mGRE packets.
- [bgp.md](bgp.md), [ospf-isis.md](ospf-isis.md): routing over the overlay. OSPF needs
  point-to-multipoint; BGP needs next-hop handling matched to the phase.
- [overlay-architecture.md](overlay-architecture.md): DMVPN/DSVPN as the pre-SD-WAN
  controllerless overlay.
- [arp.md](arp.md): NHRP is ARP's NBMA analogue, mapping an overlay address to an underlay
  one.

## References

[1] J. Luciani, D. Katz, D. Piscitello, B. Cole, and N. Doraswamy, "NBMA Next Hop Resolution
    Protocol (NHRP)," RFC 2332, Apr. 1998. [Online]. Available:
    https://www.rfc-editor.org/rfc/rfc2332

[2] F. Detienne, M. Kumar, and M. Sullenberger, "Flexible Dynamic Mesh VPN,"
    draft-detienne-dmvpn-01 (individual Internet-Draft, expired Jun. 2014), Dec. 2013.
    [Online]. Available: https://datatracker.ietf.org/doc/draft-detienne-dmvpn/

[3] "IP Addressing Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Configuring
    NHRP" (NHRP Registration; Developmental Phases of DMVPN and NHRP; Spoke Refresh
    Mechanism; Configuring a GRE Tunnel for Multipoint Operation; Enabling NHRP on an
    Interface; Changing the Length of Time NBMA Addresses Are Advertised as Valid;
    Specifying the NHRP Authentication String). [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_config-nhrp-0.html
    Read Nov. 23, 2026.

[4] "IP Addressing Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Shortcut
    Switching Enhancements for NHRP in DMVPN Networks" (DMVPN Phase 3 Networks Overview;
    NHRP as a Route Source; NHRP Route Watch Infrastructure; NHRP Purge Request Reply; NHRP
    Smart Defaults). [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_nhrp-switch-enhancemts-dmvpn-0.html
    Read Nov. 23, 2026.

[5] "Security and VPN Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Dynamic
    Multipoint VPN" (Configuring the Hub/Spoke for DMVPN; NAT-Transparency Aware DMVPN;
    routing-protocol notes), updated Jan. 11, 2021. [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m_sec-conn-dmvpn-dmvpn-0.html
    Read Nov. 23, 2026.

[6] "NetEngine AR5700, AR6700, and AR8000 Product Documentation," Huawei, V600R026C00, Issue
    01, Sep. 30, 2026 (HedEx library EDOC1100611044, login required). Verify in:
    Configuration > CLI Configuration Guide > VPN Configuration > DSVPN Configuration:
    Overview of DSVPN; Understanding DSVPN (Basic Concepts, DSVPN Fundamentals); Application
    Scenarios (Hierarchical Hub Networking); Configuration Precautions for DSVPN; Default
    Settings for DSVPN; Configuring mGRE; Configuring NHRP; Understanding DSVPN over IPsec;
    Understanding DSVPN NAT Traversal; Understanding Dual-Hub DSVPN; Example for Configuring
    DSVPN in Shortcut Mode (OSPF) and (BGP); VPN Configuration > IPsec Configuration >
    Configuring IKE Negotiation; Example for Configuring DSVPN over IPsec Tunnels Between
    the Hub and Spokes Across Different Networks; References > Command Reference > VPN >
    DSVPN Configuration Commands: nhrp authentication, nhrp authentication standard, nhrp
    entry, nhrp entry holdtime, nhrp entry multicast dynamic, nhrp network-id, nhrp
    redirect, nhrp registration interval, nhrp registration no-unique, nhrp shortcut, nhrp
    tunnel-if-state related; IPsec Configuration Commands: encapsulation-mode, exchange-mode
    (IKEv1 feature package). Confirmed Nov. 23, 2026.

[7] Wireshark source code, `epan/dissectors/packet-gre.h` (`GRE_NHRP 0x2001`) and
    `epan/dissectors/packet-nhrp.c` (operation type 8, extension type codes), master branch.
    [Online]. Available: https://gitlab.com/wireshark/wireshark. Read Nov. 23, 2026.

[8] B. Fox and B. Petri, "NHRP Support for Virtual Private Networks," RFC 2735, Dec. 1999.
    [Online]. Available: https://www.rfc-editor.org/rfc/rfc2735
