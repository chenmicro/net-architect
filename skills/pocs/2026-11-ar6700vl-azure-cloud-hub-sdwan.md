# POC: AR6700V-L as an Azure cloud hub in a partner-hosted Secure SD-WAN

> Based on product documentation, not lab-tested.

> Deployment plan, based on the **Secure SD-WAN Portfolio Solution V100R025C00** guide [1]
> (versions: see References). **TBD** marks a value still to obtain or decide, a task, not an oversight.

## Background

- **Date**: 2026-11
- **Why it matters**: AR+USG mixing is a Portfolio-solution scenario only [1], and the
  AR6700V-L's Azure mechanics come from a separate guide [2]; neither answers this alone.
- **Scope**: one AR6700V-L in Azure as an additional hub site for cloud
  access, one USG at head office acting as physical hub and RR, and **two** USG branches as
  spokes — all four sites deployed in this delivery, through all five phases of the solution's
  deployment process [1]. Two branches are enough to exercise every path: branch→HQ over MPLS,
  branch→branch through the HQ hub, branch→Azure direct over Internet, and branch→Azure
  fallback through HQ (the tromboned path, tested rather than assumed). Out of scope: the remaining production branches (they repeat the
  same two-site pattern), ExpressRoute or any private leg to Azure, and second-link redundancy
  at the Azure hub.
- **Design decisions**:

| Area | Decision | Why |
|---|---|---|
| Azure region | North Europe (`northeurope`) | Within the AR6700V-L's supported regions [2] |
| RR | HQ USG is the RR (`Gateway+RR`); the AR6700V-L is a hub with role `Gateway` [1][2] | The vCPE has one Internet link, not reliable enough for the role every tunnel depends on |
| MSP RR | None; every device is added at tenant level | Every device, the RR included, is the customer's |
| Cloud-site gateways | One vCPE, no interlink | Deviation from the guide's dual-gateway hub [1]: no in-cloud redundancy |
| Tunnel mode | GRE [1] | Required for BGP-EVPN, ZTP and the overlay services; IPsec VPN mode is static point-to-point only, and the mode cannot change once ARs are added [3] |
| Encryption | IPsec on | Security requirement; GRE rides inside IPsec |
| NAT traversal | On at the vCPE's WAN link only; off at the USG sites | Azure maps the public IP 1:1 to the NIC [4], so the vCPE sees only its private IP. Only an RR role can configure a public IP [2], so the vCPE learns it through STUN from the HQ RR and advertises it [5]. The guide's example shows the toggle off [2] |
| IP version | IPv4 only | No underlay or overlay IPv6 on a public-cloud AR6700V-L [3] |
| Security | The vCPE routes; the USGs secure | The vCPE has no IPS/AV; Azure's platform security covers the cloud side |
| VN | One VN, all four sites | The customer has a single LAN network |
| Path to Azure | Routing, no steering policy | The vCPE's only tunnels are on `Internet`, and MPLS-A and MPLS-B are separate routing domains [5], so branch→Azure takes the Internet tunnel while everything else stays MPLS-first |
| Hub priority | AR6700V-L at the default, below the USG hub [1] | Keeps transit traffic such as branch↔branch on the USG; the documentation does not define the ranking further, so TC-05 verifies it |
| Internet breakout | USG sites only | A public-cloud AR6700V-L has no local Internet access [1] |
| vnet | The customer's existing vnet and subnets | A new vnet is not allowed; the tool's default would create `192.168.0.0/16` [2] |

- **Scenario**: none. This record tests a topology and collects its inputs; it does not
  prescribe an architecture for other customers.

## Test environment

### Topology

[Figure 1 — POC topology: three USG sites, the AR6700V-L hub in Azure, and the partner-hosted controller](2026-11-ar6700vl-azure-cloud-hub-sdwan-fig1.drawio)

### Device list

| Role | Vendor | Model | Software version |
|---|---|---|---|
| Cloud hub vCPE — NCE role `Gateway` | Huawei | AR6700V-L, **8 vCPU** model on Azure `Standard_F8s_v2` (16 GB, 4 vNICs) | V600R025C00 [2] |
| Physical hub + RR — NCE role `Gateway+RR` | Huawei | **USG6600F** | V600R025C00 [1] |
| Branch spokes (×2) — NCE role `Gateway` | Huawei | **USG6500F** — **no more than 500 Mbit/s per branch** | V600R025C00 [1] |
| Controller | Huawei | iMaster NCE-Campus, partner-hosted, **MSP mode** | V300R025C00 |
| Deployment host | | Linux VM or server, x86 or ARM; Ubuntu 22.04+/openSUSE 15.6+/CentOS Stream 9+/openEuler 22.03+, glibc ≥ 2.34, OpenSSL ≥ 1.1.1m; ≥1 vCPU, ≥150 MB free, ≥3 GB free disk, public IP, DNS, outbound TCP 443 to `management.azure.com` | [2] |
| Deployment tool | Huawei | `AR6700V-L_V600R025C00SPC100_deploy-tool` (x86_64 or AArch64), from the same release package | [2] |
| Azure image | Microsoft | Image built from the AR6700V-L VHD (package `AR6700V-L_V600R025C00SPC100_AZUREX8664.tar.gz`, already in hand); settings in TC-01 step 1 | [2] |

Sizing: `Standard_F8s_v2` gives 4 vNICs [6], so a second WAN link needs no flavour change; Azure
flavours are F4s_v2/F8s_v2/F16s_v2 only [2]. The 500 Mbit/s branch edge, not the hub, limits WAN.

### Network plan

Laid out like the solution's Data Plan [1]. Source column: **customer** (the enterprise: Azure
subscription, HQ and branches), **partner** (the MSP hosting NCE-Campus), **OEM** (the team
delivering the AR6700V-L), **joint** (decided together), **known** (fixed before planning; not
to collect).

#### AR6700V-L in Azure (TC-01)

Everything the deployment tool needs to build the vCPE. Most of it is the customer's: the
subscription, the existing vnet, and the security-group approvals. The Azure column of the
Sites table is filled from this build (TC-01 step 9).

##### Azure platform

| Item | Value | Source |
|---|---|---|
| Region: Azure North Europe (Ireland); location string `northeurope` | `northeurope` | known |
| `Standard_F8s_v2` available to the subscription in North Europe | TBD | customer |
| Tenant (directory) ID | TBD | customer |
| Application (client) ID + client secret (expiry recorded) | TBD | customer |
| Subscription ID | TBD | customer |
| Contributor at subscription **and** at resource group | TBD | customer |
| Resource group name | TBD | customer |
| `Standard_FSv2` family vCPU quota in North Europe, plus public-IP and NIC quota | TBD | customer |
| `Microsoft.Compute`, `Microsoft.Network`, `Microsoft.Storage`, `Microsoft.Quota` resource providers registered | TBD | customer |
| Availability zone (only if their landing zone pins one) | TBD | customer |
| Storage account + container for the VHD upload | TBD | customer |
| Image file name: the file placed in `/home/deploytool/azure`; `image` in `deploy.json` is exactly the same name | TBD | OEM |
| Deployment host (spec in the Device list): customer machine or a jump VM in Azure | TBD | customer |
| Who uploads the VHD, and from where | TBD | joint |
| Change window + named operator for the deployment run | TBD | customer |

##### Existing vnet and routing (also TC-05)

The vCPE uses the existing vnet and two customer subnets, so the tool creates none of its own
[2].

| Item | Value | Source |
|---|---|---|
| Existing vnet name + ID (UUID) + CIDR | TBD | customer |
| WAN subnet (`wan1`, GE0/0/0): name, CIDR (/29 minimum, Azure's smallest [7]), gateway — dedicated to the vCPE's WAN NIC, no route table pointing at the vCPE | TBD | customer |
| WAN static public IP: resource name (`publicIpId`) and address | TBD | customer |
| LAN subnet (`lan1`, GE0/0/1): name, CIDR, gateway — an existing subnet; its hosts reach the vCPE's LAN IP directly | TBD | customer |
| NSG names for the WAN and LAN subnets or NICs (`securityGroup`) | TBD | customer |
| Ranges that must not be used (besides `192.168.233.0/24`, reserved by the system [2]) | TBD | customer |
| Subnets the vCPE serves: every Azure subnet in the IP subnets row (Sites, devices, and links), each associated with the route table | TBD | customer |
| Route-table routes: one per HQ and branch subnet (IP subnets row), next hop = the vCPE LAN IP; within Azure's 1,000 routes per table [8]. Not `0.0.0.0/0`: workloads keep their own Internet path | design |
| Route-table change approver and rollback plan | TBD | customer |

##### Ports and security groups

The WAN NSG allows at least the inbound ports the Azure guide lists for SD-WAN, which are also
the deployment tool's default `sg-wan1` [2].

**Control and management plane**

| Protocol | Port | Purpose | Confirmed |
|---|---|---|---|
| UDP in | 55100 | DTLS control channel with the HQ RR; must equal the overlay's DTLS port [2][9] | [2][9] |
| UDP in | 3478 | STUN, so the vCPE learns its public IP from the HQ RR [5][9] | [2][5][9] |
| UDP in | 4500 | STUN hole punching with the HQ RR [9]; the data channel uses it when NAT-traversed [5] | [2][5][9] |
| UDP in | 123 | NTP with the HQ RR | [2] |
| TCP in | 22 | SSH; source limited to the NCE southbound address and the SSH login hosts [2] | [2] |
| ICMPv4 in | all | Reachability and PMTU | [2] |
| TCP out | 10020 | Registration to the partner NCE; call-home [2] | TBD |
| TCP out | 443 | Deployment host → `management.azure.com` | TBD |

**Data plane**

| Protocol | Port | Purpose | Confirmed |
|---|---|---|---|
| IP 50 (ESP) in | — | Beyond the guide's set: the data channel if it runs without NAT traversal; Azure passes ESP to a VM's public IP [4]. Kept until TC-05 step 9 shows which form the channel takes [5][10] | [4][5][10] |

The Huawei Cloud procedure lists the same inbound set [10]. The guides call it an example: a
changed default port changes the rule.
No GRE rule (GRE rides inside IPsec) and no local-breakout ports.

| Item | Value | Source |
|---|---|---|
| WAN NSG carries the rules above (new NSG, or amendment to an existing one) | TBD | customer |
| NSGs of the LAN subnet and of every served subnet allow traffic to and from the HQ and branch prefixes | TBD | customer |
| DTLS port configured for the overlay (must equal 55100 above) | TBD | partner |
| STUN server enabled on the HQ RR (disabled by default; port 3478 [5]), and UDP 3478 allowed to it on the `Internet` link | TBD | partner + customer |
| Data-channel form, UDP 4500 or ESP: expected to depend on the NAT type the vCPE's STUN client detects; the Communication Matrix [9] has no data-channel row. Confirmed in TC-05 step 9; the rule that carries nothing is then removed | TC-05 | OEM |

##### Device identity and certificates

| Item | Value | Source |
|---|---|---|
| AR6700V-L ESN (10–40 alphanumerics, unique; recommended 30 chars: `0588038XJR` + `YYYYMMDD` + `HHMMSS` + 6 random digits) | TBD | OEM |
| NCE device-auth certificate issuer: Huawei or third party | TBD | partner |
| CA certificate / device certificate / private key / key password (PEM, DER or PKCS#12; RSA-SHA2-256/512, key ≥3072 bits; filename <50 chars, no spaces) — only if loaded at deploy time | TBD | partner or vendor |

#### Controller and tenant (TC-02)

| Item | Value | Source |
|---|---|---|
| Southbound IP:port (default 10020) — reachable from Azure over the Internet, and from every site | TBD | partner |
| Private southbound address reachable over **both** MPLS networks (MPLS links register through `Private Default South Access`) | TBD | partner |
| Northbound URL + the customer's tenant name | TBD | partner |
| Tenant-administrator accounts for the named engineers | TBD | partner → customer |
| **Tunnel mode = GRE**, set before any AR is added | TBD | partner |
| Device administrator password set at first tenant login — holder only; not recorded here | TBD | customer |

#### Global parameters (TC-03)

| Item | Value | Source |
|---|---|---|
| RR source | Tenant | [1] |
| Transport networks | `MPLS-A`, `MPLS-B`, `Internet` | design |
| Routing domains | MPLS-A and MPLS-B each in its **own** domain, both separate from Internet — the two MPLS networks come from two ISPs and cannot interconnect, and only carrier networks that can communicate share a domain [5]. Tunnels therefore form MPLS-A↔MPLS-A and MPLS-B↔MPLS-B only | customer (interconnect answer); design |
| IPsec encryption | On | design |
| Email-based deployment: URL encryption key (8–12 letters and digits) and web login — holder only; not recorded here | TBD | partner |
| NTP: time zone, and the external NTP server for the HQ RR (reachable from the controller and the CPEs) | TBD | customer |
| Tenant BGP AS number — unique per tenant, cannot be changed later | TBD | partner |
| IPv4 pool for tunnel, interlink and CPE addresses — must not overlap any site or Azure range | TBD | joint |
| Collection: application traffic, application quality, WAN link traffic | On | [1] |
| SAC: application identification, FPI, IP-based application identification, scope All | On | [1] |

#### Sites, devices, and links (TC-03, TC-04)

| Field | HQ | Branch 1 | Branch 2 | Azure |
|---|---|---|---|---|
| Site name | TBD | TBD | TBD | TBD |
| Device name | TBD | TBD | TBD | TBD |
| RR site | Yes | No | No | No |
| ESN | ESN-free deployment [1] | ESN-free deployment [1] | ESN-free deployment [1] | agreed ESN (Device identity) |
| `Internet` link: interface, IPv4/mask, gateway, up/down Mbit/s | TBD — **static public IP**: the vCPE and the spokes reach the RR here | TBD | TBD | GE0/0/0; private and public IP from TC-01 (step 9); up/down no higher than the public-IP bandwidth [2] |
| `MPLS-A` link: carrier, interface, IPv4/mask, gateway, up/down Mbit/s | TBD | TBD | TBD | — |
| `MPLS-B` link: carrier, interface, IPv4/mask, gateway, up/down Mbit/s | TBD | TBD | TBD | — |
| URL-based deployment link (one per site) — the solution deploys over the highest-priority link, MPLS before Internet [1] | `MPLS-A` | `MPLS-A` | `MPLS-A` | `Internet` |
| NTP server | external (Global parameters) | RR site | RR site | RR site |
| LAN interface + IPv4/mask (in the single VN) | TBD | TBD | TBD | GE0/0/1; LAN subnet (Existing vnet) |
| IP subnets (CIDR), all of them — one or more per site | TBD | TBD | TBD | LAN subnet + every other Azure subnet the sites reach |
| Onsite deployment: method (email / ZTP file) and onsite engineer | TBD | TBD | TBD | — (deployment tool) |
| Test host IP for the path checks | TBD | TBD | TBD | TBD |

Source: customer, except site and device names (joint). Link roles are all `Active`, interface
protocol IPoE, addressing static [1]. Southbound access service per link: MPLS links
`Private Default South Access` (priority High), Internet `Public Default South Access` (Medium)
[1].

**IP subnets.** Every subnet at each site, one or more per site. Each site advertises all of its
subnets to the RR [3]; Azure needs a route for each HQ and branch subnet, and the vCPE a static
route for each Azure subnet other than its LAN subnet (TC-05 steps 5–6). A subnet left out has
no path. None may overlap another site's subnet, the vnet, `192.168.233.0/24` (reserved by the
AR6700V-L [2]) or the tunnel/interlink pool.

#### Overlay and Internet access (TC-05, TC-06)

| Item | Value | Source |
|---|---|---|
| VN name (one VN, all four sites) | TBD | joint |
| Topology | Hub-Spoke, Simple mode, branch interconnection on; hubs = HQ USG and AR6700V-L, the AR6700V-L at its default priority below the USG; spokes = branches | design [1] |
| Internet egress at the USG sites | local breakout by default, centralized at HQ as backup [1] | design |
| Centralized Internet gateway | HQ USG | design |

#### Application experience (TC-07)

| Item | Value | Source |
|---|---|---|
| Applications to steer, guarantee or optimise: names, and whether predefined or customized | TBD | customer |
| Per application: primary transport network, switchover indicator (Voice / Real-Time Video / Low Latency Data / Bulk Data or custom), guaranteed bandwidth | TBD | joint |
| USG signature-database update path (online through the NCE signature server, or offline); also used in TC-08 | TBD | partner |

#### Network security (TC-08)

| Item | Value | Source |
|---|---|---|
| Security policies for the VN: interzones, user-to-Internet and Internet-to-user rules, USG security profiles (antivirus, IPS, URL filtering, file blocking) | TBD | customer |
| ACL policy on the AR6700V-L (overlay or underlay) — only if required | TBD | customer |
| SSL-encrypted traffic detection on the USGs — yes / no | TBD | customer |

## Test cases

Eight procedures, following the phases of the solution's deployment process [1]. Every step
names who performs it, so the procedures can be walked through with the customer beforehand.
Configure services on the controller only: the same service also configured on a device's CLI
can conflict and stop offline configuration from being delivered [1].

Order. The solution deploys the AR6700V-L after the USG sites [1]; this record builds the VM
first, because it needs the most cooperation between the customer and the OEM, and the Azure
guide also deploys the VM before configuring iMaster NCE-Campus [2]. After that, the only hard
order is that the HQ USG (hub + RR) is online before the other sites need it, as their NTP
source and RR [1]; TC-03 and TC-04 can run in either order.

### TC-01: Install the AR6700V-L in Azure

**Objective**: the AR6700V-L runs in the customer's existing North Europe vnet, built by the
deployment tool, with its WAN and LAN addresses recorded for TC-04. The solution defers
AR6700V-L deployment to its device documentation [1]; the steps below follow the Azure
deployment guide [2].

**Prerequisites**: the Azure platform, Existing vnet, Ports and Device identity tables are
complete; the partner's southbound IP is known (Controller and tenant table); the
image file name is known.

**Procedure**:

1. *(customer, Azure portal)* Build the image — the package is already in hand, so this is the
   upload step, and it is the slowest in wall-clock time.
   1. Decompress `AR6700V-L_V600R025C00SPC100_AZUREX8664.tar.gz` to obtain
      `AR6700V-L_V600R025C00SPC100_AZUREX8664.vhd`.
   2. Create a storage account: subscription, resource group, name, **Region = North Europe**,
      performance **Standard**, redundancy **GRS** with read access (LRS if GRS is unavailable
      in the region).
   3. Copy the access key: storage account → **Security + networking → Access keys → Show**.
   4. Create a container: **Data storage → Containers → Add container** (e.g. `ar6700v-l`).
   5. Upload the VHD with Azure Storage Explorer: connect using account name + key, storage
      domain `Azure (core.windows.net)`, then container → **Upload → Upload files**.
   6. Create the image: **All services → Images → Create** with OS type **Linux**, VM
      generation **Gen 1**, storage blob = the uploaded VHD, account type **Standard HDD**,
      host caching **Read/write**, same region and resource group.
2. *(customer, Entra)* Create the application and grant it access.
   1. **Microsoft Entra ID → App registrations → New registration**; copy the **Application
      (client) ID** and **Directory (tenant) ID**.
   2. **Certificates & secrets → New client secret**; set the expiry; copy the secret **value**
      immediately — it cannot be read again.
   3. **Subscription → Access control (IAM) → Add role assignment**, tab **Privileged
      administrator roles**, role **Contributor**, member = the application.
   4. Repeat the same assignment on the **resource group**.
3. *(customer)* Confirm the platform headroom before the window: `Standard_F8s_v2` available
   (`az vm list-skus --location northeurope --size Standard_F8s_v2`, or the portal **Create VM →
   Size** list, where a greyed-out size is sold out [2, `azure.check.0005`]; Microsoft publishes
   the size's specs [6] but no per-region availability); FSv2-family vCPU, public-IP and NIC
   quota in North Europe; `Microsoft.Compute`, `Microsoft.Network`, `Microsoft.Storage` and
   `Microsoft.Quota` resource providers registered.
4. *(customer with OEM guidance, Linux host)* Install the deployment tool.
   1. `mkdir -p /home/deploytool`, upload the package for the host architecture
      (`..._deploy-tool_X8664.tar.gz` or `..._AArch64.tar.gz`) with SFTP.
   2. `cd /home/deploytool && tar -zxvf AR6700V-L_V600R025C00SPC100_deploy-tool_<arch>.tar.gz`
   3. SUSE / CentOS / openEuler:
      `rpm -ivh AR6700V-L_V600R025C00_deploy-tool-25.0.0-001.x86_64.rpm --force`
      (or `.aarch64.rpm`); Ubuntu:
      `dpkg -i AR6700V-L_V600R025C00_deploy-tool-25.0.0-001.amd64.deb`
      (or `.arm64.deb`). Note the package name drops the `SPC100` that is in the tarball name.
   4. Upload the image file to `/home/deploytool/azure` with SFTP. Its file name is the one
      `image` in `deploy.json` must match exactly (step 6).
5. *(optional — customer with OEM guidance)* If certificates are already obtained, upload `Huawei_Equipment_CA.cer`,
   `AR6700V-L.pem` and `private.pem` to `/home/deploytool/azure/single`. The tool then loads them
   and sends the registration request itself after deployment.
6. *(customer with OEM guidance)* Edit `/home/deploytool/azure/single/deploy.json` as below,
   with the values from the Network plan tables. The image file sits in `/home/deploytool/azure`,
   and `image` is exactly its file name. `<…>` marks a value to fill; anything without a
   default and without a value stops the deployment [2].

   ```javascript
   {
       "provider": "azure",
       "account": {                       // from the app registration (step 2) and the Azure platform table
           "clientId": "<application (client) ID>",
           "tenantId": "<directory (tenant) ID>",
           "subscriptionId": "<subscription ID>",
           "resourceGroup": "<resource group name>"
       },
       "location": "northeurope",
       "image": "<image file name>",   // exactly the file name in /home/deploytool/azure
       "instanceType": "Standard_F8s_v2", // set explicitly, although it is also the default
       "esn": "<agreed ESN>",
       // "cert" stays commented out unless the certificates are loaded at deploy time (step 5)
       /* "cert": {
           "ca-cert": "/home/deploytool/azure/single/Huawei_Equipment_CA.cer",
           "local-cert": "/home/deploytool/azure/single/AR6700V-L.pem",
           "private-key": "/home/deploytool/azure/single/private.pem"
       }, */
       "vpc": {                           // required: without it the tool creates a new 192.168.0.0/16 vnet [2]
           "vpcId": "<existing vnet ID (UUID)>" // vpcName also works; if both are given, the ID wins [2]
       },
       "networkInterfaces": {
           "number": 2,                   // numbered in list order: wan1 = GE0/0/0, lan1 = GE0/0/1 [2]
           "interface": [                 // interfaceType: set for all interfaces or for none [2]
               {
                   "interfaceType": "wan1",
                   "subnet": "<WAN subnet name>",
                   "securityGroup": "<WAN NSG name>",
                   "publicIptype": "Static",
                   "publicIpId": "<WAN public IP name>" // the tool attaches a public IP to wan1 only; naming it fixes the address [2]
               },
               {
                   "interfaceType": "lan1",
                   "subnet": "<existing LAN subnet name>",
                   "securityGroup": "<LAN NSG name>"
               }
           ]
       },
       "controller": {                    // port (10020) and vpn-instance (underlay_1) left at their defaults [2]
           "controllerIP": "<partner NCE southbound IP>"
       }
       // "az" left out, so Azure picks the zone; add "az": <n> only if the landing zone pins one [2]
   }
   ```

7. *(customer with OEM guidance)* Run `deploy_tool deploy`. It asks, in order: the private-key password (only if
   certificates are configured), the client secret, and an admin password for the VM
   (12–72 characters, at least three of lowercase/uppercase/digit/special — used only during
   deployment). Then it prints the effective configuration and asks
   `Do you want to continue?(Y/N): Y`.
8. *(customer with OEM guidance)* Watch the stages complete: VPC → security group → subnet → public IP → network
   interface → user data → AR6700V-L. Expect roughly 8 minutes; the guide's example run takes
   20:10:40 → 20:18:40. On **Success**, back up `deploy.json` and the generated
   `deployed-resources-AR6700V-L-<timestamp>.json` to the local PC — they are the record of
   every object created.
9. *(customer, Azure portal)* Record the addresses — **VM → Networking → Network settings**:
   `eni-wan1-<timestamp>` private IP and its public IP, and `eni-lan1-<timestamp>` private IP —
   into the Azure column of the Sites table.

**Expected result**: the tool's result table shows `Success`; VM Running; console login works;
the `deployed-resources` file exists; **no new `192.168.0.0/16` vnet** exists, because an
existing one was named; the WAN NIC holds the static public IP and the LAN NIC the LAN address.
The device is not yet online in NCE — its site, device and WAN link are created in TC-04.

**If it fails**: the tool prints an errno, and the guide's error-code list maps directly —
`azure.check.0002` invalid credential, `0003` invalid subscription, `0004` invalid resource
group, `0005` flavour unknown or sold out in the region/AZ, `0006` insufficient quota,
`0007`/`0009` invalid vnet/subnet, `0010` invalid security group, `0011` invalid public IP,
`0014` NIC count above the flavour limit, `0017` `Microsoft.Quota` not registered [2]. At the
failure prompt, `Y` destroys what was created and `N` retains it for reuse on the next run —
prefer `N` when only a parameter was wrong.

### TC-02: NCE pre-configurations

**Objective**: the customer's tenant exists on the partner's controller in the view and tunnel
mode this scenario requires.

**Prerequisites**: the Controller and tenant table is complete.

**Procedure**:

1. *(partner, system administrator)* Confirm the system-level pre-configuration: the MSP and its
   MSP administrator exist, and the southbound access IP addresses are set. A changed primary
   southbound IP applies only to devices added afterwards and must be in place before any site is
   activated [1].
2. *(partner, MSP administrator)* Create the customer's tenant and its tenant-administrator
   accounts.
3. *(customer, tenant administrator)* First login: change the password, set the device
   administrator password (it takes effect on every device that comes online at a new site),
   select **LAN-WAN Convergence** and click **Start** [1].
4. *(partner or customer, tenant administrator)* Set the tunnel mode to **GRE** [1]. The mode
   cannot be changed once a site contains ARs [3].

**Expected result**: tenant login lands in the LAN-WAN Convergence view; tunnel mode shows GRE.

**If it fails**:

### TC-03: Deploy the USG sites

**Objective**: HQ (`Gateway+RR`) and both branches (`Gateway`) are online on the controller with
all three WAN links, following the solution's deployment configuration [1].

**Prerequisites**: TC-02 complete; Global parameters and the HQ/branch columns of the Sites table
complete; USGs installed and cabled at each site.

**Procedure**:

1. *(tenant administrator)* Global parameters — **Deploy > SD-WAN > Global Configuration**:
   - **Physical Network**: RR source **Tenant**; routing domains and transport networks as
     planned; IPsec encryption on; Device Activation Security — encryption key and web login (both
     needed for email-based deployment); NTP time zone and the external NTP server.
   - **Virtual Network**: AS number; IPv4 pool.
   - **Collection Configuration** and **SAC Configuration** as planned [1].
2. *(tenant administrator)* Create the sites — **Deploy > SD-WAN > Site Management > Create**:
   southbound IP service name, site name, device type Firewall, **ESN-free** on; HQ is the RR
   site, branches are not; WAN IP address type IPv4 [1].
3. *(tenant administrator)* Add the devices — **Deploy > SD-WAN > Device Management → Add Device →
   Add**: site, type, model, quantity, role (**Gateway+RR** at HQ, **Gateway** at branches), name
   [1].
4. *(tenant administrator)* Create the WAN links — **Deploy > SD-WAN > ZTP**, site under
   **Unconfigured**, device → **Create**, once per link (`MPLS-A`, `MPLS-B`, `Internet`): link
   name, transport network, role Active, VN instance, interface, IPv4 static address, mask and
   gateway, IPv4 overlay tunnel on, controller southbound access service, uplink/downlink
   bandwidth. Turn **URL-based deployment** on for the `MPLS-A` link only [1]. Set bandwidth to the real
   circuit rate: a value below it drops traffic above it [1].
5. *(tenant administrator)* NTP — same page, site under **Configured**, **NTP tab → Create**, one
   entry per link: HQ points at the external server, branches at the RR site [1].
6. *(tenant administrator)* Send the deployment information — **Deploy > SD-WAN > ZTP**: **Send
   Email** to each site's onsite engineer, or **Download ZTP File** and pass it on [1].
7. *(customer, onsite engineer)* Deploy each USG: install, cable and power on; connect a PC to the
   management port (default `192.168.0.1/24`, web port 8443); open the latest deployment URL,
   enter the encryption key, **View Configuration Parameters → Confirm Deployment** [1]. Only the
   latest URL works.
8. *(tenant administrator)* Check **Deploy > SD-WAN > Device Management** until all three USGs
   are online [1].

**Expected result**: three sites, three devices online with the planned roles; every planned WAN
link configured; NTP synchronised to the external server at HQ and to the RR elsewhere.

**If it fails**: a result page showing "Configuration Success and Network Registration Failure"
means the configuration reached the device but its WAN link is not up; once the link is
connected the device registers on its own [1]. A URL that no longer works has been superseded —
use the latest one [1].

### TC-04: Register the AR6700V-L on the controller

**Objective**: the AR6700V-L built in TC-01 is online on the controller as a tenant-level
`Gateway`. The steps follow the Azure deployment guide [2].

**Prerequisites**: TC-01 complete, with the addresses from step 9 in the Azure column of the
Sites table; Global parameters set and the HQ RR site created (TC-03 steps 1–5). The branches need
not be online yet.

**Procedure**:

1. *(tenant administrator)* Create the site: **Deploy > SD-WAN > Site Management > Create** —
   site name, device type AR, **RR site = No**, WAN IP address type IPv4 [2].
2. *(tenant administrator)* Add the device: **Device Management → Add Device → Add** — model
   AR6700V-L, **Role = `Gateway`**, device name, **ESN = the one in `deploy.json`** [2].
3. *(tenant administrator)* Create the WAN link: **Deploy > SD-WAN > ZTP**, site under
   **Unconfigured**, **Create** — link name and transport network `Internet`, role Active,
   VN instance `underlay_1`, interface **GE0/0/0**, IPv4 static with the WAN private IP, mask
   and gateway recorded in TC-01; **NAT traversal on** (Design decisions); IPv4 overlay tunnel on, URL-based deployment on, controller
   southbound access service `Public Default South Access`, uplink/downlink bandwidth no higher
   than the public-IP bandwidth [2].
4. *(tenant administrator)* NTP: same page, site under **Configured**, **NTP tab → Create** —
   server address = the HQ RR, authentication off [1].
5. *(device + tenant administrator)* Let the device register: it raises the call-home NETCONF
   session to the controller on port 10020 [2]. Confirm the device is **online**.
6. *(optional)* Load the CPE-facing certificates, if the device is to authenticate branches
   itself.

**Expected result**: the device is online in NCE with role `Gateway`.

**If it fails**: if the device stays offline, log in through the virtual console and run
`display controller offline-record` and `display controller register-fail-record` for the
registration failure cause [2].

### TC-05: Network interconnection

**Objective**: the overlay carries traffic on all four paths — branch→HQ over MPLS,
branch→branch through the HQ hub, branch→Azure direct over Internet, and branch→Azure fallback
through HQ.

**Prerequisites**: TC-03 and TC-04 complete; VN names, topology, LAN interfaces and test hosts
planned; the IP subnets row complete for every site.

**Procedure**:

1. *(tenant administrator)* WAN routes — **Network Configuration > SD-WAN > Physical Network →
   Underlay Configuration**, each site → **WAN Route** → **IPv4 Static** → a default route
   `0.0.0.0/0` per WAN link, next hop = that link's gateway [1].
2. *(tenant administrator)* RR association — **Physical Network → Connect to RR**: select each
   branch and the AR6700V-L site → **Connect** → the HQ RR site → **Detect** → **OK**. In GRE
   tunnel mode this is mandatory [1].
3. *(tenant administrator)* VN — **Virtual Network → Virtual Network Configuration → Create**,
   set the VN parameters, **Next → Add Sites** (all four), **Complete** — one VN [1].
4. *(tenant administrator)* Topology — **Topology tab**, select the VN → **Predefine Topology**,
   mode **Simple**, **Hub-Spoke**, **Branch interconnection** on; hubs = HQ USG and AR6700V-L,
   spokes = branches. Leave the AR6700V-L hub at its default priority, below the USG hub [1].
5. *(tenant administrator)* Overlay LAN side — **Overlay Service tab**, VN and site:
   1. **LAN Interface → Create**: interface and IP address for every site; no VRRP, every site
      is single-gateway [1]. The solution's *(Optional) Configuring VPC Routes for Cloud Sites*
      is not used: step 6 carries the return path [1][2].
   2. AR6700V-L site, **LAN Route tab → IPv4 Static → Create**: one route per Azure subnet other
      than the LAN subnet (IP subnets row), next hop = the LAN subnet's Azure gateway, its first
      usable address [7]. The RR reflects these routes to the other sites [3]; the cloud-site
      block on them does not apply to a tool-deployed vCPE [3].
6. *(customer, Azure portal)* Return path — **Route tables → Create** (*Propagate gateway
   routes* = Yes), **Routes → Add**: destination = each HQ and branch subnet in the IP
   subnets row, one route per subnet, next hop type **Virtual appliance**, next hop = the vCPE LAN IP; **Subnets →
   Associate** the served subnets. The Azure guide has this route table configured before the
   underlay and overlay on the controller [2]; it can equally be prepared before TC-05.
7. *(OEM)* Check a branch's routing table: the Azure subnets are present with the AR6700V-L
   site as next hop, over the `Internet` tunnel only. On a branch,
   `display bgp sd-wan routing-table peer` must show the vCPE's TNP with its Azure **public**
   IP and post-NAT port — learned through STUN — not its private address [5].
8. *(OEM)* Test from the planned hosts: branch→HQ, branch→branch, branch→Azure workload and
   back; then take a branch's `Internet` link down and repeat branch→Azure.
9. *(OEM)* During step 8, capture on the vCPE's WAN interface and record the NAT type its STUN
   client detected and the data channel's form: UDP 4500 or IP protocol 50 (ESP). Then remove
   the WAN NSG rule that carries nothing.

**Expected result**: branch→HQ on MPLS; branch→branch through the HQ hub; branch→Azure leaving
the branch on its `Internet` link with no matching flow on the HQ USG; with the branch's
`Internet` link down, branch→Azure through HQ. The Azure workload reaches each branch host and
the reply returns through the UDR. The data channel's form and the detected NAT type are recorded.

**If it fails**: *Device online but no tunnel* — RR association (step 2) or topology/VN
membership (steps 3–4) incomplete. *Tunnel up but no traffic* — LAN interfaces (step 5)
missing, or the Azure route table (step 6) is missing, not associated with the served subnets,
or points at the WAN address instead of the LAN address. *No Azure route at a branch* — the
AR6700V-L's LAN interface (step 5) missing, or, for a subnet other than the LAN subnet, its
overlay LAN static route (step 5.2) missing. *Cloud traffic goes via HQ* — the branch's direct tunnel to the vCPE is not up
(Internet link, WAN NSG, or the vCPE's public IP in its WAN link), or hub priority is
preferring the USG for the Azure route too; record which, and only then consider raising the
vCPE hub, re-testing branch→branch afterwards. *Branch↔branch goes via Azure* — the vCPE hub
priority was raised above the USG (step 4).

### TC-06: Site-to-Internet

**Objective**: the USG sites break out to the Internet locally, with HQ as centralized backup.

**Prerequisites**: TC-05 complete; security-policy rules planned.

**Procedure**:

1. *(tenant administrator)* **Network Configuration > SD-WAN > Policy Management → Traffic Policy
   → Overlay**, select the VN → **Site-to-Internet**.
2. *(tenant administrator)* **Centralized Gateway → Create**: the HQ USG [1].
3. *(tenant administrator)* **Local Gateway → Create** per branch: select the site and its
   `Internet` link. On V600 devices the Internet access priority is fixed at *Local Internet
   Access First* [1], which is what this design wants.
4. *(tenant administrator)* **Security Policy tab**, select the VN → **Create**: user-to-Internet
   rules as planned → **Attach Sites** → the USG sites → commit [1].
5. Leave the AR6700V-L out: a public-cloud AR6700V-L supports no local Internet access [1].

**Expected result**: a branch host reaches the Internet through its own `Internet` link; with
that link down, it reaches the Internet through HQ.

**If it fails**: a WAN link that already has the IGW function for site-to-site access cannot also
take local Internet access, and the reverse [1].

### TC-07: Application experience optimization

**Objective**: the planned applications are identified, steered by link quality, and given
their bandwidth share.

**Prerequisites**: TC-05 complete; SAC on in the global parameters (TC-03); the application list
and per-application targets planned.

**Procedure**:

1. *(partner, system administrator; then tenant administrator)* Signature database: configure the
   signature-database server, upgrade the controller's database, then load it to the USGs [1].
2. *(tenant administrator)* Applications — create customized applications where no predefined
   one fits, then **application groups** with the planned predefined and customized applications
   [1].
3. *(tenant administrator)* Intelligent traffic steering — **Global Configuration → Physical
   Network**: keep the defaults unless the plan says otherwise; then **Policy Management →
   Traffic Policy → Overlay**, VN → **Intelligent Traffic Steering → Create**: traffic
   classifier template, policy priority, switchover condition (predefined indicator or custom),
   transport-network priority, inter-TN policy **Preference** → associate sites [1].
4. *(tenant administrator)* QoS — **Physical Network → Underlay Configuration → Advanced
   configuration → QoS GTS** (outbound on by default); traffic classifier and policy behavior
   templates; then an overlay **QoS** policy for the AR6700V-L and a **Bandwidth Management**
   policy for the USGs, each associated with its sites [1].
5. *(optional — tenant administrator)* WAN optimization (FEC) — **Traffic Policy → Overlay → WAN
   Optimization → Create** for applications that need it [1].
6. *(OEM)* Degrade the preferred link for a steered application and watch the switchover.

**Expected result**: **Network Monitoring > WAN Monitoring > Site Monitoring** shows the
applications identified, the steering decisions on the **Intelligent Traffic Steering
Statistics** page, and the guaranteed bandwidth held under load [1].

**If it fails**: steering policies do not apply to traffic between primary and secondary hub
sites [1].

### TC-08: Network security

**Objective**: the planned security policies are enforced at each site.

**Prerequisites**: TC-05 complete; security policies, profiles and any AR ACL planned.

**Procedure**:

1. *(tenant administrator)* Device signature-database updates for the USGs; the AR6700V-L does
   not support them [1].
2. *(optional — tenant administrator)* ACL policy on the AR6700V-L — traffic classifier
   template, then **Policy Management → Traffic Policy → Overlay** (or **Underlay**), VN →
   **ACL → Create** → associate the site [1].
3. *(tenant administrator)* Security profiles for the USGs — antivirus, IPS, URL filtering, file
   blocking as planned [1].
4. *(tenant administrator)* **Policy Management → Security Policy**, VN → **Create**: interzone,
   Internet-to-user and user-to-Internet rules, associated profiles → **Attach Sites** → commit
   [1].
5. *(optional — tenant administrator)* SSL-encrypted traffic detection on the USGs [1].
6. *(OEM)* From each test host, send one flow each rule should permit and one it should block.

**Expected result**: permitted flows pass, blocked flows are blocked and logged at the site that
owns the rule.

**If it fails**: V600 devices do not support URL filtering between SD-WAN sites — filter where
the traffic breaks out to the Internet [1].

## Issues encountered

None yet; pre-delivery.

## Conclusion

Every Network plan cell is an input to one of the eight test cases, so an unfilled cell is a
step that cannot run. Only the HQ RR has to be online before the sites that depend on it.

The port rules are frozen after TC-05 step 9, which records whether the data channel runs on
UDP 4500 or as ESP; until then the WAN NSG keeps both rules.

Validate after cut-over rather than assume: the latency and throughput cost of the HQ fallback
when a branch's Internet link fails, and the rotation path for the Azure client secret and the
device certificate, which is what breaks a hub a year later.

## References

**Basis and versions.** [1] is the governing solution document: V100R025C00, written against
device release V600R025C00, which every device here runs; the partner's controller is
V300R025C00. The AR6700V-L Azure guide is the same device release. The other Huawei references
are supplementary R026C00 product documentation, cited where the solution guide is silent and
compatible with this design; if one reports changed behaviour, the row that depends on it is
re-read, and the baseline does not move. The Microsoft references cover the Azure platform.
Huawei documentation is identified by its EDOC ID rather than a URL, per
[huawei.md](../vendor-matrix/huawei/huawei.md#documentation-sources).

[1] Huawei Technologies Co., Ltd., *Secure SD-WAN Portfolio Solution V100R025C00 Deployment
    and Maintenance Guide*, V100R025C00. **EDOC1100523201**. Read on 2026-11-10. Sections
    used: Secure SD-WAN Portfolio Solution Overview; Advanced Security Cloud Access Scenario
    (Version Mapping; Solution Overview; Data Plan; Deployment Restrictions and Precautions;
    Deployment Process; Installing Network Devices; iMaster NCE-Campus Pre-configurations —
    three-level administrator split and GRE tunnel mode; Deployment Plan; Selecting a Scenario
    View; Configuring Global Parameters; Creating a Site; Adding a Device; Configuring a WAN
    Link; Configuring NTP; Sending Deployment Information to Onsite Deployment Personnel;
    Onsite Deployment; Checking the Online Status of Devices After Onsite Deployment;
    AR6700V-L Deployment; Configuring WAN Routes; Configuring Association with RR Sites;
    Configuring a VN; Configuring a Topology; Configuring LAN Interfaces; Configuring VPC Routes
    for Cloud Sites; Site-to-Internet Overview — access-mode restrictions; Local, Centralized
    and Hybrid Internet Access; Application Identification; Configuring SAC; Creating an
    Application Group; Intelligent Traffic Steering; QoS; WAN Optimization; Network Security
    Deployment — device signature database, ACL-based traffic filtering, security policy,
    SSL-encrypted traffic detection).

[2] Huawei Technologies Co., Ltd., *NetEngine AR6700V-L V600R025C00 Deployment Guide
    (Azure)*, V600R025C00. **EDOC1100591294**. Issue number and date: not yet recorded
    (the CHM copy carries neither). Sections used: Before You Start (Product Models
    and Specifications; Deployment Mode; Networking Types; Supported Regions (how to check: Info-Finder → AR6700V-L specifications →
    Software Specifications > Resource Pool Management > Virtualization deployment environment >
    Public cloud environment); Supported Flavors; Determining the
    Product Model); Introduction to the Deployment Tool (Requirements on the Operating Environment;
    Default Deployment Information); Single-Site Single-Gateway Networking (Deployment
    Constraints; Site and Device Parameter Planning; ZTP Parameter Planning; Preparing for
    Deployment; Creating Security Groups (WAN inbound ports for SD-WAN); Creating an Application; Creating an Image; Deploying an AR6700V-L Using the
    Deployment Tool; Configuring iMaster NCE-Campus; Configuring Virtual Network Routes);
    Error Codes; Configuring DTLS (the configuration topic the Creating Security Groups step
    links to — RR as DTLS server, CPEs as clients);
    Appendixes (Binding a Public IP Address; Binding an ExpressRoute Connection; Parameters
    in the azure.json File).

[3] Huawei Technologies Co., Ltd., *SD-WAN Solution & iMaster NCE-Campus Product
    Documentation*, V100R026C00, library version 01, 2026-09-30. **EDOC1100613380**. Read on
    2026-11-10. Sections used: Version Requirements → Mapping AR Models; SD-WAN Networking →
    Hub-Spoke Networking, Multi-Hub Networking; Deployment → iMaster NCE-Campus
    Pre-configurations → Configuring a Tunnel Mode; Network Interconnection → Inter-Site
    Interconnection → Device and Feature Requirements; Understanding the Solution → Knowledge
    and Concepts → SD-WAN Solution and Architecture → Overlay Route (devices send overlay LAN
    routes to the RR, which reflects them); Network Interconnection → Inter-Site
    Interconnection → Overlay Configuration → Configuring Overlay LAN-Side Routes (not
    configurable for an AR6700V-L deployed as a cloud site) → Configuring Overlay LAN-Side
    Routes (Static Routes); Cloud Site Deployment → Introduction to Cloud Site Deployment
    (Huawei Cloud or AWS only). These sections read on 2026-11-11.

[4] Microsoft, *Source Network Address Translation (SNAT) for outbound connections — Azure Load
    Balancer*, Microsoft Learn,
    `learn.microsoft.com/en-us/azure/load-balancer/load-balancer-outbound-connections`
    (page updated 2026-08-21, read 2026-11-10). Used for: a public IP on a VM's NIC is a
    stateless 1:1 NAT that carries TCP, UDP, ICMP and ESP.

[5] Huawei Technologies Co., Ltd., *HiSecEngine USG6000F, USG6000G Product Documentation*,
    V600R026C00, library version 01, 2026-09-30. **EDOC1100605493**. Read on 2026-11-10.
    Sections used: VPN Configuration → SD-WAN EVPN Configuration → Understanding SD-WAN EVPN →
    SD-WAN EVPN Fundamentals (transport network, routing domain); Configuration Precautions
    for SD-WAN EVPN (Hardware Requirements); STUN Configuration → Application Scenarios for
    STUN (STUN in SD-WAN EVPN: STUN server on the RR, STUN clients on the CPEs), Understanding
    STUN → STUN Implementation (NAT detection, pre- and post-NAT IP and port, hole punching),
    Default Settings for STUN (server disabled by default; port 3478); Configuring SD-WAN EVPN
    → (Optional) Configuring IPsec;
    Understanding SD-WAN EVPN → SD-WAN EVPN Data Forwarding (GRE encapsulation); Command
    Reference → `display bgp sd-wan routing-table peer` (TNP port fields and output example),
    `display ipsec p2mp-sa` (output example: `TransformMode: ESP`, `Encap mode: TRANSPORT`),
    `nat detect enable` (disabled by default), `source-port (STUN client view)`.

[6] Microsoft, *Fsv2-series sizes — Azure Virtual Machines*, Microsoft Learn,
    `learn.microsoft.com/en-us/azure/virtual-machines/sizes/compute-optimized/fsv2-series`
    (page updated 2026-07-27, read 2026-11-10). Used for: F8s_v2 = 8 vCPU, 16 GiB, 4 vNICs,
    12,500 Mbps, Gen 1 and Gen 2 VMs supported, accelerated networking supported. The page
    gives no per-region availability — region and quota confirmation belongs to the
    subscription (see the Azure platform table).

[7] Microsoft, *Azure Virtual Network FAQ*, Microsoft Learn,
    `learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-faq` (page updated
    2026-07-09, read 2026-11-11). Used for: the smallest supported IPv4 subnet is /29;
    Azure reserves five addresses in each subnet (the network address, the default
    gateway, two for Azure DNS, and the broadcast address).

[8] Microsoft, *Azure subscription and service limits, quotas, and constraints*, Microsoft
    Learn, `learn.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits`
    (page updated 2026-09-29, read 2026-11-11). Used for: Networking limits (Azure Resource
    Manager), user-defined routes per route table = 1,000.

[9] Huawei Technologies Co., Ltd., *NetEngine AR6700V-L V600R026C00 Communication Matrix*
    (.xlsx), V600R026C00, issue 01, 2026-09-30. **EDOC1100609800**. Read on 2026-11-11. Sheets used: About This Document (column definitions: protocols are
    transport-layer only); Body, the rows whose Special Scenario is `SD-WAN` (STUN detection
    and response, 3478; STUN hole punching, 4500–65535, default 4500; DTLS to the RR or
    edge-RR, server port 10000–65535, configurable).

[10] Huawei Technologies Co., Ltd., *NetEngine AR6700V-L Product Documentation*, V600R026C00,
    library version 01, 2026-09-30. **EDOC1100609744**. Read on 2026-11-10. Sections used: Configuration → CLI Configuration
    Guide → VPN Configuration → IPsec Configuration → Configuring an IPsec Proposal →
    Understanding IPsec Security Protocols (Table 3, comparisons between AH and ESP: ESP
    protocol number 50; NAT traversal supported); Understanding IPsec Encapsulation Modes
    (transport mode inserts the ESP header after the original IP header, no new IP header);
    Installation and Deployment → Deployment Guide → AR6700V-L Deployment (Huawei Cloud) →
    AR6700V-L Deployment (Manual Deployment Through Manual Configuration) → AR6700V-L
    Deployment (Single-Site Single-Gateway Networking) → Creating Security Groups (WAN inbound
    ports for SD-WAN: UDP 123, 3478, 4500, 55100; TCP 22; ICMP), read on 2026-11-11.
