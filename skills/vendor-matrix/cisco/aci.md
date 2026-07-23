# Cisco ACI (APIC)

- ACI (Application Centric Infrastructure) is Cisco's SDN/policy-controller
  overlay for Nexus DC fabrics — APIC is the controller, EPGs/contracts are the
  declarative, application-profile-based policy model. See [cisco.md](cisco.md)
  for how this fits against [NX-OS-native EVPN-VXLAN](nxos-vxlan.md), and
  [techniques/evpn.md](../../techniques/evpn.md) /
  [techniques/vxlan.md](../../techniques/vxlan.md) for the underlying
  control/data plane ACI's fabric rides on.

## Release history

| Version | Year | Architecturally significant changes |
|---|---|---|
| 1.x | 2014 | First GA (1.0(1e), Aug 2014) — centralized APIC cluster, EPG/contract policy model, single-pod only [1]. |
| 2.x | 2016–17 | **Multi-Pod**: one APIC cluster spanning multiple pods over a routed inter-pod network (IPN) [2]. |
| 3.x | 2017 | **Multi-Site** — independent APIC fabric domains stitched via MP-BGP EVPN + Multi-Site Orchestrator; 3.1 added **Remote Leaf** [3]. |
| 4.x | 2018–19 | **Cloud APIC** / "ACI Anywhere" — hybrid extension to AWS (4.1), then Azure (4.2); 4.2 became a designated long-lived release [4]. |
| 5.x | 2020–21 | APIC-over-L3 (no L2 adjacency required for spine/APIC), rogue-endpoint detection; 5.2 was the other long-lived release, deepened Nexus Dashboard consolidation (MSO, Nexus Insights, Network Assurance Engine) [5]. |
| 6.x | 2023–2026 | Long-lived-release model retired starting 6.0; 6.1 added standards-based EVPN remote-leaf resiliency (replacing a Cisco-proprietary protocol) and ACI↔non-ACI VXLAN-EVPN interop ("Policy Extension"); **6.2 (latest, 6.2(2), ~Jul 2026)** adds hybrid physical/virtual APIC clusters, a hardened cluster-upgrade workflow, and expanded GPO flexibility [6]. |

Latest release: **APIC 6.2(2)** (~Jul 2026). No newer long-lived-release line
exists — 4.2(x) and 5.2(x) remain the only two in ACI's history [6].

See **[aci-vs-nxos-vxlan.md](aci-vs-nxos-vxlan.md)** for the head-to-head
comparison against NX-OS-native EVPN-VXLAN, including the 2026 Cisco
convergence ("Nexus One") update relevant to new builds.

## Multi-Site: stretched workload with per-site NAT

Instance of the general
[multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md)
scenario: two ACI fabrics (one per DC), a shared/stretched private-IP subnet so
workloads can migrate between sites, but each site owns a **distinct** public
IP range behind its own independent NAT firewall. A workload can end up
physically hosted at a site other than the one whose public IP/firewall a
client used to reach it — and because NAT requires the return packet to hit
the *exact* device holding the translation entry (stricter than plain
stateful-firewall symmetry — a non-SYN, non-matching segment is dropped by the
implicit stateful check), the wrong firewall can't substitute even if it runs
an identical security policy [7].

**Correction: ACI Multi-Site's documented PBR architecture does not have a
fix for this scenario.** An earlier version of this file claimed a
single-Destination-Group pinning pattern (anchor PBR to one named firewall,
configured identically at every leaf regardless of site) solved this —
that claim doesn't hold up against Cisco's own Multi-Site service-node paper
and has been retracted. Here's why, and what the real options are.

**What the paper's PBR mechanism actually guarantees.** Cisco's stated scope
for this entire document is deliberate and narrow:

> "As of Cisco ACI Release 6.0(5), the recommended option for integrating
> L4–L7 services into a Cisco ACI Multi-Site architecture calls for the
> deployment of independent service nodes in each site... The focus in this
> document, therefore, will be exclusively on this deployment model."
>
> "This model mandates that symmetric traffic flows through the service
> nodes be maintained, because **the connection state is not synchronized
> between independent service nodes deployed in different sites**."

Every PBR use case the paper documents (EPG-to-L3Out compute-leaf
enforcement, EPG-to-EPG provider-leaf anchoring, vzAny-to-vzAny/-to-EPG/
-to-L3Out) is engineered around one guarantee: **flow symmetry** — the *same*
firewall handles both directions of a *given* flow, by resolving to **"the
local active firewall node"** relative to wherever the endpoint currently is.
That guarantee is unconditionally correct when the two sites' firewalls are
interchangeable (same policy, no unique state) — but nowhere in the document
is there a mechanism for redirecting to a **specific, named, non-local**
firewall that overrides that local resolution. "Local" is the answer PBR
always computes; there's no override.

**Why that breaks this scenario specifically.** Each site here owns a
*distinct* public IP range with its own **independent, unsynchronized** NAT
firewall — exactly the "connection state is not synchronized" case the paper
flags. If the workload migrates to DC2 mid-session, its return traffic hits
DC2's compute leaf, which — per the paper's own design, correctly and as
intended — redirects to **DC2's own local firewall (FW2)**. FW2 never
created the translation entry; only FW1 (DC1) did. There's no PBR knob in
this architecture to force it to FW1 instead — the "single Destination
Group, same target everywhere" pattern previously claimed here isn't
something this document (or the general EPG-to-L3Out/EPG-to-EPG mechanics
elsewhere in it) actually supports.

**The one model in this same paper that would sidestep the problem** is an
**active/standby firewall pair *stretched* across sites** — one logical
device (not independent per-site instances), so "local" trivially resolves
to the same thing everywhere since there's no second instance to
mis-resolve to. But Cisco explicitly flags this **"Limited support,"** not
the recommended architecture, and adds:

> "Cisco ACI Multi-Pod remains the recommended architectural approach for
> the deployment of active/standby service-node pairs across data
> centers."

i.e. Cisco's own guidance is to use a *different* fabric architecture
(Multi-Pod, not Multi-Site) if a stretched active/standby pair is a hard
requirement — not to force it onto Multi-Site's independent-node model [7].

**Net**: on ACI Multi-Site with independent per-site firewalls (the
documented, recommended design), this scenario has **no confirmed PBR-based
fix**. The viable paths are the ones already covered generically in
[multi-site-workload-mobility.md](../../scenarios/multi-site-workload-mobility.md):
Option 1 (SNAT, sacrificing client-IP visibility), the architectural fix
(don't let NAT'd tiers migrate independently of their public IP), a NAT
platform with cross-site state sync, or — if a stretched active/standby pair
is genuinely required — reconsidering ACI Multi-Pod instead of Multi-Site for
this fabric.

## References

[1] "Cisco APIC Release Notes, Release 1.0(1e)," Cisco, August 2014. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/1-x/release/notes/apic_rn_101.html

[2] "Cisco APIC Layer 3 Configuration Guide — Multi-Pod," Cisco, Release 2.x. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/2-x/L3_config/b_Cisco_APIC_Layer_3_Configuration_Guide/b_Cisco_APIC_Layer_3_Configuration_Guide_chapter_010011.html

[3] "Cisco ACI Multi-Site Architecture White Paper," Cisco, 2017. [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-740861.html

[4] "Cisco Cloud APIC for Azure Installation Guide, Release 4.2(x)," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/cloud-apic/4-x/install/Cisco-Cloud-APIC-Installation-Guide-Azure-42x/Cisco-Cloud-APIC-Installation-Guide-42x_chapter_01.html

[5] "Cisco ACI Long-Lived Release 5.2(x)," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/long-lived-release/aci-long-lived-release-5-2-x.html

[6] "Cisco APIC Release Notes, Release 6.2(2)," Cisco, July 2026. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/release-notes/cisco-apic-release-notes-622.html

[7] "Cisco ACI Multi-Site and Service Node Integration White Paper," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-743107.html