# IPsec

- IPsec protects IP traffic between two peers with security associations (SAs) negotiated
  by IKE. In network design it is the default site-to-site and third-party attachment
  encryption: branch to HQ, branch to SASE PoP, and DC to cloud.
- The protocols are standard. How a device decides which traffic to protect, which routes
  point at a tunnel, and when a tunnel interface is up are implementation choices, and they
  differ between vendors and between product lines of one vendor.

## Architecture

- **SA:** a simplex connection protected by AH or ESP, never both. Protecting traffic with
  both needs two SAs [1].
- **Databases:** the Security Policy Database (SPD) decides whether a packet is protected,
  bypassed or discarded. The Security Association Database (SAD) holds the SA parameters [1].
- **Forwarding is outside IPsec:** RFC 4301 assumes only that traffic that has passed IPsec
  processing is forwarded "in a fashion consistent with the context in which IPsec is
  implemented". Routing tables, tunnel interfaces and their state aren't part of the
  standard [1].
- **ESP:** the header that precedes ESP carries protocol number 50 [2]. A compliant
  implementation must not allow an ESP SA with both NULL encryption and no integrity
  algorithm [1].

### ESP packet format

From RFC 4303, Figure 1 [2]. The SPI and Sequence Number are 4 octets each. Integrity
covers everything from the SPI through the Next Header field; confidentiality covers the
Payload Data through the Next Header field.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ ----
|               Security Parameters Index (SPI)                 | ^Int.
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ |Cov-
|                      Sequence Number                          | |ered
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ | ----
|                    Payload Data* (variable)                   | |   ^
~                                                               ~ |   |
|                                                               | |Conf.
+               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ |Cov-
|               |     Padding (0-255 bytes)                     | |ered*
+-+-+-+-+-+-+-+-+               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ |   |
|                               |  Pad Length   | Next Header   | v   v
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ ------
|         Integrity Check Value-ICV   (variable)                |
~                                                               ~
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Transport and tunnel mode

| Mode | Header placement | Use |
|---|---|---|
| Transport | ESP after the IP header; protects only the next-layer protocol, not the IP header [1] | Host to host, or traffic that terminates on a gateway acting as a host [1] |
| Tunnel | An SA applied to an IP tunnel; access controls apply to the inner headers [1] | Whenever either end is a security gateway, the SA must be tunnel mode, with two exceptions: traffic destined for the gateway itself, and a transport SA between intermediate systems, which gateways may support [1] |

IPv4 packets before and after ESP, from RFC 4303 sections 3.1.1 and 3.1.2 [2]:

```
Transport mode
                 BEFORE APPLYING ESP
            ----------------------------
      IPv4  |orig IP hdr  |     |      |
            |(any options)| TCP | Data |
            ----------------------------

                 AFTER APPLYING ESP
            -------------------------------------------------
      IPv4  |orig IP hdr  | ESP |     |      |   ESP   | ESP|
            |(any options)| Hdr | TCP | Data | Trailer | ICV|
            -------------------------------------------------
                                |<---- encryption ---->|
                          |<-------- integrity ------->|

Tunnel mode
                 AFTER APPLYING ESP
            -----------------------------------------------------------
      IPv4  | new IP hdr* |     | orig IP hdr*  |   |    | ESP   | ESP|
            |(any options)| ESP | (any options) |TCP|Data|Trailer| ICV|
            -----------------------------------------------------------
                                |<--------- encryption --------->|
                          |<------------- integrity ------------>|
```

GRE over IPsec uses the second exception: the protected packets are GRE packets between the
two gateways, so transport mode is allowed and avoids a second outer IP header. See
[gre.md](gre.md).

### IKEv2

- **Exchanges:** every IKE message is half of a request/response pair. IKE_SA_INIT and
  IKE_AUTH (four messages in the common case) set up the IKE SA and the first Child SA, and
  must complete before any other exchange. Later exchanges are CREATE_CHILD_SA or
  INFORMATIONAL [3].
- **Mode negotiation:** Child SAs are tunnel mode unless a USE_TRANSPORT_MODE notification is
  sent and accepted. If the responder declines, the SA is tunnel mode, and an initiator that
  can't accept that must delete it [3].
- **Ports:** IKE sends and receives on UDP 500. Messages may also arrive on UDP 4500, where
  they start with four zero octets [3].
- **Traffic selectors:** when a packet matches a "protect" SPD entry and no SA exists, IKE
  creates one. Keeping the SPD up to date is outside IKE's scope [3].
- **Liveness:** if only outgoing traffic has been seen on an IKE SA's Child SAs, a peer needs
  to confirm the other end is alive to avoid black holes. RFC 7296 calls this a liveness
  check, "sometimes called dead peer detection" [3]. An INFORMATIONAL request with no
  payloads is commonly used for it, and the recipient must answer every INFORMATIONAL
  request [3].

IKEv2 workflow, built from the exchanges in RFC 7296 sections 1.2–1.4 [3]. `SK { }` means
encrypted and integrity-protected with keys derived from the IKE_SA_INIT Diffie-Hellman
exchange; `[ ]` marks optional payloads.

```
Initiator                                              Responder
    |  outbound packet matches a "protect" SPD entry, no SA yet  |
    |                                                            |
    |  IKE_SA_INIT  (UDP 500, clear text)                        |
    |-- HDR, SAi1, KEi, Ni ------------------------------------->|  crypto offer, DH value, nonce
    |<------------------------- HDR, SAr1, KEr, Nr, [CERTREQ] ---|  chosen suite, DH value, nonce
    |                                                            |
    |  both sides derive SKEYSEED -> SK_e / SK_a keys            |
    |                                                            |
    |  IKE_AUTH  (encrypted)                                     |
    |-- HDR, SK {IDi, [CERT,] [CERTREQ,] [IDr,] AUTH,            |
    |            SAi2, TSi, TSr} ------------------------------->|  identity + proof, Child SA offer,
    |<------- HDR, SK {IDr, [CERT,] AUTH, SAr2, TSi, TSr} -------|  traffic selectors
    |                                                            |
    |====== IKE SA + first Child SA (pair of ESP SAs) up =========|
    |<================= ESP data, both directions ===============>|
    |                                                            |
    |  CREATE_CHILD_SA  (new Child SA)                           |
    |-- HDR, SK {SA, Ni, [KEi,] TSi, TSr} ---------------------->|
    |<------------------------ HDR, SK {SA, Nr, [KEr,] TSi, TSr} |
    |                                                            |
    |  INFORMATIONAL  (liveness check, delete, errors)           |
    |-- HDR, SK {} ---------------------------------------------->|  empty request = liveness check
    |<--------------------------------------------- HDR, SK {} --|  must be answered
```

### NAT traversal

An endpoint that detects a NAT must send all later traffic from UDP 4500, which is reserved
for UDP-encapsulated ESP and IKE; UDP encapsulation must never use port 500 [3]. ESP is
then carried in UDP on the same ports as IKE [4]. The SPI must not be zero, which lets a receiver tell ESP from IKE on port 4500:
an IKE message starts with a 4-octet Non-ESP Marker of zeros where the SPI would be [4].

```
UDP-encapsulated ESP (RFC 3948, section 2.1)
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Source Port            |      Destination Port         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Length              |           Checksum            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      ESP header [RFC2406]                     |
~                                                               ~
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

NAT-keepalive packets (a single 0xFF octet) only hold the NAT mapping open, and receivers
must not use them to decide whether a connection is live [4].

## Policy-based and route-based IPsec

RFC 4301 defines only the SPD [1]; "policy-based" and "route-based" are industry names for
the two ways implementations feed it. Huawei's documentation describes both [5]:

| Model | What selects protected traffic | Routing |
|---|---|---|
| Policy-based | An ACL in the policy bound to the outbound interface [5] | A route to the remote subnet out of that interface via the underlay next hop [5] |
| Route-based (tunnel interface) | Every packet routed into the tunnel interface; no ACL [5] | A route, static or dynamic, with the tunnel as outbound interface [5] |

Route-based IPsec makes the routing table the policy, so a dynamic routing protocol can run
over it when the tunnel carries multicast (GRE over IPsec, see [gre.md](gre.md)).

## Cross-vendor / variants

### Huawei (USG firewalls and NetEngine AR routers, V600R026C00)

Both lines offer the same three ways to build a tunnel. The configuration text is shared,
but the AR documents options the USG doesn't [5], [6].

| Method | Selects traffic by | Notes |
|---|---|---|
| ISAKMP IPsec policy | Advanced ACL | Applied to an interface as a policy group [5], [6] |
| Policy template | ACL of the initiating peer | Hub accepting many peers [5], [6] |
| IPsec profile | Routing into a tunnel interface, no ACL | `tunnel-protocol ipsec` or `gre` (AR also mGRE for DSVPN) [5], [6] |

Required routes [5]:

- Every mode needs a route to the peer's public address, so IKE negotiation packets leave
  the right interface.
- Policy mode: a route to the remote subnet out of the interface with the policy, via the
  public next hop (`ip route-static 10.1.1.0 24 1.1.1.254`).
- Profile mode: a route with the tunnel as outbound interface
  (`ip route-static 10.1.1.0 24 Tunnel1`). For `tunnel-protocol ipsec`, a destination is
  needed on one end only.

Platform differences:

| Item | USG6000F/G | AR5700/6700/8000 |
|---|---|---|
| Profile to tunnel interface | One profile per tunnel interface and one tunnel interface per profile; `ipsec profile name [ alone \| master \| slave ]` [5] | One profile per tunnel interface; a profile can serve up to 32 tunnel interfaces, at most two with the same source and destination. `shared` (mGRE only) negotiates one tunnel per physical interface [6] |
| Tunnel interface state tied to IPsec | Not documented; no such command in the library [5] | `ipsec tunnel-state-dynamic enable`, restrictions below [6] |
| Route injection | `route inject`, documented below [5] | The library has a policy-template example with reverse route injection; not reviewed yet |

**Tunnel interface state on the AR** [6]:

- Default: a tunnel interface goes up when an IPsec policy or profile is bound to it and down
  when it is unbound, whatever the state of the IPsec tunnel.
- `ipsec tunnel-state-dynamic enable` (system view, off by default, applies to every tunnel
  interface): the interface goes up when an IPsec tunnel is established and down when all
  tunnels on it are disconnected or the policy or profile is unbound.
- It has no effect when negotiation needs the interface itself to be up:
  - the tunnel interface's address equals the policy's `tunnel local` address;
  - neither a tunnel source nor `tunnel local` is set, so the tunnel interface's address is
    used to negotiate;
  - a template IPsec policy is used;
  - negotiation uses IPv6;
  - tunnel setup is triggered by traffic.
- `sa trigger-mode { auto | traffic-based }` sets how setup is triggered, defaults to
  `traffic-based`, and exists only in the ISAKMP IPsec policy view. The association
  therefore needs an ISAKMP policy with `sa trigger-mode auto`. The documentation doesn't
  say how a profile triggers setup.
- An IPsec policy group can be applied to a tunnel interface whose encapsulation is IPsec,
  mGRE or GRE.

**Route injection (USG)** [5]:

- ISAKMP and template IPsec policies only, and not when the policy group is on a Layer 2
  interface.
- `route inject { static | dynamic } [ preference p ]` installs a route to the destination
  subnet taken from the SA's flow information. `static` keeps it regardless of tunnel
  state; `dynamic` installs it only while the tunnel is up.
- The next hop defaults to the address of the interface the policy is applied to.
  `route inject nexthop <ip>` replaces it. That's required in hot standby, so the two
  devices inject different next hops, and when the protected destination is the tunnel's
  remote address. `nexthop auto` uses the next hop of the best route to the destination.
- Equal preferences load-balance injected routes; different preferences make one a backup.
- `firewall verification ipsec-route enable` (default on) keeps injected routes consistent
  when they change in bulk.

**Other Huawei specifics** [5]:

- `tunnel local` is chosen from routes during negotiation. Set it when there are equal-cost
  routes to the peer, the interface address is dynamic, or the interface has secondary
  addresses.
- Security policy on the USG: permit Local↔Untrust between the two public addresses for
  IKE (UDP 500, ESP, UDP 4500 with NAT traversal), and Trust↔Untrust between the protected
  subnets.
- Hot standby with IPsec is in [hisecengine-usg.md](../vendor-matrix/huawei/hisecengine-usg.md).

## Design considerations

- **Routes don't follow tunnel state by default.** Because forwarding is outside the
  standard [1], a static route into a route-based tunnel is typically installed while the
  tunnel interface is up. On the AR, by default, that interface is up once the policy or
  profile is bound, not when IKE succeeds [6]; the USG documentation doesn't tie it to IPsec
  state either [5]. Traffic then black-holes until the peer answers. Ways to fix this,
  in order of portability:
  1. Run a routing protocol inside the tunnel. Its packets are protected, so routes exist
     only while the tunnel works. A plain IPsec tunnel interface carries unicast only, so
     OSPF needs GRE over IPsec; BGP's unicast session can run over either [5].
  2. Dynamic route injection, on platforms that have it (USG [5]).
  3. A platform-specific link between interface state and SA state (AR
     `tunnel-state-dynamic` [6]), within its restrictions.
- **Liveness:** enable IKE liveness checks (DPD) so a dead peer is found without user
  traffic [3]. NAT keepalives don't count [4].
- **Policy vs. route-based:** policy-based is the cross-vendor lowest common denominator
  for third-party peers (SASE PoPs, cloud gateways) but scales poorly; every new subnet pair
  is a selector change on both ends. Prefer route-based where both ends support it.
- **Firewall control-plane rules:** a firewall terminating IPsec must permit IKE and ESP to
  itself, and, if a routing protocol runs inside the tunnel, the routing protocol's unicast
  packets too. See [gre.md](gre.md) for the USG rule.

## Relationship to other techniques

- [gre.md](gre.md): GRE over IPsec, for multicast and routing protocols through the tunnel.
- [overlay-architecture.md](overlay-architecture.md): SD-WAN overlays are typically IPsec
  meshes managed by a controller.
- [sase.md](sase.md): IPsec is the standard attachment for third-party sites to an SSE/SASE
  PoP.
- [bgp.md](bgp.md), [ospf-isis.md](ospf-isis.md): routing protocols run inside route-based
  tunnels.
- [fhrp.md](fhrp.md): Huawei IPsec hot standby terminates the tunnel on a VRRP virtual
  address.

## References

[1] S. Kent and K. Seo, "Security Architecture for the Internet Protocol," RFC 4301,
    Dec. 2005. [Online]. Available: https://www.rfc-editor.org/rfc/rfc4301

[2] S. Kent, "IP Encapsulating Security Payload (ESP)," RFC 4303, Dec. 2005. [Online].
    Available: https://www.rfc-editor.org/rfc/rfc4303

[3] C. Kaufman, P. Hoffman, Y. Nir, P. Eronen, and T. Kivinen, "Internet Key Exchange
    Protocol Version 2 (IKEv2)," RFC 7296, Oct. 2014. [Online]. Available:
    https://www.rfc-editor.org/rfc/rfc7296

[4] A. Huttunen, B. Swander, V. Volpe, L. DiBurro, and M. Stenberg, "UDP Encapsulation of
    IPsec ESP Packets," RFC 3948, Jan. 2005. [Online]. Available:
    https://www.rfc-editor.org/rfc/rfc3948

[5] "HiSecEngine USG6000F, USG6000G Product Documentation," Huawei, V600R026C00, Issue 01,
    Sep. 30, 2026 (HedEx library EDOC1100605493, login required). Verify in Configuration >
    Configuration Guide > VPN Configuration > IPsec Configuration:
    - Configuring IPsec - CLI > Configuring IPsec Using an IPsec Policy > Configuring an
      IPsec Policy > Configuring an ISAKMP IPsec Policy;
    - Configuring IPsec - CLI > Configuring IPsec Using an IPsec Profile > Configuring a
      Tunnel Interface and Applying an IPsec Profile;
    - Configuring IPsec - CLI > Enhanced IPsec Configuration > IPsec Reliability >
      Configuring IPsec Route Injection; Configuring IPsec Route Verification;
    - Configuration Examples for IPsec > CLI: Example for Establishing an IPsec Tunnel in
      ISAKMP Mode (Using PSK Authentication); Using an IPsec Profile (Through PSK
      Authentication); Using an IPsec Policy Template (Branches Use the Same PSK for
      Authentication and Reverse Route Injection).

    Confirmed Nov. 14, 2026.

[6] "NetEngine AR5700, AR6700, and AR8000 Product Documentation," Huawei, V600R026C00,
    Issue 01, Sep. 30, 2026 (HedEx library EDOC1100611044, login required). Verify in
    Configuration > CLI Configuration Guide > VPN Configuration > IPsec Configuration:
    - Configuring IPsec Using an IPsec Policy > Applying an IPsec Policy Group;
    - Configuring IPsec Using an IPsec Profile > Configuring a Tunnel Interface and Applying
      an IPsec Profile;
    - References > Command Reference > VPN > IPsec Configuration Commands > ipsec
      tunnel-state-dynamic enable; ipsec profile (Tunnel interface view); sa trigger-mode.

    Confirmed Nov. 14, 2026.
