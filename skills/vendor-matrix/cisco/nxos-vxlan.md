# Cisco NX-OS VXLAN EVPN

- Standalone, box-by-box BGP EVPN control plane over VXLAN on Nexus 9000 —
  standards-based (RFC 7432/8365), the alternative to [ACI](aci.md)'s
  controller-managed model. See [cisco.md](cisco.md) for the fork-in-the-road
  framing against ACI, and [techniques/vxlan.md](../../techniques/vxlan.md) /
  [techniques/evpn.md](../../techniques/evpn.md) for the vendor-neutral
  mechanics this rides on.

## Release history

| Version | Year | Key VXLAN/EVPN architectural changes |
|---|---|---|
| 7.0 | 2015 → 2017 | VXLAN BGP EVPN control plane first introduced on Nexus 9000 (early 2015). [ref](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/vxlan/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_7x_chapter_0100.html) **EVPN Multi-Site** (DCI between fabrics via Anycast/vPC Border Gateways) added later in the same train, 7.0(3)I7(1), 2017. |
| 9.2 | 2018 | Multi-Site + vPC support formalized; VXLAN Cross Connect (point-to-point VTEP tunneling); TRM border-leaf with vPC. [ref](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/92x/vxlan-92x/configuration/guide/b-cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-92x/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide_9x_chapter_0100.html) |
| 9.3 | 2019–21 | **CloudSec** (encrypted Multi-Site DCI), EVPN↔MPLS-SR interop, dual-RD Multi-Site — hardening/scale of the 9.2 architecture, not a new paradigm. [ref](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/93x/vxlan/configuration/guide/b-cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-93x/b-cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-93x_chapter_0101.html) |
| 10.1 | 2021 | VXLAN EVPN loop detection & mitigation, VXLAN tunnel encryption — platform/scale expansion, no major new architecture. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/101x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-101x/m-new-and-changed-information.html) |
| 10.2 | 2021–22 | **EVPN Hybrid IRB Mode** (mixed asymmetric/symmetric IRB) and **EVPN Distributed NAT** — real architectural additions. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/102x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-102x/m-new-and-changed-information.html) |
| 10.3 | 2022–25 | VXLAN BGP-EVPN Null Route, Q-in-VNI with L2PT, PKI support on CloudSec — incremental hardening. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/103x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-103x/m_configuring_vxlan_bgp_evpn.html) |
| 10.4 | 2023–26 | VXLAN EVPN Multi-Site egress traffic engineering/load balancing; **GPO/SGACL microsegmentation** for VXLAN fabrics. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/104x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-104x/m-evpn-distributed-nat-.html) |
| 10.5 | 2024–26 | Downstream-VNI (DSVNI) optimization; **EVPN over RFC 5549** (IPv4 VTEPs via IPv6 BGP sessions); dynamic underlay tunnel load balancing. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/105x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-105x/m_configuring_vxlan_bgp_evpn.html) |
| 10.6 | 2025–26 | **EVPN ESI Multi-Homing** (10.6(1)F) — standards-based BGP-EVPN-native multihoming, explicitly positioned as an alternative to vPC/vPC Fabric Peering; IPv6-underlay support for BGW/Multi-Site; SR-MPLS↔VXLAN handoff. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-106x/m-interoperability-with-mvpn-multi-homing-using-esi.html) |

Latest release: **NX-OS 10.6(3)F** (~Apr 2026). No 10.7 or 11.x train exists yet
as of this writing.
[ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/release-notes/cisco-nexus-9000-nxos-release-notes-1063F.html)

See **[aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md)** for the head-to-head
comparison against ACI, including the 2026 Cisco convergence ("Nexus One")
update relevant to new builds.

For L4-7 service redirection (firewall/LB insertion, and the Multi-Site
stretched-workload/per-site-NAT case study) see **[nxos-epbr.md](nxos-epbr.md)**
— ePBR ships as its own Configuration Guide, confirmed separate from the VXLAN
one this file covers, so it's documented in its own file rather than folded in
here.
[ref](https://www.cisco.com/c/en/us/support/switches/nexus-9000-series-switches/products-installation-and-configuration-guides-list.html)
