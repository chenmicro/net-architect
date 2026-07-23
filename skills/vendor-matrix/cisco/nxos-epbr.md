# Cisco NX-OS ePBR (Enhanced Policy-Based Redirect)

- ePBR is a general Layer 4-7 service-redirection feature for Nexus 9000
  NX-OS — service chaining, load-balancing across service nodes, and health
  tracking of service appliances. It ships with its **own release train and
  its own Configuration Guide** (`.../configuration/epbr/...`), confirmed
  separate from the [VXLAN Configuration Guide](nxos-vxlan.md)
  (`.../configuration/vxlan/...`) on Cisco's own
  [Nexus 9000 guides index](https://www.cisco.com/c/en/us/support/switches/nexus-9000-series-switches/products-installation-and-configuration-guides-list.html)
  — it is not a VXLAN feature, even though VXLAN EVPN Multi-Site is one
  environment it supports. See [nxos-vxlan.md](nxos-vxlan.md) for the
  standalone EVPN-VXLAN fabric this file's Multi-Site case study rides on.
- **Standards status: Cisco-proprietary, not a standard technique.**
  "Policy-based routing" as a general concept traces to a 1989 IETF
  Informational RFC that outlined *models* for it but never became an
  interoperable wire protocol [1].
  In practice every vendor's PBR is its own non-interoperable implementation
  (Cisco route-maps, Linux policy routing tables, etc.), and ePBR's
  redirection, health-tracking, and VXLAN/[GPO](nxos-gpo.md)-aware
  service-chaining layer on top of that baseline is entirely Cisco's own
  design — same pattern as vPC, CloudSec, and GPO in
  [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md#proprietary-tech-inside-nx-os-evpn-vxlan).
  There is no vendor-neutral technique file for PBR/service-chaining in this
  repo yet — add one under `skills/techniques/` if a second vendor's
  implementation needs documenting here.

## Release history

| Version | What changed |
|---|---|
| 9.3(5) | First introduced, single-site only [2]. |
| 10.1(1) | Platform/protocol coverage broadened — IPv4, IPv6, VXLAN, GX/FX3 hardware — still single-site [3]. |
| 10.2(1) | **Multi-Site support** — service chaining/load-balancing across VXLAN EVPN Multi-Site fabrics. This is the release the Multi-Site NAT case study below depends on [4]. |
| 10.5(2)F | **[GPO](nxos-gpo.md)-based multi-site service chains** — sources/destinations distributable across sites, multi-node chains across VRF contexts [5]. |

## Multi-Site: stretched workload with per-site NAT

Instance of the general
[multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md)
scenario — same problem as [ACI's version](aci.md#multi-site-stretched-workload-with-per-site-nat):
two fabrics, one shared/stretched private subnet, each site owns a distinct
public IP range behind its own independent NAT firewall, and a migrated
workload's return traffic must reach the *exact* firewall that holds the NAT
session state, not just any firewall running the same policy.

**Topology note — the firewall sits at the service leaf, not at the fabric's
external boundary.** In Cisco's reference design, the active/standby firewall
pair connects **one-arm** to a dedicated Service Network attached at the
**service leaf** nodes — an internal fabric role, distinct from the BGW/Border
Leaf nodes that actually connect to the "external routed domain." North-South
traffic is explicitly redirected *through* the firewall on its way to/from
that external boundary: ingress leaf (Tenant VRF) → **Service VRF** → service
leaf → firewall → back into Tenant VRF → BGW/Border Leaf → external network,
and the mirrored path inbound. The firewall itself is never the literal
network edge; ePBR is what inserts it into the path between internal
endpoints and whichever node actually terminates the external connection [6].

**What the whitepaper documents vs. what this scenario needs.** Cisco's
VXLAN Multi-Site + service-node integration whitepaper documents ePBR
redirection for two firewall redundancy models, both of which are **stretched
clusters** — the Active/Standing pair (single `service-end-point IP`, the
active node's address inherited by the standby on failover) and the
Active/Active cluster (Split Spanned EtherChannel or Individual Interface
mode). In both cases the firewalls share a common identity — a single IP for
A/S, a shared vMAC/vIP for A/A — that makes a single ePBR service object
trivially correct [6].

The whitepaper's earlier section "Independent Firewall Services Deployed per
Site" notes that "ePBR can provide the easiest answer also to this
requirement" and warns that "it is mandatory to avoid creating asymmetric
traffic paths via the independent firewalls services deployed in separate
sites, which would result in dropping the stateful traffic flows" — but the
subsequent ePBR sections never document a concrete pattern for the
independent-per-site case. No Cisco packet-walk, configuration sample, or
service-end-point pattern exists in the whitepaper for anything other than
stretched clusters.

**The inference and its problems.** The single-service-end-point pattern
could structurally be extended to independent firewalls: define one
`epbr service` with a single IP pinned to Site A's independent firewall and
apply it identically on every leaf/BGW at both sites. With the Service VRF +
`set-vrf` design, all traffic would redirect to that one IP regardless of
source site. But this extension carries problems the whitepaper never
addresses:

- **No failover**: if Site A's independent firewall dies completely, all
  flows die — there's no standby device to inherit the single IP, unlike the
  stretched A/S case where failover is built-in.
- **100% DCI hairpin for the non-local site**: unlike the stretched cluster
  designs (where the same IP is present at both sites), the independent
  model permanently pins all traffic to one site's firewall — Site B's local
  traffic must always cross the DCI, not just migrated workloads.
- **Different failure semantics**: the stretched A/S model guarantees the
  service IP moves with the active unit; the independent model has no such
  guarantee.

The GPO-based multi-site service chains introduced in 10.5(2)F default to
proximity-first (each site gets its own local primary, failing over
cross-site only on health probe failure) — that's the correct pattern for
stretched clusters with local nodes and the wrong one for independent
per-site NAT, but the whitepaper doesn't address how to override it for
the independent case either [5].

**Verdict**: the single-service-end-point ePBR pattern is **not confirmed**
for independent per-site firewalls with per-site NAT — same bottom line as
ACI, arrived at differently: ACI has an explicit architectural contradiction
(PBR always resolves to "local"), while NX-OS has a structural inference from
a documented stretched-cluster pattern to an undocumented independent-fabric
one. The ePBR approach *is* confirmed for stretched active/standby and
active/active firewall clusters — just not for the independent per-site NAT
deployment that creates this scenario.

## References

[1] "Models of Policy Based Routing," IETF RFC 1104, June 1989. [Online]. Available: https://datatracker.ietf.org/doc/html/rfc1104

[2] "Configuring ePBR," Cisco Nexus 9000 Series NX-OS ePBR Configuration Guide, Release 9.3(x). [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/93x/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-93x/m-configuring-epbr.html

[3] "Configuring ePBR," Cisco Nexus 9000 Series NX-OS ePBR Configuration Guide, Release 10.1(x). [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/101x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-101x/m-configuring-epbr.html

[4] "Configuring ePBR," Cisco Nexus 9000 Series NX-OS ePBR Configuration Guide, Release 10.2(x). [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/102x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-102x/m-configuring-epbr.html

[5] "Configuring ePBR," Cisco Nexus 9000 Series NX-OS ePBR Configuration Guide, Release 10.5(x). [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/105x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide/chapter.html

[6] "Cisco VXLAN Multi-Site and Service Node Integration," Cisco White Paper. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-multi-site-and-service-node-integration.html