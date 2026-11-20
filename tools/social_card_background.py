#!/usr/bin/env python3
"""Generate the background image for the site's social (link-preview) cards.

The Zensical ``social`` plugin draws each page's title and description on top
of this 1200x630 SVG (see ``cards_layout_options.background_image`` in
mkdocs.yml).  CI runs this script before the site build; the output is not
committed.

The art is a light 3D scene seen by one orthographic camera, TILT degrees above
the horizon:

* a network laid out in 2D (data-centre clusters on the right, branch clusters
  reaching left) sits on a ground plane placed by one affine matrix (rotate by
  ALPHA within the plane, then tilt);
* the plane rests on a large globe whose latitude/longitude grid is projected
  from real sphere points; the sphere radius is chosen so the surface under the
  network faces the camera at exactly TILT, with the horizon at HORIZON_Y;
* square data-centre halls stand on the big clusters and a cloud floats in the
  sky; both go through the same projection, so the whole scene shares one
  viewpoint.

Text areas drawn by the plugin: page title x 62-926 / y 192-448, description
y 512-576.  Light colours keep that dark text readable over the art.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

W, H = 1200, 630

# --- Camera and ground plane -------------------------------------------------
# [x'; y'] = SCALE * [[cos a, -sin a], [sin t sin a, sin t cos a]] [x; y] + [e; f]
# Heights above the plane rise by SCALE * cos(TILT) per unit.
ALPHA, TILT, SCALE = math.radians(-16), math.radians(20), 1.22
PLANE_CENTER, SCREEN_CENTER = (820, 330), (700, 395)

# --- Globe -------------------------------------------------------------------
HORIZON_Y, GRID_PX = 165, 78.5  # horizon height; on-screen grid cell size

# --- Network layout (plane coordinates) --------------------------------------
# (x, y, radius, node count, style); the main mass sits on the right and small
# branch sites reach toward the left.  Style "dc" lays nodes out as a loose
# lattice (a fabric); any other style scatters them radially.
CLUSTERS = [
    (1060, 125, 80, 11, "site"),
    (930, 320, 105, 17, "dc"),
    (1110, 455, 72, 10, "site"),
    (680, 190, 42, 5, "branch"),
    (440, 120, 26, 3, "edge"),
    (660, 460, 40, 5, "branch"),
    (380, 420, 22, 3, "edge"),
    (170, 300, 14, 2, "edge"),
]
# More data-centre clusters, given as screen positions (blank areas of the
# card).  The first and last sit past the right and bottom-right borders, so
# the card edge cuts them and the network seems to carry on beyond the frame.
EXTRA_DC_SCREEN = [(1190, 285), (920, 525), (1150, 615)]
# WAN links between cluster hubs: (from, to, width, opacity, dash style).
ARCS = [
    (0, 1, 1.8, 0.85, ""), (0, 2, 1.8, 0.85, ""), (1, 2, 1.8, 0.85, ""),
    (1, 3, 1.4, 0.75, ""), (3, 4, 1.1, 0.6, "dash"), (0, 3, 1.0, 0.5, "dot"),
    (1, 5, 1.4, 0.75, ""), (5, 6, 1.1, 0.6, "dash"), (6, 7, 0.9, 0.45, "dot"),
    (0, 8, 1.8, 0.85, ""), (8, 2, 1.8, 0.85, ""), (1, 9, 1.8, 0.85, ""),
    (9, 10, 1.8, 0.85, ""), (10, 2, 1.8, 0.85, ""),
]

# --- Data-centre halls -------------------------------------------------------
# Identical square halls on a 3x3 grid: the first takes the centre cell x and
# each extra hall one of its 8 neighbours:
#   NW N NE
#   W  x  E
#   SW S SE
# A layout lists the extra directions, so [] is one hall, ["E"] two, and
# ["E", "S"] three.  The group is centred on its cluster's hub.
DIRECTIONS = {"N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
              "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1)}
CLUSTER_LAYOUT = {
    0: [],          # upper site: 1 hall
    1: ["E", "S"],  # main (biggest) site: 3 halls
    2: ["N"],       # right site: 2 halls
    8: [],          # right edge, cut by the border: 1 hall
    9: ["E"],       # bottom middle: 2 halls
    10: [],         # bottom-right corner, cut by the border: 1 hall
}
HALL, HALL_H, HALL_UNITS, HALL_GAP = 40, 15, (2, 2), 10

# --- Cloud -------------------------------------------------------------------
CLOUD_SCREEN, CLOUD_HEIGHT = (1085, 85), 200  # high in the top-right sky

PALETTE = ["#7dd3fc", "#93c5fd", "#bae6fd", "#a5d8f5", "#c7e7fb"]
SIDE_A, SIDE_B, TOP, EDGE = "#e3f2fd", "#c4e5fa", "#f8fcff", "#8fd0f5"
DASHES = {"": "", "dash": ' stroke-dasharray="5 6"', "dot": ' stroke-dasharray="2 6"'}

MA = SCALE * math.cos(ALPHA)
MB = SCALE * math.sin(TILT) * math.sin(ALPHA)
MC = -SCALE * math.sin(ALPHA)
MD = SCALE * math.sin(TILT) * math.cos(ALPHA)
ME = SCREEN_CENTER[0] - (MA * PLANE_CENTER[0] + MC * PLANE_CENTER[1])
MF = SCREEN_CENTER[1] - (MB * PLANE_CENTER[0] + MD * PLANE_CENTER[1])
UP = SCALE * math.cos(TILT)


def project(x: float, y: float, h: float = 0.0) -> tuple[float, float]:
    """Plane point (and height above it) -> screen point."""
    return (MA * x + MC * y + ME, MB * x + MD * y + MF - h * UP)


def unproject(sx: float, sy: float) -> tuple[float, float]:
    """Inverse of the ground-plane matrix: screen point -> plane point."""
    det = MA * MD - MB * MC
    x, y = sx - ME, sy - MF
    return ((MD * x - MC * y) / det, (-MB * x + MA * y) / det)


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _points(points) -> str:
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in points)


def build_svg() -> str:
    rng = random.Random(7)
    clusters = list(CLUSTERS)

    # Nodes: (x, y, radius, colour, cluster index); the first node is the hub.
    nodes = []
    for ci, (cx, cy, rad, n, style) in enumerate(clusters):
        pts = []
        tries = 0
        while len(pts) < n and tries < 5000:
            tries += 1
            if style == "dc":  # loose lattice, hinting at a fabric
                gx = cx + rng.randint(-2, 2) * rad / 2.6 + rng.uniform(-6, 6)
                gy = cy + rng.randint(-2, 2) * rad / 2.6 + rng.uniform(-6, 6)
            else:
                a = rng.uniform(0, 2 * math.pi)
                d = rad * math.sqrt(rng.random())
                gx, gy = cx + d * math.cos(a), cy + d * math.sin(a)
            if all(math.hypot(gx - px, gy - py) > 24 for px, py in pts):
                pts.append((gx, gy))
        for i, (x, y) in enumerate(pts):
            hub = 7 if rad >= 60 else (5 if rad >= 30 else 4)
            r = hub if i == 0 else rng.choice([2.5, 3, 3.5, 4, 5] if rad >= 60 else [2, 2.5, 3])
            nodes.append((x, y, r, PALETTE[1] if i == 0 else rng.choice(PALETTE), ci))
    for sx, sy in EXTRA_DC_SCREEN:
        cx, cy = unproject(sx, sy)
        ci = len(clusters)
        clusters.append((cx, cy, 60, 8, "dc"))
        pts = []
        while len(pts) < 8:
            gx = cx + rng.randint(-2, 2) * 60 / 2.6 + rng.uniform(-6, 6)
            gy = cy + rng.randint(-2, 2) * 60 / 2.6 + rng.uniform(-6, 6)
            if all(math.hypot(gx - px, gy - py) > 24 for px, py in pts):
                pts.append((gx, gy))
        for i, (x, y) in enumerate(pts):
            r = 7 if i == 0 else rng.choice([2.5, 3, 3.5, 4, 5])
            nodes.append((x, y, r, PALETTE[1] if i == 0 else rng.choice(PALETTE), ci))
    hubs = [next(n for n in nodes if n[4] == ci) for ci in range(len(clusters))]

    out: list[str] = []
    p = out.append
    p(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    p("  <!-- Generated by tools/social_card_background.py; do not edit. -->")
    p("""  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#eaf2fa"/>
    </linearGradient>
    <radialGradient id="halo">
      <stop offset="0" stop-color="#38bdf8" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#38bdf8" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow">
      <stop offset="0" stop-color="#bae6fd" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#e0f2fe" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gridfade" cx="0.72" cy="0.55" r="0.7">
      <stop offset="0" stop-color="#fff" stop-opacity="1"/>
      <stop offset="0.65" stop-color="#fff" stop-opacity="0.6"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
    <mask id="gridmask"><rect width="1200" height="630" fill="url(#gridfade)"/></mask>
    <style>.plane * { vector-effect: non-scaling-stroke; }</style>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>""")

    # Globe (orthographic view along +z; view space x right, y up, z to viewer)
    anchor = project(*PLANE_CENTER)
    globe_r = (anchor[1] - HORIZON_Y) / (1 - math.cos(TILT))
    gx0, gy0 = anchor[0], anchor[1] + globe_r * math.cos(TILT)
    pole = _unit((0.28, 0.86, -0.42))  # north pole just behind the horizon
    e1 = _unit(_cross((0, 0, 1), pole))
    e2 = _cross(pole, e1)

    def sphere(lat, lon):
        la, lo = math.radians(lat), math.radians(lon)
        return tuple(math.cos(la) * math.cos(lo) * e1[i] + math.cos(la) * math.sin(lo) * e2[i]
                     + math.sin(la) * pole[i] for i in range(3))

    def globe_path(points):
        segs, cur = [], []
        for v in points:
            x, y = gx0 + globe_r * v[0], gy0 - globe_r * v[1]
            if v[2] > 0 and -60 < x < W + 60 and -60 < y < H + 60:  # front-facing, on the card
                cur.append((x, y))
            elif cur:
                segs.append(cur)
                cur = []
        if cur:
            segs.append(cur)
        return ["M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in s) for s in segs if len(s) > 1]

    p('  <g mask="url(#gridmask)" fill="none" stroke="#9ccfee" stroke-width="1">')
    for width, opacity in [(36, 0.12), (20, 0.18), (8, 0.25)]:  # atmosphere glow
        p(f'    <circle cx="{gx0:.1f}" cy="{gy0:.1f}" r="{globe_r + width / 2:.1f}" fill="none" '
          f'stroke="#bae6fd" stroke-opacity="{opacity}" stroke-width="{width}"/>')
    p(f'    <circle cx="{gx0:.1f}" cy="{gy0:.1f}" r="{globe_r:.1f}" fill="#f4f9fe" '
      f'stroke="#9ccfee" stroke-opacity="0.8" stroke-width="1.4"/>')
    step = math.degrees(GRID_PX / globe_r)
    fine = step / 8
    n_lat, n_lon = int(90 / step), int(360 / step)
    for k in range(-n_lat, n_lat + 1):  # parallels
        for d in globe_path([sphere(k * step, j * fine) for j in range(int(360 / fine) + 1)]):
            p(f'    <path d="{d}" stroke-opacity="0.55"/>')
    for k in range(n_lon):  # meridians
        for d in globe_path([sphere(-90 + j * fine, k * step) for j in range(int(180 / fine) + 1)]):
            p(f'    <path d="{d}" stroke-opacity="0.55"/>')
    p("  </g>")

    # Network on the ground plane, drawn in plane coordinates under the matrix
    p(f'  <g class="plane" transform="matrix({MA:.5f} {MB:.5f} {MC:.5f} {MD:.5f} {ME:.2f} {MF:.2f})">')
    for cx, cy, rad, _, _ in clusters:
        p(f'    <circle cx="{cx}" cy="{cy}" r="{rad * 1.7:.0f}" fill="url(#glow)"/>')
    seen = set()
    for i, a in enumerate(nodes):  # each node to its nearest neighbours in the cluster
        same = sorted((math.hypot(a[0] - b[0], a[1] - b[1]), j) for j, b in enumerate(nodes)
                      if j != i and b[4] == a[4])
        k = 3 if clusters[a[4]][4] == "dc" else 2
        for _, j in same[:k]:
            key = tuple(sorted((i, j)))
            if key in seen:
                continue
            seen.add(key)
            b = nodes[j]
            p(f'    <line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
              f'stroke="#7dd3fc" stroke-opacity="0.6" stroke-width="1.2"/>')
    for a, b, width, opacity, dash in ARCS:
        (x1, y1), (x2, y2) = hubs[a][:2], hubs[b][:2]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        qx, qy = mx - (y2 - y1) * 0.28, my + (x2 - x1) * 0.28
        p(f'    <path d="M{x1:.1f} {y1:.1f} Q{qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}" fill="none" '
          f'stroke="#7dd3fc" stroke-opacity="{opacity}" stroke-width="{width}"{DASHES[dash]}/>')
    for node in nodes:
        x, y, r, color, _ = node
        if node in hubs:
            p(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 3.7:.0f}" fill="url(#halo)"/>')
            p(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#ffffff" stroke="#7dd3fc" '
              f'stroke-width="{2 + r / 7:.1f}"/>')
        else:
            p(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" fill-opacity="0.9"/>')
    p("  </g>")

    # Data-centre halls, through the same projection
    def face(points, fill):
        p(f'    <polygon points="{_points(points)}" fill="{fill}" stroke="{EDGE}" '
          f'stroke-width="1.2" stroke-linejoin="round"/>')

    def solid(x0, y0, w, d, h, z0=0.0):
        """A box on (or above) the plane; returns its visible side faces."""
        corners = [(x0 - w / 2, y0 - d / 2), (x0 + w / 2, y0 - d / 2),
                   (x0 + w / 2, y0 + d / 2), (x0 - w / 2, y0 + d / 2)]
        cx, cy = project(x0, y0)
        sides = []
        for i in range(4):
            (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
            mid = project((ax + bx) / 2, (ay + by) / 2)
            if mid[1] > cy:  # faces the viewer
                sides.append(((ax, ay), (bx, by)))
                face([project(ax, ay, z0), project(bx, by, z0), project(bx, by, z0 + h),
                      project(ax, ay, z0 + h)], SIDE_A if mid[0] < cx else SIDE_B)
        face([project(x, y, z0 + h) for x, y in corners], TOP)
        return sides

    def dc_hall(x0, y0, w, d, h, units):
        """Low and windowless, with wall louvres and rooftop cooling fans."""
        for (ax, ay), (bx, by) in solid(x0, y0, w, d, h):
            n = max(3, int(math.hypot(bx - ax, by - ay) / 7))
            for k in range(1, n):
                px_, py_ = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
                a, b = project(px_, py_, h * 0.25), project(px_, py_, h * 0.75)
                p(f'    <line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                  f'stroke="{EDGE}" stroke-width="0.9" stroke-opacity="0.8"/>')
        cols, rows = units
        cells = []
        for i in range(cols):
            for j in range(rows):
                ux = x0 - w / 2 + w * (i + 0.5) / cols
                uy = y0 - d / 2 + d * (j + 0.5) / rows
                cells.append((project(ux, uy)[1], ux, uy))
        size = min(w / cols, d / rows) * 0.5
        for _, ux, uy in sorted(cells):  # back to front
            solid(ux, uy, size, size, h * 0.14, z0=h)
            fan = [project(ux + size * 0.32 * math.cos(a / 12 * math.pi),
                           uy + size * 0.32 * math.sin(a / 12 * math.pi), h * 1.14) for a in range(24)]
            p(f'    <polygon points="{_points(fan)}" fill="#e0f2fe" stroke="{EDGE}" stroke-width="0.9"/>')
        return project(x0, y0, h * 1.14)  # roof centre

    roofs = []
    pitch = HALL + HALL_GAP
    for ci in sorted(CLUSTER_LAYOUT, key=lambda c: project(*hubs[c][:2])[1]):  # back to front
        x, y = hubs[ci][:2]
        cells = [(0, 0)] + [DIRECTIONS[d] for d in CLUSTER_LAYOUT[ci]]
        mx = sum(c[0] for c in cells) / len(cells)
        my = sum(c[1] for c in cells) / len(cells)
        halls = [(x + (cx_ - mx) * pitch, y + (cy_ - my) * pitch) for cx_, cy_ in cells]
        tops = [dc_hall(hx, hy, HALL, HALL, HALL_H, HALL_UNITS)
                for hx, hy in sorted(halls, key=lambda c: project(*c)[1])]
        roofs.append((sum(t[0] for t in tops) / len(tops), sum(t[1] for t in tops) / len(tops)))

    # Cloud in the sky, with its shadow (a projected circle) on the ground
    gx, gy = unproject(CLOUD_SCREEN[0], CLOUD_SCREEN[1] + CLOUD_HEIGHT * UP)
    shadow = [project(gx + 40 * math.cos(a / 18 * math.pi), gy + 40 * math.sin(a / 18 * math.pi))
              for a in range(36)]
    p(f'    <polygon points="{_points(shadow)}" fill="#bae6fd" fill-opacity="0.35"/>')
    cx, cy = project(gx, gy, CLOUD_HEIGHT)
    for rx, ry in roofs:
        p(f'    <line x1="{cx:.1f}" y1="{cy + 16:.1f}" x2="{rx:.1f}" y2="{ry:.1f}" stroke="#7dd3fc" '
          f'stroke-opacity="0.6" stroke-width="1.2" stroke-dasharray="3 5"/>')
    lobes = [(-26, 6, 14), (-9, -6, 19), (13, -3, 16), (29, 7, 11)]
    p(f'    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="60" fill="url(#halo)" opacity="0.6"/>')
    p(f'    <g fill="#ffffff" stroke="{EDGE}" stroke-width="1.4">')
    for dx, dy, r in lobes:
        p(f'      <circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r}"/>')
    p(f'      <rect x="{cx - 38:.1f}" y="{cy + 2:.1f}" width="76" height="16" rx="8"/>')
    p("    </g>")
    p('    <g fill="#ffffff">')
    for dx, dy, r in lobes:
        p(f'      <circle cx="{cx + dx:.1f}" cy="{cy + dy:.1f}" r="{r - 1.2:.1f}"/>')
    p(f'      <rect x="{cx - 36.8:.1f}" y="{cy + 3.2:.1f}" width="73.6" height="13.6" rx="6.8"/>')
    p("    </g>")
    p('  <rect x="0" y="0" width="1200" height="8" fill="#0284c7"/>')
    p("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="SVG file to write")
    args = parser.parse_args()
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(build_svg(), encoding="utf-8")
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
