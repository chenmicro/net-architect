# Huawei Xinghe Intelligent Lossless Storage Network (NoF+)

- NoF+ is Huawei's centralized-storage network solution: NVMe over RoCEv2 between hosts
  and OceanStor Dorado arrays on CloudEngine switches, positioned to replace FC SAN,
  FCoE SAN, and traditional IP SAN such as iSCSI [4, Scenario Description].
- On top of standard NVMe/RoCE ([techniques/nvme-of.md](../../techniques/nvme-of.md)) it
  adds three things: the **iNOF control plane** (discovery, zoning, fault notification),
  **long-distance lossless** for cross-DC links, and a **FabricInsight O&M** view of the
  storage I/O [1, Overview of iNOF], [1, Understanding Antilocking PFC],
  [6, NoF Network O&M Overview]. The DC lossless set it runs on — AI ECN, PFC deadlock
  prevention, rPFC, DPFR — is CloudEngine platform machinery, documented in
  [cloudengine.md](cloudengine.md#lossless-and-dcb-feature-set).
- **The tie to Huawei is iNOF.** It is not a standard, and its plug-and-play and
  fault-driven switchover need array-side support: Dorado V6 (5300 excepted) and MacroSAN
  MS5000/MS7000 qualify, NetApp EF is explicitly excluded
  ([Platforms and compatibility](#platforms-and-compatibility))
  [4, Peripheral Product Description]. See [How open is NoF+?](#how-open-is-nof).
- **Switch scope**: box models CE6885-SAN-56F, CE8855H-SAN-40F, and CE8865-SAN-4C; chassis
  CE16800-X. Older SAN boxes and other CloudEngine models are out of scope — where a
  source states a figure only for them, this file says so. Port, card, and compatibility
  detail is in [Platforms and compatibility](#platforms-and-compatibility).
- **Versions**: CloudEngine runs V300R026C00 [1], [5]; the solution documentation read
  here is V100R025C10 [4]. Feature availability has to be checked against both.
- **Sources**: after-sales documentation only, ordered per
  [huawei.md](huawei.md#documentation-sources) — device documentation ([1] for the
  CloudEngine 9800/8800/6800 SAN models, [5] for the CE16800 family), then FabricInsight
  and NCE-Fabric ([6], [7]), then the solution deployment guide [4]. A feature and its O&M
  counterpart are separate claims, so each is cited to the document that owns it.
- Related: [huawei.md](huawei.md) for the product lines, [cloudengine.md](cloudengine.md)
  for the switch platforms.

## Fabric design

- **Planes**: a service (TCP) network and a storage network, the storage side split into
  planes A and B. Storage designs are one-layer, two-layer, or three-layer
  [4, Recommended Networking and Device Models].
- **Roles and models**, as the deployment guide recommends them
  [4, Recommended Networking and Device Models]:

| Topology | Role | In-scope models listed |
|---|---|---|
| Single-layer, 25GE | Leaf | CE6885-SAN-56F; CE8865-SAN-4C with CE88-SAN-D26F-H; CE16800-X with J or J2 25GE cards |
| Two-layer, 25GE access | Leaf and spine | CE6885-SAN-56F; CE8865-SAN-4C with CE88-SAN-D26F-H; CE16800-X with J or J2 cards as spine |
| Two-layer, 100GE access | Leaf | CE8865-SAN-4C with CE88-SAN-D16CQ-H |
| Three-layer, 25GE access | Compute leaf | CE6885-SAN-56F; CE8865-SAN-4C with CE88-SAN-D26F-H |
| Three-layer, 25GE access | Storage leaf and spine | CE16800-X with J cards CEX-L24CQJ and CEX-L36CQJ, or J2 card CEX-L48CQJ2; or CE8865-SAN-4C with CE88-SAN-D26F-H |
| Intra-city, 25GE access | DCI leaf | CE6885-SAN-56F combined with the service leaf; CE8865-SAN-4C; CE16800-X |
| Intra-city, 100GE access | DCI leaf | CE8865-SAN-4C with CE88-SAN-D16CQ-H; CE16800-X |

- **Features each role must run.** "Required" is the guide's own wording ("must be
  deployed", "must be configured"); "not listed" means that page's must-deploy statement
  omits the feature, not that the device cannot do it
  [4, Single-Layer Networking for Centralized Storage], [4, Two-Layer Networking for
  Centralized Storage], [4, Three-Layer Networking for Centralized Storage]:

| Feature | Single-layer leaf | Leaf, two-/three-layer | Spine | Storage leaf | DCI leaf |
|---|---|---|---|---|---|
| AI ECN | required | required | required | required | not listed |
| DCB PFC | required | required | required | required | not listed |
| PFC deadlock detection | required | required | required | required | not listed |
| PFC deadlock prevention | not listed | required | required | required | not listed |
| Anti-locking PFC | — | — | — | — | required, on the long-distance interfaces |
| Long-distance buffer optimisation | — | — | — | — | required |
| MACsec | — | — | — | — | optional |
| iNOF | recommended | recommended | recommended | recommended | required, as the plane's reflector |
| Hard zoning | optional | optional | not listed | not listed | not listed |

  - The single-layer fabric is the one topology where PFC deadlock prevention is absent,
    and the DCI leaf is the only role whose must-deploy list is entirely long-distance
    features — the rest of its lossless configuration comes from being a leaf or a spine
    in the DC.
- **Deployment mode assumed throughout** [4]: each plane deployed independently, leaves
  neither stacked nor M-LAG'd, servers single-homed, host multipathing for server-side
  redundancy and the two planes for the network side.
- **iNOF is recommended, not required** [4]: the topology pages deploy it when Dorado
  storage is used, and the compatibility list also admits the MacroSAN arrays
  ([Platforms and compatibility](#platforms-and-compatibility)). Where it is used, the DCI
  leaves carry it and act as the plane's reflectors ([iNOF](#inof)).
- **Hard zoning is optional** [4]; what it costs is in [Zoning](#zoning).
- **AI ECN needs a newer main processing unit on the chassis**: CEX-MPUD or CEX-MPUE on
  CE16800-X, CE-MPUD-3E or CE-MPUE on the CE16800 [4].
- **Scale** [4]: a fixed 25GE box leaf is rated for at most 6:1 oversubscription in the
  three-layer design (48 × 25GE access against 2 × 100GE uplink), and a server leaf at most
  6:1 in the two-layer DCI baseline. Where two-layer and three-layer both meet the
  requirement, the guide prefers two-layer.

## iNOF

Everything in this section — discovery, zones, zone isolation and filtering, BFD, and RPFR
— is configured under `ai-service` → `inof`, plus interface level for BFD and RPFR
[1, iNOF Configuration], [5, iNOF Configuration].

- **What it is**: Intelligent Lossless NVMe over Fabrics, the control layer that lets the
  switches learn hosts, publish zones, and notify them of faults [1, Overview of iNOF].
- **Roles**: one or two switches are reflectors and every other iNOF switch is a client
  that connects to each reflector. Two reflectors must be clients of each other and must
  list the same clients [1, Understanding iNOF], [5].
- **Where the reflectors go** [4, 25GE Access > Networking Baseline 2]:
  - **Single-layer storage DC**: none inside the DC. The DCI leaves are the plane's
    reflectors — DCI Leaf1/Leaf2 for plane A, Leaf3/Leaf4 for plane B — and the DC
    storage leaves are their clients.
  - **Two- and three-layer DCs**: the spine nodes, two per fabric, are the reflectors and
    clients of each other; every server-facing device, leaves and DCI leaves alike, is a
    client of those two.
- **Availability**: every in-scope model supports iNOF. The chassis gates some iNOF
  functions on card type — see the feature table in
  [Platforms and compatibility](#platforms-and-compatibility). Which standard CloudEngine
  models lack iNOF is in [cloudengine.md](cloudengine.md#model-feature-support).
- **Packaging**: iNOF ships in the AI Fabric feature package, which is part of the basic
  software.
- **IPv4 and IPv6 iNOF keep separate global configurations**, and for each address family
  the data synchronized from the reflector prevails over the local one [5].

### Control channel

- **Who talks to whom**: an iNOF connection exists between *every reflector and every
  client*, and between the reflectors themselves, which back each other up. Clients have no
  connection to each other and only need to be directly connected to hosts
  [1, Understanding iNOF].
- **What it carries**: TCP with the iNOF information in the **Data field**, destination port
  10000–57999, default 19516, the same port on every device
  [1, Understanding iNOF], [1, Configuring the iNOF Reflector and Client]. Four payload
  types:
  - connection establishment, itself "similar to the process of TCP connection
    establishment";
  - zone configuration, sent from the reflector to each client once zoning is complete on
    the reflector;
  - dynamic host information, where a client summarizes LLDP neighbour changes and the
    reflector redistributes them;
  - interface error-down, sent to the whole system when an interface enters error-down on a
    PFC deadlock or at the CRC alarm threshold, so other devices adjust paths.
- **Roles and addressing** [1, Configuring the iNOF Reflector and Client]:
  - `role { reflector | reflect-client }` — the client keyword is `reflect-client`.
  - `service-address { ip-address | ipv6-address } [ port-id port-id ]` sets the device's own
    address in the iNOF system, and must not be the management interface's address.
  - On a reflector, `peer <client-address> reflect-client` names each client; the connection
    then establishes itself.
  - A reflector holds at most **256 IPv4 and 256 IPv6 client addresses**.
  - Once zone or peer configuration exists, the device cannot be changed to the client role.
- **What synchronizes from a reflector** to the clients: the customized zones, the
  default-zone auto-add function, zone isolation, and BFD for iNOF. Any of them configured on
  either reflector takes effect system-wide, which is why the two must match [1].
- **Authentication** [1, Configuring iNOF Authentication]: `authentication-mode hmac-sha256
  password <password>` adds an HMAC-SHA256 digest to the packets; a receiver discards packets
  that fail it, both ends must share the password, and changing it briefly interrupts service
  before the connection is re-established.
- **Counters separate the three packet classes** [1, Verifying the Configuration]:
  `display inof lldp packet statistics` (LLDPDUs from hosts), `display inof notice packet
  statistics` (notifications exchanged with hosts), `display inof synchronization packet
  statistics [peer …]` (switch-to-switch, with timestamps), plus `display inof peer
  connection` and the `inconsistent` variants of `display inof configuration zone|host-group`
  that list configuration present on only one reflector.
- **The host agent is not on this channel.** nvme-snsd's only socket bind is a raw socket for
  LLDP [2]; the TCP channel is switch-to-switch, which is why only reflectors are configured.
- **RPFR's connection state is verifiable** with `display inof rpfr connection information`
  and `display inof rpfr history information`, documented for the CE6860-SAN, CE8850-SAN,
  CE6885-SAN, CE8855H-SAN, and CE8865-SAN only [1, Verifying the Configuration].

### Workflow

1. Install Huawei UltraPath and the NoF Enabler plug-in on the server. NoF Enabler
   implements Storage Network Smart Discovery (SNSD), which must be enabled on both hosts
   and arrays [1, Understanding iNOF], [4]; see
   [Host agent and host software](#host-agent-and-host-software).
2. Configure IP addresses, VLANs, and routes on the switches, enable iNOF, and configure
   zones on the reflectors ([Zoning](#zoning)).
3. iNOF synchronizes the zone configuration across the switches. Only the reflectors need
   the configuration; clients learn it from them [1, Configuring an iNOF Zone].
4. The array reports that it is online or offline to the switches over LLDP.
5. The switches propagate the status and notify the hosts in the zone.
6. When a storage device comes online, the host connects to it automatically.
7. When a storage device goes offline, the host drops the connection and triggers
   multipath failover ([Fault notification and fast recovery](#fault-notification-and-fast-recovery)).

### Zoning

- **Zones live on the reflectors.** A zone can be configured only on the reflector, which
  then sends the member information to every client; with two reflectors their zone
  configurations must be identical or the backup between them fails
  [1, Configuring an iNOF Zone], [5].
- **Two kinds of zone** [1, Creating an iNOF Customized Zone], [5]:
  - **Default zone** — every device has one, it cannot be deleted, and members cannot be
    added by hand. A separate function adds each newly connected SNSD host and is enabled
    by default (`default-zone enable` under `ai-service` → `inof`); turning it off keeps
    unknown hosts out and saves network and storage resources. On a client the local
    setting is ignored and the reflector's synchronized setting applies. A host already
    in a customized zone is not added to the default zone.
  - **Customized zones** (`zone zone-name` under the same view) — a newly connected SNSD
    host whose address is already listed joins automatically. Members are an address, an
    address range, or an **iNOF host group**: `host-group name` plus
    `host ip-address [to ip-address]`. A member or host group can belong to several zones.
- **Isolation: soft versus hard zoning** [1, Configuring iNOF Zone Isolation], [5].
  `hard-zoning enable` under `ai-service` → `inof` turns on iNOF zone isolation — the
  hard zoning this file refers to — and it is **off by default**.
  - **Without it** membership is only a classification: no communication is restricted.
  - **With it** hosts in different zones cannot communicate at all, and a default-zone
    host cannot reach a customized-zone host.
  - **Inside a zone the rules are role-based**: a host is classified from LLDP information
    as *initiator* (opens NVMe sessions), *target* (serves them), both, or unknown. Two
    hosts cannot communicate only when both are initiators or both are targets; every
    other pairing can.
  - A host can be in several zones, and two hosts communicate when their zones overlap
    and they are not both initiators or both targets. An *invalid* or unknown role
    communicates with every role, so a host that fails LLDP classification is not
    restricted.
  - Isolation exists only on the reflector, and with several reflectors it must be
    enabled on all of them.
  - **It consumes ACL resources**, so zone granularity is a capacity input, not a tidiness
    choice: the guide, having called the function optional, immediately advises "one host
    and one storage device for each zone" to conserve them
    [4, Recommended Networking and Device Models]. On a fabric that also carries service
    traffic, those ACLs compete with the service-side policies.
- **Zone information filtering** (optional) [1, iNOF Zone Information Filtering], [5]: by
  default a reflector synchronizes every zone to its clients. A `synchronization policy` —
  at most four per device, each holding up to 4000 zones — is applied per client as a
  whitelist or blacklist, so a client sees only the zones it needs.

- **Controller automation** [7, Configuring Zones]: iMaster NCE-Fabric delivers zone
  configurations in batches from **Resource Pool > Zone**. Create a zone against a
  fabric, refresh to pick up that fabric's iNOF reflectors, synchronize the devices'
  default zone into the controller, then import zones from the downloadable template or
  create them by hand with a name and host list.
  - A fabric with one device makes that device the reflector automatically; with several,
    you designate one or two.
  - The fabric must contain **only** iNOF devices, or the fabric association fails when
    the zone is created.
  - **Model gap**: [7] asks for V300R022C00 or later and lists CE6860-SAN, CE8850-SAN,
    and the CE16800 with SAN cards; the three in-scope SAN boxes are outside that list, so
    configure zones on the reflector as above and confirm with Huawei before designing the
    controller into the build.
  - Separate from zoning, an iNOF runbook package
    (`iMasterNCE-Fabric_{version}_Runbook_nof.zip`) provisions access-side iNOF
    configuration through preset workflows, and publishing a workflow generates an API for
    a third-party platform to call.

### Fault notification and fast recovery

| Fault | Mechanism | Documented timing |
|---|---|---|
| Host access link | Both the switch and the host detect it, so the host switches path on its own [4, Scenario Description] | — |
| Storage access link | The host cannot see this fault; the switch detects it and iNOF notifies every host in the zone, which then switches path [4, Scenario Description] | — |
| Link between the two access switches | BFD for iNOF, then an iNOF notification to the zone [1, Understanding BFD for iNOF] | BFD defaults are 1000 ms send, 1000 ms receive, and multiplier 3, so about 3 s detection before the notification [4, Scenario Description] |
| Spine-leaf ECMP link | DPFR — a platform feature, see [cloudengine.md](cloudengine.md#dpcf-and-dpfr) [1] | sub-millisecond [1, Understanding Data Plane Fault Awareness] |
| Host on OS-native multipathing | RPFR on the access switch of the storage node [1, (Optional) Configuring RPFR] | VMware only: 40–60 s before 7.0 Update 2, under 15 s on 7.0 Update 2a [4, Peripheral Product Description] |

- **What the switch treats as a fault**: link-down; error-down, which an interface enters
  on a PFC deadlock or when CRC errors reach the alarm threshold [1], [5]; and the LLDP
  age-out, zone-change, and IP-change conditions that show up as disconnect reasons on the
  host side [2]. Whichever fires, iNOF advertises the event to the rest of the system [1].
- **A notification is not a guaranteed failover** [1, Configuration Precautions for iNOF],
  [5]:
  - on a network fault notification the storage system first runs its own I/O keepalive
    check, and if I/O still flows it does not fail over;
  - a `shutdown`-triggered port-down event is reported even while the port is physically
    up, which can again end in no failover [5];
  - if a reflector-to-client connection fails, the switch clears everything learned over
    that connection and notifies the terminals in the zone;
  - with redundant paths in a plane, routing convergence can still drop I/O command
    packets — the host then waits for the I/O to time out and retries.
- **RPFR** (RDMA Proxy for Fast Recovery) is for hosts that run the operating system's own
  multipathing instead of UltraPath. The access switch of the storage node acts as an RDMA
  proxy: it learns the RoCE connection state, detects a fault on its link to the storage
  node, and tells the compute nodes to drop the failed connection and switch to the backup
  link [1, (Optional) Configuring RPFR], [4].
  - Configured with `rpfr enable` under `ai-service` → `inof`, and again on the
    interface [1]. Card and model support is in
    [Platforms and compatibility](#platforms-and-compatibility).
  - **Not guaranteed** [1, Configuration Precautions for iNOF], [5]: the proxy fails in
    about 5% of cases, and is very likely to fail if the Layer 3 logical interfaces of the
    access interfaces fail at the same time.
  - So treat "zero service interruption" as a best case, not a promise.
- **Switch-to-switch link faults are not iNOF's job.** DPFR handles them, and it is a
  CloudEngine platform feature with its own limits, documented in
  [cloudengine.md](cloudengine.md#dpcf-and-dpfr) [1]. In a NoF+ design it has to run on
  every leaf and spine in the plane.
- **DPCF is not part of this design.** It is the companion feature for silent faults, but
  it detects them from TCP retransmission timing and marks the path switch in the TCP
  header's reserved bits, so it covers TCP flows only; RoCEv2 storage I/O is UDP and gains
  nothing from it [1, Understanding Data Plane Fault Awareness > DPCF]. DPFR and iNOF are
  what protect the storage flows; the feature itself is in
  [cloudengine.md](cloudengine.md#dpcf-and-dpfr).

## Host agent and host software

- **Two options on the host**, both listed by the deployment guide
  [4, Peripheral Product Description]: Huawei's UltraPath multipathing plug-in, or the
  open-source SNSD daemon. The daemon matters because it is the part a customer can
  inspect and rebuild.
- **What nvme-snsd is**: a Linux daemon under BSD 3-Clause, published in the `linux-nvme`
  GitHub organization and in openEuler [2].
- **Huawei's OceanStor NOF Enabler 1.2.0** package contains two components [3]:

  | Component | RPM | What it is |
  |---|---|---|
  | NOF Director | `nvme-snsd-1.02.010-linux` (x86_64, aarch64) | The nvme-snsd daemon (`/usr/bin/nvme-snsd`, systemd unit `nvme-snsd.service`, sample `snsd.conf`) — the same project as the open-source repository, at version 1.02.010 |
  | NOF INI | `nvme-ini-1.02.010-<OS>` | Replacement Linux NVMe host drivers (`nvme-core`, `nvme-fabrics`, `nvme-rdma`, `nvme-tcp`, `nvme-fc`, `nvme`), GPL-licensed, built against each distribution kernel |

- **NOF INI details** [3]:
  - it takes priority over the in-box drivers through
    `/etc/depmod.d/zz02-nvme-ini-*.conf` overrides;
  - it ships only for CentOS 7.6, CentOS/RHEL 8.0–8.5 (plus a Lustre kernel build),
    AlmaLinux/RHEL 8.6, and Rocky 8.5;
  - it conflicts with NVIDIA's `mlnx-nvme` driver.
- **Installation** [3]: `install.sh -d` installs only the Director and `-i` only INI; the
  Director needs `/etc/nvme/snsd.conf` to exist first.
- **The Director can run alone** [3]: on other distributions you install only it and keep
  the in-box NVMe drivers.
- **Version gap** [3]: the packaged 1.02.010 binary has no ODCC/CMCC strings, so the
  `--standard` option in the open-source repository is newer than this package.
- **How it works**, from its source [2]:
  - **Registration**: the host sends LLDP frames with an extension TLV carrying its IP
    address, protocol, role (host), and NQN — this is how the switch learns which host
    sits on which port.
  - **Notifications**: the switch sends raw Ethernet frames (EtherType 0x88A7) with TLVs
    for source and destination IP, sequence number, state, reason, and the peer's
    protocol, role, and NQN. The host acknowledges each one and can query the switch.
  - **Action on a notification**: the daemon connects or disconnects the NVMe-oF
    controller through the kernel's standard `/dev/nvme-fabrics` interface. Zone change,
    IP change, and LLDP age-out force a disconnect.
  - **Fast fault declaration**: it sets the NVMe keep-alive timeout to 100 ms, so the
    kernel declares the path failed almost immediately and multipathing moves I/O.
  - **Local link down**: the daemon watches the host's own link state and disconnects
    after `restrain-time` (recommended 0 s).
- **Configuration**: `/etc/nvme/snsd.conf` [2].
  - `[SW]` lists the host IPs on a switched network; `[DC]` lists host and array IPs for
    direct connection.
  - `--standard` selects the ODCC (default) or CMCC message format: the ODCC profile of
    ODCC-2020-05016, or China Mobile's profile of it [8]. Which document defines the CMCC
    variant is an inference from the flag, not a statement read here.
- **Limits in the README** [2]:
  - Linux only, not Windows or VMware; RPFR covers VMware hosts instead
    ([Fault notification and fast recovery](#fault-notification-and-fast-recovery)).
  - One IP address per physical port.
  - No IPv6, although the source has IPv6 TLVs: iNOF itself keeps IPv4 and IPv6
    independent [1, Configuration Precautions for iNOF], so the gap is in the agent.
  - Only RoCE is supported today.
  - The README dates from 2021 and does not list the SAN models; the repository was last
    updated in April 2026 (DSCP support).

  switches but are documented as features rather than as part of a topology

## Intra-city (cross-DC) lossless network

Configured, in order of the subsections below, with `abs-pfc`, `qos buffer
headroom-pool` / `dcb pfc buffer` / `long-distance mode`, and MACsec
[4, Intra-city Long-Distance Deployment Solution].

- **Purpose**: two DCs in one city back each other up and both serve traffic, so a device
  or even a whole-DC failure moves services to the other DC — something classic DR could
  not do — while remote backup stays asynchronous [4, Scenario Description].
  - Reading and writing NVMe over RoCE across the city needs an end-to-end lossless RoCE
    network: two DCI leaf nodes per DC, joined by WDM equipment or bare fibre as dual
    planes [4, Scenario Description].
  - Two storage models ride on it: intra-city active-active (synchronous dual-write) and
    synchronous replication [4, Scenario Description]. Remote, non-metro replication runs
    over lossy TCP and is out of scope.
- **DCI leaf coverage** [4, 25GE Access > Networking Baseline 2, 100GE Access > Networking
  Baseline 1]:
  - 25GE access: CE6885-SAN and CE8865-SAN as DCI leaf nodes, for combined and for
    independent deployment, with CE6885-SAN also appearing as a two-layer DCI server leaf.
  - 100GE access: CE8865-SAN as an independent DCI leaf or a two-layer DCI node, and
    CE16800-X with J or J2 cards.
  - **DCI oversubscription must not exceed 10:1** [4, 25GE Access > Networking Baseline 2,
    100GE Access > Networking Baseline 2].
- **Storage-side limits** [4, Scenario Description]: HyperReplication/S needs the sites
  less than 100 km apart, under 3 ms of bidirectional latency, and more bandwidth than the
  peak write I/O rate. A 100 km one-way delay is 0.5 ms, so the 3 ms budget is mostly
  device and WDM latency, not fibre.
- **Two prerequisites beyond the fabric**: anti-locking PFC on the long-distance
  interfaces, and the NoF+ long-distance storage scenario package in the CE software
  [4, Peripheral Product Description]. Sizing follows
  [Buffer, ECN, and shaping](#buffer-ecn-and-shaping).

### Anti-locking PFC

- **Why it exists**: it needs less buffer than traditional PFC for the same bandwidth and
  distance, which is what fits a metro link into the headroom ceiling
  [1, Understanding Antilocking PFC]. The CLI calls it `abs-pfc` [1, Antilocking PFC
  Configuration].
- **Distance rules**: only for DCI links longer than 10 km, never inside a DC, and the DCI
  gateway must be a dedicated switch — otherwise the specifications drop. The
  distance-based headroom check must be enabled and pass
  [5, Configuration Precautions for Antilocking PFC].
- **100 km is the headroom check's ceiling**: `long-distance mode` offers only `level-1`,
  `level-10`, `level-25`, `level-50`, and `level-100`. Traffic shaping is a separate
  mechanism and does not raise it; the resulting gap is in
  [Buffer, ECN, and shaping](#buffer-ecn-and-shaping).
- **How it works** [1, Understanding Antilocking PFC]: it scans the lossless queues and
  sends a PFC frame carrying a timer, pausing the upstream device for a computed period
  `t` in each scan cycle, instead of pausing until the queue drains.
  - Traditional PFC must hold `2 × (B × 2T)`: `B × 2T` of traffic still arrives after the
    pause threshold is crossed, and the resume threshold must sit at least `B × 2T` below
    the pause threshold or the queue runs dry.
  - Anti-locking PFC must hold `B × 2T + threshold`, and the documentation advises a
    threshold of 0 — so about `B × 2T`. With the same buffer and bandwidth that is about
    twice the distance, because `T` is roughly doubled.
  - In bandwidth-delay terms ([techniques/nvme-of.md](../../techniques/nvme-of.md#design-considerations)):
    traditional PFC needs about `2 × B × RTT` of headroom and anti-locking PFC about
    `1 × B × RTT`. It is still PFC, not an FC credit: the buffer can still run out, and
    then the link drops.
- **Configuration**: an `abs-pfc profile` names the lossless priorities and is applied
  with `abs-pfc enable`; at most two profiles and 20 queues per device. The upstream queue
  rate limit must equal the downstream inbound rate limit.
- **Exclusions and hazards**: it is mutually exclusive with flow control on the same
  interface, and cannot run on the same interface as traditional PFC (`dcb pfc`).
  Transient packet loss happens when you configure it under traffic, when the link RTT
  changes, or when the interface bandwidth changes (split, aggregation, optic swap).

### Buffer, ECN, and shaping

This is the arithmetic for a long link, and it spends buffer that the switch splits by
chip, interface, and queue [1, Understanding Buffer Optimization] — three layers to get
right, as [cloudengine.md](cloudengine.md#lossless-and-dcb-feature-set) describes.

The deployment guide's DCI pages are the only Huawei procedure read here that configures
an in-scope model as a DCI node; the 25GE-access pages (CE6885-SAN, CE8865-SAN) and the
100GE-access pages (CE8865-SAN, CE16800-X) use the same recipe
[4, Intra-city Long-Distance Deployment Solution]. It sets:

| Item | Value |
|---|---|
| Bandwidth-delay product | `BDP = interface bandwidth × RTT`, with RTT ≈ 1 ms per 100 km (10 µs/km) |
| Static ECN thresholds on the lossless queue | lower drop threshold = 1 BDP, upper = 2 BDP, maximum drop probability 10% (worked example: 10G at 60 km → 750,000 and 1,500,000 bytes) |
| Chip-level headroom pool | `qos buffer headroom-pool size <n> mbytes slot <n>`, sized from distance × port count × bandwidth: 4 MB for ≤ 100 km × 1 × 100GE on the box pages, 2 MB for ≤ 128 km × 1 × 100GE on the CE16800-X pages |
| Per-queue headroom | `dcb pfc buffer <q> hdrm <n>`: 512 kB on 25GE–100GE interfaces, 1024 kB on 200GE/400GE (cable ≤ 500 m) |
| Long-distance mode | `long-distance mode level-100` (the 100 km maximum), then `start long-distance detect` to re-run the check after a link change |
| Link-down reporting | `carrier down-hold-time 200`, which delays the down event by 200 ms |

**Long-distance specification per port group** [4, 25GE Access > Networking Baselines 1
and 2, 100GE Access > Networking Baselines 1 and 2]. The guide publishes a budget rather
than a single speed, and shaping is how a link stays inside it:

| Model | Published long-distance specification |
|---|---|
| CE16800-X, 100GE cards CEX-L24CQJ, CEX-L36CQJ, CEX-L48CQJ2 | ≤ 64 km × 2 × 100 Gbit/s, ≤ 128 km × 1 × 100 Gbit/s, or ≤ 200 km × 1 × 64 Gbit/s, shaping the 100GE ports |
| CE16800-X with CEX-L72YS6CQJ2 | the same, or the stricter ≤ 40 km × 2 × 100 Gbit/s / ≤ 80 km × 1 × 100 Gbit/s, which leaves the whole 72 × 25GE + 4 × 100GE group for intra-DC traffic |
| CE6885-SAN-56F, CE8865-SAN-4C | Specification 1: ≤ 50 km × 2 × 100 Gbit/s, ≤ 100 km × 1 × 100 Gbit/s, or ≤ 200 km × 1 × 50 Gbit/s (100GE shaped to 50GE). Specification 2: ≤ 75 km × 2 × 100 Gbit/s, ≤ 150 km × 1 × 100 Gbit/s, or ≤ 200 km × 1 × 75 Gbit/s (100GE shaped to 75GE) |

- Read each line as one fixed budget of distance × bandwidth per port group — 128 km ×
  100 Gbit/s for CE16800-X, 100 or 150 km × 100 Gbit/s for the two boxes — spent either on
  two ports at half the distance or on one port shaped below 100 Gbit/s at the full
  distance. That is where the 64, 75, and 50 Gbit/s figures come from.
- Every port in the group that does not carry the long link stays available for intra-DC
  traffic, and the intra-DC interconnection distance on those ports is capped at 500 m [4].
- **The ECN thresholds are the 2 × BDP rule made concrete**: the queue may fill to two
  round trips' worth of data before marking, which is the traditional-PFC sizing derived in
  [techniques/nvme-of.md](../../techniques/nvme-of.md#design-considerations).
- **The headroom pool is smaller than the BDP.** At 100 km and 100GE the BDP is about
  12.5 MB, while the guide sizes the chip-level headroom pool at 4 MB on the box pages and
  2 MB on the CE16800-X pages, so the pool is not the whole in-flight budget — the queue's
  shared buffer, sized by the 2 × BDP ECN thresholds, holds the rest. The published sizes
  also differ per model for the same 1 × 100GE budget: the boxes scale 4 MB (≤ 100 km) down
  to 2 MB (100–150 km), the chassis gives 3 MB at ≤ 80 km and 2 MB at ≤ 128 km. Treat them
  as starting points and raise the pool if packets drop [4].
- **Two published distance limits to reconcile.** `long-distance mode` tops out at
  `level-100`, while the per-model specifications above run to 200 km with shaping. How a
  150–200 km link satisfies the headroom check is worth confirming with Huawei before
  quoting one for these models.

### Encryption

- **MACsec is optional** on the long-distance link [1, Configuration Precautions for
  MACsec], with cipher suites GCM-AES-128/256, GCM-AES-XPN-128/256, and SM4
  (`gcm-sm4-128`, `gcm-sm4-xpn-128`) [1, macsec cipher-suite].
- **Only some ports qualify**: for example slots 1 and 3 of the CE8865-SAN-4C. On the
  long-distance side, the guide's MACsec-capable interfaces are 100GE1/1/1–2 and
  100GE1/3/1–2 on CE88-SAN-D26F-H, and 100GE1/1/1–6, 100GE1/1/13–16, 100GE1/3/1–6, and
  100GE1/3/13–16 on CE88-SAN-D16CQ-H [4, Intra-city Long-Distance Deployment Solution].

## Operations and monitoring

Switch side, this is System Monitoring → service telemetry; everything else here runs in
FabricInsight [1, Configuration Precautions for Service Telemetry], [6, NoF Network O&M
Overview].

- **FabricInsight measures the storage I/O**: I/O throughput and latency on the
  storage-side and compute-side access devices, visualized per fabric
  [6, NoF Network O&M Overview].
  - **Two measurement modes**: *port polling*, which measures all traffic on the
    compute-side access ports, and *assured service monitoring*, which measures named host
    and storage IPs on both access devices and is the more accurate of the two.
  - **Latency is split by segment** (network, storage, compute) in assured service
    monitoring, which is what lets the operator decide whether the slowdown is theirs
    [6, I/O Visualization].
  - **Delivery**: FabricInsight pushes the task to the CE switches over NETCONF, or the
    task is configured by hand; the switches return the I/O data as telemetry over UDP.
  - **Availability** [6]: needs the network health value-added package, is not available in
    the lightweight deployment of the FabricInsight advanced solution, and needs I/O
    quality visualization configured on both access devices.
- **rPFC excludes the telemetry view.** rPFC keeps PFC at the network edge by having the
  destination switch tell the source switch to throttle, but it is mutually exclusive with
  the service telemetry resource mode — and on the SAN models I/O quality visualization
  runs only in that mode, so the two cannot be enabled together [1]. Choose one per fabric.
- **Device constraints on the SAN models** [1, Configuration Precautions for Service
  Telemetry], [5]:
  - IPv4 only, and I/O quality visualization needs NTP or a high-precision soft clock;
  - on CE6885-SAN, CE8865-SAN, and the CE16800, chip limits mean it does not measure every
    I/O and some latency segments are not measured;
  - mutually exclusive with Eth-Trunk DLB, NPCC, and ECMP dynamic load balancing;
  - throughput visualization ignores RDMA transfers smaller than 1 MiB.
- **VM-level I/O view** [6, I/O Visualization]: per VM it lists the VM name, HCS IP
  address, host ID, and read and write throughput, and expands to the IP address of the
  compute device that VM reaches storage through. I/O details can also be viewed by host
  IP, storage IP, or VM name, which is what makes a VM → host → storage path traceable.
  - The per-VM rows carry an **HCS IP**, so the view presumes an HCS-managed virtual
    estate; the device side is the service telemetry capability above.
  - A three-analyzer cluster supports 3 availability zones, each with 8 arrays and 150
    hosts.
- **Zone consistency check** [6, Zone Consistency Comparison]: import zones from
  FabricInsight's template at a chosen time, then compare — same plane, the imported
  configuration against the reflector's current one; planes A and B, the two planes'
  reflectors against each other. Both show IPs added to or removed from each zone, so zone
  drift that breaks host-to-storage access surfaces. It arrived in FabricInsight
  V100R025C00 [6, What's New], so an O&M design that depends on it pins that release.
- **Packet-loss localization**:
  - **IPAS** reports loss per switch for all RoCE packets — coarse, with no 5-tuple. On the
    device it selects flows with ACL rules or VXLAN reserved fields, and computes loss per
    device as packets in minus packets out for each statistics interval [1, IPAS].
  - **Drop records** in FabricInsight list drops as events by device, 5-tuple, and event
    type, with a per-interface view and filters by session IP, port, protocol, loss cause,
    and lost-packet threshold [6, Drop Records]. Their parameters are delivered from
    FabricInsight to iMaster NCE-Fabric rather than straight to the switches
    [6, Drop Records], so this view assumes the controller is in the design
    ([cloudfabric.md](cloudfabric.md)).
- **RoCE metrics and the AI ECN comparison** [6, RoCE Gain Comparison]: per queue —
  lossless-queue throughput, packets discarded in the lossless queue, PFC frames sent and
  received, ports sending or receiving PFC frames, PFC deadlock and recovery counts,
  ECN-marked packets on the port, and read and write IOPS. Because the device records when
  AI ECN was enabled, FabricInsight can compare the 12 hours before that point with the 12
  hours after it.

## Platforms and compatibility

- **SAN switches**, from the device documentation's hardware description [1]. None of them
  support stacking.

  | Model | Default ports | Higher rates |
  |---|---|---|
  | CE6885-SAN-56F | 48 × 25GE SFP28/SFP56 + 8 × 100GE QSFP28/QSFP56 | 25GE → 50GE in groups of 8 ports; 100GE → 200GE in pairs |
  | CE8855H-SAN-40F | 32 × 100GE QSFP28 + 8 × 400GE QSFP-DD | 100GE ports 17–32 → 200GE in pairs; 400GE splits to 2 × 200GE or 4 × 100GE |
  | CE8865-SAN-4C, CE88-SAN-D26F-H card | 24 × 25GE + 2 × 100GE | 25GE → 50GE in groups of 8; 100GE → 200GE in pairs |
  | CE8865-SAN-4C, CE88-SAN-D16CQ-H card | 16 × 100GE | Ports 5–8 → 200GE in pairs |
  | CE8865-SAN-4C, CE88-SAN-D12F-H card | 8 × 25GE + 4 × 400GE | 25GE → 50GE by command (ports 1–8 together) |

  - The CE8865-SAN-4C has four subcard slots, and port speeds above the default are
    optional upgrades.
- **CE16800 family** [5]: chassis CE16800-X4, -X8, and -X16, with J2 series line cards
  CEX-L40DQJ2 (40 × 400GE), CEX-L48CQJ2 (48 × 100GE), CEX-L72YS6CQJ2 (72 × 25GE + 6 ×
  100GE), and CEX-L36DQ2CQJ2 (36 × 400GE + 2 × 100GE).
- **Which model can run which feature** — this is the one place that answers it:

  | Feature | SAN boxes | CE16800-X |
  |---|---|---|
  | iNOF | all three [1, Configuration Precautions for iNOF] | X4/X8/X16 [5, Configuration Precautions for iNOF] |
  | RPFR | SAN models only [1, (Optional) Configuring RPFR] | SAN, J, or J2 cards [5, (Optional) Configuring RPFR] |
  | iNOF host groups | all three [1, Creating an iNOF Customized Zone] | J or J2 cards [5] |
  | Zone information filtering | all three [1, iNOF Zone Information Filtering] | J or J2 cards [5] |
  | Zone isolation | all three [1, Configuring iNOF Zone Isolation] | SAN, J, or J2 cards; takes effect before NPCC where they overlap [5] |
  | Anti-locking PFC | documented [1, Antilocking PFC Configuration] | documented [5, Antilocking PFC Configuration] |
  | DPFR | documented [1, Data Plane Fault Awareness] | documented [5, Data Plane Fault Awareness] |
  | Service telemetry | documented, with the chip limits in [Operations and monitoring](#operations-and-monitoring) [1, Configuration Precautions for Service Telemetry] | documented on X4/X8/X16 and on the 16804/8/16 with J cards [5, Service Telemetry] |

- **CE8855H-SAN-40F**: a documented SAN model [1] that appears in none of the deployment
  guide's topology or DCI tables, so treat a CE8855H design as one to confirm with Huawei
  rather than one the guide covers.
- **Topologies**: one-layer, two-layer, and three-layer designs, with reflector placement
  and the role-to-model mapping in [Fabric design](#fabric-design).
- **Compatibility**, from the deployment guide's Peripheral Product Description [4]:
  - **Huawei storage**: OceanStor Dorado V6 — 18000 series (18500/18800), 8000 (6800),
    6000 (5600), 5000 (5500). Dorado 18000 V6 supports iNOF but does not do 100 Gbit/s
    RoCE, and **Dorado 3000 V6 (5300) does not support iNOF**.
  - **Dorado version gate**: 6.1.0 associates SNSD with CE iNOF; 6.1.2 adds intra-city
    HyperMetro; 6.1.3 adds HyperReplication; 6.1.5 adds NoF+ IPv6 with CE V300R022C00 and
    later. Both intra-city steps also need the NoF+ long-distance storage scenario package
    on the CE side. 6.1.0 and earlier are single-DC only.
  - **Third-party storage**: MacroSAN MS5000 series (MS5520G2/MS5580G2/MS5500G2-Mach) and
    MS7000 series (MS7000/MS7000G2/MS7000G2-Mach/MS7000G2-HG) at V1.5.12 — listed with **no
    iNOF restriction**, so they can run plug-and-play and fault-driven switchover; NetApp
    EF300/EF600/EF570 at 11.70.1 GA — **iNOF explicitly not supported** on them [4].
  - **Servers and NICs**: x86, or ARM paired with Kylin V10SP1-0518 and CentOS 8.2;
    Mellanox CX4, CX5, or CX6 on RoCEv2, with CX4 not recommended for intra-city and
    ConnectX-3 unsupported.
  - **Host OS, physical**: SUSE 15 SP1, Red Hat 8.0, CentOS 8.0/8.1/8.2. It is a whitelist —
    anything absent (Hyper-V, KVM) is unsupported — and the patch level for a specific
    project has to be cleared by Huawei's storage solution team.
  - **Host OS, VM**: VMware 7.0 Update 2a. Update 2 is the floor — below it an
    ESXi-to-array link loss interrupts VM I/O far longer than on 2a (the figures are in
    [Fault notification and fast recovery](#fault-notification-and-fast-recovery)). **iNOF
    does not work in VMware scenarios**, because VMware has no centralized storage plug-in.
  - **Host software**: UltraPath, DCS SPDK (DCS 8.9.0) or HCS SPDK (HCS 8.3.1), and the
    OceanStor NoF Enabler package, which supplies SNSD
    ([Host agent and host software](#host-agent-and-host-software)).

## Cross-vendor / variants

NoF+ is compared against two things: a standard NVMe/RoCE fabric and an FC SAN. Each
document owns its own facts — this file never restates an FC or transport-agnostic figure —
so a comparison is a projection over three files rather than a table maintained here.

- **Standard NVMe/RoCE**:
  [nvme-of.md](../../techniques/nvme-of.md#cross-vendor--variants) for the transport
  comparison, and [roce.md](../../techniques/roce.md) for PFC, ECN, and deadlock handling.
- **FC**: [fibre-channel.md](../../techniques/fibre-channel.md#cross-vendor--variants) for
  the Brocade/Cisco table,
  [#flow-control](../../techniques/fibre-channel.md#flow-control) for credits and distance,
  and [#speeds](../../techniques/fibre-channel.md#speeds) for port rates.
- **NoF+**: the three feature sets of this file, in order — [Fabric design](#fabric-design)
  for roles and topology; then [iNOF](#inof) with [Workflow](#workflow), [Zoning](#zoning)
  and [Fault notification and fast recovery](#fault-notification-and-fast-recovery);
  [Intra-city](#intra-city-cross-dc-lossless-network) with [Anti-locking PFC](#anti-locking-pfc),
  [Buffer, ECN, and shaping](#buffer-ecn-and-shaping) and [Encryption](#encryption);
  [Operations and monitoring](#operations-and-monitoring); and
  [Platforms and compatibility](#platforms-and-compatibility). The DC lossless set these
  features sit on (AI ECN, PFC deadlock prevention, rPFC, DPFR) is in
  [cloudengine.md](cloudengine.md#lossless-and-dcb-feature-set), not here.

Read the three at the same heading — failover, zoning, distance, visibility, encryption,
port speed — and the difference is the answer. Where a file is silent on a heading, that
silence is the finding.

- **Cost of the NoF+ features**: Huawei CloudEngine SAN switches, plus an array that
  supports iNOF ([Platforms and compatibility](#platforms-and-compatibility)). See
  [How open is NoF+?](#how-open-is-nof).
- **Not NoF+ specific**: NVMe raises queue count and depth from 1/254 to 64K/64K — NVMe
  versus SAS general knowledge, not something NoF+ adds; see
  [techniques/nvme-of.md](../../techniques/nvme-of.md).

### How open is NoF+?

- **Standard NoF has no vendor tie**: see
  [techniques/nvme-of.md](../../techniques/nvme-of.md#how-open-are-fc-and-roce). NoF+ adds
  a tie only through iNOF and RPFR.
- **Who supports iNOF today** — one switch vendor and a short list either side:
  - **Switches**: Huawei SAN models and the CE16800-X, licence-gated
    ([cloudengine.md](cloudengine.md#model-feature-support)).
  - **Arrays**: Dorado V6 (5300 excepted) and MacroSAN MS5000/MS7000; NetApp EF is excluded
    ([Platforms and compatibility](#platforms-and-compatibility)).
  - **Hosts**: nvme-snsd (BSD, Linux on the packaged distributions) or Huawei's UltraPath;
    VMware hosts fall back to switch-side RPFR
    ([Host agent and host software](#host-agent-and-host-software)).
- **What a second vendor would have to implement.** iNOF is three interfaces, and only one
  of them is TCP:
  - **LLDP extension TLV** — the host or array registers its IP address, protocol, role,
    and NQN, which is also how the switch classifies a host as initiator or target
    [1, Understanding iNOF], [2].
  - **TCP control channel, default port 19516, reflector to client** — the protocol payload
    a second implementation has to speak: connection establishment, zone distribution, host
    information, and error-down events ([Control channel](#control-channel))
    [1, Understanding iNOF].
  - **Raw Ethernet notifications, EtherType 0x88A7** — switch-to-host state changes with a
    disconnect reason, which the host acknowledges and can query [2]. This one is not TCP
    and does not cross a router.
  - Plus the semantics that make the packets useful: the zone model (default and
    customized, host groups, isolation, filtering) and the reflector backup rules
    [1], [5].
- **Where the barrier actually is** — technical possibility is not the gate:
  - **Server side: yes, and already open.** The host end is BSD-licensed source, so the
    LLDP TLV and the 0x88A7 frames are documented by implementation; another vendor could
    implement them, and a Windows or VMware port is an engineering task rather than a
    licensing one.
  - **Array side: yes, and already demonstrated.** MacroSAN is on the compatibility list
    with no iNOF restriction, which shows a second array vendor can meet the requirement;
    the deployment guide's condition is that SNSD runs on the arrays as well as the hosts
    [4, Peripheral Product Description].
  - **Switch side: written down, but unproven in the field.** The host-switch protocol is
    specified publicly: ODCC-2020-05016, *NVMe over RoCEv2 Network Control Optimization
    Technical Requirements and Test Specifications* (2020), co-published by CAICT, China
    Telecom, China Mobile, Huawei, and Mellanox, covering device plug-and-play and
    storage-link reliability [8]. Huawei carried the same architecture into the IETF as
    draft-nof-framework-00, which states that it draws on that ODCC specification and
    defines the host, switch, and storage procedures including fast fault-aware switchover
    [9]. Neither is a standard: the IETF drafts expired in September 2022 and were never
    revised.
  - **The real gate is commercial, not technical.** iNOF is licence-gated on the switch, and
    a second implementation would have to match Huawei's zone and reflector semantics, not
    just its wire format: the packets could be reimplemented, the behaviour contract is
    Huawei's.

## Design considerations

- **Ecosystem lock-in**: iNOF runs only on Huawei SAN switches, and plug-and-play needs
  UltraPath or NoF Enabler on the hosts ([How open is NoF+?](#how-open-is-nof)). With an
  array outside the iNOF list, or with hosts on OS-native multipathing and no RPFR, the
  design falls back to standard NVMe/RoCE failover behaviour. The O&M view carries its own
  dependency: the NoF O&M features are FabricInsight with the network health package, not
  the switches alone [6].
- **Fit**: hosts and storage controllers both need RoCE NICs. The deployment guide aims
  RoCE SAN at mission-critical databases, centralized storage and backup, and HA/failover
  environments — the workloads it presents as replacing FC SAN [4, Scenario Description].
- **Sizing an inter-DC link**: work from the published per-model budget
  ([Buffer, ECN, and shaping](#buffer-ecn-and-shaping)) and from the measured RTT rather
  than the straight-line distance, because WDM devices and repeaters push RTT above the
  fibre-only figure [4].
- **Present failover as a mechanism, not a number**: the BFD detection profile and the
  guest-OS switchover time are what the sources quantify
  ([Fault notification and fast recovery](#fault-notification-and-fast-recovery)), and the
  array's own keepalive check and RPFR's failure rate both override a clean handover.
- **Priority on a CE16800 spine**: the chassis maps priority from the DSCP only. Its
  compute-network collaboration function pushes the switch's lossless-service, queue, and
  DSCP mapping to Ascend servers, which then mark packets to match — but that needs Ascend
  servers with the function enabled, so with any other NIC the host must set the DSCP
  itself [5, Compute-Network Collaboration]. It is supported on the X4/X8/X16 and on
  CE16804/8/16 with J cards [5, Configuration Precautions for Compute-Network
  Collaboration].

## Relationship to other techniques

- [techniques/nvme-of.md](../../techniques/nvme-of.md): the transport-agnostic NoF layer
  this solution extends, with the FC-versus-RoCE decision and the buffer/distance analysis
  that the inter-DC sizing here applies.
- [techniques/fibre-channel.md](../../techniques/fibre-channel.md): the FC SAN that NoF+
  replaces — credit-based flow control, zoning and the name server, RSCN, and the two
  switch vendors' features.
- [techniques/roce.md](../../techniques/roce.md): PFC, ECN/DCQCN, and deadlock handling,
  the machinery under the Huawei features described here (AI ECN, PFC deadlock prevention,
  anti-locking PFC).
- [techniques/ai-gpu-fabric.md](../../techniques/ai-gpu-fabric.md): the same lossless
  toolkit aimed at compute traffic; a storage SAN uses dual independent planes rather than
  a rail-optimized topology.
- [cloudengine.md](cloudengine.md): the switch platforms, and which of them carry the SAN
  feature set as opposed to the standard data-centre one.
- [cloudfabric.md](cloudfabric.md) and [huawei.md](huawei.md): the controller that delivers
  zones (NCE-Fabric) and the Huawei documentation sources.

## References

[1] Huawei, *CloudEngine 9800, 8800, and 6800 Series Switches Product Documentation*, V300R026C00, Issue 01, 2026-09-30, HedEx library EDOC1100611778. Sections:
- Get to Know the Product > Hardware Description > Chassis (CE6885-SAN-56F, CE8855H-SAN-40F, CE8865-SAN-4C: ports and port rate notes) and Cards (CE88-SAN-D26F-H, CE88-SAN-D16CQ-H, CE88-SAN-D12F-H).
- Configuration > Configuration Guide > Intelligent Lossless Network Configuration: iNOF Configuration (Overview of iNOF, Understanding iNOF, Configuration Precautions for iNOF, Configuring an iNOF Reflector > Configuring iNOF Authentication, Configuring an iNOF Reflector > Configuring the iNOF Reflector and Client, Configuring an iNOF Zone > Creating an iNOF Customized Zone, Configuring an iNOF Zone > (Optional) Configuring the Function of Automatically Adding Hosts to the iNOF Default Zone, Configuring an iNOF Zone > (Optional) Configuring iNOF Zone Isolation, Configuring an iNOF Zone > (Optional) Configuring the iNOF Zone Information Filtering Function, Configuring BFD for iNOF > Understanding BFD for iNOF, (Optional) Configuring RPFR, Verifying the Configuration); Antilocking PFC Configuration (Understanding, Configuration Precautions, Configuring Antilocking PFC, Configuration Examples); Buffer Optimization Configuration; rPFC Configuration; AI ECN Configuration > Configuration Precautions.
- Configuration > Configuration Guide > High Availability Configuration > Data Plane Fault Awareness Configuration (Understanding > DPFR; Understanding > DPCF; Configuration Precautions).
- Configuration > Configuration Guide > Security Configuration > MACsec Configuration > Configuration Precautions.
- Configuration > Configuration Guide > System Monitoring Configuration: Service Telemetry Configuration > Configuration Precautions; Intelligent Traffic Analysis > IPAS.
- References > Command Reference > Security > MACsec Configuration Commands > macsec cipher-suite.

Last confirmed 2026-11-02.

[2] "nvme-snsd," linux-nvme on GitHub, BSD 3-Clause. [Online]. Available: https://github.com/linux-nvme/nvme-snsd (README: configuration, impact and restrictions, supported switches; source: src/snsd.h, src/snsd_reg.c, src/snsd_server.c, src/snsd_switch.c, src/snsd_conn_nvme.h; latest commit 2026-04-21; last confirmed 2026-11-02). Mirror: https://gitee.com/openeuler/nvme-snsd

[3] Huawei, *OceanStor NOF Enabler 1.2.0* software package (OceanStor_NOF_Enabler_1.2.0.zip), published on the Huawei enterprise support site under product OceanStor NOF Enabler (PID 251608654), software download. Inspected: install.sh; packages/OceanStor NOF Director/nvme-snsd-1.02.010-linux.{x86_64,aarch64}.rpm; packages/OceanStor NOF INI/nvme-ini-1.02.010-*.rpm (module metadata and depmod.d overrides). Last confirmed 2026-11-02.

[4] Huawei, *Xinghe Intelligent Fabric DCN Solution Product Documentation (Intelligent Lossless Scenario)*, V100R025C10, Library Version 01, 2026-03-31, HedEx library EDOC1100559388 (verify at support.huawei.com HedEx, `docid=EDOC1100559388`). Sections:
- Deployment Guide for the Centralized Storage Scenario > Intra-DC Network Deployment Guide: Scenario Description (basic concepts, traffic model, failover paths and the default BFD for iNOF timers); Recommended Networking and Device Models: Single-Layer, Two-Layer, and Three-Layer Networking for Centralized Storage (per-role must-deploy features, recommended and optional models, deployment mode, oversubscription); Peripheral Product Description (storage arrays, third-party arrays, servers, NICs, host OS, host software).
- Deployment Guide for the Centralized Storage Scenario > DCI Deployment Guide (Intra-city Long Distance Transmission): Scenario Description (link types, traffic models); Recommended Networking and Device Models > Intra-city Long-Distance Deployment Solution (25GE Access): Networking Baseline 1 Combined Deployment of DCI Leaf Nodes and Service Leaf Nodes, Baseline 2 Independent Deployment of DCI Leaf Nodes, Baseline 3 Two-Layer DCI Networking, Baseline 4 Combined Deployment of Spine Nodes and DCI Leaf Nodes; and (100GE Access): Networking Baseline 1 Independent Deployment of DCI Leaf Nodes, Baseline 2 Two-Layer DCI Networking — per-model distance × ports × rate budgets, port groups, oversubscription, reflector placement. The baseline numbering is not the same in the two access-speed solutions.
- Deployment Guide for the Centralized Storage Scenario > DCI Deployment Guide (Intra-city Long Distance Transmission) > Switch Configuration: Intra-city Long-Distance Deployment Solution (25GE Access) (IPv4) > Independent Deployment of DCI Nodes: Configuring DCI Leaf Nodes (CE6885-SAN or CE8865-SAN); Intra-city Long-Distance Deployment Solution (100GE Access) (IPv4) > Two-Layer DCI Networking: Configuring DCI Leaf Nodes (CE8865-SAN); Configuring DCI Leaf Nodes (CE16800-X Equipped with J or J2 Series Cards).

Last confirmed 2026-11-02.

[5] Huawei, *CloudEngine 16800 Series Switches Product Documentation*, V300R026C00, Issue 01, 2026-09-30, HedEx library EDOC1100611763 (verify at support.huawei.com HedEx, `docid=EDOC1100611763`). Sections:
- Get to Know the Product > Hardware Description: Chassis (CE16800-X4, CE16800-X8, CE16800-X16); Cards (CEL48CQ-SAN, CEL72XS-SAN, CEX-L40DQJ2, CEX-L48CQJ2, CEX-L72YS6CQJ2, CEX-L36DQ2CQJ2).
- Configuration > Configuration Guide > Intelligent Lossless Network Configuration: iNOF Configuration (Configuration Precautions for iNOF, Configuring an iNOF Zone > Creating an iNOF Customized Zone, Configuring an iNOF Zone > (Optional) Configuring the iNOF Zone Information Filtering Function, Configuring an iNOF Zone > (Optional) Configuring iNOF Zone Isolation, (Optional) Configuring RPFR); Compute-Network Collaboration Configuration (Understanding Compute-Network Collaboration, Configuration Precautions for Compute-Network Collaboration); Antilocking PFC Configuration (Understanding Antilocking PFC, Configuration Precautions for Antilocking PFC); Buffer Optimization Configuration > Configuration Precautions for Buffer Optimization.
- Configuration > Configuration Guide > High Availability Configuration > Data Plane Fault Awareness Configuration (Understanding, Application Scenarios of DPFR and DPCF, Configuration Precautions, Configuring DPCF, (Optional) Configuring Co-Deployment of IFIT and DPCF).
- Configuration > Configuration Guide > System Monitoring Configuration > Service Telemetry Configuration > Configuration Precautions for Service Telemetry.

Last confirmed 2026-11-02.

[6] Huawei, *iMaster NCE-FabricInsight Product Documentation*, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100609401 (verify at support.huawei.com HedEx, `docid=EDOC1100609401`). The V100R025C00 library was also read, for the What's New statements that date the two NoF features. Sections:
- Product Description > Features > Application Assurance > NoF Network O&M: NoF Network O&M; NoF Network O&M > I/O Visualization; NoF Network O&M > Zone Consistency Comparison.
- Product Description > Features > Network Resource > Telemetry: RoCE Gain Comparison; Performance KPI > Metric Details; Drop Records.
- Operation Guide > Application Assurance > NoF Network O&M: NoF Network O&M Overview; Configuring I/O Measurement Tasks for NoF Services.
- Document Package Information: About This Document (deployment solutions and the value-added packages each includes); What's New in both releases (V100R025C00 introduces the zone consistency comparison; V100R026C00 introduces DPCF path-switching telemetry).

Last confirmed 2026-11-02.

[7] Huawei, *iMaster NCE-Fabric Product Documentation*, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100609197 (verify at support.huawei.com HedEx, `docid=EDOC1100609197`; this is the NCE-Fabric library, not *iMaster NCE-Fabric MDC Product Documentation*). The same Configuring Zones page, with the same model list, is also in the V100R025C00 library. Sections:
- Configuration Guide > Commissioning > Resource Pool Management > Configuring Zones (automatic batch delivery of iNOF zone configurations; prerequisites and supported models; Resource Pool > Zone procedure).
- Runbook > Preset Workflows > Preset Workflow Software Package Usage Guide > Preset Workflows > iNOF Workflows (Bringing a Server/Application Online and Offline, in Batches, Migrating a Server, Querying, Deleting VLANs Allowed by an Eth-Trunk Interface).
- Runbook > Preset Workflows > Preset Workflow Software Package Usage Guide > Configuration Delivery Through a Preset Workflow > iNOF Workflow Usage Guide.

Last confirmed 2026-11-02.

[8] Open Data Center Committee (ODCC), *NVMe over RoCEv2 Network Control Optimization Technical Requirements and Test Specifications*, ODCC-2020-05016, 2020, co-published by CAICT, China Telecom, China Mobile, Huawei, and Mellanox. [Online]. Available: https://www.odcc.org.cn/download/p-1331876862386143234.html (Chinese-language consortium specification; covers device plug-and-play and storage-link reliability; cited for the existence and scope of the specification, not read in full here; last confirmed 2026-11-03)

[9] L. Zhao, H. Wang, S. Chen (Huawei), "NVMe over Fabric Network Framework," Internet-Draft draft-nof-framework-00, 7 March 2022, Standards Track, expired 8 September 2022; companion requirements draft: L. Guo (CAICT), Y. Feng (China Mobile), J. Zhao (China Telecom), L. Zhao, H. Wang (Huawei), "NVMe over Fabric Network Requirement," draft-nof-requirement-00, 7 March 2022, Experimental. [Online]. Available: https://www.ietf.org/archive/id/draft-nof-framework-00.txt and https://www.ietf.org/archive/id/draft-nof-requirement-00.txt (both -00 only, no later revision; the framework states it draws on ODCC-2020-05016 and defines host, switch, and storage procedures including fast fault-aware switchover; last confirmed 2026-11-03)

