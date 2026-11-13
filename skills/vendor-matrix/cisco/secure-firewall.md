# Cisco Secure Firewall — Threat Defense clustering

**Scope: Firewall Threat Defense (FTD) clustering on the Secure Firewall 3100, 4200 and 6100,
managed by Firewall Management Center (FMC), as documented for release 10.x** [1]. See the
[Cisco hub](cisco.md) for other product lines.

## Models and cluster size

| Model | Maximum nodes | Interface modes (minimum FMC / FTD) |
|---|---|---|
| Secure Firewall 3100 | 16 from 7.6.0; 8 before [1] | Spanned EtherChannel; Individual interface from 7.6.0 [1] |
| Secure Firewall 4200 | 16 from 7.6.0; 8 before [1] | Spanned EtherChannel; Individual interface from 7.6.0 [1] |
| Secure Firewall 6100 | 4 [1] | Spanned EtherChannel and Individual interface, clustering from 10.0.0 [1] |

All nodes of a cluster are the same model [1].

## Interface modes

- **Spanned EtherChannel (Cisco's recommendation):** one EtherChannel spans every chassis in the
  cluster. It works in routed and transparent mode and allows IPS-only interfaces (inline sets,
  passive interfaces) [1].
- **Individual interfaces:** normal routed interfaces, each with its own local IP address used
  for routing. IPS-only interfaces are not supported. Individual interfaces rely on routing
  protocols to load-balance traffic [1].
- **Main cluster IP:** on each interface it is a fixed address that always belongs to the control
  node and moves to the new control node on a change of control node [1].

## Dynamic routing

- **Spanned EtherChannel mode:** the routing process runs only on the control node, which learns
  the routes; routing packets that reach a data node are redirected to the control node [1].
- **Individual interface mode:** each node runs the routing protocol as a standalone router and
  learns routes independently. EIGRP does not form neighbor relationships with cluster
  peers in this mode [1].

## Inter-site clustering

- **Site ID:** each node gets a site ID from 1 to 8; 0 disables inter-site clustering [1].
- **FlexConfig only:** director localization, site redundancy and cluster flow mobility are
  configured only through FlexConfig [1].
- **Cluster control link (CCL):** round-trip time between units under 20 ms; the link must not
  drop or reorder packets, and a dedicated link is recommended between sites. Set the CCL MTU at
  least 100 bytes above the data interface MTU [1].
- **Individual interface mode across sites:** Cisco's reference architecture extends the CCL at
  Layer 2 across the sites [2].

## Site-to-site VPN in a cluster

- **Centralized (default):** only the control node may carry site-to-site VPN configuration; data
  nodes must not have any VPN configured. All units must run the same software version, and
  after an upgrade or downgrade every unit must be on the target version before VPN traffic
  resumes [1].
- **Distributed (opt-in):** IKEv2 site-to-site connections are distributed across the nodes [1].
  - Platforms: Secure Firewall 4200 (from FMC/FTD 10.0.0) and 6100 [1].
  - Requirements: Spanned EtherChannel mode, routed firewall mode, IKEv2 only, and a Carrier
    licence on every member [1].
  - Not supported: inter-site clustering, and interface PAT [1].
  - Capacity: the cluster's maximum VPN sessions are at most half the listed platform figure
    (listed: 4215 10,000; 4225 12,500; 4245 15,000; 6160 280,000; 6170 350,000) [1].

## References

[1] "Cisco Secure Firewall Management Center Device Configuration Guide, 10.x — Clustering:
Secure Firewall 3100/4200/6100," Cisco, updated Nov. 11, 2026. [Online]. Available:
https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/device-config/100/management-center-device-config-10-0/ha-scale-cluster.html
— verify in: Prerequisites for clustering (model requirements, hardware and software
requirements); Clustering configuration > Cluster interfaces (Spanned EtherChannels, Individual
interfaces, Cluster control link reliability for inter-chassis clustering); Create a Cluster,
step 3 (site ID); Configure distributed Site-to-Site VPN; Reference for Clustering > Dynamic
routing, Dynamic routing in individual interface mode; History for clustering. Confirmed
Nov. 13, 2026.

[2] "Secure Firewall Reference Architecture for Individual Interface Mode Clusters," Cisco.
[Online]. Available:
https://secure.cisco.com/secure-firewall/docs/secure-firewall-reference-architecture-for-individual-interface-mode-clusters
— verify the CCL design for inter-site clusters. Confirmed Nov. 13, 2026.
