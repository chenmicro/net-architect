# ACI to Huawei CloudFabric Migration — Pre-Design Questionnaire

**Scope: designing the questionnaire a customer fills in before the HLD/LLD of a Cisco ACI
to Huawei CloudFabric migration.** This file sets out how to build that questionnaire. The
fabrics themselves are covered in [aci.md](../vendor-matrix/cisco/aci.md) and
[cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md).

## Composes

1. [cisco/aci.md](../vendor-matrix/cisco/aci.md#nx-os-style-cli-configuration-mode-removed-in-612):
   what the APIC configuration export carries and what it doesn't. This decides which
   questions you can drop.
2. [huawei/cloudfabric.md](../vendor-matrix/huawei/cloudfabric.md): the target model. Only
   ask about source features that need a decision on the target.
3. The Huawei migration guide's survey chapters [1]. Use them as a checklist to rule on,
   not as a list of questions to copy (see [Ruling on the Huawei checklist](#ruling-on-the-huawei-checklist)).

## Structure

- **Section 0, known information:** list what you already know before asking anything.
  Use two tables:
  - project scope;
  - the source fabric today.

  Each row states one fact and has a "Confirm (Y/N) or correction" cell. When you already
  know a fact, put it here instead of asking for it, and don't repeat it elsewhere.
- **Four level-1 categories**, in this order:
  1. physical, at cabinet level;
  2. network configuration;
  3. business traffic;
  4. O&M.
- **Network configuration, split by owning team:**
  - the ACI fabric (network team);
  - firewalls (security team);
  - load balancers (IT team).

  Firewall and load-balancer items cover only how those devices connect to the fabric and
  how they route.
- **Order inside every section:**
  1. inventory and versions;
  2. the export request;
  3. "answer only if the export is not available" fallback items;
  4. "answer in all cases" items.
- **Numbering:** use one scheme. Sections are `1.1`, and every item, question or table, is
  `1.1.1`. Don't number questions and tables separately.

## Writing the items

- **Every item must feed the HLD, the LLD or post-migration validation.** Don't add
  "why we ask" text.
- **Write each item as an instruction to the person filling it in:** "Collect …",
  "Attach …", "Export …", "Fill in …". Never write "Send us …". The completed document
  comes back to you, so each item has to say what to do. The only place you speak as the
  recipient is section 0 ("We already hold …").
- **Prefer tick boxes to free text.** A table has a title (the item text) and one to three
  empty rows.
- **Don't ask for anything the export already contains.** For example, ports, optics, node
  names and VRF-to-L3Out bindings all come from the export.
- **Avoid ACI terms in the business-traffic category.** That category is answered by
  application owners, so say "IP subnet", not "BD".
- **When a format doesn't map one-to-one onto Huawei's, leave the option open** (flow
  export is one example). The customer states what they use instead of picking from your
  list.
- **Build the business traffic paths so they can double as the validation baseline.** The
  migration test cases are taken from them.

## ACI-specific collection

- **On APIC 6.1(2) or later, ask for the JSON configuration export.** The NX-OS-style
  configuration mode and `show running-config` were removed in that release (see
  [aci.md](../vendor-matrix/cisco/aci.md#nx-os-style-cli-configuration-mode-removed-in-612)).
  Huawei's eDeskPro ACI collection template still sends `show running-config` whatever the
  APIC release, so on these releases its output has to come from the export [2].
- **Ask for raw command output only where an analyzer imports it verbatim, and only for
  data the export doesn't hold.** That covers run-time state, such as running versions and
  controller state, and commands that take arguments, such as `show vpc map`. Ask for each
  as an attachment, in one line with tick boxes.
- **The export holds configuration, not outcomes.** Which egress is active at the moment
  is routing state, so check it with a test case rather than a question.

## Ruling on the Huawei checklist

Huawei's guide lists nine dimensions of information to collect (networking, device model,
configuration file, software version, service entry, routing protocol, service model,
access side, performance), plus two service-analysis tables (protocol interconnection,
and topology, traffic model and service access) [1]. Rule on each candidate item:

| Ruling | When |
|---|---|
| Add | It changes the design and nothing else supplies it, for example the software version and HA protocol of reused firewalls and load balancers |
| Add in narrowed form | Only part of it matters, for example routing protocols other than BGP/OSPF only where the fabric peers with the core |
| Move to section 0 | You already know the answer, for example IPv4 only, no multicast, or no VMM integration |
| Drop | The export answers it, it doesn't apply to the source (e.g. FabricPath in ACI), or it's too vague to answer |

Keep the rulings in a separate gap-analysis note next to the questionnaire, so they don't
have to be argued again.

The guide's interconnection table marks several protocols as not interworking or not
recommended for interconnection during a migration. Each of these is worth a question,
because the answer changes the cut-over design [1]:

- **EIGRP:** not supported. Huawei recommends moving to OSPF or BGP before
  interconnecting.
- **Gateway redundancy:** Huawei doesn't interconnect HSRP and VRRP. Its ACI procedure
  routes between the fabrics instead, over an interconnection subnet with static routes.
  The new side points at the legacy HSRP virtual IP, and each subnet's gateway moves by
  swapping the static routes. So collect the interconnection VLAN and subnet, and the
  legacy gateway's virtual IP and protocol.
- **STP on the DCI devices between the legacy and new networks:** not recommended.
- **VXLAN or FabricPath interconnection:** not recommended. Use a hand-off if it is
  needed.

## Check before issuing

The Huawei survey chapters don't cover these, so check them separately:

- MTU and jumbo frames per host, per appliance and per DCI path. VXLAN adds 50 bytes.
- The distance and one-way latency between the DCs.
- How long the old fabric must stay ready for rollback after a batch moves.
- Licence quantities (controller, Digital Map) and which party supplies them.

## References

[1] "Best Practices of Migrating a Data Center Network to an SDN Network," Huawei,
EDOC1100299470, updated Apr. 21, 2025 (outside a HedEx library, no issue number).
Verify in: Data Center Network Migration > Migration
Preparation > Live Network Information Collection (the information-dimension table); >
Live Network Service Analysis (Table 1, Network protocol interconnection; Table 2);
Data Center Network Migration > Network Migration > Scenario 6: ACI > Manual Migration >
Step 4: Layer 3 Network Migration > Layer 3 Network Migration (static-route
interconnection and gateway move). Confirmed Nov. 13, 2026 against a local CHM copy.

[2] eDeskPro V100R025C10SPC310 (windows-x64), Huawei software package. The ACI collection
template is in `product/CollectItem/ipmaster/IP/IPMaster.xml` (`CollectItemSet
ACI_Info_IpMaster`, 29 commands under `ProductVersion name="IP_common"`), and the only APIC
entry in `config/deviceversion/SupportVersion.xml` is `version="common"`. Checked
Nov. 8, 2026 against the extracted package.
