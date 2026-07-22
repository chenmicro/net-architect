# ACI vs. NX-OS-native EVPN-VXLAN

Both run on the same Nexus hardware/silicon and the same VXLAN data plane — the
fork is **who owns the control plane and policy model**, not the topology. See
[aci.md](aci.md) and [nxos-vxlan.md](nxos-vxlan.md) for each solution's own
architecture and release history; this file is the head-to-head comparison and
the judgment call between them.

## Comparison

| | **NX-OS EVPN-VXLAN** | **ACI** |
|---|---|---|
| Control plane | Standard BGP EVPN (RFC 7432 / RFC 8365), configured per-device via CLI/NX-API | APIC controller pushes policy fabric-wide; EVPN-like control plane under the hood but abstracted away — you don't touch BGP directly |
| Config model | Imperative — you configure VNIs, VRFs, route-targets per box (or via Ansible/Terraform on top) | Declarative — application profiles, EPGs, contracts; APIC renders them to the fabric |
| Policy/segmentation | VRF-lite + route-target import/export, done manually (see [multi-tenancy.md](../../techniques/multi-tenancy.md)) | Whitelist-model contracts between EPGs, centrally managed; microsegmentation and app-centric policy are native, not bolted on |
| Multi-vendor interop | Standards-based — EVPN/VXLAN interop with Arista, Juniper, etc. since it's RFC 7432/8365 | APIC-managed leaf/spine must be Cisco Nexus (ACI-mode); no multi-vendor fabric |
| Automation surface | NX-API, YANG, or third-party orchestration (Ansible, Terraform providers) — you build the automation layer | Built-in — APIC is the single source of truth with REST/GUI/Terraform provider, no separate orchestration layer needed |
| Troubleshooting | Familiar box-by-box CLI (`show bgp l2vpn evpn`, etc.) — operationally transparent, easy to reason about hop-by-hop | Centralized visibility (APIC health scores, fault correlation) but a steeper learning curve — you're troubleshooting the controller's abstraction, not raw BGP |
| Flexibility | Full flexibility — anything BGP/VXLAN allows, including non-standard topologies | Constrained to APIC's supported topology/policy model — less flexible by design, trading it for consistency |
| Lock-in | Low — config is portable in concept to any EVPN-capable vendor even if syntax differs | High — APIC, EPG/contract model, and Nexus ACI-mode leaf/spine are a package deal |
| Licensing | Per-switch NX-OS licensing (feature-tier based) | ACI licensing adds APIC + fabric-wide feature licensing on top of hardware |
| Best fit | Teams that want standards-based control, multi-vendor optionality, or already have strong network automation practice | Teams wanting centralized policy/app-centric management, multi-tenant DC-as-a-service, or tighter integration with Cisco's broader stack (Nexus Dashboard, hybrid cloud ACI extensions) |

## Judgment call

Pick based on **who's operating it and what "day 2" looks like**, not just
feature checklists:

- If the org already treats network config as code (CI/CD, Ansible/Terraform,
  GitOps) and wants standards-based portability, **NX-OS EVPN-VXLAN** usually
  wins — full control, no controller dependency.
- If the priority is centralized multi-tenant policy, faster time-to-provision
  for app teams, or deep investment in the Cisco ecosystem, **ACI** wins despite
  the lock-in and cost premium.

## 2026 convergence note

Cisco announced **"Nexus One"** in Nov 2025 — a convergence initiative unifying
ACI and NX-OS/VXLAN-EVPN fabric management under a common Nexus Dashboard plane
and open EVPN/VXLAN standards, rather than ACI's controller-specific
abstraction. Not a formal ACI end-of-life, but Cisco's own messaging and
multiple integrator sources (e.g. FirstPassLab, TravTeks) indicate new-build
guidance is leaning toward NX-OS-native VXLAN EVPN going forward — worth
factoring into this decision for 2026+ greenfield builds, and worth
re-verifying against Cisco's current messaging since this initiative is recent
and still evolving.
[ref](https://blogs.cisco.com/datacenter/unifying-the-data-center-with-cisco-nexus-one-the-network-that-works-for-you)

### Why Cisco is making this shift

Four reasons recur across Cisco's own framing and independent commentary:

- **Open standards became the market default, not the differentiator.**
  VXLAN/EVPN (RFC 7432/8365) is now the industry-wide DC fabric standard —
  Arista, Juniper, and others all interop on it. ACI's proprietary,
  controller-only abstraction went from "advanced" to "isolated" as the rest of
  the market converged on an open baseline.
  [ref](https://blogs.cisco.com/datacenter/cisco-nexus-one-fabric-unify-data-center-operations-with-open-vxlan-evpn-standards)
- **Operational skill transfer.** NX-OS EVPN-VXLAN troubleshooting (BGP route
  types, VTEP reachability, ARP suppression) maps to transferable networking
  knowledge; ACI's EPG/contract abstraction requires a Cisco-specific mental
  model that doesn't carry to any other vendor or even to non-ACI Cisco gear.
  [ref](https://firstpasslab.com/blog/2026-03-06-cisco-aci-sunset-nxos-vxlan-evpn-future-ccie-dc/)
- **Unifying the management layer instead of the fabric OS.** Cisco is
  converging both onto **Nexus Dashboard** as the single automation/telemetry
  plane — decoupling "give customers a controller-managed experience" from "run
  a Cisco-only proprietary fabric OS." That undercuts ACI's core reason to
  exist, since centralized policy can now sit on top of standards-based NX-OS.
  [ref](https://www.travteks.com/blog/nd-moving-from-aci/)
- **Cost of maintaining two divergent stacks.** ACI runs different switch-side
  software from mainline NX-OS; converging reduces Cisco's own engineering
  overhead, not just customer-facing complexity.

## Proprietary tech inside NX-OS EVPN-VXLAN

The *core* control/data plane (BGP EVPN + VXLAN) is genuinely open and
interoperable, but "NX-OS is standards-based" is a claim about that baseline
only — several load-bearing features around it are still Cisco-specific, same
pattern as ACI just less totalizing:

| Feature | Status |
|---|---|
| **vPC** (device-level VTEP redundancy) | Cisco-proprietary — this is exactly what EVPN ESI Multi-Homing ([nxos-vxlan.md](nxos-vxlan.md), 10.6, RFC 8365) was introduced to *replace*, confirming vPC itself was never a standard. [ref](https://firstpasslab.com/blog/2026-01-18-vxlan-evpn-multi-homing-esi-nexus/) |
| **CloudSec** (Multi-Site DCI encryption) | Cisco-proprietary protocol — uses MACsec's cryptographic primitives, but the key-exchange mechanism (a Cisco-defined BGP tunnel-encap attribute) and BGW-to-BGW session model are Cisco's own design, not an IETF standard. [ref](https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-106x/m-configuring-cloudsec.html) |
| **GPO** (Group Policy Option — ACI-style tag-based segmentation for NX-OS) | Based on `draft-smith-vxlan-group-policy`, a Cisco-authored IETF draft with **Informational** intended status that **expired in 2019** without progressing to an RFC — a quasi-standard that never reached multi-vendor ratification, functionally Cisco's way of bringing ACI's segmentation model into the "open" stack without it actually being an open standard. [ref](https://datatracker.ietf.org/doc/html/draft-smith-vxlan-group-policy) |
| OTV, FabricPath, FEX (legacy DCI/fabric tech, still present in the NX-OS portfolio) | Cisco-proprietary, predate EVPN-VXLAN |

Net: NX-OS EVPN-VXLAN has a **broader open baseline** than ACI (which is
proprietary top-to-bottom — EPG/contract model, APIC, everything), but it is
not proprietary-free. The multi-vendor interop claim in the comparison table
above holds for the RFC-baseline feature set; several of Cisco's more advanced
capabilities (legacy multihoming, DCI encryption, microsegmentation) are still
Cisco-only implementations layered on top.
