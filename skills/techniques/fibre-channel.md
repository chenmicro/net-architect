# Fibre Channel (FC)

- Fibre Channel is a dedicated storage networking technology, standardized by the
  INCITS T11 committee under ANSI [1, §2.1].
- **Its own ecosystem**: FC is not an Ethernet or IP variant. It has its own physical
  layer, encoding, frame format, addressing, routing protocol, fabric services, and
  flow control. FC switches, host bus adapters (HBAs), and optics are separate
  products from Ethernet ones.
- **Upper-layer protocols**: FC carries SCSI (FCP), NVMe (FC-NVMe), mainframe FICON,
  and IP [2, slide 8].
- **Where it comes up in design**: as the incumbent SAN that NVMe over RoCE or NVMe
  over TCP would replace.

## Protocol stack

FC defines five levels [1, §2.3], [2, slide 8]:

| Level | Function |
|---|---|
| FC-0 | Physical interface and media (link speeds) |
| FC-1 | Encoding and decoding (8b/10b, 64b/66b, 256b/257b), ordered sets, link control protocol |
| FC-2 | Frame structure, flow control, classes of service, sequence and exchange management |
| FC-3 | Common fabric services |
| FC-4 | Upper-layer protocol mappings: FCP-4 (SCSI), FC-NVMe-2 (NVMe), FC-SB-6 (FICON), RFC 4338 (IP) |

## Frame format

```
+-----+-----------+--------------------------------+-----+-----+
| SOF | FC Header |          Data Field            | CRC | EOF |
|  4  |    24     | Optional Header(s) + Payload   |  4  |  4  |
|     |           |        0 to 2112 octets        |     |     |
+-----+-----------+--------------------------------+-----+-----+
                  maximum frame: 2148 octets
```

- SOF and EOF are FC transmission words that delimit the frame.
- The value of SOF selects the class of service.
- The CRC is 32-bit, using the FDDI polynomial [1, §2.3].
- **Error correction before the CRC**: Brocade Gen 8 uses dual forward error correction
  (FEC), which corrects some bit errors so they never reach the CRC check [4]. The CRC
  above is what catches the rest. Whether a Cisco module offers an equivalent FEC, or a
  link-level retransmission option, is not checked here [5].
- The data field carries up to 2112 octets [1, §2.3], [2, slide 9].

The 24-octet header [2, slide 9], [1, §2.3–2.4]:

| Word | Bits 31–24 | Bits 23–16 | Bits 15–8 | Bits 7–0 |
|---|---|---|---|---|
| 0 | R_CTL | D_ID (destination N_Port_ID) | | |
| 1 | CS_CTL | S_ID (source N_Port_ID) | | |
| 2 | TYPE (FC-4 protocol) | F_CTL | | |
| 3 | SEQ_ID | DF_CTL | SEQ_CNT | |
| 4 | OX_ID | | RX_ID | |
| 5 | Parameter | | | |

- **Sequence**: an FC-4 information unit becomes one sequence of frames. The frames
  share a SEQ_ID, and SEQ_CNT orders them [1, §2.4].
- **Exchange**: related sequences form an exchange, which is one operation such as a
  SCSI or NVMe I/O. The exchange is identified by the originator and responder
  exchange IDs (OX_ID, RX_ID) [1, §2.4].
- **Classes of service** [1, §2.3]:
  - Class 1: dedicated connection;
  - Class 2: multiplexed, with delivery confirmation;
  - Class 3: datagram;
  - Class 4: fractional bandwidth;
  - Class 6: reliable multicast.
  - Switches commonly support Class 2, Class 3, and Class F (switch-to-switch) [4].

## Addressing, login, and fabric services

- **Identifiers**:
  - Each port has a permanent 64-bit name, the World Wide Name (N_Port_Name).
  - Each port also gets a volatile 24-bit address, the N_Port_ID or FCID, used for
    forwarding [1, §2.2].
  - The first byte of the FCID is the switch's Domain ID, roughly the equivalent of
    an IP subnet [2, slide 16].
- **Port types** [2, slide 13], [1, §2.1]:
  - N_Port: the node port on a host or target.
  - F_Port: the switch port facing an N_Port.
  - E_Port: a switch port facing another switch, forming an inter-switch link (ISL).
  - NL_Port and FL_Port: the loop-capable variants.
- **Logins** [1, §2.2], [2, slides 17, 28]:
  - **FLOGI** (fabric login): the N_Port logs in to the fabric and receives its FCID.
    The receive data field size, and so the maximum frame size, is negotiated here.
  - **PLOGI** (port login): two N_Ports log in to each other before communicating.
    It also logs into the name server.
  - **PRLI** (process login): sets up the FC-4 protocol, such as SCSI or NVMe.
- **Well-known addresses** [2, slide 16]:
  - 0xFFFFFE: fabric login server, which receives FLOGI.
  - 0xFFFFFD: fabric controller.
  - 0xFFFFFC: name server (FCNS).
  - 0xFFFFFA: management server.
- **Routing**:
  - Fabric Shortest Path First (FSPF) computes paths across arbitrary topologies of up
    to 239 switches [2, slide 20].
  - Cisco MDS load-balances across up to 16 equal-cost paths [5].

### Plug-and-play

FC's plug-and-play is the login sequence itself, not a discovery protocol bolted on
top: a port that comes up gets addressed, registered, and notified with nobody
configuring it.

1. **The switch port works out what its peer is.** An E_Port candidate sends ELP to
   the fabric controller (0xFFFFFD) or waits for FLOGI; whichever arrives decides
   whether the port becomes an E_Port or an F_Port [2, slides 14, 16].
2. **The fabric addresses the device, not the administrator.** The N_Port logs in to
   the login server (0xFFFFFE) and the F_Port allocates an FCID out of its own domain
   [2, slide 17]. The host holds no address of its own — no DHCP, no VLAN, no per-port
   configuration — and the FCID is volatile, so it is reissued at every login.
3. **Registration makes the port findable.** The port logs in to the name server
   (0xFFFFFC) and registers its FC-4 type, for example "scsi-fcp, initiator", with
   RFT_ID [2, slide 28].
4. **Discovery is a lookup, not a scan.** An initiator asks the name server for the
   ports of a given FC-4 type (GID_FT) and is told which FCIDs it may reach. The
   active zone set decides the answer, so access control and discovery are the same
   database [2, slides 19, 28].
5. **Changes are pushed, not polled.** Ports register for state change notification
   (SCR) with the fabric controller; when a device enters or leaves the fabric, the
   switches send RSCNs to the ports that asked for them, and those ports re-query the
   name server [2, slides 18–19]. This is FC's built-in equivalent of the switch-to-host
   fault notification that NVMe/RoCE SANs add through vendor extensions.

- **What that buys**: an initiator reaches a target without knowing the topology
  between them, because the fabric resolves the path [2, slide 33]. A new port is
  reachable once it logs in; a recabled port just logs in again.
- **Zones stay the administrator's job, and they decide whether plug-and-play survives
  a change.** Zoning is a standard fabric service, not a vendor add-on, and the fabric
  answers queries from the active zone set — it never creates a zone for a new device
  [2, slide 28].
  - Zones written against the 64-bit port name follow the device: it keeps its access
    when moved, because the name is permanent while the FCID is not [1, §2.2],
    [2, slides 16–17].
  - Zones written against FCIDs or switch ports follow the cable instead, so a moved
    device arrives outside its zone.

## Flow control

- **Buffer-to-buffer credits**: FC is lossless by design [2, slides 22–25].
  - **Part of the standard, not a vendor feature.** Credit flow control is defined at
    FC-2 and is how every FC link works, whichever vendor made the switch or HBA: the
    receiver advertises a buffer count in its login service parameters, the sender
    decrements per frame and waits for R_RDY to replenish [1, §2.3], [2, slides 22–25].
  - Each side of a link advertises its number of receive buffers during login. The
    two values may differ and are not negotiated.
  - The sender decrements its credit count for every frame it sends and stops at
    zero.
  - The receiver returns an R_RDY primitive each time it frees a buffer, and the
    sender increments its count.
  - No frame is sent unless the receiver has a buffer for it, so congestion never
    causes drops.
  - **What is vendor-specific**: how many buffers a port or port group owns, how many
    of them one long-distance port may claim, and how the switch recovers lost credits.
    - Cisco publishes a 16,000-credit ceiling per 64G port [5], which is also its
      long-distance limit.
    - Brocade pools a port group's buffers and lets one long-distance E_Port claim the
      unreserved ones: 22,338 unreserved credits per 64-port group on a G720, or 16,578
      when QoS is not enabled. Allocation is `portCfgLongDistance`, with separate credit
      recovery, and Extended Fabrics adds DWDM metro links with in-flight compression and
      encryption on ISLs [4], [9].
    - The mechanism is identical; the pool sizes are not.
- **Slow drain**: a slow or congested device holds credits, which backs up traffic
  toward it.
  - Vendors add detection and mitigation; the per-platform list is in
    [Cross-vendor / variants](#cross-vendor--variants).
  - This is the FC counterpart of PFC head-of-line blocking on lossless Ethernet
    ([roce.md](roce.md)).
- **Sizing credits for distance** — derived here from frame time, and it matches the
  formula Brocade publishes (below). Re-run the vendor's own calculator before
  committing a design.
  - One credit is one receive buffer, so one frame may be in flight per credit.
    Keeping a link at its full rate therefore needs one credit for every frame that
    fits into the round trip:

    ```text
    credits ≈ RTT ÷ frame time           frame time = frame size ÷ per-direction rate
    ```

  - Assumptions: light travels at about 2 × 10^8 m/s in fibre, so the round trip is
    about 10 µs per km (5 µs/km each way); frames are 2148 octets at full size
    (2112-octet payload plus header, CRC, and SOF/EOF); 512-byte I/Os use 548-octet
    frames.
  - Result at full-size frames:

    | Speed | Payload rate, one direction | Frame time | Credits per km, 2 KB frames | Credits per km, 512 B frames |
    |---|---|---|---|---|
    | 16GFC | 1600 MB/s | 1.3 µs | ~7 | ~29 |
    | 32GFC | 3200 MB/s | 0.67 µs | ~15 | ~58 |
    | 64GFC | 6400 MB/s | 0.34 µs | ~30 | ~117 |
    | 128GFC | 12.4 GB/s | 0.17 µs | ~58 | ~227 |
    | 256GFC | 24.9 GB/s | 0.086 µs | ~115 | ~453 |

  - **Rule of thumb**: with 2 KB frames, plan about half the link speed in Gbit/s of
    credits per km of link, at every generation. A 100 km 64GFC ISL therefore needs
    roughly 3,000 credits per port.
  - **Brocade documents the same rule** [9]: buffers for distance = distance × link
    speed ÷ 2, plus 6 credits reserved for fabric services (and 14 more with QoS). A
    50 km 32G link is `50 × 32 ÷ 2 + 6 = 806` credits. Read per kilometre, that is
    speed ÷ 2 — the estimate above — so it is safe to quote as a vendor figure in a
    Brocade fabric.
  - **At 128G**: the rule gives 64 credits per km of 2 KB frames, so about 6,400
    credits for a 100 km link (`100 × 128 ÷ 2 + 6 = 6,406`) and about 12,800 for
    200 km. At 128G, long distance is a buffer-capacity problem well before it is an
    optics problem.
    - The table above shows ~58 per km for 128G because the frame-time derivation uses
      the exact 12.4 GB/s payload rate; Brocade's rule rounds to speed ÷ 2 and gives 64.
      Plan on the higher number.
  - **No published 128G per-port maximum.** Brocade's credit tables stop at 64G
    (57.8 Gbit/s line rate), and the Cisco module documented here is 64G per port
    [5], [9]. So size a 128G link against its port group's unreserved pool, and
    confirm the per-port ceiling with the vendor.
  - **Frame size sets the number**, not just speed: credits scale inversely with frame
    size, so 512-byte I/Os need about four times as many as 2 KB. A storage workload's
    real I/O size is the input that matters most. Brocade expresses the same thing by
    inflating the distance: `desired_distance = real distance × 2112 ÷ average payload`,
    so a 1024-byte average payload doubles the credits [9].
  - **Cross-check**: Cisco's 16,000-credit ceiling [5] covers about 500 km at 2 KB
    frames and about 140 km at 512 bytes by this estimate.
  - **Credits are per link, not end to end.** Each hop buffers its own frames, so only
    the long ISLs need the extra credits; short hops on either side do not pool their
    buffers to help a long one.

## Speeds

| Generation | Throughput (MB/s) | Line rate | T11 spec complete | On the market |
|---|---|---|---|---|
| 8GFC | 1600 | 8.5 GBd NRZ | 2006 | 2008 |
| 16GFC | 3200 | 14.025 GBd NRZ | 2009 | 2011 |
| 32GFC | 6400 | 28.05 GBd NRZ | 2013 | 2016 |
| 64GFC | 12800 | 28.9 GBd PAM-4 | 2017 | 2020 |
| 128GFC | 24850 | 56.1 GBd PAM-4 | 2022 | 2024 |
| 256GFC | 49700 | 112.2 GBd PAM-4 | 2025 | Market demand |

Source: [3].

- **The throughput column counts both directions.** A 64GFC link's 28.9 GBd PAM-4 line
  rate carries 57.8 Gbit/s, which is 7.2 GB/s, so 12,800 MB/s cannot be a one-way
  payload rate. Half of each figure in the table is the per-direction payload rate.
  Credit sizing (see [Flow control](#flow-control)) works from the per-direction rate,
  so halve these numbers before using them there.
- Each generation is backward compatible with at least the two before it [3].
- Shipping examples:
  - Brocade Gen 8 G820: 56 × 128G ports, 580 ns local-switching latency at 128G, and
    autosensing 128/64/32/16G [4].
  - Cisco MDS 9700: 48 × 64G per module, autosensing 64/32/16/8G [5].

## Standards access

- **Who maintains the standards**: T11 maintains them; the FC industry association
  (FCIA) does not [6].
- **Getting them**:
  - Published standards are bought from INCITS, through the ANSI eStandards Store or
    Accuris (Techstreet) [6], [7].
  - Drafts are free to download only during public review [7].
- **Host support**: FC support is included in Linux distributions [8].
- **What this means**: FC is an open standard in the same sense as RoCE. Anyone may
  implement it, but the specification text is not free. The practical constraint is
  the dedicated hardware ecosystem.

## Cross-vendor / variants

The two FC switch vendors are Broadcom (Brocade) and Cisco (MDS):

| | Brocade Gen 8 (G820) [4] | Cisco MDS 9700 64G module [5] |
|---|---|---|
| Fastest port | 128G | 64G |
| Fabric partitioning | Zoning (default, port/WWN, peer, target-driven), Integrated Routing | Zoning (enhanced, Smart Zoning), VSANs, Inter-VSAN Routing |
| Link encryption | AES-GCM-256 on ISLs; post-quantum algorithms | TrustSec FC link encryption on ISLs |
| NVMe visibility | IO Insight (SCSI and NVMe), VM Insight | SAN Analytics (VM-initiator-target-namespace) |
| Congestion handling | Slow Drain Device Quarantine, FPIN, congestion signaling | Dynamic Ingress Rate Limiting, virtual output queues |
| Availability | Non-disruptive daemon restart | Non-disruptive software upgrades |

- **NVMe/FC**:
  - Defined by INCITS as FC-NVMe (INCITS 540-2018) and FC-NVMe-2 (INCITS 556-2020)
    [5].
  - It runs on the same fabric, zoning, and name server as SCSI FCP.
  - Both vendors' current platforms support it [4], [5].

## Design considerations

- **Dual fabrics**: FC SANs are built as two independent fabrics (A and B), with host
  multipathing across them. NVMe/RoCE SANs copy this design.
- **Zoning is mandatory practice**: the name server only answers within the active zone
  set, so zones are the access control ([Plug-and-play](#plug-and-play)).
- **Credits set the distance**: size buffer-to-buffer credits for the link's round
  trip and frame size ([Flow control](#flow-control) has the arithmetic). Too few
  credits throttle a long link even when bandwidth is available.
- **Slow drain is the main operational risk**: one slow device backs up a whole fabric
  through credit starvation, so enable the vendor's detection
  ([Flow control](#flow-control)).
- **Compare like with like**: vendor comparisons often quote 16G or 32G FC. Compare
  NVMe/RoCE against 64G or 128G FC (see [Speeds](#speeds)).

## Relationship to other techniques

- [roce.md](roce.md): RoCE reaches losslessness differently, with PFC pause and ECN
  instead of credits. The congestion problems (head-of-line blocking, slow drain)
  look similar.

## References

[1] C. DeSanti, "Transmission of IPv6 Packets over Fibre Channel," IETF RFC 3831, July 2004, §2 "Summary of Fibre Channel." [Online]. Available: https://www.rfc-editor.org/rfc/rfc3831

[2] A. J. Casamento (Broadcom) and E. Mazurek (Cisco), "SAN Overview: How Fibre Channel Hosts & Targets Really Communicate," SNIA Networking Storage Forum webcast, 2021-09-23. [Online]. Available: https://www.snia.org/sites/default/files/ESF/How-Fibre-Channel-Hosts-Targets-Communicate-Final.pdf (last confirmed 2026-11-02)

[3] "The Fibre Channel Roadmap," Fibre Channel Industry Association, updated 2023-08-07. [Online]. Available: https://fibrechannel.org/roadmap/ (FC speed roadmap table; last confirmed 2026-11-02)

[4] "Brocade G820 Switch Product Brief," Broadcom, G820-Switch-PB103, 2026-06-12. [Online]. Available: https://docs.broadcom.com/doc/G820-Switch-PB (Highlights, Advanced Security, and Specifications: Performance, Maximum Fabric Latency, Classes of Service, Fabric Services and Features, Long Distance, Security, Management and Monitoring; last confirmed 2026-11-02)

[5] "Cisco MDS 9700 48-Port 64-Gbps Fibre Channel Switching Module Data Sheet," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/products/collateral/storage-networking/mds-9700-series-multilayer-directors/datasheet-c78-2466559.html (Product overview, Main benefits, Table 1 Protocols; last confirmed 2026-11-02)

[6] "Specifications (T11 Committee)," Fibre Channel Industry Association. [Online]. Available: https://fibrechannel.org/specifications-t11-committee/ (last confirmed 2026-11-02)

[7] "Purchase Standards or Download dpANS," INCITS. [Online]. Available: https://www.incits.org/standards-information/purchase-standards-or-download-dpans (last confirmed 2026-11-02)

[8] "FC-NVMe for Containerized Machine Learning Q&A," Fibre Channel Industry Association. [Online]. Available: https://fibrechannel.org/fc-nvme/ ("Fibre Channel is included in the Linux distributions"; last confirmed 2026-11-02)

[9] "Brocade Fabric OS Administration Guide, 9.2.x," Broadcom. [Online]. Available: https://techdocs.broadcom.com/us/en/fibre-channel-networking/fabric-os/fabric-os-administration/9-2-x/v26761894.html (Buffer-to-Buffer Credits and Credit Recovery: "Calculating the Number of Buffers Required Based on Full-Size Frames" and "Allocating Buffer Credits Based on Average-Size Frames"; "Buffer Credits per Switch or Blade Model"; "Fibre Channel Gigabit Values Reference Definition"; last confirmed 2026-11-02)
