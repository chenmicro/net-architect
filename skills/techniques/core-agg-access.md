# Core / Aggregation / Access

- **Three-tier** (core → distribution/aggregation → access) is the traditional model:
  access switches provide port density and PoE to endpoints, distribution aggregates
  access uplinks and is the L2/L3 boundary (SVIs, HSRP/VRRP), core provides high-speed,
  low-latency transit between distribution blocks and to the WAN/DC edge.
- **Collapsed core** (distribution and core merged into one tier) fits smaller or
  single-building campuses — fewer devices to manage, one less hop, but less headroom
  to scale out by adding distribution blocks later. Use three-tier when there are
  multiple buildings/large floors that each want their own distribution block and
  fault domain; collapse when there's one building or the whole campus is one
  administrative/fault domain anyway.
- L2/L3 boundary placement is the key design decision: pushing L3 down to access
  (routed access) shrinks STP's blast radius and gives faster convergence via ECMP
  routing instead of spanning-tree recalculation, at the cost of losing L2 adjacency
  for things that need it (some legacy apps, certain VoIP or clustering setups).
  Modern campus designs (e.g. Cisco SD-Access, fabric-based campus) increasingly
  default to routed access with a VXLAN or similar overlay for the L2 services that
  still need to stretch.
- Redundancy at each tier: dual-homed access-to-distribution uplinks (or a fabric
  equivalent), distribution/core resiliency via HSRP/VRRP or a stacking/chassis
  redundancy model, sized for N+1 at minimum in anything customer- or life-safety-facing.
