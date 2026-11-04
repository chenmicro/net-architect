# POC: General-purpose Digital Map on a multi-vendor data center network

> Based on product documentation and information about the live network, not lab-tested.

> Skeleton. Field values are filled only where a source supports them. Blank fields
> are not yet known.

## Background

- **Date**: 2026-11
- **Why it matters**: the live network mixes a Huawei fabric with non-fabric Huawei
  devices and with Cisco, Fortinet, Check Point, and F5 devices. Digital Map coverage differs per
  device, so the end-to-end result depends on the weakest device in a path.
- **Scope**: general-purpose Digital Map only: topology restoration and path
  navigation. Application topology, Simulation View, and AI Digital Map are out of
  scope. Security View is in scope only as the source of firewall policy data. Path
  navigation stays inside one data center and ends at the DC edge. Cross-DC paths are
  out of scope, although both inter-DC link groups appear in the topology.
- **What path navigation shows**: all possible equal-cost paths for a 5-tuple, calculated from
  the region modeling data and the 5-tuple information of the endpoints [1]. It does
  not show the exact path of a live TCP or UDP session, so a test checks that the real path
  is among the results.
- **Deployment**: two iMaster NCE-Fabric domain controllers managed by one iMaster
  NCE-Fabric MDC.
- **Product versions**: iMaster NCE-Fabric and MDC V100R026C00.
- **Version scope**: every documented fact here is read in V100R026C00, in the Stellar AI
  Fabric Data Center Network Solution Product Documentation (MDC Scenario) [1], which carries
  the MDC documentation set in full.
- **Scenario**: [skills/vendor-matrix/huawei/cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md#digital-map-imaster-nce-fabric)

## Test environment

### Topology

Both data centers have the same topology, shown here for one of them.

```
 Extranet       Extranet (VPN)     Internet            Branches
     │               │ site-to-site    │                   │
┌────┼── Data center ┼─────────────────┼───────────────────┼─────────┐
│Extranet router  VPN firewall    Internet router     Branch router  │
│AR6710-L         FPR-2140        AR6710-L               AR8140      │
│    │               │                 │                   │         │
│    │               │            Internet firewall        │         │
│    │               │            Check Point 23500        │         │
│    └────────┐      │      ┌──────────┘                   │         │
│             │      │      │                              │         │
│             Inner firewall                               │         │
│             FPR4100                                      │         │
│               │       │                                  │         │
│Proxy firewall │       │                                  │         │
│FortiGate ─── Core ────┼──────────────────────────────────┘         │
│           S67XX-H     │       Core to other DC core: L3 traffic    │
│              │        │                                            │
│──────────────┼────────┼────────── Fabric: CE6881H, CE6885, CE9865  │
│              │        │                                            │
│ Fabric border         Fabric border                                │
│  (DC tenant)          (DMZ tenant)                                 │
│      │   │                │                                        │
│      │   DC firewall      │                                        │
│      │   ASA 5525-X       │                                        │
│      │   (off-path)       │                                        │
│      └────────┬───────────┘                                        │
│             Spine ─── IPN leaf                                     │
│               │            IPN to other DC IPN: L2 traffic         │
│               │            (L3 underlay, Segment VXLAN overlay)    │
│          Server leaf                                               │
│               │                                                    │
│          Servers, F5                                               │
└────────────────────────────────────────────────────────────────────┘
```

The FortiGate has no physical link to the branches. Branch traffic enters through the
AR8140 and the core. The FortiGate is an HTTP proxy for branch terminals.

Controllers: one iMaster NCE-Fabric MDC manages one iMaster NCE-Fabric domain controller
per data center.

The IPN switches are leaf switches with a special role: inter-site Segment VXLAN.

The FPR-2140 also has a link to the core. This POC leaves that link out.

### Device list

| Role | Vendor | Model | Software version |
|---|---|---|---|
| Multi-site controller | Huawei | iMaster NCE-Fabric MDC | V100R026C00 |
| Domain controller (x2) | Huawei | iMaster NCE-Fabric | V100R026C00 |
| Internet router, extranet router | Huawei | AR6710-L | |
| Branch router, on DC core | Huawei | AR8140 | |
| VPN firewall | Cisco | FPR-2140 | Threat Defense (FTD) 7.4.2.4 |
| Internet firewall | Check Point | 23500 | |
| Firewall management server | Check Point | | |
| Firewall management server | Cisco | FMC | |
| Inner firewall | Cisco | FPR4100 (FPR4K-SM-12) | Threat Defense (FTD) 7.2.9 |
| Proxy firewall, on DC core | Fortinet | FortiGate | |
| DC core switch | Huawei | S67XX-H | |
| Fabric switch | Huawei | CE6881H | |
| Fabric switch | Huawei | CE6885 | |
| Fabric switch | Huawei | CE9865 | |
| DC firewall, off-path on fabric border leaf, DC tenant only | Cisco | ASA 5525-X | |
| Load balancer, under server leaf switches | F5 | BIG-IP i2000, i4000, LTM only | |

Firewall roles are confirmed. The ASA is the DC
firewall. The FPR models are Cisco Firepower and run Threat Defense: 7.2.9 and 7.4.2.4 are
Threat Defense releases, while standalone ASA uses a 9.x version line [2][3]. Both register
to the FMC, the Firepower management server in the environment.

Each data center has its own DC firewall, with no cluster between them. For reference, ASA
supports inter-site clustering, and the 5525-X supports 2-unit clusters from 9.1(4) [4]. Routed mode with
Spanned EtherChannel is reported as supported from 9.5 [4]. This was not checked against
the 9.14 guide, the last release for this model [2].

### Network plan

**Asset model**

Each data center has five regions, ten in total. The zones split the network into several access
regions plus one core region, and the IPN switches stay in the fabric region, so no separate
interconnection zone is planned.

| Item | Value |
|---|---|
| Institutions | Two data centers with the same topology. Extranet as an external institution. Branches as level-1 branches, hub-spoke |
| Internet access zone (access region) | Internet router, internet firewall |
| Extranet zone (access region) | Extranet router, VPN firewall |
| WAN zone (access region) | Branch router, proxy firewall |
| Core region (core region) | S67XX-H, inner firewall |
| Fabric zone (service resource region) | CE switches, DC firewall, F5 |
| Inter-institutional links | DCI (core to core for L3 traffic, IPN to IPN for L2 traffic), external private line, Internet |
| Management reachability, MDC to firewalls | Required |
| Management reachability, MDC to Check Point manager | RESTful on the web API, port 443 by default [1] |
| Management reachability, MDC to FMC | RESTful on the web API, port 443 by default [1] |

**Device roles**

Roles are set manually after the devices are added to each region. Role names follow the role
list on the Managing Devices page: egress gateway, VAS, core, aggregation, leaf, MGMT, and
BMC [1].

| Role | Devices |
|---|---|
| Egress gateway | AR6710-L, AR8140 |
| VAS | Firewalls, F5 |
| Core | S67XX-H |
| Aggregation | Spine |
| Leaf | Server leaf, border leaf, IPN leaf |

**Device coverage plan**

Devices reach the MDC as managed by a domain controller, added manually, discovered
automatically, or synchronized from a third-party system [1]. The firewalls and the F5 sit
outside the fabric, so they are added on the MDC.

"Listed support" is what the documentation lists: Table 1 of the collection task for basic
collection, and network-security convergence for security collection [1].

| Device | Inventory and links | Runtime tables | Policy and NAT source | Listed support | Expected path role |
|---|---|---|---|---|---|
| CE6881H, CE6885, CE9865 | Domain controller sync | Device collection, distributed mode [1] | Not applicable | | Full model [1] |
| S67XX-H | Added on the MDC | Device collection [1] | Not applicable | | |
| AR6710-L, AR8140 | Added on the MDC | No AR model on the Device Data Collection page [1] | | | |
| FPR4100, FPR-2140 (FTD) | Added on the MDC | Table 1 items except the link table [1] | `CiscoFirepower_Policy` through the FMC, which needs RESTful parameters in addition to STelnet [1] | `Firepower2110` 6.6.1, basic collection; `firepower2110` 7.1, security collection. No other model or version [1] | |
| ASA 5525-X | Added on the MDC | Table 1 items [1] | `Third-party_firewall_Policy` [1] | ASAv 9.17(1), device management 7.17(1) [1], above this model's last release [2] | |
| Check Point 23500 | Added on the MDC | Outside the preconfigured list, which covers 3600 R81.20 only [1] | `CheckPoint_Policy` through the firewall manager [1] | 3600 R81.20, basic collection; 5200 R81.20, security collection [1] | |
| F5 i2000, i4000 | Added on the MDC | Table 1 items [1] | `Third-party_firewall_Policy` [1] | BIG-IP 3600 v12.1.0 and 4000 v11.6.1, basic collection; 12.x, 15.x, 17.x, security collection [1] | |
| FortiGate | Added on the MDC | Table 1 items [1] | `Third-party_firewall_Policy` [1] | FortiGate-100F v7.6.3 [1] | |

**Link discovery plan**

Domain controllers know the fabric's inter-device links and send them to the MDC, so fabric
links do not use topology restoration. Restoration is for devices outside the fabric, or with
LLDP disabled, and runs on the MDC [1].

LLDP is disabled on the firewalls for security. Point-to-point links use /28 to /30
addressing, inside the range the interconnection IP algorithm calculates: it takes subnet
masks from 24 to 31 and selects 28, 29, 30, and 31 by default [1]. Expected methods below come
from the southbound data each algorithm needs [1]. TC-08 confirms them.

| Link | Expected method |
|---|---|
| Inside the fabric | Domain controller sync |
| Core to core, inter-DC | Inter-institutional link [1] |
| IPN to IPN, inter-DC | Inter-institutional link [1] |
| Core to fabric border | LLDP |
| F5 to server leaf | LLDP, or the interconnection IP algorithm, which takes the F5 configuration file [1] |
| Core to proxy firewall | Interconnection IP, LACP if aggregated |
| Fabric border to DC firewall | Interconnection IP, LACP if aggregated |
| Core to inner firewall | Interconnection IP, LACP if aggregated |
| Inner firewall to fabric border (DMZ tenant) | Interconnection IP, LACP if aggregated |
| Inner firewall to extranet router | Interconnection IP if AR data is collected, otherwise manual |
| Inner firewall to VPN firewall | Interconnection IP, LACP if aggregated |
| Core to branch router | LLDP if AR data is collected, otherwise manual |
| Inner firewall to internet firewall | Manual |
| Internet firewall to internet router | Manual |

Rows that use FTD data depend on TC-05.

**Collection plan**

| Item | Value |
|---|---|
| Fabric devices | Distributed mode, collected by the domain controller [1] |
| Devices outside the fabric | Collected by the MDC, unless associated with a domain controller [1] |
| Collection period | Set on the task as a periodic task in minutes, hours, days, or weeks [1] |
| Indicators for topology restoration | MAC, interface packet statistics, ARP, link table [1] |
| Indicators for path navigation | Link table, ARP, MAC, and routing table, plus the interface, VLAN, VPN, vSYS, and aggregation data basic navigation mode needs [1]; for F5, the configuration file [1] |

## Test cases

| Phase | Test cases |
|---|---|
| Onboarding and collection | TC-01 to TC-06 |
| Topology restoration | TC-07 to TC-10 |
| Path navigation | TC-11 to TC-22 |

### TC-01: MDC manages both domain controllers and synchronizes data
**Objective**: Confirm that basic device information, inter-device links, and virtual
resources such as VBDIF reach the MDC over Kafka from both domain controllers. No manual device
addition is needed for these devices.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-02: Manage devices outside the fabric
**Objective**: Add the third-party devices and the Huawei devices outside the fabric on
the MDC, with vendor and model. These are the firewalls, the Check Point
firewall manager, F5, S67XX-H, AR6710-L, and AR8140.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-03: Institution and region model
**Objective**: Build the asset hierarchy for both data centers, add the devices to each
region, then set each device role manually.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-04: Third-party driver package and credentials
**Objective**: Confirm the preconfigured GND package on each listed model and set device
credentials, including RESTful parameters for Check Point and Cisco Firepower [1]. At
V100R026C00 nothing is imported for a listed model, so the test checks that the package
collects, and imports one only for a model outside Table 1 [1].
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-05: Runtime data collection per device family
**Objective**: Collect the indicators in the collection plan with device collection in
distributed mode, and record which items succeed on each device family. Start with
FPR4100 and FPR-2140, which run FTD and register to the FMC.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-06: Firewall and load balancer policy collection
**Objective**: Collect security and NAT policies with `CheckPoint_Policy`,
`CiscoFirepower_Policy` through the FMC, and `Third-party_firewall_Policy` for the remaining
devices, then confirm that the Cisco policies appear under Device Policy Management.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-07: LLDP link discovery
**Objective**: Measure how many expected links appear from LLDP and domain controller
sync alone.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-08: Link restoration on devices without LLDP
**Objective**: Work through the link discovery plan and record which algorithm finds
which link. Add the rest manually or by template.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-09: Host link restoration
**Objective**: Restore the links between leaf switches and servers.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-10: Topology views and correction workflow
**Objective**: Check the level-1, level-2, and level-3 views, then confirm, delete, and
blacklist restored links.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-11: Basic forwarding mode
**Objective**: Set basic forwarding mode, with generated or manual tables, on the devices
that do not support full modeling. Do this before modeling.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-12: Region modeling
**Objective**: Model the regions in each data center and confirm that no device is
reported as not supporting modeling.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-13: Path inside one fabric tenant
**Objective**: Query a path between two hosts in one fabric as the baseline.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-14: Path from the DC tenant to the DMZ tenant
**Objective**: Query permitted and denied flows through fabric border, core, inner
firewall, and fabric border again. The path crosses the border in two tenants.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-15: Path to the VPN firewall
**Objective**: Query a path through the inner firewall, ending at the FPR-2140.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-16: Path to the Internet
**Objective**: Query a path through the inner firewall and Check Point 23500, ending at
the internet router.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-17: Path to the extranet
**Objective**: Query a path through the inner firewall, ending at the extranet
router.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-18: Branch path through the branch router
**Objective**: Query a path from the AR8140 through the core into the fabric.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-19: Path through the DC firewall
**Objective**: Query permitted and denied flows in the DC tenant that a fabric border
sends through the off-path ASA and back.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-20: Branch path through the proxy firewall
**Objective**: Query the two TCP sessions of the HTTP proxy as separate paths: from a branch
terminal to the FortiGate, and from the FortiGate to a destination outside the data center.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-21: Path to an F5 virtual IP
**Objective**: Confirm that a path to a virtual IP reaches the F5 under the server leaf
and follows its LTM address translation.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

### TC-22: Path through firewall NAT
**Objective**: Confirm that a query to a DNAT address on a firewall selects the NAT
policy and follows the post-NAT address.
**Prerequisites**:
**Procedure**:
**Expected result**:
**If it fails**:

## Issues encountered

Predicted from documentation and information about the live network.

### ISSUE-01: Firewall links are not discoverable through LLDP
**Found in**: TC-07, TC-08, TC-20
**Symptom**: Firewall links are missing after LLDP discovery.
**Root cause**: LLDP is disabled on the firewalls for security, so the link table has no entry
for those links.
**Fix**: Use the interconnection IP algorithm on Layer 3 links, which matches on subnet
masks from 24 to 31, with 28, 29, 30, and 31 selected by default, and the LACP algorithm on
LACP aggregates [1]. The port traffic algorithm is the alternative: it needs a periodic
collection task at an interval of no more than 1 hour, with at least one day of data collected
first, and it cannot resolve links where traffic is low, under 100 packets per port in 24
hours, or only regular keepalive traffic runs [1]. Otherwise create the link manually or by
template [1]. Check Point is listed only as 3600 R81.20 [1].
**Verification**:

### ISSUE-02: Check Point has no configuration dump over the CLI
**Found in**: TC-05, TC-08, TC-16
**Symptom**: No configuration dump is available over the CLI.
**Root cause**: V100R026C00 lists Check Point once, as 3600 R81.20 in the preconfigured
package [1], and this network runs 23500, so driver collection is not established for it.
Its policy data comes over the RESTful API, which Check Point needs in addition to STelnet
parameters, and `CheckPoint_Policy` collects VSX and interface-bound routing data as well as
the policies [1].
**Fix**: Set the RESTful parameters, then run the `CheckPoint_Policy` process [1].
**Verification**:

### ISSUE-03: Check Point is managed through its firewall manager
**Found in**: TC-02, TC-06
**Symptom**:
**Root cause**: On the live network the Check Point gateways are managed through their manager,
and the MDC has no device group for it.
**Fix**: Add the firewall manager as the network device, then set its web API login user,
password, port, and management IP [1].
**Verification**:

### ISSUE-04: AR collection and modeling are not confirmed
**Found in**: TC-05, TC-12, TC-16, TC-17, TC-18
**Symptom**:
**Root cause**: The Device Data Collection page names CE and S switches, USG and Eudemon
firewalls, and third-party devices, and no AR model [1].
**Fix**: Automatic basic forwarding needs a routing table, link table, interface data,
VLANs, VPNs, and vSYSs, plus NAT policies for third-party devices [1], so this device may need
a manual table.
**Verification**:

### ISSUE-05: FTD is outside the documented firewall scope
**Found in**: TC-05, TC-06, TC-14, TC-15, TC-22
**Symptom**:
**Root cause**: The inner and VPN firewalls run FTD [3] and register to the FMC, which is the
policy source for them. V100R026C00 lists Cisco Firepower as `Firepower2110`, 6.6.1 for basic
collection and `firepower2110` 7.1 for security collection, with no other model or version,
and never says FTD [1]. These devices are FPR4100 at 7.2.9 and FPR-2140 at 7.4.2.4, so both
model and release are outside the list [3]. Cisco reaches the FTD CLI with `connect ftd` [3].
NAT policies match only on some third-party firewall models, and only with basic navigation
mode configured and NAT data collected [1].
**Fix**: Run TC-05 and TC-06 on both firewalls first, and set the RESTful parameters on both
so `CiscoFirepower_Policy` can reach the FMC [1]. V100R026C00 lists `firepower2110`
Version 7.1 for network-security convergence and preconfigures the driver package [1]. So
ask Huawei whether that support covers FTD on these models and releases. If they fail,
record the FTD commands and outputs in the Third-Party Device Data Collection Template and
give it to Huawei professional services, who develop the driver package [5]. Request a
customized GND package and mapping file [1]. A GND package carries its commands in
`collect_config` and its parsing rules in `collect_mapping`, then is compressed, signed,
imported, and deployed [5]; a self-developed package needs a repository and an imported
public key, with a private key of RSA 3072 to 4096 bits, and the MDC lists two import modes:
ASC adds an `.asc` file, and CMS adds a `.cms` file and an optional `.crl` file [1].
Deployment interrupts some services, so run it off-peak [1]. The guide's collection models
have no policy or NAT model, and it does not cover the firewall mapping file [5]. Otherwise
use manual links and manual basic forwarding tables, which have no policy fields [1]. The
device model field must match the driver rule [1][5].
**Verification**:

### ISSUE-06: Restoration depends on live traffic
**Found in**: TC-08, TC-09
**Symptom**: Backup or idle links are missing or wrong.
**Root cause**: The MAC forwarding table algorithm runs in the VLAN scenario only, supports a
tree topology rather than a chain, and needs traffic on every link, so a backup link carrying
no traffic cannot be discovered. The port traffic algorithm cannot resolve links where
traffic is low or where only regular keepalive traffic runs [1].
**Fix**: Delete wrong links and blacklist them. A deletion without the blacklist is
restored again on the next run [1]. Validity is an aging setting from 1 to 3650 days [1].
**Verification**:

### ISSUE-07: Results reflect the last collection and model
**Found in**: TC-12
**Symptom**: A query does not show a recent change.
**Root cause**: Modeling runs on collected device and region data, so a change made after the
last collection or model does not appear until both run again [1].
**Fix**: Set the collection interval in the collection task, and remodel after each collection
[1].
**Verification**:

### ISSUE-08: Scale and feature limits
**Found in**: TC-12
**Symptom**: Paths are interrupted on devices with DCI, DCI through Segment VXLAN,
microsegmentation, IPsec VPN, EIP, or IPv6 [1]. The IPN switches carry Segment VXLAN.
**Root cause**: These are documented path navigation limits in the hardware scenario.
Modeling also covers at most 3000 devices [1].
**Fix**:
**Verification**:

### ISSUE-09: Domain controller sync does not carry runtime tables
**Found in**: TC-01, TC-05, TC-12
**Symptom**: Devices and links appear on the MDC, but the IPv4 routing, MAC, and ARP
tables are missing.
**Root cause**: Sync carries devices, uncleared alarms, device events, ports, links, device
groups, fabrics, VAS resource pools, end ports, and end port IP addresses, and no routing,
MAC, or ARP table [1].
**Fix**: Create device collection tasks for the runtime tables. Distributed mode can be
selected [1].
**Verification**:

### ISSUE-10: ASA 5525-X is outside the listed ASA release
**Found in**: TC-05, TC-19
**Symptom**:
**Root cause**: The last ASA release for this model is 9.14, so it cannot run the listed ASAv
9.17(1) release, and Cisco end of support was Sep. 30, 2025 [2].
**Fix**: If collection fails, request a customized GND package and mapping file through Huawei
professional services [1], or carry the ASA with basic navigation mode, which needs its own
routing, ARP, MAC, interface, and aggregation data [1].
**Verification**:

## Conclusion

## References

[1] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612446 (verify at
support.huawei.com HedEx, `docid=EDOC1100612446`). The governing solution document, and the only
source for the V100R026C00 facts here: it carries the MDC documentation set in full, with the
same topics and text as the iMaster NCE-Fabric MDC product documentation. Read for: Device Data
Collection > Creating a Collection Task (Table 1, secondary authentication table); Collecting
Data > Synchronizing Data from Domain Controllers; Path Navigation (overview, Modeling a Region,
Basic Navigation Mode > Constraints and Limitations); Topology Restoration > Configuring
Restoration Algorithms; Managing Links > Managing Inter-Device Links; Security View >
Network-Security Convergence > Limitations and Constraints (Table 2); Preparations > Collecting
Third-Party Data (Table 1). Confirmed Nov. 4, 2026.

[2] "Cisco Secure Firewall ASA Compatibility" and "Cisco Secure Firewall Threat Defense
Compatibility Guide," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/security/asa/compatibility/asamatrx.html and
https://www.cisco.com/c/en/us/td/docs/security/firepower/compatibility/firepower-compatibility.html
Verify: ASA 5525-X last version and end of support; FPR-2140 last Threat Defense version.
Read through search results on Oct. 31, 2026. Direct access returned HTTP 403.

[3] "Cisco Secure Firewall Threat Defense Release Notes, Version 7.2.x" and "Version
7.4.x," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/release-notes/threat-defense/720/threat-defense-release-notes-72.html
and https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/release-notes/threat-defense/740/threat-defense-release-notes-74.html
Also "Verify Firepower Software Versions," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/security/firepower-ngfw/217884-verify-firepower-software-versions.html
Verify: 7.2.9 (build 44, Oct. 22, 2024); 7.4.2.4 (build 9, Sep. 25, 2025); `connect ftd`.
Read through search results on Oct. 31, 2026.

[4] "CLI Book 1: Cisco ASA Series General Operations CLI Configuration Guide, 9.2 — ASA
Cluster," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/security/asa/asa92/configuration/general/asa-general-cli/ha-cluster.html
and "Common Issues with ASA Inter-Site Transparent Cluster," Cisco. [Online]. Available:
https://www.cisco.com/c/en/us/support/docs/security/adaptive-security-appliance-asa-software/200439-Common-Issues-with-ASA-Inter-Site-Transp.html
Verify: feature history for 2-unit clusters and inter-site clustering. Read through search
results on Oct. 31, 2026. The 9.14 guide was not retrieved.

[5] "Digital Map Third-Party Device Driver Package Development Guide," Huawei, Issue 01,
Apr. 17, 2023 (EDOC1100300656, no product version stated). Verify in:
2.2 Driver Package Development; 2.3 Driver Package Packaging; 2.4 Driver Package Test;
3 Collector Capability Reference. Confirmed Oct. 31, 2026.
