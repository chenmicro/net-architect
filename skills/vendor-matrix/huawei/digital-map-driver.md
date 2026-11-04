# Huawei Digital Map third-party device driver

How to read and develop the driver package for basic collection from third-party devices in
iMaster NCE-Fabric MDC Digital Map. Basic collection is the lower layer: security collection likely
parses the device configuration it collects *inferred*. See
[digital-map.md](digital-map.md#data-sources). A driver package is a Generic NE driver (GND) software
package with subtype `nic`. For CLI collection it is JSON only: the commands to send and the rules to
parse their output [1][2].

Each section compares the Development Guide [1] with the shipped package
`netsecurity_equipment` 1.0.96 [2]. The guide is dated 2023, states no product version, and
has no later issue. The shipped package is newer and is the working reference, so follow it
where they differ.

V100R026C00 preconfigures a GND package for all the models in
[digital-map.md](digital-map.md#supported-third-party-devices), so nothing is imported for them,
and a driver is needed only for other models or versions [3]. The preconfigured packages are not
read here, so 1.0.96 is the only package this file covers [2].

Marked *inferred*: the behavior comes from how the package uses a key, because no cited
document defines it.

## Terms

| Term | Meaning |
|---|---|
| MDC | iMaster NCE-Fabric MDC, the multi-site controller that runs third-party collection |
| Software package | A compressed package for one function. Types include SND, GND, SSP, and MDA [3] |
| Product package | A collection of software packages, handled in a batch [3] |
| SND | Specific NE driver. Likely the package for device capability openness *inferred*. Holds a `.py` file with device type, vendor, and connection data, and a YANG model of device features [3] |
| GND | Generic NE driver. Defines service YANG models, and maps service models to device models [3]. The collection `nic` subtype holds JSON instead [2] |
| SSP | Specific Service plugin. Delivers network-level service configuration. Likely the package for service capability openness *inferred*. Holds a Jinja2 template, a Python mapping script, and a service YANG model [3] |
| NE | Network element, a managed device |
| Driver package | Here, the GND package with `package-subtype` `nic` that runs basic collection [1][2] |
| Basic collection | Device data collected through the driver package |
| Security collection | Security and NAT policies collected by a preset process in Collection Designer, which can build on basic collection |
| Preconfigured package | A GND package already on the MDC for the models listed in [digital-map.md](digital-map.md#supported-third-party-devices) [3]. The standalone `netsecurity_equipment` package, imported by hand, is V100R025C00 only and has no successor in later releases [4] |
| Input plug-in | Sends commands to a device, configured in `collect_config` [1] |
| Parser plug-in | Parses command output, configured in `collect_mapping` [1] |
| Resource type | `resourceType`, the data category, such as `route` [1] |
| Indicator group | `fieldGroup`, a set of related fields, such as `routingTable` [1]. The collection UI shows each one as an indicator [3] |
| Indicator | In the guide, one field in a group, such as `destIp` [1]. In the UI, a whole group [3] |
| Collection item | The Configuration Guide's name for the same UI entry, such as Routing table [5] |
| Item | One `collect_config` entry, which collects one indicator group *inferred* |
| Helper item | An item that collects no data, such as `secondaryAuth` [2] |
| Family | A device subfolder under a vendor: `Firepower` or `FW` [2] |
| `collect_mapping` | Package files that parse device command output [1] |
| `fieldMappings` | Keys inside `collect_config` that map parsed values to later commands [1] |
| SpEL | Spring Expression Language, used in `src` [1] |
| ASC | Signature mode, with a `.asc` file [3] |
| CMS | Signature mode, with `.cms` and `.crl` files [3] |
| CRL | Certificate revocation list |
| SHA256 | Integrity-only mode, with no signature file. Not listed on the current MDC [1][3] |

## Software package layout

The guide's layout [1], labeled against the provided driver `netsecurity_equipment` 1.0.96 [2].
These labels apply to every code block in this file:

- `// ADD`: in the package, not in the guide. The meaning is *inferred*.
- `// NOT USED`: in the guide, not used by the package.
- `// PACKAGE`: the package uses a different name.

```
├─pkg.json
└─nic                            // PACKAGE: nic.zip, with plugin and pipeline at its root
  ├─plugin
  │ ├─default_cli_parse          // PACKAGE: default_cli_parse_huawei
  │ │ ├─YAML file                // NOT USED: the guide requires it with a JAR for a custom parser
  │ │ └─collect_mapping
  │ │   └─Vendor                 // PACKAGE: default_cli_parse_{vendor}
  │ │     ├─Resource name        // PACKAGE: {family} subfolder, only Firepower and FW
  │ │     │ └─{fieldGroup}.json
  │ │     └─{fieldGroup}.json    // ADD: the vendor's other models, no subfolder
  │ └─default_pull_input         // PACKAGE: default_pull_input_huawei
  │   └─collect_config
  │     └─Vendor                 // PACKAGE: default_pull_input_{vendor}
  │       ├─Resource name        // PACKAGE: {family} subfolder, only Firepower and FW
  │       │ └─{fieldGroup}.json
  │       ├─{fieldGroup}.json    // ADD: the vendor's other models, no subfolder
  │       └─*.jar                // ADD: F5 only, with its own .cms and .crl
  └─pipeline/huawei_cli_fabric/support    // ADD: all 7 vendors
    └─{vendor}                   // ADD: lowercase vendor name
      ├─{family}                 // ADD: subfolder, only Firepower and FW
      │ └─{vendor}_{name}.json   // ADD: fields kept for each group
      └─{vendor}_{name}.json     // ADD: the vendor's other models, no subfolder
```

`{family}` is `Firepower` under `cisco` or `FW` under `h3c`. The guide's text gives
`{vendor}/{resource name}/{indicator group}.json`. It does not define resource name, and
these two folders are device families, not resource types. The package is imported with its `.cms` and `.crl` files. `nic.zip` holds 282 files:
279 JSON, plus the JAR with its `.cms` and `.crl` [2].

## JSON file structure

### pkg.json

| Key | Guide [1] | Shipped package [2] |
|---|---|---|
| `name` | Can be changed | `netsecurity_equipment` |
| `version` | Can be changed | `1.0.96` |
| `package-type` | `gnd` | `gnd` |
| `package-subtype` | `nic`, cannot be changed | `nic` |
| `producer` | `nic`, cannot be changed | `huawei`, which differs |
| `nce-min-versions` | `22.0.0` | `22.0.0` |
| `devices` | Vendor, type, and version regex | 9 entries |
| `hooks` | Empty | Empty |

### collect_config

The guide's structure, trimmed from its example [1], labeled against the package [2]:

```jsonc
[{
  "supportVersions": [{"vendor": "HUAWEI", "type": "V1R22C00", "versions": [".*"]}],
  "collectPeriods": ["900000-"],
  "resourceType": "vlan",
  "fieldGroup": "stpVlan",
  "fieldId": [],                     // NOT USED: empty in all 87 uses
  "afterConnection": "afterConnection.charsetSetter",  // ADD: helper to run after login
  "script": [{
    "type": "JSON",                  // ADD value: JAVA, once, for F5 arpTable
                                     // NOT USED value: XML
    "collectMode": "SSH",
    "persistenceType": "TXT",
    "check": "secondaryAuth.secondaryAuth",  // ADD value: {file}.{check id}
    "command": [{
      "name": "display vlan",
      "isPersistence": "false",
      "resultFieldGroup": "vlanInfo",
      "saveRule": "NE",              // NOT USED value: NE. Package uses COLLECTITEM or empty
      "commandCache": [],
      "endPattern": "...",           // ADD: prompt regex, for when the prompt changes
      "duplicate": "true",           // ADD: allows a repeated command
      "collectionName": "vlanInfo",  // ADD: links saved output to a foreach result set
      "timeOut": "5400",             // ADD: command timeout
      "commandIntervalTime": "2000", // ADD: delay between commands
      "anonymization": "false",      // ADD: on H3C configuration commands
      "scriptPath": "com.huawei..."  // ADD: Java class when script.type is JAVA
    }],
    "foreach": [{
      "collection": "vlanInfo",
      "command": [{"name": "display stp vlan {vlanId}", "saveRule": "COLLECTITEM"}],
      "if": [{"test": "", "command": [], "foreach": []}],
      "else": [{"command": [], "foreach": []}]     // NOT USED
    }]
  }],
  "check": [{
    "id": "cpuCheck",
    "command": [],                   // NOT USED: replaced by preChecks
    "condition": {},                 // NOT USED: replaced by preChecks
    "preChecks": [{                  // ADD: ordered commands before collection
      "productVersion": "COMMON",
      "checkHealths": [{
        "name": "show running-config | include username",  // {superPassword} is also usable
        "pattern": "unrecognize_1 || isEmpty_1",  // resultMatches ids
        "opType": "EQ",              // Guide key, here under checkHealths
        "threshold": "",             // Guide key, here under checkHealths
        "breakOnSuccess": "true"     // ends the sequence on a match
      }]
    }],
    "stopOnError": "false"           // ADD
  }],
  "resultMatches": [{                // ADD: named regexes that checks and helpers test
    "id": "unrecognize_1",
    "split": {"value": "\n"},
    "filter": "^\\w(.*)[\\r]?",
    "pattern": ".*Unrecognized command.*"
  }],
  "ActionAfterConnections": [{       // ADD: in helper files, sets the charset
    "id": "charsetSetter",
    "continueWhenFailed": "true",
    "Actions": [{"cmd": "display character-set", "resultMatch": "charsetMatch1(1)",
                 "default": "GBK", "setCharset": "true"}]
  }],
  "resultFieldGroups": [{"id": "vlanInfo", "parseRule": "vlanParseRule", "fieldMapping": "vlanMapping"}],
  "parseRules": [{"id": "vlanParseRule",
                  "rules": [{"id": "r2", "split": "\n", "regex": "^\\s*(\\d+)\\s+.*$", "mode": "LOOPMATCH"}]}],
  "fieldMappings": [{"id": "vlanMapping", "mapping": [{"src": "#r2[0][1]", "target": "vlanId"}]}]
}]
```

Guide meanings that the block does not show [1]:

| Field | Meaning |
|---|---|
| `type`, `versions`, `fieldId`, `persistenceType`, `script.check`, `isPersistence`, `saveRule`, `commandCache`, `foreach`, `if`, `else`, `check` | Optional. The other guide fields are mandatory, except `collectPeriods`, which is unmarked |
| `resultFieldGroup` | Mandatory with `foreach` |
| `resultFieldGroups`, `parseRules`, `fieldMappings` | Mandatory with `check` or `foreach` |
| `script.type` | Selects the executor: `JSON` or `XML` |
| `persistenceType` | Saving type, not used for CLI commands |
| `isPersistence` | Whether the output is stored permanently |
| `commandCache` | Cached indicators passed to the parser plug-in |
| `foreach.command` | Parameters must be targets of the `collection` result set |
| `condition.opType` | `LT`, `GT`, `EQ`, `NEQ` |
| `rules.mode` | `LOOPMATCH` matches many times, `FIRSTMATCH` once |
| `mapping.src` | Source value, in SpEL |

### collect_mapping

The guide's structure, trimmed from its example [1], labeled against the package [2]:

```jsonc
[{
  "supportVersions": [{"vendor": "HUAWEI", "type": "V1R22C00", "versions": [".*"]}],
  "resourceType": "arp",
  "fieldGroup": "vxlan",
  "fieldIds": [],                    // NOT USED
  "command": "display arp",          // ADD value: regex matched against the sent
                                     // command, for example show route .*
  "dataSegmentation": {
    "mode": "regex",                 // NOT USED values: endwith, contain
    "value": "^([^\\s]+) current state\\s*:",
    "separatorRowBelongs": "next"    // NOT USED value: ignore
  },
  "rules": [{
    "id": "r1",
    "split": "\n",
    "regex": "^([1-9]\\d{0,2}(?:\\.\\d{1,3}){3})",
    "mode": "LOOPMATCH",             // ADD value: LOOPMATCHAPPEND, appends lines
    "apendSplit": "",                // ADD: join string for LOOPMATCHAPPEND
    "filter": "\\s*"                 // NOT USED
  }],
  "mapping": [
    {"src": "#r1[#index][1]", "target": "ip",
     "require": true},               // ADD: likely drops a record with no value
    {"src": "rawContent", "target": "content"},       // ADD value: whole output, unparsed
    {"src": "#global['ifName']", "target": "ifName"}, // ADD value: reads commandCache
    {"src": "#messageCompletion(...)", "target": "ifName",
     "formula": "messageCompletion"}  // ADD: helper called from src
  ]
}]
```

Guide meanings that the block does not show [1]:

| Field | Meaning |
|---|---|
| `type`, `versions`, `fieldGroup`, `fieldIds`, `dataSegmentation`, `rules.filter` | Optional |
| `dataSegmentation.mode`, `value`, `separatorRowBelongs` | Mandatory for segmenting |
| `rules.split` | Mandatory when there are rules |
| `rules.filter` | Matches only output that meets this regex |
| `rules.mode` | `FIRSTMATCH` matches once, `LOOPMATCH` matches all |

### pipeline

The guide does not describe these files [1]. Each entry appears to list the fields kept for
one group *inferred*, for example [2]:

```json
[{
  "resourceType": "route",
  "fieldIds": ["vsys", "vpnName", "destMask", "nextHopIP", "destIp", "ifName"],
  "supportVersions": [{"vendor": "CheckPoint", "type": ".*", "versions": [".*"]}],
  "extendProperties": {"group": "routingTable"}
}]
```

One file can hold several groups. `cisco_interface.json` holds three interface groups [2].

## Collector capability

The 2023 guide is the only issue. The package still follows its structure, with some added keys
(see `// ADD` above), and the main change since then is more indicators: 10 groups in the guide
[1], 21 in the package [2], and 26 in the V100R026C00 list. The cost is that no document
defines fields for the newer groups. Groups 7 to 13 and 16 to 19 can be copied from the package,
and groups 22 to 26 have no field source.

Fields below are the union of pipeline `fieldIds` [2].

Each group appears as one indicator in the collection task and its template [5][3]. The
Configuration Guide calls these collection items, and its appendix lists 25 [5][3]. The V100R026C00 MDC indicator
list has 26: the same 25 plus Vlan BD Binding. For all 21 groups in this package, its
`resourceType` and `collectMetricGroup` equal the package `resourceType` and `fieldGroup`, so
`collectMetricGroup` is the group name [2]. The table lists all 26. Groups 22 to 26 have no
item in this package [2]. The UI calls other interface IP addresses Interface extra IP, and on Cisco devices it holds HSRP
virtual IP addresses [3].

Those 5 items exist in the MDC list, so the collector knows them, but this package gives no
device a way to collect them. Their names below come from the V100R026C00 list. Their fields
are not in any cited source. The appendix does not list Vlan BD Binding [3][5]. Adding
one to a driver needs the fields from Huawei. Four database tables are known:
`DCNDeviceReliabilityInterface`, `DCNBgpRouterId`, `DCNOspfRouterId`, and
`DCNDeviceInterfaceExtraIp` [5].

Used for is `enUsage` and Details is `enDetails`, as written in the V100R026C00 list.

| # | Resource type | Group | Collection item | Used for | Details | In guide | Fields |
|---|---|---|---|---|---|---|---|
| 1 | `arp` | `arpTable` | ARP | Path navigation, restore topology | Used for fine-grained path navigation and query of navigation access location on Huawei devices, as well as topology restoration of links between devices and host links. | Yes | `ip`, `vpnName`, `macAddress`, `ifName`, `vlanId`, `ceVlanId`, `arpType` |
| 2 | `configuration` | `currentConfiguration` | Device configuration | Multi-cloud simulation, network security, path navigation | Configuration-based simulation for multi-cloud environments, integrated network security reconstruction of firewall security policies and NAT policies, and precision path navigation for Huawei devices. | Yes | `content` |
| 3 | `route` | `routingTable` | Routing table | Multi-cloud simulation, network security, path navigation | Used for checking local routes published by BGP during multi-cloud simulation configuration, strategy path restoration in network security integration and path navigation. | Yes, without `vsys` | `vsys`, `vpnName`, `rd`, `destMask`, `masklength`, `routeType`, `imTableId`, `from`, `pathId`, `nextHopIP`, `protocol`, `routeFlag`, `cost`, `destIp`, `preference`, `ifName` |
| 4 | `vlanMac` | `vlanDynamicMac` | MAC | Path navigation, restore topology | Used for path navigation query to access location, host link restoration, and link reconstruction between devices based on MAC forwarding table restoration algorithm. | Yes, without `bdid` | `bdid`, `slotId`, `vlanId`, `macAddress`, `ifName` |
| 5 | `lldp` | `lldpNeighbor` | Link table | Multi-cloud simulation, network security, path navigation | The foundational data upon which digital maps and related business functions (including multi-cloud simulation, network security, path navigation, etc.) rely. | Yes, without the two `remoteNe` address fields | `ifName`, `localNeName`, `remoteNeName`, `remoteIfName`, `remoteNeIp`, `remoteNeMac` |
| 6 | `interface` | `interfaceStatistics` | Packet statistics on interfaces | Restore topology | Used for calculating link traffic conditions, and based on port traffic reconstruction algorithm to reconstruct the link between devices. | Yes, without the state fields | `ifName`, `physicalState`, `protocolState`, `receiveByte`, `sendByte`, `receiveDropByte`, `sendDropByte`, `receiveBandwidth`, `sendBandwidth` |
| 7 | `interface` | `interfaceState` | Interface information | Multi-cloud simulation, network security, path navigation | The foundational data upon which digital maps and related business functions (including multi-cloud simulation, network security, path navigation, etc.) rely. | No | `ifName`, `ifIp`, `ifMask`, `macAddress`, `physicalState`, `protocolState` |
| 8 | `interface` | `interfaceVlan` | VLAN allowed by an interface | Path navigation | Used for path navigation to generate third-party device basic forwarding table. | No | `ifName`, `rawVlan`, `vlanBegin`, `vlanEnd` |
| 9 | `interface` | `interfaceVpn` | VPN bound to an interface | Network security, path navigation | Used for creating security zones and one-click restoration of security zones in network security convergence, as well as generating the basic forwarding table for third-party devices through path navigation. | No | `ifName`, `vpn`, `vsys` |
| 10 | `interface` | `interfaceVsys` | vSYS bound to an interface | Network security, path navigation | Used for strategy path restoration and security policy management in network security convergence, as well as generating the basic forwarding table for third-party devices (for firewalls only) through path navigation. | No | `ifName`, `ifIp`, `ifMask`, `physicalState`, `protocolState`, `vsys` |
| 11 | `ethTrunk` | `trunkMember` | Eth-Trunk interface member relationship | Network security, path navigation, restore topology | The foundational data upon which digital maps and related business functions (including multi-cloud simulation, path navigation, restore topology, etc.) rely. | No | `trunkName`, `memberPortName` |
| 12 | `ethTrunk` | `lacpInterface` | LACP | Restore topology | The technology used to restore links between devices that have not enabled LLDP. | No | `trunkName`, `memberPortName`, `localSystemId`, `localPortNo`, `localOperationalKey`, `peerSystemId`, `peerPortNo`, `peerOperationalKey` |
| 13 | `ethTrunk` | `peerLink` | Peer-link | Restore topology | The technology used to restore the link between two M-LAG devices that have not enabled LLDP. | No | `trunkName`, `localSystemId`, `peerSystemId` |
| 14 | `dfsGroupMlag` | `dfsGroupNodeMlag` | M-LAG | Multi-cloud simulation, restore topology | An interface for multi-cloud simulation to determine inter-visit relationships, which belongs to M-LAG, and a topology reconstruction algorithm based on the MAC forwarding table. | Yes, with different fields | `ifName`, `mlagId`, `neIp`, `remoteNeIp`, `vrfName` |
| 15 | `vlan` | `stpVlan` | STP VLAN | Path navigation | Precision Path Navigation for Huawei Devices. | Yes | `vlanId`, `ifName`, `role`, `state`, `neName` |
| 16 | `vlan` | `deviceVlan` | Device VLAN | Restore resource pool | Used for restoring VLAN resource pool. | No | `vlanBegin`, `vlanEnd` |
| 17 | `bd` | `bridgeDomain` | Bridge domain (BD) | Restore resource pool | Used for restoring BD resource pool. | No | `bdId`, `state` |
| 18 | `vni` | `vniInfo` | VNI | Restore resource pool | Used for restoring VNI resource pool. | No | `vniId` |
| 19 | `acl` | `aclRule` | ACL rule group | Restore resource pool | Used for restoring ACL resource pool. | No | `aclName`, `aclType`, `ruleId` |
| 20 | `vxlan` | `vxlanPeer` | VXLAN peer information | Path navigation | Network Path Navigation for VXLAN Protocol Support. | Yes | `vniId`, `destinationIp`, `outVniId`, `sourceIp` |
| 21 | `tunnelInfo` | `vxlanTunnel` | VXLAN tunnel information | Path navigation | Network Path Navigation for VXLAN Protocol Support. | Yes | `tunnelId`, `sourceIp`, `destinationIp`, `state`, `type` |
| 22 | `reliability` | `reliabilityInterface` | HRP interface | Network security | Configuration deployment for Huawei firewall in network security integration. | No |  |
| 23 | `bgpInfo` | `bgpRouterId` | BGP router ID | Multi-cloud simulation | The boundary routing collection function for multi-cloud simulation and BGP RouterID conflict detection during configuration modification. | No |  |
| 24 | `ospfInfo` | `ospfRouterId` | OSPF router ID | Multi-cloud simulation | OSPF Router ID conflict check when modifying configurations for multi-cloud simulation. | No |  |
| 25 | `interface` | `interfaceExtraIp` | Other interface IP addresses | Path navigation | Network Path Navigation for Cisco Devices. | No |  |
| 26 | `vlanBd` | `vlanBDBinding` | Vlan BD Binding | Path navigation | Used for Layer 2 three-segment VXLAN path navigation. | No |  |

The guide spells the M-LAG resource type `dfsgroupmlag`, with `neName` instead of the
package fields, and the package uses `dfsGroupMlag` [1][2].

The package has no firewall policy or NAT group. The only ACL item is for Cisco N9K and N7K [2].
The V100R026C00 indicator list has no such group either.
Firewall policy and NAT come from security collection, with Device configuration as the
listed input. See
[digital-map.md](digital-map.md#data-sources).

### Device mapping list

The guide's list is one sentence: the models support Huawei switches, routers, firewalls,
and LB devices in the NCE-Fabric scenario [1]. The list below comes from the shipped package
[2]. Columns are the group numbers in the table above. Groups 22 to 26 have no item, so they
are left out.

| Vendor / model | 1\* | 2\* | 3\* | 4\* | 5\* | 6\* | 7\* | 8\* | 9\* | 10\* | 11\* | 12\* | 13\* | 14\* | 15\* | 16 | 17 | 18 | 19 | 20\* | 21\* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Check Point |  |  | Y |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Cisco N9K, N7K | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y | Y | Y | Y | Y | Y | Y | Y | Y |  |  |
| Cisco N5K, N3K, other Nexus | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y | Y | Y | Y | Y |  |  |  |  |  |  |
| Cisco WS- | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y | Y |  |  | Y |  |  |  |  |  |  |
| Cisco Catalyst, C35, C45 | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y |  |  |  | Y |  |  |  |  |  |  |
| Cisco ASR 1000 | Y | Y | Y |  | Y | Y | Y | Y | Y |  | Y | Y |  | Y |  |  |  |  |  |  |  |
| Cisco ASR 9000 | Y | Y | Y |  | Y | Y | Y | Y | Y |  | Y | Y |  |  |  |  |  |  |  |  |  |
| Cisco ISR | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y |  |  |  |  |  |  |  |  |  |  |
| Cisco NCS | Y | Y | Y |  |  | Y | Y | Y | Y |  | Y |  |  | Y |  |  |  |  |  |  |  |
| Cisco ASA, Firepower, FP | Y | Y | Y | Y |  | Y | Y | Y |  | Y | Y | Y |  |  |  |  |  |  |  |  |  |
| Cisco FP2130 | Y | Y | Y |  |  | Y | Y | Y |  | Y | Y | Y |  |  |  |  |  |  |  |  |  |
| F5 | Y | Y | Y | Y | Y | Y | Y | Y |  | Y | Y | Y |  |  |  |  |  |  |  |  |  |
| Fortinet | Y | Y | Y | Y |  | Y | Y | Y | Y | Y | Y | Y |  |  |  |  |  |  |  |  |  |
| H3C switches, SR, MSR | Y | Y | Y | Y | Y | Y | Y | Y | Y |  | Y | Y |  |  | Y |  |  |  |  | Y | Y |
| H3C SecPath | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |  |  |  |  |  |  |  |  | Y | Y |
| Hillstone | Y | Y | Y | Y | Y† | Y | Y | Y | Y | Y | Y | Y |  |  |  |  |  |  |  |  |  |
| Palo Alto |  | Y | Y |  |  |  |  |  |  | Y |  |  |  |  |  |  |  |  |  |  |  |

A number marked \* is a group used for path navigation or topology restoration.

† Hillstone `lldpNeighbor` needs 5.5R8 or later [2].

Cisco item rules vary, so its rows are sample strings tested as a full regex match against
every rule: `N9KC93180`, `N5K-C5672`, `WS-C2960X`, `Catalyst 9300`, `ASR1002-X`, `ASR9006`,
`ISR4451-X-4x1GE`, `NCS5504`, `FPR-2140`, `FP2130` [2]. How the MDC matches `type` is an open
item.

The Firepower rule names `Firepower 4100`, `Firepower 9300`, `FP2130`, `ASA5520`, `ASA5545`, and
`ASA 5585Ssp10`, as well as `Firepower.*`, `ASA.*`, and `FP.*` [2]. Its commands use `connect asa`, so
these models appear to run ASA software *inferred*.

V100R026C00 preconfigures a GND package for Firepower2110 Version 6.6.1 and ASAv 9.17(1), and
network-security convergence lists firepower2110 Version 7.1 [3]. These are FTD: the preset
`CiscoFirepower_Policy` process uses the FMC REST API and FTD paths, such as
`/api/fmc_config/v1/domain/` and `/policy/ftdnatpolicies/`. The documentation never says FTD.
The 1.0.96 package here is from V100R025C00 and has no FTD item [2]. The preconfigured package was not
read, so its commands are unknown.

`pkg.json` also names MP, DPtech, A10, Topsec, ZTE, Ruijie, Sangfor, iHorizon, and Juniper in
`description`, but they have no folders or `devices` entries [2].

## Developing a driver

For a device that is not preconfigured, V100R026C00 says to develop a GND package from this guide,
then import and deploy it [3]. Best Practices still has professional services supply an SND package and import it before
collection, and it is out of date on this: the product documentation is correct [3][6]. The MDC describes an SND package as a `.py` file and YANG models,
which is a different format from this `gnd` and `nic` package [2][3].

1. **Requirements**: list the vendor, model, version, and commands [1]. Record commands and
   outputs in the Third-Party Device Data Collection Template [7].
2. **Choose a base**: copy the closest family in the package, because the guide's schema
   lacks keys that real devices need [1][2]. Keep helper items such as the login check.
3. **Write `collect_config`**: one file per `fieldGroup`, with the device's commands. Use
   `foreach` for per-VRF or per-interface commands, and `endPattern` when the prompt changes
   [1][2].
4. **Write `collect_mapping`**: one file per `fieldGroup`, with a `command` regex that matches
   the sent command, and targets from [Collector capability](#collector-capability) [1][2].
5. **Write `pipeline`**: add entries whose `group` matches each `fieldGroup` [2].
6. **Set `supportVersions`** in all three layers, as the package does. The rule
   must match the model set on the MDC [2][5].
7. **Package**: zip `plugin/` and `pipeline/` as `nic.zip`, then zip it with `pkg.json` [1][2].
8. **Sign for the repository mode** in [Import paths](#import-paths) [1].
9. **Import and deploy** under Basic Service > Southbound Open Service > Package Repo >
   Package Management. Success shows Deployed and ACTIVE [3].
10. **Test**: create a collection task, then check the result. The guide uses
    `POST /rest/unicollectmanagerservice/v1/collect-tasks/operate`, and the MDC also offers
    Device Collection > Collection Task List [1][5].

### Import paths

| | Huawei-signed package | Self-developed package |
|---|---|---|
| Signature | Huawei code-signing certificate [2] | Your own, by repository mode |
| Before import | Nothing | Create a repository, then import the public key [3] |
| Public key | Not applicable | Set Provider to the software package provider. The private key is RSA, 3072 to 4096 bits [3] |
| Files, ASC mode | Not applicable | `.zip`, `.asc` [3] |
| Files, CMS mode | `.zip`, `.cms`, `.crl` [2][3] | `.zip`, `.cms`, and optionally `.crl` [3] |

The current MDC lists only ASC and CMS, in Repository Management and in the import dialog [3].
A repository can use both, and a package passes if either check passes [3]. SHA256 appears
only in the 2023 guide's dialog and in Best Practices, which are out of date on this [1][6].

Name and Version together identify a software package [3]. An update uninstalls the original
package and activates the target version [3]. Deployment and update interrupt some services, so
run them off-peak [3]. Limits are 100 MB per software package and 2 MB for `pkg.json` [3].

## Open items

- How `type` is matched: full or partial regex.
- Which rule wins when two packages or items match the same device.
- What `producer` must be for a self-developed package.
- Which signature tool the guide means [1].
- How `preChecks` behaves with `stopOnError` false.
- The fields of groups 22 to 26.
- Which FTD and FMC versions are covered, and whether FTD managed with FDM is supported.

## References

[1] "Digital Map Third-Party Device Driver Package Development Guide," Huawei, Issue 01,
Apr. 17, 2023 (EDOC1100300656, no product version stated). Verify in:
1.2 Main Function; 2.1 to 2.5; 3 Collector Capability Reference. Confirmed Oct. 31, 2026.

[2] `netsecurity_equipment` GND package, version 1.0.96, from
iMasterNCE-Fabric_V100R025C00SPC120_netsecurity_equipment.zip (Huawei software download, iMaster
NCE-Fabric, release 267730047). Verify
in: `pkg.json`; `nic.zip`; `plugin/default_pull_input_huawei/collect_config/`;
`plugin/default_cli_parse_huawei/collect_mapping/`; `pipeline/huawei_cli_fabric/support/`.
Confirmed Oct. 31, 2026.

[3] "Stellar AI Fabric Data Center Network Solution Product Documentation (MDC Scenario),"
Huawei, V100R026C00, Library Version 01, 2026-09-30, HedEx library EDOC1100612446 (verify at
support.huawei.com HedEx, `docid=EDOC1100612446`). Verify in: Documentation Guide > What's New;
Digital Map Usage Guide > General Configurations > Collecting Data > Device Data Collection >
Creating a Collection Task (Table 1, secondary authentication table, indicator figures); Digital
Map Usage Guide > FAQ > How Do I Perform a Switchover Between Distributed and Centralized Data
Collection Modes on a Device? (Appendix); Path Navigation > Basic Navigation Mode > Constraints
and Limitations; Security View > Network-Security Convergence > Limitations and Constraints;
Southbound Open Service > Overview (Capability, Feature Introduction); Package Management >
Package Repository (Repository Management, Package Management, Uploading a Public Key). Same
topics and text as the iMaster NCE-Fabric MDC product documentation. Confirmed Nov. 4, 2026.

[4] "iMaster NCE-Fabric MDC Product Documentation," Huawei, V100R025C00, Issue 04, Jun. 30, 2026
(HedEx library EDOC1100509717, login required). Verify in: Digital Map > Security View > Network-Security
Convergence > General Configurations > Preparations > Deploying a GND Package and Uploading the
Mapping File. Confirmed Oct. 31, 2026.

[5] "iMaster NCE-Fabric V100R026C00 Digital Map Configuration Guide," Huawei, Issue 01,
Sep. 30, 2026 (in the V100R026C00 Digital Map Best Practices package, EDOC1100614770). Verify in: 1.4.2.1 Device Data Collection, Creating a Collection Task; 1.5.8
How Do I Perform a Switchover Between Distributed and Centralized Data Collection Modes on a Device?
(Appendix: Mapping Between Collection Items and Tables). Confirmed Nov. 1, 2026.

[6] "iMaster NCE-Fabric V100R026C00 Digital Map Best Practices," Huawei, Issue 01,
Sep. 30, 2026 (EDOC1100614770). Verify in: 4.1 Information Survey; 7 Obtaining Driver Packages and
Scripts; 8.3.1 Deploying Third-Party Device SND Packages. Confirmed Nov. 1, 2026.

[7] "iMaster NCE-Fabric Digital Map Third-Party Device Data Collection Template," Huawei, 05
Collection Template (in the V100R026C00 Digital Map Best Practices package, EDOC1100614770). Verify in: Description. Confirmed Nov. 1, 2026.
