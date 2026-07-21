# PoE

- Budget PoE at the **switch power supply** level, not just per-port capability —
  a switch can support 802.3bt (90W/port, PoE++) per port yet not have enough total
  PSU capacity to deliver that to every port simultaneously; check the chassis/stack
  power budget against realistic worst-case draw (all ports at max class), not just
  nameplate per-port numbers.
- Standards: 802.3af (PoE, 15.4W at source/~12.95W at device), 802.3at (PoE+, 30W/
  ~25.5W), 802.3bt (PoE++/UPoE, up to 90-100W/~71-90W depending on type). Match the
  standard to the actual endpoint draw — Wi-Fi 6/6E APs with multiple radios and USB
  accessories, PTZ cameras, and thin-client/monitor combos increasingly need 802.3at
  or 802.3bt, not legacy 802.3af.
- Cable length and category affect deliverable power at high wattages (resistive
  loss) — for 90W-class PoE++ over longer runs, verify against the vendor's
  cable-length derating table rather than assuming full budget at any distance.
- Redundant power (dual PSU, or PoE-specific UPS/backup) is a distinct decision from
  data redundancy — anything safety- or business-critical (access control, cameras,
  emergency phones) on PoE needs its power path reviewed independently of network
  path redundancy.
