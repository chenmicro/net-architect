# Arista

## EOS

- A single binary image runs across Arista's entire switch portfolio (campus,
  DC, low-latency) — unlike vendors that ship different OS trains per product
  line, one EOS image (feature-gated by license/platform capability) simplifies
  qualification and upgrade planning across a mixed fleet.
- **SysDB** is EOS's central, publish-subscribe state database — every process
  (routing protocol agent, forwarding agent, CLI) reads/writes through SysDB
  rather than sharing state via ad hoc IPC. This is the architectural reason EOS
  has a strong reputation for in-service software upgrades and process-level
  fault isolation: a crashing agent can restart and resync from SysDB without a
  full reboot.
- **EOS SDK** exposes SysDB and platform state to custom on-box Python/Go/C++
  agents — relevant when a design calls for custom automation or telemetry logic
  running directly on the switch rather than off-box, e.g. bespoke traffic
  engineering logic or a custom health-check agent reacting to local state in
  real time.

## CloudVision (CVP)

- Arista's fleet-wide management plane: telemetry (via streaming state, not
  polling — NetDB/OpenConfig-style), configuration management, and change
  automation across the EOS fleet from one console.
- **CV-CUE** (Cognitive Unified Edge, from the Mojo Networks acquisition) extends
  the same CloudVision management plane to wireless/campus access, relevant when
  a design spans both DC (Arista's traditional strength) and campus/access under
  one operational pane rather than siloed tooling.
- CloudVision's streaming-telemetry model (state pushed continuously, not
  polled) is a meaningful differentiator for AI-fabric and other
  congestion-sensitive designs where near-real-time buffer/queue visibility
  matters — see [techniques/ai-gpu-fabric.md](../techniques/ai-gpu-fabric.md).

## Broadcom Merchant Silicon

- Arista is a merchant-silicon shop by design — Tomahawk (high-radix, DC
  spine-leaf, increasingly AI-fabric-oriented with deep buffers and
  RoCEv2-tuned features) and Trident (leaf/access-oriented, broader feature
  depth per port) are Broadcom ASIC families Arista builds switches around,
  rather than developing fully custom silicon in-house.
- Practical implication: Arista's roadmap and generational leaps track
  Broadcom's silicon roadmap fairly closely — useful to know when
  timing a purchase against an upcoming Broadcom silicon generation
  (e.g. Tomahawk 5/6 class parts for higher-radix, higher-speed AI fabrics).
- Merchant silicon vs. custom ASIC (contrast with Cisco Silicon One, Juniper's
  custom DC/edge silicon) is a real tradeoff to surface in vendor comparisons:
  merchant silicon generally means faster access to leading-edge port speeds/
  radix (Broadcom ships first, vendors integrate), while custom silicon can
  offer differentiated features/buffer architectures a shared merchant part
  can't.

## Low-Latency (7130 Series)

- The 7130 series is Arista's purpose-built low-latency line (via the Metamako
  acquisition) — FPGA-based, cut-through switching with nanosecond-class
  latency and precision timestamping, aimed squarely at electronic
  trading/market-data use cases where microseconds of latency have direct
  financial impact.
- This is a distinct product family from Arista's general DC/campus line
  (7000-series proper) — don't default to it outside latency-sensitive
  financial/trading contexts; general DC fabrics should stay on the
  Tomahawk/Trident-based mainline switches, which optimize for a different
  balance of buffering, feature depth, and port economics.
- Cut-through switching (forwarding begins before the full frame is received)
  trades error-checking completeness for latency — appropriate for trading
  environments with controlled, low-error-rate links, not a general substitute
  for store-and-forward in a typical enterprise/DC design.
