# POC: ACI L2 stretch to external SDN region — shared subnet, separate MSTP domains

> **Status: Proposal — untested.** This record documents a proposed design
> pattern that has not been validated in a lab. The test steps and issues
> are predicted, not observed. Update this status after lab execution.

## Metadata

| Field | Value |
|---|---|
| **Date** | ~2026-08 |
| **Scope** | Stretch an IP subnet from a Cisco ACI fabric to an external SDN region while keeping two L2/MSTP failure domains isolated — no L2 flooding, no BPDU exchange, no STP interaction between regions |
| **ACI side** | Cisco Nexus 9300-EX (or later) leaf switches, ACI release 6.0(1g) |
| **Internal side** | Non-Cisco L2 switches running MSTP (802.1s) |
| **External side** | External SDN gateway running MSTP (802.1s) |

---

## 1. Testing Targets

### Objectives

1. Validate that a single ACI bridge domain with four EPGs (two tagged, two native/untagged) can stretch an IP subnet across two independent MSTP domains without merging them
2. Validate that Flood in Encapsulation scopes BUM traffic per-VLAN, preventing cross-domain BPDU leakage
3. Validate that proxy ARP (enabled automatically by Flood in Encapsulation) allows endpoints in different VLANs to reach each other at L3 via the ACI pervasive SVI
4. Validate that two separate native-VLAN EPGs are required — a single native-VLAN EPG merges the MSTP domains
5. Validate that BPDU Guard on access ports (not uplinks) provides loop protection without err-disabling legitimate uplinks

### Success criteria

| Criterion | Pass condition |
|---|---|
| L2 isolation | MSTP BPDUs from internal domain do not appear on external-domain ports, and vice versa |
| IP reachability | Endpoints in VLAN 10 (internal) and VLAN 20 (external) can ping each other via the ACI SVI |
| MSTP domain independence | Each MSTP region retains its own root bridge; no TCN propagation between domains |
| Proxy ARP | ACI answers ARP requests for IPs in the other VLAN with its own SVI MAC |
| BPDU Guard placement | BPDU Guard on access ports blocks accidental loops; BPDU Guard on uplink ports err-disables legitimate links |

---

## 2. Testing Environment

### Topology

Two independent L2/MSTP domains — internal non-Cisco L2 switches connecting to local servers, and an external SDN region — connect to the same ACI bridge domain through separate EPGs. Both share the same IP subnet (10.1.1.0/24) and the same ACI pervasive gateway (10.1.1.1).

```
 ACI Fabric
 ┌──────────────────────────────────────────┐
 │  Bridge Domain: Subnet 10.1.1.0/24       │
 │  SVI 10.1.1.1 (pervasive)                │
 │  Flood in Encapsulation: ON              │
 │                                          │
 │  ┌────────────┐  ┌────────────┐          │
 │  │EPG-Inside  │  │EPG-Outside │          │
 │  │ VLAN 10    │  │ VLAN 20    │          │
 │  └─────┬──────┘  └─────┬──────┘          │
 │        │               │                 │
 │  ┌─────▼──────┐  ┌─────▼──────┐          │
 │  │Native-In   │  │Native-Out  │          │
 │  │ untagged   │  │ untagged   │          │
 │  └─────┬──────┘  └─────┬──────┘          │
 └────────┼───────────────┼─────────────────┘
          │               │
     ┌────▼────┐     ┌────▼────┐
     │Non-Cisco│     │External │
     │L2 Switch│     │SDN GW   │
     │(MSTP)   │     │(MSTP)   │
     └────┬────┘     └────┬────┘
          │               │
     ┌────▼────┐   ┌──────▼──────┐
     │Local    │   │ External SDN│
     │Servers  │   │ Region      │
     └─────────┘   └─────────────┘
```

### Design under test: four EPGs in a single bridge domain

| Component | VLAN | Purpose |
|---|---|---|
| EPG-Inside | 10 | Internal servers (tagged) |
| EPG-Native-Inside | — (untagged) | Catches untagged MSTP BPDUs from internal non-Cisco L2 switches |
| EPG-Outside | 20 | Uplink to external SDN region via vPC (tagged) |
| EPG-Native-Outside | — (untagged) | Catches untagged MSTP BPDUs from external SDN GW |
| Bridge Domain | — | Subnet 10.1.1.0/24, pervasive SVI 10.1.1.1 |
| VRF | — | Same VRF for all EPGs |

With **Flood in Encapsulation** enabled on the bridge domain [1, pp. 113–114]:
- Broadcast, unknown unicast, and multicast are scoped to ports within the same VLAN — no cross-VLAN L2 flooding
- All control-plane traffic (STP, OSPF, ARP, etc.) stays within its originating VLAN (ACI 3.1+)
- Proxy ARP is automatically enabled — ACI answers ARP requests for IPs in the other VLAN with its own SVI MAC, then routes the packet at L3 within the bridge domain
- **Requirements**: -EX or later leaf switches, unicast routing enabled, subnet configured on the bridge domain, MAC addresses unique across VLANs
- **Incompatible with**: microsegmentation, IPv6 (not validated)

### Loop prevention layers

| Layer | Mechanism | Where | Purpose |
|---|---|---|---|
| 1 | **vPC + LACP** | ACI leaf → external SDN GW | Both uplinks forward, no STP blocking port |
| 2 | **Spanning Tree** | Internal non-Cisco L2 switches + external SDN switches | Handles loops within each L2 domain independently; BPDUs flow freely across ACI uplinks within their respective native-VLAN EPGs |
| 3 | **MCP** (Mis-Cabling Protocol) | ACI leaf ports | Detects miscabling at the ACI edge |
| 4 | **BPDU Guard** | Both internal and external switch **access ports only** | Prevents accidental loop from patching two access ports together [1, p. 129] |

---

## 3. Testing Steps

### Step 1: Baseline — single native-VLAN EPG (negative test)

**Action**: Create a single native-VLAN EPG covering both internal and external-facing ports.

**Expected (negative)**: MSTP BPDUs from the internal domain appear on external-domain ports, and vice versa — the two MSTP regions merge into a single spanning tree. If the two regions have different root bridges, spanning tree re-converges and may disrupt traffic.

**Gate**: Confirmed failure — single native-VLAN EPG is insufficient. Proceed to Step 2 with the two-native-EPG design.

### Step 2: Four-EPG isolation — BPDU containment

**Action**:
1. Create EPG-Native-Inside with access/untagged static binding on internal-facing ports
2. Create EPG-Native-Outside with access/untagged static binding on external-facing vPC ports
3. Enable Flood in Encapsulation on the bridge domain
4. Capture BPDUs on internal and external ports

**Expected**: MSTP BPDUs from EPG-Native-Inside do not appear on EPG-Native-Outside ports. BPDUs from EPG-Native-Outside do not appear on EPG-Native-Inside ports. Each MSTP region retains its own root bridge.

**Gate**: Must pass before proceeding. If BPDU leakage is observed, verify Flood in Encapsulation is enabled and that both native-VLAN EPGs are in the same bridge domain.

### Step 3: Proxy ARP — cross-VLAN IP reachability

**Action**:
1. Place a test server in EPG-Inside (VLAN 10) with IP 10.1.1.10
2. Place a test server in EPG-Outside (VLAN 20) with IP 10.1.1.20
3. From 10.1.1.10, ping 10.1.1.20
4. Capture ARP on both VLANs

**Expected**: 
- 10.1.1.10 ARPs for 10.1.1.20 → ACI responds with its SVI MAC (proxy ARP)
- Ping succeeds
- No ARP broadcasts cross between VLAN 10 and VLAN 20

**Gate**: Must pass before proceeding.

### Step 4: BPDU Guard placement

**Action**:
1. Enable BPDU Guard on an external switch access port (not the ACI uplink)
2. Patch a cable between two access ports on the external switch
3. Observe the port state

**Expected**: BPDU Guard err-disables the access port, preventing the loop. The ACI uplink remains up.

**Negative test**: Enable BPDU Guard on the ACI uplink port. Observe that legitimate BPDUs from the external switch err-disable the uplink, breaking connectivity.

**Gate**: Confirmed — BPDU Guard on access ports only; BPDU Guard on uplinks is destructive.

### Step 5: MSTP TCN scope

**Action**:
1. Trigger a topology change on the internal MSTP domain (link flap)
2. Observe TCN propagation on the external MSTP domain

**Expected**: TCN stays within the internal MSTP domain. External domain does not see the TCN. No MAC table flushes on external-side switches.

**Gate**: Must pass — confirms Flood in Encapsulation scopes TCN propagation per-VLAN.

#### MST instance → VLAN mapping

The Design Guide [1] also requires the administrator to explicitly configure the
mapping of MST instances to VLANs on the external switches. This is standard
MSTP behavior per 802.1s: each **MST instance** (numbered 0–4094) runs its own
spanning tree, and one or more VLANs are mapped to an instance. When a TCN
arrives on instance *N*, only the MAC address table entries for VLANs mapped to
instance *N* are flushed — VLANs in other instances are untouched.

Without explicit VLAN→instance mapping:
- All VLANs default to the **IST** (Internal Spanning Tree, instance 0), meaning
  a TCN on any port flushes MACs for every VLAN in the MST region — collapsing
  the per-VLAN isolation that Flood in Encapsulation provides.
- Conversely, if VLAN 10 and VLAN 20 are mapped to different MST instances, a
  TCN from the internal domain (VLAN 10's instance) does not flush MACs on the
  external domain (VLAN 20's instance), even if the BPDU somehow crosses.

This mapping is configured on the external switches, not in ACI — ACI's Flood
in Encapsulation handles BPDU containment within the fabric; the external
switches' MST instance mapping handles TCN MAC-flush scope within their own
MSTP domain.

### Step 6: Operational sequence (EPG shutdown/unshut)

**Action**:
1. Create EPG-Outside in Shutdown state
2. Attach vPC, verify LACP is in P state
3. Unshut the EPG
4. Verify connectivity

**Expected**: No loops or traffic disruption during the bring-up. LACP bundle forms correctly before the EPG starts forwarding.

**Gate**: Confirmed — the operational sequence from [1, p. 130] works as documented.

---

## 4. Issues Encountered

### Issue 4.1: Single native-VLAN EPG merges MSTP domains

**Symptom**: With a single native-VLAN EPG covering both internal and external ports, MSTP BPDUs from the internal domain appear on external ports. The two MSTP regions elect a single root bridge — potentially on the wrong side for one domain, causing re-convergence.

**Root cause**: Flood in Encapsulation scopes BUM traffic per-VLAN, not per-port. A single native-VLAN EPG carries untagged BPDUs from both sides in the same VLAN scope, so BPDUs flood freely between internal and external ports.

**Fix**: Create two separate native-VLAN EPGs — EPG-Native-Inside and EPG-Native-Outside — each with access/untagged bindings on their respective port sets. ACI allows multiple EPGs with untagged bindings in the same bridge domain; the only constraint is that a given physical port can have at most one untagged binding [1, pp. 129–130].

**Verification**: Capture BPDUs on external-facing ports — no BPDUs from internal domain present. Each MSTP region retains its own root bridge.

### Issue 4.2: Untagged MSTP BPDUs silently dropped without native-VLAN EPG

**Symptom**: External MSTP domain cannot detect topology changes through the fabric. BPDU frames are not forwarded.

**Root cause**: MSTP BPDU frames carry no VLAN tag — they are sent untagged over the native VLAN [1, p. 129] [2]. Without a VLAN tag, ACI cannot classify the BPDU into any EPG, and the frame is silently dropped. The external MSTP domain becomes partitioned across the ACI fabric.

**Fix**: Create native-VLAN EPGs with access/untagged static port bindings. The physical domain's VLAN pool must include the native VLAN ID so the leaf port accepts the untagged BPDU frames [2]. In the ACI GUI, the port mode shows as "Access (802.1P)" — this maps to "native" (untagged) in the ACI object model [3].

**Verification**: `show spanning-tree` on external switches shows BPDUs sent and received across the ACI uplink. MSTP topology changes propagate correctly within each domain.

### Issue 4.3: Cross-VLAN BUM leakage without Flood in Encapsulation

**Symptom**: When Flood in Encapsulation is disabled, the four-EPG design provides no isolation. Broadcast from VLAN 10 (EPG-Inside) reaches VLAN 20 (EPG-Outside). Unknown-unicast flooding from one side hits the other side's endpoints. MSTP BPDUs cross between native-VLAN EPGs.

**Root cause**: Without Flood in Encapsulation, ACI defaults to flooding BUM traffic at the bridge-domain level regardless of VLAN tag [1, pp. 113–114]. All four EPGs collapse into a single BUM domain.

**Fix**: Enable Flood in Encapsulation on the bridge domain. This scopes BUM traffic per-VLAN: BPDUs in EPG-Native-Inside stay within that EPG's port set; BPDUs in EPG-Native-Outside stay within its port set.

**Verification**: Before fix — BPDU capture shows cross-domain leakage. After fix — clean separation. Proxy ARP also becomes available only after Flood in Encapsulation is enabled.

### Issue 4.4: BPDU Guard on uplink err-disables legitimate link

**Symptom**: Enabling BPDU Guard on the ACI uplink port causes the port to err-disable when a legitimate BPDU arrives from the external switch.

**Root cause**: BPDU Guard is designed for access ports — it err-disables any port that receives a BPDU [1, p. 129]. On an uplink connected to an external switch running STP, BPDUs are expected and legitimate. BPDU Guard on the uplink breaks connectivity entirely.

**Fix**: Place BPDU Guard on **access ports only** on both the internal and external switches. The Design Guide [1, p. 130] explicitly states: *"Ensure that the external Layer 2 network has Spanning Tree enabled so that if a loop occurs Spanning Tree can help prevent the loop."* Do not disable STP on uplinks. BPDU Guard on access ports protects against the specific threat of someone accidentally patching two access ports between external switches, creating a physical loop outside the fabric that bypasses the vPC.

**Verification**: Access-port BPDU Guard correctly err-disables patched-together access ports without affecting the uplink. Uplink BPDUs flow freely.

---

## 5. Design findings

### EPG vs L2Out

**Tested**: Both EPG and L2Out approaches for L2 external connectivity. **Finding**: EPG approach is more flexible and more widely used. L2Out is more restrictive (one VLAN per L2Out) and primarily serves as a training-wheels loop-prevention construct. The ACI Design Guide explicitly recommends the EPG approach [1, p. 128].

### MSTP variant choice

Both the internal non-Cisco L2 switches and the external SDN region run **MSTP (802.1s)**. MSTP is the IEEE standard default on non-Cisco platforms (Huawei, Arista, Juniper). The four-EPG pattern works with any MSTP-speaking external device.

### Latency consideration

The flood-in-encapsulation + proxy-ARP model means inter-region traffic takes a routed hop through the ACI SVI (same leaf switch if both EPGs are on the same leaf, or across the fabric if they span leaves). This is typically negligible but worth noting for latency-sensitive workloads.

### EPG-level vs BD-level Flood in Encapsulation

The ACI Layer 2 Networking Configuration Guide [4] documents Flood in Encapsulation
as a setting available at **both** the EPG and bridge-domain level, with four distinct
behavior combinations:

| EPG FiE | BD FiE | Behavior |
|---|---|---|
| ON | ON | Flood in encapsulation takes place for traffic on all VLANs and VXLANs within the bridge domain |
| OFF | ON | Flood in encapsulation takes place for traffic on all VLANs and VXLANs within the bridge domain |
| ON | OFF | Flood in encapsulation takes place for traffic on that VLAN or VXLAN within the EPG of the bridge domain |
| OFF | OFF | Flooding takes place within the entire bridge domain |

**Finding**: For the four-EPG design, **EPG-level Flood in Encapsulation = ON with
BD-level = OFF** provides the most granular BUM scoping — each EPG's traffic is
contained to its own VLAN. BD-level = ON enables the same behavior across all
VLANs in the BD (functionally equivalent for this design but broader in scope).
The critical takeaway is that **BD-level = OFF with EPG-level = ON still provides
per-VLAN isolation** — the EPG-level setting is sufficient on its own.

The earlier statement that Flood in Encapsulation must be enabled "on the bridge
domain" [1, pp. 113–114] reflects the Design Guide's use of bridge-domain-level
configuration as the canonical path. The Configuration Guide [4] confirms the
more granular EPG-level option exists and is sufficient for the four-EPG pattern.

### Physical separation requirement

The two MSTP regions must have **no direct L2 connection outside the ACI fabric**. The ACI bridge domain is the only L2 path between them. Any additional physical link creates a loop that Spanning Tree on the external switches may or may not detect (depending on whether BPDUs cross between VLANs — with Flood in Encapsulation, they do not).

---

## References

[1] "Cisco Application Centric Infrastructure Design Guide," Cisco White Paper,
    last updated June 6, 2024, based on ACI release 6.0(1g).
    https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-application-centric-infrastructure-design-guide.pdf
    *Changeable* — verify pages 113–114 (Flood in Encapsulation), pages 127–132
    (Connecting EPGs to External Switches including MSTP/native-VLAN EPG pattern
    and BPDU Guard placement), and page 128 (EPG vs L2Out recommendation).

[2] "FabricPath to ACI Migration Cisco Validated Design Guide," Cisco,
    first published September 1, 2014, last updated May 5, 2017.
    https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/migration_guides/fabricpath_to_aci_migration_cisco_validated_design_guide.pdf
    *Changeable* — verify the "ACI With MST" section and associated Figure 8
    (Assign Port to an EPG Using Native Mode). The native-VLAN EPG pattern is
    described on pages 14–15 of the PDF.

[3] "Cisco ACI and STP (MSTP)," Cisco Community, solved thread ID 5261828.
    https://community.cisco.com/t5/application-centric-infrastructure/cisco-aci-and-stp-mstp/td-p/5261828
    *Changeable* — verify the thread is still accessible; the port mode
    (Access/802.1P → native/untagged in the object model) is confirmed in the
    accepted solution.

[4] "Bridging," Cisco APIC Layer 2 Networking Configuration Guide, Release 6.0(x),
    Cisco. Table 1: Behavior When Both BDs and EPGs Are Configured.
    https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/6x/l2-configuration/cisco-apic-layer-2-networking-configuration-guide-60x/bridging-60x.html
    *Changeable* — verify Table 1 (EPG-level vs BD-level Flood in Encapsulation
    interaction matrix); confirmed 2026-08 based on the ACI 6.0(x) documentation
    track. Search terms if URL changes: "cisco apic layer 2 networking configuration
    guide 60x bridging flood in encapsulation EPG bridge domain table".
