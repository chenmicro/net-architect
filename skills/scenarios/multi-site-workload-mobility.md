# Multi-Site DC with Cross-Site Workload Mobility

The general shape: two (or more) DC sites, each with its own fabric, joined by a
stretched/shared addressing plane so workloads can migrate between sites without
re-IP — but each site keeps its own **distinct, independent identity toward the
outside world** (its own public IP range, its own internet/WAN edge, its own
stateful firewall). That mismatch — shared internally, distinct externally — is
the root of every traffic-symmetry problem in this scenario, not a corner case
of any one vendor's implementation.

## Topology and traffic flow

Vendor-neutral shape of the problem — the concrete enforcement mechanism
(named "redirect mechanism" here) differs per platform and is documented in
the relevant vendor file, not here (see Composes below).

```mermaid
flowchart TB
    Client(["External Client"])

    subgraph SiteA["Site A — distinct public identity A"]
        EdgeA["Stateful edge device A\n(NAT / firewall)\npublic ↔ private translation\n★ holds this flow's session state"]
        FabricA["DC Fabric A"]
    end

    subgraph SiteB["Site B — distinct public identity B (unused in this flow)"]
        FabricB["DC Fabric B"]
        WL["Workload\nshared/stretched private subnet\n(mobile — currently in Site B)"]
        EdgeB["Stateful edge device B\n✗ no session state\nfor this flow"]
    end

    Client -->|"① enters via Site A's\npublic identity"| EdgeA
    EdgeA -->|"② translate/inspect,\ncreate session state"| FabricA
    FabricA -->|"③ workload not local\n→ forward across DCI"| FabricB
    FabricB -->|"④ deliver to workload"| WL
    WL -->|"⑤ response toward client\n(workload just sees\nwhoever it thinks the peer is)"| FabricB
    FabricB -.->|"⑥ return MUST reach\nedge device A specifically\n→ hairpin across DCI"| FabricA
    FabricA -.->|"⑦ deliver to device A,\nnot local device B"| EdgeA
    EdgeA -->|"⑧ reverse translate\n(session state matched)"| Client
```

The two facts this diagram exists to make visible: (1) the workload's location
is decoupled from the public identity used to reach it — that's the whole
point of the stretched/shared addressing plane — and (2) the return leg is
therefore *not* free to take the locally-convenient path through Site B's own
edge device, because that device has no session state for the flow. Steps ⑥–⑦
are where a vendor-specific redirect mechanism has to intervene; without one,
default routing would send the response out Site B's local edge instead and
the flow would fail (silently, for NAT, or via inspection drop, for a plain
stateful firewall).

## Fix options

Two independent ways to guarantee the return leg reaches the correct
stateful/NAT device (steps ⑥–⑦ in the diagram above). They trade off
differently and aren't mutually exclusive with the severity distinction below
— pick based on whether the workload needs to see the true client IP.

### Option 1: SNAT + DNAT ("hairpin NAT") — vendor-agnostic

Add source translation alongside the existing destination translation. Edge
device A rewrites the client's public IP to its own fixed inside address, not
just the public VIP to the workload's private IP. The workload then sees
`src = edge device A's inside IP`, not the client's address — and because that
source is what it replies *to*, the reply's destination is now a fixed,
non-mobile, Site-A-anchored address instead of an arbitrary internet client.
Ordinary destination-based routing gets it back to Site A correctly, from
either site, with no redirect policy involved at all.

- **Security/visibility limitation**: the workload never sees the real client
  IP — only edge device A's address. Anything downstream that depends on true
  client IP (access logs, per-client rate limiting, IP allowlisting, geo-IP,
  abuse detection) breaks unless compensated for. HTTP(S) can partially
  mitigate this with an `X-Forwarded-For`-style header inserted by the edge
  device; most non-HTTP protocols have no equivalent, so this is a real
  functional loss, not just a logging inconvenience.
- Also worth a capacity check at scale: SNAT/PAT shares a small pool of inside
  IPs/ports across every flow, and can hit port exhaustion under high
  concurrent-connection counts — mitigate with multiple SNAT addresses if so.
- Still crosses the DCI hairpin when the workload isn't local to Site A — this
  fixes *correctness* of the return path, not the extra hop's cost.

### Option 2: Pin the redirect mechanism to the specific device (no SNAT) — vendor/solution-specific

Keep only destination translation (true client IP stays visible to the
workload), and instead force the return leg to the correct device with an
explicit, platform-provided redirect mechanism. Because no SNAT is applied,
the reply is still addressed to an arbitrary external client, so generic
routing can't solve this on its own — the mechanism differs per platform, and
this is genuinely unresolved for some of them:

- **Cisco ACI**: **no confirmed fix on Multi-Site's documented, recommended
  architecture.** Cisco's own Multi-Site service-node paper scopes itself
  exclusively to "independent service nodes in each site" with connection
  state that is **not synchronized** across sites, and every PBR mechanism it
  describes (EPG-to-L3Out, EPG-to-EPG, vzAny variants) resolves the redirect
  target to "the local active firewall node" — there's no documented
  mechanism for pinning PBR to a specific, named, non-local firewall instead.
  See [skills/vendor-matrix/cisco/aci.md](../vendor-matrix/cisco/aci.md#multi-site-stretched-workload-with-per-site-nat)
  for the full trace (an earlier version of that file claimed a
  single-Destination-Group pinning fix; it didn't hold up and has been
  retracted). The one architecture in the same paper that would sidestep the
  problem — a stretched active/standby firewall pair, one logical device
  instead of independent per-site ones — is explicitly flagged "Limited
  support," and Cisco's own guidance there is to use **ACI Multi-Pod**
  instead of Multi-Site if that's a hard requirement [1].
- **NX-OS-native EVPN-VXLAN Multi-Site**: **no confirmed fix on independent
  per-site firewalls with per-site NAT.** Cisco's own
  VXLAN Multi-Site + service-node integration whitepaper documents ePBR
  redirection exclusively for **stretched firewall clusters** — the
  single `service-end-point IP` pattern is correct for an active/standby
  stretched pair (one IP shared by both devices, inherited on failover), but
  the whitepaper never documents the same pattern for independent per-site
  firewalls where each site owns its own IP and its own NAT session state.
  Applying that single-IP pattern to independent devices (pin all traffic to
  one site's firewall IP from every leaf/BGW) is a structural inference from
  the documented stretched-A/S case that comes with problems the whitepaper
  doesn't address: no failover if that pinned firewall dies, 100% DCI hairpin
  for the non-local site at all times, and different failure semantics than the
  stretched case (no standby to inherit the IP). See
  [skills/vendor-matrix/cisco/nxos-epbr.md](../vendor-matrix/cisco/nxos-epbr.md#multi-site-stretched-workload-with-per-site-nat)
  for the full trace. The ePBR approach *is* confirmed for stretched
  active/standby and active/active firewall clusters — just not for the
  independent per-site NAT deployment that creates this scenario in the first
  place [2].
- **Other vendors** (Arista, Juniper, Huawei Multi-Site/DCI designs): not yet
  researched in this repo — confirm before recommending rather than assuming
  parity with either Cisco solution.

## Composes

1. [skills/techniques/spine-leaf-clos.md](../techniques/spine-leaf-clos.md) and
   [evpn.md](../techniques/evpn.md) — the stretched fabric itself: DCI between
   sites, Type-5 route summarization vs. stretched L2/L3, and the underlying
   reason a workload's location can be decoupled from its addressing in the
   first place.
2. [skills/techniques/multi-tenancy.md](../techniques/multi-tenancy.md) — the
   VRF/segmentation boundary between the shared-internally addressing plane and
   whatever per-site external identity (VRF, L3Out, internet edge) sits outside
   it.
3. The relevant vendor DC-fabric file, only needed for Option 2 above — see
   Fix options for which platforms currently have this documented (see
   Maintenance in [SKILL.md](../../SKILL.md) for why the concrete mechanism
   lives in the vendor file, not here).

## Cross-cutting judgment

- Two distinct severities of this problem exist, and they need different fixes
  — don't reach for the heavier one by default:
  - **Plain stateful-firewall asymmetry** (independent, non-NAT firewalls per
    site, either one can legitimately inspect a flow) — solvable by keeping
    ingress/egress paths topologically aligned, e.g. granular host-route
    advertisement so traffic naturally enters at the site the workload lives
    on.
  - **NAT specifically** is stricter: the return packet must reach the *exact*
    device that created the translation entry — no independent peer device can
    substitute, even with a shared security policy. This is what makes both
    fix options above necessary in the first place.
- Neither fix option removes the cross-site DCI hairpin when workload and
  owning-DC diverge — both just guarantee correctness of that hairpin. If the
  hairpin cost itself is unacceptable at the traffic volume in question, the
  fix is architectural, not a NAT/redirect-policy tweak: decouple the two
  independence assumptions causing the conflict — e.g. don't let
  internet-facing (NAT'd) tiers migrate independently of their public
  IP/DNS record, or move to a firewall platform with cross-site session-state
  sync so either site's device can legitimately serve the flow.

## Questions to ask early

- Does the workload or its downstream logging/security controls need true
  client-IP visibility? This is the primary decision between the two fix
  options — Option 1 (SNAT) is simpler and vendor-agnostic but sacrifices
  client-IP visibility; Option 2 preserves it but is vendor/solution-specific
  and, for some platforms, not yet a confirmed capability.
- Is the private/internal addressing plane genuinely stretched (same subnet,
  either site), or per-site with routed reachability? The whole problem class
  only exists in the stretched case.
- Is cross-site workload migration a live, frequent behavior (load balancing,
  DRS-style mobility) or a rare DR failover? Frequent migration makes hairpin
  cost and either fix option matter continuously; rare DR failover may
  tolerate a simpler, coarser fix (e.g. full site cutover of both workload and
  public IP together).
- Do the external-facing stateful devices (NAT firewalls, load balancers)
  support cross-site session/state synchronization? If yes, that may remove
  the need for either fix option entirely.
- ACI or NX-OS-native EVPN-VXLAN Multi-Site? Only relevant if Option 2 is
  chosen — Option 1 doesn't depend on this at all.

## References

[1] "Cisco ACI Multi-Site and Service Node Integration White Paper," Cisco. [Online]. Available: https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-743107.html

[2] "Cisco VXLAN Multi-Site and Service Node Integration," Cisco White Paper. [Online]. Available: https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-multi-site-and-service-node-integration.html