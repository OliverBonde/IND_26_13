"""Map horizontal BR18 R'w requirements onto filled wall zones.

Room-facing boundaries define a filled partition strip spanning the physical
wall thickness. IFC wall geometries must still corroborate each strip, and a
long wall is only coloured where it separates the specific room pair.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from shapely.geometry import GeometryCollection, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union

# One fixed, clearly distinguishable colour per horizontal R'w threshold.
# No interpolation/gradient.  Grey means an unresolved requirement.
RW_COLORS = {
    20: "#F5E642",  # lemon yellow
    36: "#FFCE00",  # gold
    44: "#FF9A00",  # amber
    48: "#FF7100",  # orange
    50: "#F04B15",  # orange red
    55: "#D92724",  # red
    60: "#AD1932",  # crimson
    65: "#770D30",  # dark red
}
UNCERTAIN_COLOR = "#858B92"
NEUTRAL_ROOM_COLOR = "#F5F6F8"


@dataclass(frozen=True)
class PairOverlay:
    iid: str
    a: str
    b: str
    status: str
    rw: str
    separator_keys: tuple = ()
    description: str = ""
    rule: str = ""
    direction: str = "horisontal"


def rw_value(rw: str) -> int | None:
    match = re.search(r"\d+", str(rw or ""))
    return int(match.group()) if match else None


def overlay_color(status: str, rw: str) -> str:
    if status != "Beregnet":
        return UNCERTAIN_COLOR
    return RW_COLORS.get(rw_value(rw), UNCERTAIN_COLOR)


def _as_polygon(loops):
    polygons = []
    for outline in loops or ():
        if len(outline) < 3:
            continue
        try:
            poly = Polygon(outline)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty and poly.area > 0.01:
                polygons.append(poly)
        except Exception:
            pass
    return unary_union(polygons) if polygons else None


def _line_parts(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type in ("LineString", "LinearRing"):
        if geometry.length > 0:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for piece in geometry.geoms:
            yield from _line_parts(piece)


def pair_wall_segments(plan: dict[str, Any], pair: PairOverlay):
    """Return real IFC wall segments within the facing-boundary corridor.

    Room polygons and wall cross sections use world-space metres (or consistently
    scaled coordinates), as produced by the existing floor-plan loader.
    """
    if pair.direction != "horisontal":
        return []
    space_loops = plan.get("spaces", {})
    if pair.a not in space_loops or pair.b not in space_loops:
        return []
    pa, pb = _as_polygon(space_loops[pair.a]), _as_polygon(space_loops[pair.b])
    if pa is None or pb is None:
        return []
    if pa.intersection(pb).area > 0.25:
        return []  # Overlapping rooms are not a reliable shared-wall segment.
    distance = pa.boundary.distance(pb.boundary)
    if distance > 1.20:
        return []
    radius = min(max(distance / 2 + 0.20, 0.25), 0.72)
    facing = pa.boundary.buffer(radius).intersection(pb.boundary.buffer(radius))
    if facing.is_empty:
        return []

    # If the acoustic analysis verified a particular IfcWall, use ONLY that
    # wall's sections.  This avoids colouring nearby corridor/branch walls.
    keys = {tuple(k) for k in pair.separator_keys}
    wall_lines = plan.get("wall_objects", ())
    if keys:
        candidates = [(guid, a, b) for guid, a, b in wall_lines
                      if ("guid", str(guid)) in keys]
        # A verified non-wall separator (or missing wall geometry) must not be
        # replaced with an unrelated nearby wall.
        if not candidates:
            return []
    else:
        candidates = wall_lines

    clipped = []
    for _guid, a, b in candidates:
        try:
            line = LineString((a, b))
            if line.length < 0.12 or not line.intersects(facing):
                continue
            for part in _line_parts(line.intersection(facing)):
                if part.length >= 0.16:
                    clipped.append(part)
        except Exception:
            continue
    if not clipped:
        return []
    result = []
    seen = set()
    # Avoid drawing duplicate edges resulting from triangulated IFC faces.
    for line in _line_parts(unary_union(clipped)):
        coords = list(line.coords)
        if len(coords) < 2:
            continue
        for i in range(len(coords)-1):
            a = tuple(float(c) for c in coords[i]); b = tuple(float(c) for c in coords[i+1])
            if LineString((a,b)).length < .14:
                continue
            key = tuple(sorted((tuple(round(v, 3) for v in a), tuple(round(v,3) for v in b))))
            if key not in seen:
                seen.add(key)
                result.append((a,b))
    return result


# --- V7.1: filled wall zones rather than fragmented IFC mesh-edge strokes ---
# Room boundary surfaces normally represent the two opposite faces of a
# separating wall. A closed 2-D band between those surfaces paints the WHOLE
# separating construction, including door-sized interruptions in the mesh.
# A candidate real IfcWall must still be spatially corroborated: the band is
# never drawn from mere proximity between two rooms.


def _boundary_edges(poly):
    """Return usable straight room-face edges even for finely tessellated IFC.

    IFC room boundaries frequently contain dozens of collinear (or slightly
    jittered) sub-20 cm edges. The old implementation discarded each of them
    individually, producing *partial* coloured walls, especially vertically.

    Simplify each closed boundary ring before extracting edges. This merges
    contiguous wall-face segments without crossing actual room corners or
    changing the source room geometry used for drawing/area calculations.
    """
    shapes = [poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", ()))
    for shape in shapes:
        if shape.geom_type != "Polygon":
            continue
        for ring in (shape.exterior, *shape.interiors):
            # Preserve genuine wall returns and room shape changes, while
            # eliminating collinear mesh subdivisions / centimetre jitter.
            simplified = ring.simplify(.045, preserve_topology=True)
            coords = list(simplified.coords)
            if len(coords) < 4:
                coords = list(ring.coords)
            for a, b in zip(coords, coords[1:]):
                length = ((b[0]-a[0])**2 + (b[1]-a[1])**2)**0.5
                if length > .18:
                    yield a, b, length


def _between_parallel_edges(edge_a, edge_b, max_gap=1.20):
    """Polygon bridging the overlapping, facing portions of two room faces.

    Edges must be nearly parallel, close, and have a substantial projected
    overlap. Each polygon is bounded by the respective room faces, not by the
    tiny triangles at the openings of an IfcWall mesh.
    """
    (a0,a1,la), (b0,b1,lb) = edge_a, edge_b
    ux, uy = (a1[0]-a0[0])/la, (a1[1]-a0[1])/la
    vx, vy = (b1[0]-b0[0])/lb, (b1[1]-b0[1])/lb
    alignment = ux*vx + uy*vy
    if abs(alignment) < 0.985:
        return None
    # The second line must be near the first, not somewhere far away along
    # a long collinear line through several rooms.
    signed_gap = (b0[0]-a0[0])*(-uy) + (b0[1]-a0[1])*ux
    gap = abs(signed_gap)
    if gap > max_gap:
        return None
    t_b0 = (b0[0]-a0[0])*ux+(b0[1]-a0[1])*uy
    t_b1 = (b1[0]-a0[0])*ux+(b1[1]-a0[1])*uy
    lo, hi = max(0., min(t_b0,t_b1)), min(la, max(t_b0,t_b1))
    if hi-lo < .20:
        return None
    # Corresponding points on both face segments at the same projection.
    inv = 1.0/alignment
    def on_a(t):
        return (a0[0]+ux*t, a0[1]+uy*t)
    def on_b(t):
        v=(t-t_b0)*inv
        return (b0[0]+vx*v, b0[1]+vy*v)
    polygon = Polygon((on_a(lo), on_a(hi), on_b(hi), on_b(lo)))
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    # When room boundaries coincide, use a visually legible thin centre strip.
    if polygon.is_empty or polygon.area < (hi-lo)*.008:
        polygon = LineString((on_a(lo), on_a(hi))).buffer(.035, cap_style=2)
    return polygon if not polygon.is_empty else None


def _wall_lines_for_pair(plan, pair):
    keys = {tuple(key) for key in pair.separator_keys}
    by_guid = plan.get('wall_by_guid')
    if by_guid is not None:
        if keys:
            lines = [segment for kind,guid in keys if kind == 'guid'
                     for segment in by_guid.get(str(guid), ())]
            return lines
        return [seg for pieces in by_guid.values() for seg in pieces]
    walls = plan.get('wall_objects', ())
    if keys:
        return [(a,b) for guid,a,b in walls if ('guid',str(guid)) in keys]
    return [(a,b) for _guid,a,b in walls]


def _polygon_parts(geom):
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == 'Polygon':
        if geom.area > .001:
            yield geom
    elif hasattr(geom, 'geoms'):
        for part in geom.geoms:
            yield from _polygon_parts(part)


def pair_wall_areas(plan: dict[str,Any], pair: PairOverlay):
    """Return filled wall polygons confined to this horizontal room pair.

    The wall band spans the two room-facing wall surfaces rather than tracing
    cut edges, so openings and tessellation do not cause coloured dashes.
    Require a real nearby IfcWall, from the specified separator if available.
    """
    if pair.direction != 'horisontal':
        return []
    space_loops = plan.get('spaces', {})
    if pair.a not in space_loops or pair.b not in space_loops:
        return []
    pa = _as_polygon(space_loops[pair.a]); pb = _as_polygon(space_loops[pair.b])
    if pa is None or pb is None:
        return []
    if pa.intersection(pb).area > .25 or pa.boundary.distance(pb.boundary) > 1.20:
        return []

    # Confirm the IFC element exists on this horizontal section. A host GUID
    # from an unrelated level/part of the building must never be rendered.
    candidates = _wall_lines_for_pair(plan,pair)
    if not candidates:
        return []

    # Pair neighbouring room face edges, including stepped/L-shaped walls.
    a_edges = list(_boundary_edges(pa)); b_edges = list(_boundary_edges(pb))
    bands = []
    for ea in a_edges:
        for eb in b_edges:
            band = _between_parallel_edges(ea,eb)
            if band is not None:
                bands.append(band)
    if not bands:
        return []

    # Only paint bands spatially supported by the concrete IfcWall. For a
    # validated shared wall we can extend across its door cuts, but not beyond
    # where the two rooms are opposite one another.
    corroborating_lines = []
    for a,b in candidates:
        try:
            segment = LineString((a,b))
            if segment.length > .03:
                corroborating_lines.append(segment)
        except (ValueError, TypeError):
            continue
    if not corroborating_lines:
        return []
    # Minor offsets occur between the IFC wall and the exported space faces.
    wall_near = unary_union(corroborating_lines).buffer(.16)
    reliable = []
    for band in bands:
        if band.intersects(wall_near) and band.intersection(wall_near).area > .002:
            reliable.append(band)
    if not reliable:
        return []

    merged = unary_union(reliable).buffer(0)
    # Avoid painting over the *interior* of either room. Their boundary lines
    # remain visible; a tiny shrink compensates for IFC precision tolerances.
    merged = merged.difference(pa.buffer(-.005)).difference(pb.buffer(-.005))
    return list(_polygon_parts(merged))


def create_level_overlays(plan, pairs):
    """Return (pair, filled wall polygon) entries and number not located."""
    shown, missing = [], 0
    for pair in pairs:
        if pair.direction != 'horisontal':
            continue
        if pair.a not in plan.get('spaces', {}) or pair.b not in plan.get('spaces', {}):
            continue
        shapes = pair_wall_areas(plan, pair)
        if shapes:
            shown.extend((pair, shape) for shape in shapes)
        else:
            missing += 1
    return shown, missing
