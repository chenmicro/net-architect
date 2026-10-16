# Silent Host Reachability in Overlay Fabrics

## Background

One subnet inside an EVPN-VXLAN fabric carries a **Linux UDP syslog server** and
the Linux devices that log to it, all in the same subnet. The server takes UDP
continuously and sends nothing back — UDP has no acknowledgement — so it is a
receive-only service except for the occasional TCP session an administrator opens
to inspect logs. Three facts shape the design:

- **Unknown unicast is dropped, not flooded.** Preventing flood is the point, so
  a frame addressed to a MAC the fabric has not learned is discarded rather than
  spread across the subnet.
- **Both ends run Linux.** A Linux ARP entry goes STALE rather than being
  deleted, and the sender keeps using the cached MAC — see
  [arp.md](../techniques/arp.md#linux-arp-cache-retention) and its
  transport-layer treatment of UDP versus TCP.
- **Nothing is misconfigured.** A receive-only service simply never produces the
  frame that every reactive learning scheme depends on.

The question this scenario answers: **how do you hold the server's MAC in the
fabric's forwarding table when nothing the server sends refreshes it, and unknown
unicast may not be flooded to carry a frame addressed to a MAC that has aged out?**

**Scope: L2/bridged reachability** — forwarding for a host whose MAC is unknown
to the fabric, or has aged out of it.

## The challenge

**Requirements.** Syslog delivery must stay continuous, without enabling unknown
unicast flooding, and without changing the server: a Linux receiver has no reason
to emit keepalives, and the occasional admin TCP session is too rare and too
irregular to be the mechanism.

**Nothing teaches the fabric the server's MAC.** EVPN learns endpoints reactively
from data-plane traffic (RFC 7432 Type 2 [3]), so a host that never transmits
cannot be learned, advertised, or re-learned. Whatever forwarding entry the
server has exists only because it once sent something — a boot-time gratuitous
ARP, an admin session, or a reply to an ARP request. Test first whether the
service really is receive-only: a TCP listener self-resolves, because RFC 9293
§3.4 and Figure 5 have each side of a connection send its initial sequence number
and acknowledge the peer's, so its own SYN,ACK teaches the fabric [12]. Here the
service is UDP virtually all of the time.

**A dropped unknown unicast is a silent loss.** The senders' ARP caches still
name the server's MAC, so their datagrams leave addressed to it, and the fabric's
remaining decision is what to do with a MAC it does not know. Where that answer is
"drop", the syslog stream stops with no error surfacing anywhere: UDP has no
retransmission, and a fire-and-forget sender never inspects its send path. RFC
9161 §3.6 is the standard's baseline for the opposite choice — an unresolved
request floods — which is precisely what this design forbids [6].

### ARP / MAC timer mismatch

The two aging timers run on different clocks and, by default, on opposite sides of
the problem; the classic analysis is [1], and Cisco documents the failure in a
campus VLAN network with asymmetric routing and HSRP, without any overlay [11].
IEEE 802.1Q ages a dynamic MAC entry from its creation *or last update*, with a
recommended default of **300 s** [4]. ARP cache timeouts are far longer and are
not standardized — 20 minutes to 4 hours across the platforms tabulated in
[arp.md](../techniques/arp.md#arp-and-mac-timer-reference). The failure sequence
is:

1. A sender (host or router) retains a usable destination IP-to-MAC binding.
2. A switch on the forwarding path ages out that destination MAC because it has
   not observed frames with that source MAC on the relevant VLAN.
3. The sender keeps sending frames to the cached MAC. They are unknown unicast:
   flooded to eligible VLAN ports in an ordinary switched network [4], [11], and
   **dropped in this one**.

In a conventional network the symptom is excess flooding rather than lost
reachability [11]; under this scenario's drop policy the same mismatch becomes a
delivery failure. A timer difference alone does not prove an outage — return
traffic, ARP refresh, and endpoint-maintenance procedures may keep or restore the
forwarding entry [6], [9], [11] — so check actual aging and refresh behavior
before aligning timers. On the Linux side the entry goes STALE, the kernel
transmits on the cached MAC through a 5 s DELAY, then probes that MAC with
**unicast** ARP before falling back to broadcast probes; each unicast probe is
itself addressed to the server's MAC, so the drop policy discards it
[arp.md](../techniques/arp.md#linux-arp-cache-retention).

## The solution

**Option 1 — make the gateway's own ARP aging the refresh clock.** The subnet's
distributed L3 gateway (Huawei VBDIF; SVI or IRB elsewhere) holds a **dynamic**
ARP entry for the syslog server, and Huawei's ARP aging mechanism probes such an
entry when its aging time expires: the device sends an ARP aging probe, a reply
updates the entry, and the absence of a reply deletes it [13]. That probe-and-reply
cycle is precisely the refresh this scenario lacks:

1. The gateway's aging time for the server's entry expires.
2. The gateway sends an ARP aging probe for the server's address.
3. Linux answers it — the target of an ARP request replies with a unicast ARP
   Reply [13] — which a receive-only UDP service cannot avoid.
4. That reply is an ingress frame **from** the server's MAC at its attaching leaf,
   so it creates or refreshes the dynamic FDB entry. IEEE 802.1Q ages an entry
   from its creation *or last update*, recommended default 300 s [4]. The leaf
   also keeps the EVPN Type 2 binding alive, so remote leaves carry the MAC rather
   than flood toward an unknown one.
5. The server's MAC therefore never becomes unknown unicast: the drop policy is
   never exercised, and no flooding is added.

The design rule is a **timing relationship**: set the gateway interface's ARP
aging time comfortably **below** the MAC aging time — for example 150 s against
the 300 s default — so the probe and its reply land inside the forwarding entry's
lifetime. Two details make the margin real rather than cosmetic:

- **The aging probes are unicast by default.** Huawei's mechanism unicasts the
  probes and broadcasts only the last one [13]. A unicast probe is itself
  addressed to the server's MAC, so it needs the FDB entry to still exist;
  probing that begins only after the entry has expired is dropped as unknown
  unicast, and the entry is deleted instead of refreshed.
- **The mismatch is the default, not an edge case.** Most platforms hold ARP far
  longer than MAC aging (4 h on Cisco IOS XE and Arista, 25 min on NX-OS, 20 min
  on Junos, against a 300 s MAC default — see the timer table in
  [arp.md](../techniques/arp.md#arp-and-mac-timer-reference)), so the forwarding
  entry always expires first.

RFC 9135 §7.3 describes age-out ARP probing for a previously learned silent host,
so this is standard-adjacent rather than a vendor trick [5], and Cisco's campus
mitigation — bringing the two aging times closer so ARP traffic refreshes MAC
learning before the entry expires — is the same idea in a switched network [11].

**Prerequisites and traps.**

- **The gateway must already hold a dynamic entry for the server.** Aging probes
  fire for existing entries only; in a same-subnet-only flow nothing routes
  through the gateway, so the entry may never be created. When the administrator
  connects over TCP from another subnet, the gateway routes to the server and
  seeds the entry naturally — but that is a side effect, not a design. Otherwise
  seed it explicitly, or use Option 2.
- **A static ARP entry cannot do this job.** A static entry is neither aged nor
  overwritten [13], so it produces no aging probe and cannot refresh the FDB
  entry. Static state is for a host that cannot answer at all, not for keeping a
  learned entry alive.
- **Verify the platform's aging parameters** — aging time, aging-probe attempts,
  aging-probe mode — against the current release documentation, and confirm the
  VBDIF specifics: the Huawei command reference was still inaccessible at the
  Oct. 16, 2026 check, so command-level applicability stays **unverified** [13].

**Option 2 — proactive discovery from the gateway.** Where the gateway holds no
entry for the server, a per-subnet probe cycle creates one through the same
request → reply → FDB refresh path. Cost scales with subnet size rather than with
the number of silent hosts; the current command's VBDIF applicability is
unverified (see the Huawei bullet under cross-cutting judgment).

**Option 3 — keep ARP/BUM flooding while dropping unknown unicast.** The
constraint forbids flooding unknown *unicast*, not broadcast. If ARP requests
still flood within the BD, a Linux sender whose entry fails eventually re-ARPs
with a broadcast request that reaches the server, and the reply re-teaches the
fabric. Treat this as the recovery path of last resort, not the design: it is the
lossy path the timer mismatch produces, and it holds only while broadcast
flooding is permitted.

**Fallback — pin the binding.** An explicitly provisioned IP-to-MAC binding on the
attaching leaf, for a host that will not answer ARP at all. It supplies neither
the attachment nor EVPN reachability by itself, and it breaks if the server's NIC
changes (see the ARP-deaf bullet below).

## Composition

Read in this order:

1. **[techniques/arp.md](../techniques/arp.md)** — the bridged trigger cases
   and the ACI gleaning requirements (§ARP in fabric / overlay contexts);
   learned-binding refresh and aging (§Endpoint aging and refresh in overlays,
   §ARP and MAC timer reference); legacy VLAN active discovery (§Active
   discovery in legacy VLAN networks); then §Cross-vendor / variants and
   §Design considerations.
2. **[techniques/evpn.md](../techniques/evpn.md)** — §Silent host handling
   (RFC 9161 proxy tables and proxy-miss flooding) and §Cross-vendor / variants.
3. **[techniques/vxlan.md](../techniques/vxlan.md)** — BUM path and
   flood-vs-drop behavior.
4. **Vendor files** — [cisco/aci.md](../vendor-matrix/cisco/aci.md) (§Silent
   host detection: COOP, GIPo/FTAG, hardware proxy),
   [cisco/nxos-vxlan.md](../vendor-matrix/cisco/nxos-vxlan.md) and
   [arista.md](../vendor-matrix/arista.md) (unknown-unicast defaults),
   [cisco/nxos-gpo.md](../vendor-matrix/cisco/nxos-gpo.md) (policy enforcement
   needs a learned IP binding).

## Cross-cutting judgment

- **ACI (Cisco)**: the bridged recovery path turns on one BD setting — a
  received host ARP with ARP Flooding **disabled** can still trigger gleaning
  on a target-IP COOP miss — while that path requires BD unicast routing with
  a deployed subnet. Unknown-MAC data frames are a separate Flood/Hardware-Proxy
  decision, and gleaning discovers into COOP rather than as intra-pod EVPN
  [2], [7], [10].
- **Huawei CloudFabric**: do not conflate ordinary gateway ARP resolution,
  periodic `arp smart-discover`, and tunnel-failure `arp broadcast-detect`.
  The command surface and its verification caveat live in
  [arp.md](../techniques/arp.md#arp-active-detection-huawei-smart-discover);
  the cited reference was inaccessible on the Oct. 16, 2026 recheck, so
  smart-discover's VBDIF availability and current-release defaults are
  **unverified** — do not prescribe a VBDIF command from a VLANIF example.
- **Juniper EVPN-VXLAN**: `static-mac-ip` is a configured per-entry probe list,
  not fabric-wide discovery, and is no evidence that Juniper IRB gateways lack
  ordinary dynamic discovery [8].
- **Standard EVPN (Arista EOS, NX-OS native, others)**: verify the actual
  bridge-only path and platform configuration before adding periodic external
  scans; NX-OS also documents optional MAC-delete-triggered ARP refresh [9].
- **ARP-deaf fallback (all vendors)**: for a live host that cannot answer ARP,
  an explicitly provisioned IP-to-MAC binding and a usable MAC forwarding path
  may be needed — but a static ARP entry supplies neither the attachment nor an
  EVPN route, and static state cannot restore a powered-off host; the
  response-gated Juniper feature is not a universal fallback [8].

## References

[1] "Silent Hosts in EVPN Fabrics," ipSpace.net, Ivan Pepelnjak, May 2023 —
full citation in [arp.md](../techniques/arp.md) [3]; timer analysis above.

[2] "ACI Fabric Endpoint Learning White Paper," Cisco — full citation and
COOP/gleaning mechanics in [arp.md](../techniques/arp.md) [2] and
[aci.md](../vendor-matrix/cisco/aci.md) [9].

[3] A. Sajassi et al., "BGP MPLS-Based Ethernet VPN," IETF RFC 7432 — full
citation and route-type analysis in [evpn.md](../techniques/evpn.md) [1].

[4] "IEEE Standard for Local and Metropolitan Area Networks — Bridges and
Bridged Networks," IEEE Std 802.1Q — aging/refresh rules cited in
[arp.md](../techniques/arp.md) [6].

[5] A. Sajassi et al., "Integrated Routing and Bridging in Ethernet VPN
(EVPN)," IETF RFC 9135, October 2021, §5.3 and §7.3. [Online]. Available:
https://www.rfc-editor.org/rfc/rfc9135.html — full procedure notes in
[evpn.md](../techniques/evpn.md) [6]. Verified Oct. 16, 2026.

[6] J. Rabadan et al., "Operational Aspects of Proxy ARP/ND in Ethernet
Virtual Private Networks," IETF RFC 9161, January 2022, §3.5–3.6. [Online].
Available: https://www.rfc-editor.org/rfc/rfc9161.html — optional refresh
probes without a subnet IP, and proxy-miss flood handling. Verified Oct. 16, 2026.

[7] "Troubleshoot ACI Intra-Fabric Forwarding — MultiPod Forwarding," Cisco,
Doc ID 218013. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/cloud-systems-management/application-policy-infrastructure-controller-apic/218013-troubleshoot-aci-intra-fabric-forwarding.html
— verify "Proxied requests where the EP is not in COOP" and "Other possible
causes." Rechecked Oct. 16, 2026.

[8] "Static Configuration of MAC-IP Bindings," Juniper Networks, Junos OS
EVPN documentation. [Online]. Available:
https://www.juniper.net/documentation/us/en/software/junos/evpn/topics/concept/static-mac-ip.html
— verify response-gated learning/advertisement, sender IP 0, and probe-disable
behavior; check Feature Explorer for platform/release support. Rechecked
Oct. 16, 2026.

[9] "IPv4 Addresses," Cisco Nexus 9000 Series NX-OS Unicast Routing
Configuration Guide, Release 10.6(x). [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/unicast-routing-configuration/cisco-nexus-9000-series-nx-os-unicast-routing-configuration-guide/m-n9k-configuring-ipv4-93x.html
— verify "Configuring periodic ARP refresh on MAC delete for SVIs" and
"Guidelines and Limitations for IPv4." Rechecked Oct. 16, 2026.

[10] S. Garg, "Understand ARP Flooding and ARP Gleaning in ACI," Cisco TAC,
Doc ID 222179, July 23, 2024. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/technical-details/222179-understand-arp-flooding-and-arp-gleaning.html
— verify the separate unknown-MAC, host-ARP, and routed-IP workflows and the
requirements in "Understanding ARP Gleaning." Rechecked Oct. 16, 2026.

[11] "Unicast Flooding in Switched Campus Networks," Cisco Support,
Doc ID 23563, updated Feb. 8, 2016. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/switches/catalyst-6000-series-switches/23563-143.html
— verify "Problem Definition" and "Cause 1: Asymmetric Routing," especially
the campus VLAN/HSRP example and ARP-timeout/MAC-aging mitigation. Rechecked
Oct. 16, 2026. Used to establish the non-overlay mechanism, not current
platform timer defaults.

[12] W. Eddy, Ed., "Transmission Control Protocol (TCP)," IETF RFC 9293,
August 2022, §3.4 and Figure 5. [Online]. Available:
https://www.rfc-editor.org/rfc/rfc9293.txt — Figure 5 (TCP Connection State
Diagram) shows the passive opener in LISTEN responding to a received SYN with
SYN,ACK, and §3.4 requires each side to send its initial sequence number and
to acknowledge the peer's. Verified via doc-fetcher Oct. 16, 2026.

[13] "ARP," Huawei Support Encyclopedia (Info-Finder). [Online]. Available:
https://info.support.huawei.com/info-finder/encyclopedia/en/ARP.html
— verify "ARP Aging Mechanism": dynamic ARP aging parameters are the aging
time, aging-probe attempts, and aging-probe mode; when the aging time expires
the device sends an ARP aging probe, a reply updates the entry, and no reply
deletes it; the probe is unicast by default with only the last probe
broadcast; static ARP entries can be neither aged nor overwritten. Rechecked
Oct. 16, 2026. Generic mechanism description — the CloudEngine command
reference for the concrete VBDIF parameters (EDOC1100439391) was still
blocked by robots policy/HTTP 403, so command-level specifics are unverified.
