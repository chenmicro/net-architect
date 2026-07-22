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
  interoperable wire protocol.
  [ref](https://datatracker.ietf.org/doc/html/rfc1104)
  In practice every vendor's PBR is its own non-interoperable implementation
  (Cisco route-maps, Linux policy routing tables, etc.), and ePBR's
  redirection, health-tracking, and VXLAN/GPO-aware service-chaining layer on
  top of that baseline is entirely Cisco's own design — same pattern as vPC,
  CloudSec, and GPO in [aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md#proprietary-tech-inside-nx-os-evpn-vxlan).
  There is no vendor-neutral technique file for PBR/service-chaining in this
  repo yet — add one under `skills/techniques/` if a second vendor's
  implementation needs documenting here.

## Release history

| Version | What changed |
|---|---|
| 9.3(5) | First introduced, single-site only. [ref](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/93x/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-93x/m-configuring-epbr.html) |
| 10.1(1) | Platform/protocol coverage broadened — IPv4, IPv6, VXLAN, GX/FX3 hardware — still single-site. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/101x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-101x/m-configuring-epbr.html) |
| 10.2(1) | **Multi-Site support** — service chaining/load-balancing across VXLAN EVPN Multi-Site fabrics. This is the release the Multi-Site NAT case study below depends on. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/102x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide-102x/m-configuring-epbr.html) |
| 10.5(2)F | **GPO-based multi-site service chains** — sources/destinations distributable across sites, multi-node chains across VRF contexts. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/105x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide/chapter.html) |

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
endpoints and whichever node actually terminates the external connection.
[ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-multi-site-and-service-node-integration.html)

**The mechanism: ePBR, configured as one service across both sites, not
per-site independent services.** NX-OS has no feature literally named after
ACI's "single destination group" — the equivalent is achieved by *how* ePBR is
configured, not by a distinct anchoring feature:

- Define **one** `epbr service` object with a **single service-end-point IP**
  (the firewall's one-arm Service Network address in Cisco's worked example —
  a two-arm/inside-outside deployment is mentioned as supported but not
  detailed) and apply the *identical* configuration on every service leaf,
  border gateway (BGW), compute leaf, and border leaf across **both** sites —
  not a separate local service object per site. With only one candidate IP
  defined anywhere in the multi-site domain, there is no local alternative for
  a leaf at the other site to redirect to.
  [ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-multi-site-and-service-node-integration.html)
- Cisco's own worked example for this ("ePBR and Active/Standby Firewall
  Cluster Stretched across Sites") uses the dedicated Service VRF + `set-vrf`
  described above to steer both the forward and return leg of an inter-site
  flow to the one active firewall without creating a BGW routing loop.
  [ref](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-multi-site-and-service-node-integration.html)
- Since 10.5(2)F, ePBR also supports GPO-based multi-site service chains
  (`epbr failover-group` for cross-site health-tracked backup), but the
  documented default pattern there is proximity-first — each site gets its own
  local primary chain, failing over cross-site only on a health probe failure.
  That default is the *wrong* pattern for this scenario (it's exactly the
  "local firewall" assumption that breaks under NAT); the single-service-object
  pattern above must be used deliberately instead.
  [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/105x/configuration/epbr/cisco-nexus-9000-series-nx-os-epbr-configuration-guide/chapter.html)

**Caveat:** Cisco's worked example uses a plain "permit any" ASA with no NAT
configuration shown — it demonstrates session-affine redirection to a
stateful service node in general, not a NAT-specific deployment. No Cisco
source uses terms like "sticky" or "session affinity" for this, and there's no
worked packet-walk confirming behavior under the *shared-private-subnet-
across-sites* framing specifically (the whitepaper's own framing is
active/standby firewall clustering, not workload mobility) — the mapping from
"single service-end-point" to "NAT-session affinity" is a structural inference
from the confirmed redirection mechanism, not a verbatim Cisco claim for this
exact scenario. Treat as a strong likely-fix, not a confirmed-identical
parallel to ACI's provider-leaf anchoring.
