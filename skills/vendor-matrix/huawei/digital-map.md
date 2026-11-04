# Huawei Digital Map

iMaster NCE-Fabric MDC Digital Map, V100R026C00, read in the Stellar AI Fabric Data Center
Network Solution Product Documentation (MDC Scenario) [1]. That library carries the MDC
documentation set in full — Digital Map, installation, maintenance, and reference — so it is the
only source this file cites.

## Digital Map data

Where Digital Map gets the data for path navigation.

### Data sources

Digital Map has two collection layers. Basic collection reads devices through a driver package.
Security collection runs a preset workflow in Collection Designer on top of it. V100R026C00
preconfigures a GND package for every model in Table 1, so nothing is imported for them
[1]. See
[digital-map-driver.md](digital-map-driver.md).

| | Basic collection | Security collection |
|---|---|---|
| Menu | Basic Service > Data Collection > Device Collection > Collection Task List | Basic Service > Data Collection > Third-Party System Collection > Collection Task List |
| Runs | Preconfigured GND package [1] | Preset process for the firewall type, viewed in Third-Party System Collection > Collection Designer [1] |
| Data | Routes, ARP, MAC, interfaces, links, device configuration [1] | Security policies and NAT policies, and service and address sets on firewalls [1] |
| Access | STelnet parameters, with a secondary authentication password on some firewalls [1] | STelnet parameters. Check Point and Cisco Firepower also need RESTful parameters [1] |
| Unsupported model | [Develop a GND package](digital-map-driver.md#developing-a-driver), then import and deploy it [1][2] | No procedure in this release |

| Preset process | Collects and parses |
|---|---|
| `USG_Policy` | Security and NAT policies of Huawei USG devices |
| `CheckPoint_Policy` | Security and NAT policies of Check Point firewalls, and their VSX and routing table data |
| `CiscoFirepower_Policy` | Security and NAT policies of Cisco Firepower firewalls |
| `Third-party_firewall_Policy` | Security and NAT policies of third-party firewalls, and NAT policies of LBs |

RESTful parameters give the MDC the firewall's web API, port 443 by default, to query its
configuration [1]. The indicator list gives Device configuration as an input for reconstructing
firewall security policies and NAT policies. `USG_Policy` and `Third-party_firewall_Policy` 1.0.28 have
the same steps: ValidateInput, CreateCollection, CheckTask, and ParseCfg [1]. So they create a device
collection task, then parse the collected configuration *inferred*. The script in each step can be
viewed in Collection Designer.

For security policy recommendation, the
southbound collection items are N/A on Cisco Firepower [1], because its data comes from FMC.

The preset `CiscoFirepower_Policy` process calls the FMC REST API, under
`/api/fmc_config/v1/domain/`, for device records, FTD HA pairs, IPv4 static routes, physical, sub, and EtherChannel interfaces,
security zones, network and port objects, access policies and rules, and FTD NAT policies and
rules. So the process targets FTD managed by FMC. The RESTful dialog is set per firewall and
has its own optional Management IP address, so that field likely holds the FMC address *inferred*
[1]. FDM has a separate API, so an FTD managed with FDM likely has no
collection path *inferred*.

Policy collection keeps only data that converts to 5-tuples, and lists what it skips under
unsupported configurations [1].

Domain controller sync carries devices, uncleared alarms, device events, ports, links, device
groups, fabrics, VAS resource pools, end ports, and end port IP addresses. Routing, MAC, and ARP
tables are not part of it, so they need a device collection task [1].

### Supported third-party devices

| Vendor | Basic collection | Security collection |
|---|---|---|
| Palo Alto | PA-3410 10.2.7-h18 | PA-3410 10.2.7-h18 |
| Cisco ASA | ASAv software 9.17(1), device management 7.17(1) | ASAv software 9.17(1), device management 7.17(1) |
| Cisco Firepower | Firepower2110 Version 6.6.1 | firepower2110 Version 7.1 |
| Cisco Nexus | Nexus 9000 and 9000v 7.0(3)I7(10) | Not applicable, switch |
| F5 | BIG-IP 3600 v12.1.0, BIG-IP 4000 v11.6.1 | BIG-IP 12.x, 15.x, and 17.x |
| Check Point | 3600 R81.20 | 5200 R81.20 |
| Fortinet | FortiGate-100F v7.6.3 | FortiGate-100F v7.6.3 |
| H3C | SecPathF5080 Version 7.1.064 | SecPath-F5080 R9660 |
| Hillstone | SG-6000-K5680 Version 5.5 | SG-6000-K5680 5.5R11 |
| DPtech | FW1000 series S311C013D111 | Not supported |

Models and versions are from [1]. Basic collection is the list of preconfigured GND packages, in
Creating a Collection Task. Security collection is the list for network-security convergence, in
Limitations and Constraints. The two lists are separate, so a device can differ between them, such
as Firepower2110 at 6.6.1 for basic collection and 7.1 for security collection [1]. A model or
release outside these lists needs a GND package imported and deployed first [1].

The standalone `netsecurity_equipment` package is V100R025C00 only: it is imported by hand there,
and no later release ships it, because V100R026C00 preconfigures the driver packages instead
[3][4][1]. Version 1.0.96 is the one package read in detail [4]. Its firewall list has
PA-3060 9.1.16, ASAv 9.18, H3C F5080 R9660, FortiGate-100F 7.6.3,
SG-6000-K5680 5.5R11, and BIG-IP 12.x, 15.x, or 17.x, and it also carries Check Point and Nexus
items. Its Firepower rules use `connect asa`, so they do not reach FTD [4]; the preconfigured
package is the supported path for the models above [1].

The collection items are one list for all models: ARP, MAC, device
configuration, interface information, packet statistics on interfaces, VLAN allowed by an
interface, vSYS bound to an interface, VPN bound to an interface, routing table, link table
(LLDP), LACP, and Eth-Trunk interface member relationship [1].

The vendor name on the MDC must match. Fortinet, Hillstone, and DPtech are case-sensitive [1].
Check Point needs its expert mode password for the link table, and Cisco ASAv and Firepower need
their privileged mode password, set as the secondary authentication password [1]. The Firepower
items in that table are the list above without the link table [1].

Firepower here means FTD. The documentation never says FTD, but `CiscoFirepower_Policy` uses FTD API
paths, and versions 6.6.1 and 7.1 follow Threat Defense numbering [1]. No other Firepower model
or version is listed.

### Basic navigation data

Huawei devices get fine-grained simulation of forwarding and policy matching. Third-party
devices rely on basic navigation mode, which is on by default for them and generates basic
forwarding tables after collection [1]. Other devices can join as basic forwarding devices [1].
The DTRB explicitly lists Hillstone SG6000 5.5R8, F5 4000 11.5.4, and Cisco Nexus 7-5-2 7.0(8)
for V100R024C10 [5].

Basic forwarding covers Layer 2 and Layer 3 only. It does not cover M-LAG, VRRP switchover, or
Layer 4 and Layer 7 features [1]. Logical ports are not valid input, so use physical interface
plus VLAN [1].

Basic navigation mode needs this data [1]:

| Data | Group | In the preconfigured items |
|---|---|---|
| Interface information | `interfaceState` | Yes |
| VPN bound to an interface | `interfaceVpn` | Yes |
| vSYS bound to an interface | `interfaceVsys` | Yes |
| Other interface IP addresses, HSRP virtual IP addresses on Cisco devices | `interfaceExtraIp` | No |
| VLANs allowed by an interface | `interfaceVlan` | Yes |
| Routing table | `routingTable` | Yes |
| Link table | `lldpNeighbor` | Yes |
| Aggregated link membership | `trunkMember` | Yes |
| NAT policies, third-party devices | Not a group | From third-party system collection |

Other interface IP addresses matter only on Cisco devices that run HSRP. The note on automatic
basic forwarding tables does not list it [1].

The indicator list says `interfaceVpn`, `interfaceVsys` (firewalls only), and `interfaceVlan`
generate the third-party basic forwarding table. NAT matching on a third-party firewall needs
NAT data from third-party system collection, and basic navigation mode [1].

### Path navigation and restoration limits

In the hardware scenario, paths are interrupted on devices configured with DCI, DCI through
Segment VXLAN, microsegmentation, IPsec VPN, EIP, or IPv6, and a modeling region covers at most
3000 devices [1].

The interconnection IP address restoration algorithm takes subnet masks from 24 to 31 and
selects 28, 29, 30, and 31 by default. Restored links age out: the validity period is 1 to 3650
days, and a link deleted without the blacklist returns on the next run [1].

## Open items

- What `CheckPoint_Policy` runs. Its steps can be viewed in Collection Designer [1].
- Which firewall configurations ParseCfg can parse, and whether that includes FTD.
- Whether a Firepower version or model outside the listed ones collects and parses correctly.

## References

[1] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612446 (verify at
support.huawei.com HedEx, `docid=EDOC1100612446`). Sections: Digital Map > Digital Map Usage
Guide > General Configurations > Collecting Data > Device Data Collection > Creating a
Collection Task (Table 1); General Configurations > Path Navigation (overview, Modeling a
Region, Basic Navigation Mode > Constraints and Limitations); Topology Restoration >
Configuring Restoration Algorithms; Data Asset Management > Managing Links > Managing
Inter-Device Links; Digital Map > Security View > Network-Security Convergence > Limitations and
Constraints (Table 2); Preparations > Collecting Third-Party Data (Table 1); Southbound Open
Service > Package Management > Package Repository. Same topics and text as the iMaster
NCE-Fabric MDC product documentation. Confirmed Nov. 4, 2026.

[2] "Digital Map Third-Party Device Driver Package Development Guide," Huawei, Issue 01,
Apr. 17, 2023 (EDOC1100300656, no product version stated). Verify in:
2.2 Driver Package Development. Confirmed Oct. 31, 2026.

[3] "iMaster NCE-Fabric MDC Product Documentation," Huawei, V100R025C00, Issue 04, Jun. 30, 2026
(HedEx library EDOC1100509717, login required). Verify in: Digital Map > Security View > Network-Security
Convergence > General Configurations > Preparations > Deploying a GND Package and Uploading the
Mapping File (Table 1). Confirmed Nov. 1, 2026.

[4] `netsecurity_equipment` GND package, version 1.0.96, from
iMasterNCE-Fabric_V100R025C00SPC120_netsecurity_equipment.zip (Huawei software download, iMaster
NCE-Fabric, release 267730047). Verify in:
`plugin/default_pull_input_huawei/collect_config/`. Confirmed Oct. 31, 2026.

[5] "iMaster NCE-Fabric V100R026C00 Digital Map DTRB," Huawei, Jul. 17, 2026 package date
(in the V100R026C00 Digital Map Best Practices package, EDOC1100614770, no issue number). Verify in: DTRB Checklist > Path navigation > Supported device models. The
checklist text refers to V100R024C10. Confirmed Nov. 1, 2026.
