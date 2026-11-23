# GRE

- Generic Routing Encapsulation carries one network-layer protocol inside another [1]. In
  design work it shows up as the tunnel that carries multicast and routing protocols
  across a network that only routes unicast between two endpoints, most often inside IPsec
  (GRE over IPsec).
- GRE has no encryption and no standard liveness check (see below), so it is almost always
  paired with IPsec on untrusted transport.

## Encapsulation

- **Packet:** delivery header, then GRE header, then payload packet [1].
- **IPv4 delivery:** IP protocol 47 [1].
- **Header:** a 4-octet base header with a Checksum Present bit, a version and a Protocol
  Type field, followed by optional Checksum and Reserved1 fields (4 octets) when the C bit
  is set [1]. Protocol Type values are EtherTypes, and a receiver should discard a packet
  with an unlisted type [1].
- **Key and Sequence Number:** optional 4-octet extensions, signalled by the K and S bits.
  The Key identifies a flow within a tunnel; the Sequence Number keeps packets in order [2].

GRE header with the RFC 2890 extensions [2]:

```
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|C| |K|S| Reserved0       | Ver |         Protocol Type         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      Checksum (optional)      |       Reserved1 (Optional)    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Key (optional)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Sequence Number (Optional)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
- **Overhead:** the delivery header plus 4 to 16 octets of GRE header (base, checksum, key,
  sequence number), before any IPsec overhead [1], [2].
- **Liveness:** RFC 2784 defines no keepalive [1]. GRE keepalives are vendor features, so
  their behaviour, and whether the peer answers them, depends on the implementation.

## GRE over IPsec

- **Why:** GRE carries multicast, broadcast and non-IP packets, such as routing-protocol
  traffic, which IPsec alone can't. IPsec then protects the GRE packets [3].
- **What IPsec sees:** traffic from the GRE tunnel source to the GRE tunnel destination,
  i.e. between the two gateways' public addresses [3]. A policy-based selector or ACL
  therefore matches those two addresses, not the LAN subnets [3].
- **Mode:** IPsec transport mode is recommended. GRE already adds a public IP header, so
  tunnel mode adds a second one and makes fragmentation more likely [3]. RFC 4301 allows
  transport mode here because the traffic terminates on the gateways
  ([ipsec.md](ipsec.md#transport-and-tunnel-mode)).

Layering, combining the GRE packet structure [1] with ESP transport and tunnel mode
([ipsec.md](ipsec.md#transport-and-tunnel-mode)). GW-A and GW-B are the two gateways'
public addresses, which are also the GRE tunnel source and destination.

```
LAN packet       | IP LAN-A>LAN-B | TCP | Data |

GRE              | IP GW-A>GW-B, proto 47 | GRE | IP LAN-A>LAN-B | TCP | Data |

GRE over IPsec, transport mode (recommended)
                 | IP GW-A>GW-B, proto 50 | ESP hdr | GRE | IP LAN-A>LAN-B | TCP | Data | ESP trlr | ICV |
                                                    |<------------- encrypted ------------->|

GRE over IPsec, tunnel mode (extra outer IP header)
                 | IP GW-A>GW-B, proto 50 | ESP hdr | IP GW-A>GW-B, proto 47 | GRE | IP LAN-A>LAN-B | TCP | Data | ESP trlr | ICV |
```

A policy-based selector sees the middle layer: GRE from GW-A to GW-B. A route-based tunnel
needs no selector, because the route into the GRE tunnel interface chooses the traffic.

## mGRE (multipoint GRE)

mGRE is not a new encapsulation. It changes the tunnel interface model, not the packet:

- **On the wire:** each packet is ordinary GRE, a delivery header with protocol 47 and the
  GRE header above, addressed to one remote endpoint. A capture can't tell an mGRE packet
  from a point-to-point one.
- **Interface model:** one tunnel interface has a source but **no configured destination**,
  and reaches many remote endpoints [4], [5]. The tunnel subnet behaves like a
  non-broadcast multi-access (NBMA) network [5].
- **Destination per packet:** the route's next hop is a tunnel address. A protocol-to-NBMA
  mapping turns it into the remote public address that becomes the delivery header's
  destination. NHRP provides that mapping, which is why Cisco and Huawei both require NHRP on
  an mGRE interface [4], [5]. See [nhrp.md](nhrp.md).
- **Multicast:** a multicast or broadcast packet, such as an OSPF hello, is copied as unicast
  to every endpoint in a multicast mapping list (Cisco `ip nhrp map multicast`, Huawei
  `nhrp entry multicast dynamic`) [4], [5], [6].
- **Key:** an mGRE interface uses the RFC 2890 Key field like any GRE tunnel. Cisco carries the
  key in every GRE packet but in no NHRP message [5]. Both vendors need a unique key when two
  tunnels share a source [4], [5]. Cisco requires the same key on every hub and spoke of one
  DMVPN [6]. Huawei drops a packet whose key doesn't match, and keys must be set on both ends
  or on neither [4].

mGRE is covered here rather than in its own file because, as a protocol, it is GRE. Its
control plane, packet exchanges and vendor solutions (Cisco DMVPN, Huawei DSVPN) live in
[nhrp.md](nhrp.md).

| Item | Cisco IOS XE | Huawei AR (V600R026C00) |
|---|---|---|
| Mode | `tunnel mode gre multipoint` [5] | `tunnel-protocol gre p2mp`. Changing the mode deletes the source and NHRP settings [4] |
| Source | `tunnel source`; front-door VRF with `tunnel vrf` [6] | `source [ vpn-instance <name> ] <ip>` or `source <interface>`. No secondary address. Changing the source deletes the interface's IPsec configuration [4] |
| Key | `tunnel key` [5] | `gre key { simple \| cipher }`, off by default [4] |
| Keepalive | Not used on mGRE in the sources read | mGRE interfaces don't support GRE keepalive [4] |
| IPsec | `tunnel protection ipsec profile` [6] | `ipsec profile <name> [ shared ]`. `shared` is mGRE-only and needed when several mGRE interfaces share one physical interface [4] |

## Cross-vendor / variants

### Huawei (USG firewalls and NetEngine AR routers, V600R026C00)

**Tunnel interface** [3]:

- `tunnel-protocol gre`, `source` (local gateway's outbound address or interface) and
  `destination` (remote gateway's outbound address). Unlike `tunnel-protocol ipsec`, GRE
  needs `destination` on both ends.
- The tunnel IP address can be any unused address, but for a dynamic routing protocol to
  learn routes through the tunnel, both ends must be in the same subnet.
- On the USG, add the tunnel interface to a security zone.

**Binding IPsec** [3], [4]:

- **Profile on the GRE tunnel interface:** no ACL; everything routed into the tunnel is
  GRE-encapsulated, then IPsec-protected [3], [4].
- **ACL-based (USG):** only an ISAKMP IPsec policy, applied to a physical or Virtual-IF
  interface, never a template. The ACL matches the GRE tunnel's source and destination [3].
- **AR:** an IPsec policy group can also be applied directly to a GRE tunnel interface [4].
- **NAT on the same USG:** add an ACL rule permitting the pre-NAT source address [3].

**Tunnel interface state (USG)** [3]: the GRE tunnel interface goes down only when its
destination is unreachable or equals the tunnel's own address, when its source interface
is down, or when keepalive finds the remote end unreachable. IPsec SA state isn't among
the documented conditions. Without keepalive, the interface can be up while the remote end
is unreachable.

**GRE keepalive** (same text in both libraries) [3], [4]:

- `keepalive [ period p [ retry-times n ] ]`, off by default; 5 s and 3 retries when
  enabled.
- It acts only on the end that sends. The peer answers whether or not it has keepalive
  configured, so enable it on both ends to protect both directions.
- With IPsec applied to the tunnel interface (profile), keepalive packets are sent
  unencrypted, and a peer that requires encryption may drop them. With IPsec applied to
  the physical interface (ACL), they are encrypted.

For AR's `ipsec tunnel-state-dynamic` and its restrictions, see
[ipsec.md](ipsec.md#huawei-usg-firewalls-and-netengine-ar-routers-v600r026c00).

**Routing protocols and the USG security policy** [3]:

- `firewall packet-filter basic-protocol enable` is on by default. Unicast packets to or
  from the device itself for OSPF (protocol 89), BGP (TCP 179), BFD (UDP 3784, 4784), LDP
  (TCP 646) and DHCP are then subject to security policy.
- Multicast packets, such as OSPF hellos to 224.0.0.5, are never controlled by security
  policy, so an OSPF neighbour can appear while unicast exchanges are dropped.
- Huawei advises against turning the function off, because it then bypasses even deny
  rules.

## Design considerations

- **Routing over the tunnel follows real reachability; static routes don't.** A routing
  protocol's packets cross the tunnel (encrypted when IPsec protects it), so learned routes
  exist only while the GRE-over-IPsec path works. A static route into the tunnel follows
  only the GRE interface's state, which on Huawei ignores IPsec SA state [3]. Prefer a
  routing protocol whenever there is a backup path or the routes are redistributed onward.
- **Recursive routing:** the route to the tunnel destination must never resolve through
  the tunnel itself. Keep a specific underlay route (static or from the WAN) to the peer's
  public address, and don't advertise the public addresses into the routing protocol that
  runs over the tunnel.
- **Keepalive with a profile:** keepalive tests the GRE path, not IPsec, and may be dropped
  by an encrypting peer [3]. Use the routing protocol's own timers or BFD for failure
  detection instead.
- **MTU:** account for the IPv4 delivery header, GRE header and ESP overhead. Transport mode
  keeps the overhead down [3].
- **Firewall control plane:** on a firewall endpoint, permit the routing protocol's unicast
  packets between the tunnel addresses to and from the Local zone [3].

## Relationship to other techniques

- [ipsec.md](ipsec.md): GRE over IPsec, route-based IPsec, and Huawei tunnel-state options.
- [ospf-isis.md](ospf-isis.md), [bgp.md](bgp.md): routing protocols run over GRE tunnels.
- [management-plane.md](management-plane.md): ERSPAN uses GRE encapsulation.
- [nhrp.md](nhrp.md): NHRP, the control plane of mGRE, and the Cisco DMVPN and Huawei DSVPN
  solutions built on it.
- [overlay-architecture.md](overlay-architecture.md): on the AR, a `gre p2mp` (mGRE) tunnel
  interface with an IPsec profile implements DSVPN [4].

## References

[1] D. Farinacci, T. Li, S. Hanks, D. Meyer, and P. Traina, "Generic Routing Encapsulation
    (GRE)," RFC 2784, Mar. 2000. [Online]. Available: https://www.rfc-editor.org/rfc/rfc2784

[2] G. Dommety, "Key and Sequence Number Extensions to GRE," RFC 2890, Sep. 2000. [Online].
    Available: https://www.rfc-editor.org/rfc/rfc2890

[3] "HiSecEngine USG6000F, USG6000G Product Documentation," Huawei, V600R026C00, Issue 01,
    Sep. 30, 2026 (HedEx library EDOC1100605493, login required). Verify in: Configuration >
    Configuration Guide > VPN Configuration > IPsec Configuration > Understanding IPsec >
    IPsec Enhancements > Understanding GRE over IPsec; Configuration Examples for IPsec >
    CLI: Example for Establishing a GRE over IPsec Tunnel Using an IPsec Profile; Using
    ISAKMP; VPN Configuration > GRE Configuration > Understanding GRE > Keepalive Detection;
    Configuring GRE - CLI > Configuring a GRE Tunnel > Configuring a Tunnel Interface,
    (Optional) Enabling the Keepalive Function; Command Reference > VPN > GRE Configuration
    Commands > keepalive (Tunnel interface view); Command Reference > Security Protection >
    Security Policy Configuration Commands > firewall packet-filter basic-protocol enable.
    Confirmed Nov. 14, 2026.

[4] "NetEngine AR5700, AR6700, and AR8000 Product Documentation," Huawei, V600R026C00, Issue
    01, Sep. 30, 2026 (HedEx library EDOC1100611044, login required). Verify in:
    Configuration > CLI Configuration Guide > VPN Configuration > IPsec Configuration >
    Configuring IPsec Using an IPsec Profile > Configuring a Tunnel Interface and Applying
    an IPsec Profile; Configuring IPsec Using an IPsec Policy > Applying an IPsec Policy
    Group; References > Command Reference > VPN > GRE Configuration Commands > keepalive
    (Tunnel interface view); Configuration > CLI Configuration Guide > VPN Configuration >
    DSVPN Configuration > Understanding DSVPN > Basic Concepts of DSVPN (mGRE attributes, no
    keepalive); Configuring Basic DSVPN Functions > Configuring mGRE; Configuring DSVPN over
    IPsec; References > Command Reference > VPN > GRE Configuration Commands > source (MGRE
    Tunnel interface view), gre key; IPsec Configuration Commands > ipsec profile (Tunnel
    interface view); DSVPN Configuration Commands > nhrp entry multicast dynamic. Confirmed
    Nov. 14, 2026; DSVPN and mGRE sections Nov. 23, 2026.

[5] "IP Addressing Configuration Guide, Cisco IOS XE 17.x," Cisco, chapter "Configuring
    NHRP" (sections How NHRP and NBMA Networks Interact; Configuring a GRE Tunnel for
    Multipoint Operation; Configuring a Static IP-to-NBMA Address Mapping on a Station).
    [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_config-nhrp-0.html
    Read Nov. 23, 2026.

[6] "Security and VPN Configuration Guide, Cisco IOS XE 17.x," Cisco, chapters "Dynamic
    Multipoint VPN" (Configuring the Hub/Spoke for DMVPN: `tunnel key`, `ip nhrp map
    multicast`) and "DMVPN Support for IWAN" (`tunnel vrf`, `tunnel protection ipsec
    profile`), both updated Jan. 11, 2021. [Online]. Available:
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m_sec-conn-dmvpn-dmvpn-0.html
    and
    https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/sec-vpn/b-security-vpn/m-sec-conn-dmvpn-mtt.html
    Read Nov. 23, 2026.
