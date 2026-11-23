"""Analyse af rum-naboskab i IFC til BR18 R'w.

Naboskab prioriterer eksplicitte IfcRelSpaceBoundary2ndLevel-links.
Geometrisk fallback er KANDIDATER, ikke dokumenteret adskillelse.
Alle geometriske koordinater er i meter (IfcOpenShell create_shape, world coords).

Kræver: ifcopenshell, shapely. Regelmodul: br18_Rw_rules.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from bisect import bisect_left, bisect_right
from math import hypot
from typing import Callable

from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.ops import polygonize, unary_union

from br18_Rw_rules import Rum, Rumpar, Rumtype, rumtype, bestem_lydisolation

UNCATEGORIZED = "Ikke kategoriseret"


@dataclass
class SpaceShape:
    guid: str
    verts: tuple
    faces: tuple
    bounds: tuple  # (xmin, ymin, zmin, xmax, ymax, zmax)
    _cache: dict = field(default_factory=dict)

    def footprint(self, height: float):
        """Geometry sliced *at this height*, not a 2D projection of the whole solid."""
        key = round(height, 3)
        if key in self._cache:
            return self._cache[key]
        if not (self.bounds[2] + 0.002 < height < self.bounds[5] - 0.002):
            return None
        lines = []
        for i in range(0, len(self.faces), 3):
            pts = [(self.verts[3*j], self.verts[3*j+1], self.verts[3*j+2])
                   for j in self.faces[i:i+3]]
            crossings = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                p, q = pts[a], pts[b]
                d = q[2] - p[2]
                if abs(d) < 1e-9:
                    continue
                t = (height - p[2]) / d
                if -1e-8 <= t <= 1+1e-8:
                    xy = (round(p[0] + t*(q[0]-p[0]), 3),
                          round(p[1] + t*(q[1]-p[1]), 3))
                    if xy not in crossings:
                        crossings.append(xy)
            if len(crossings) == 2 and crossings[0] != crossings[1]:
                lines.append(LineString(crossings))
        geometry = None
        if lines:
            try:
                polygons = [p for p in polygonize(unary_union(MultiLineString(lines)))
                            if p.area > .08]
                if polygons:
                    geometry = unary_union(polygons)
                    if not geometry.is_valid:
                        geometry = geometry.buffer(0)
            except Exception:
                pass
        self._cache[key] = geometry
        return geometry


def shape_from_arrays(guid, vertices, faces):
    verts = tuple(float(x) for x in vertices)
    faces = tuple(int(x) for x in faces)
    if not verts or not faces:
        return None
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    return SpaceShape(guid, verts, faces,
                      (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))


@dataclass
class Adjacency:
    a: str
    b: str
    direction: str
    evidence: str   # "IFC-grænse" / "Geometrisk kandidat"
    detail: str = ""
    door_hints: str = ""
    door_choice: str = "Ukendt"  # "Ja" only automatically with sufficient IFC evidence
    door_source: str = "Ikke afklaret"  # IFC / Manuel / Ikke afklaret
    door_evidence: str = ""
    verified: str = "Ubekræftet"  # user confirmation, never auto confirmed for geometry
    flexible_choice: str = "Nej"
    noisy_choice: str = "Ukendt"
    separator_keys: tuple = ()  # Verified IFC wall/slab entity keys

    def key(self):
        return tuple(sorted((self.a, self.b)))


def _candidate_from_geometry(a: SpaceShape, b: SpaceShape, max_gap: float = .55):
    """Conservative proximity tests. NEVER imply a guaranteed physical separator."""
    ax, ay, az0, ax2, ay2, az1 = a.bounds
    bx, by, bz0, bx2, by2, bz1 = b.bounds
    if ax > bx2 + max_gap or bx > ax2 + max_gap or ay > by2 + max_gap or by > ay2 + max_gap:
        return None
    common_min, common_max = max(az0, bz0), min(az1, bz1)
    if common_max - common_min > .65:
        height = common_min + min(1.2, (common_max - common_min) / 2)
        pa, pb = a.footprint(height), b.footprint(height)
        if pa is None or pb is None:
            return None
        overlap = pa.intersection(pb).area
        # Overlapping volumes are not separations.
        if overlap > max(.25, min(pa.area, pb.area)*.07):
            return None
        distance = pa.distance(pb)
        if distance > max_gap:
            return None
        # Need a meaningful *length* of facing boundaries, not just a corner.
        nearby = pa.boundary.intersection(pb.boundary.buffer(max_gap+.01)).length
        opposite = pb.boundary.intersection(pa.boundary.buffer(max_gap+.01)).length
        if min(nearby, opposite) < .75:
            return None
        return "horisontal", (f"section z={height:.2f} m, "
                              f"distance between room surfaces ≈ {distance:.2f} m, "
                              f"nearby shared boundary ≥ {min(nearby, opposite):.2f} m")
    # Vertical pairs may have a thin slab gap, but must not significantly overlap in height.
    if az1 <= bz0 + .75 and az1 >= bz0 - .75:
        lower, upper = a, b
    elif bz1 <= az0 + .75 and bz1 >= az0 - .75:
        lower, upper = b, a
    else:
        return None
    # Slice inside each room, not in the slab (otherwise empty geometries).
    zlo = max(lower.bounds[2]+.02, lower.bounds[5] - min(.35, (lower.bounds[5]-lower.bounds[2])*.3))
    zup = min(upper.bounds[5]-.02, upper.bounds[2] + min(.35, (upper.bounds[5]-upper.bounds[2])*.3))
    pa, pb = lower.footprint(zlo), upper.footprint(zup)
    if pa is None or pb is None:
        return None
    intersection = pa.intersection(pb).area
    if intersection < .75 or intersection < .10*min(pa.area, pb.area):
        return None
    return "vertikal", f"floor separation, overlapping projection ≈ {intersection:.2f} m²"


def _explicit_boundaries(model, selected_guids: set | None = None):
    """Only a *corresponding* IFC space boundary establishes an explicit room pair.

    Grouping on the same wall alone would produce many false room pairings.
    """
    found = {}
    for boundary in model.by_type("IfcRelSpaceBoundary"):
        opposite = getattr(boundary, "CorrespondingBoundary", None)
        if opposite is None:
            continue
        s1 = getattr(boundary, "RelatingSpace", None)
        s2 = getattr(opposite, "RelatingSpace", None)
        if not s1 or not s2 or not s1.is_a("IfcSpace") or not s2.is_a("IfcSpace"):
            continue
        if s1.GlobalId == s2.GlobalId:
            continue
        if selected_guids is not None and not (
            s1.GlobalId in selected_guids or s2.GlobalId in selected_guids
        ):
            continue
        # A corresponding boundary may describe a virtual or otherwise
        # non-physical partition. Acoustic R'w requires a real separator.
        if str(getattr(boundary, "PhysicalOrVirtualBoundary", "PHYSICAL")).upper().endswith("VIRTUAL"):
            continue
        component = getattr(boundary, "RelatedBuildingElement", None)
        if component is None:
            continue
        from ifc_relation_analysis import _kind
        direction = _kind(component)
        if direction is None:
            continue
        key = tuple(sorted((s1.GlobalId, s2.GlobalId)))
        detail = "IfcRelSpaceBoundary: corresponding boundary"
        if component:
            detail += f", {component.is_a()} ({getattr(component, 'Name', None) or component.GlobalId})"
        # A single room pair can share several distinct walls (e.g. an
        # L-shaped room enclosing two sides of a smaller room). Keep every
        # positively corresponding IFC boundary, not only the last one.
        if key in found:
            adj = found[key]
            if adj.direction != direction:
                continue  # Do not combine horizontal walls and floor slabs.
            host = _entity_key(component)
            if host is not None and host not in adj.separator_keys:
                adj.separator_keys = (*adj.separator_keys, host)
        else:
            adj = Adjacency(*key, direction, "IFC-grænse", detail,
                            verified="Bekræftet")
            host = _entity_key(component)
            if host is not None:
                adj.separator_keys = (host,)
            found[key] = adj
    return found


def _door_bbox(model, notify=None):
    import ifcopenshell.geom
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    doors = []
    for door in model.by_type("IfcDoor"):
        try:
            shape = ifcopenshell.geom.create_shape(settings, door)
            v = shape.geometry.verts
            if not v:
                continue
            x, y, z = v[0::3], v[1::3], v[2::3]
            doors.append((door.GlobalId, Point((min(x)+max(x))/2, (min(y)+max(y))/2), min(z), max(z)))
        except Exception:
            continue
    return doors


def _door_hints(adj: Adjacency, shapes: dict, doors: list):
    if adj.direction != "horisontal" or adj.a not in shapes or adj.b not in shapes:
        return ""
    a, b = shapes[adj.a], shapes[adj.b]
    z0, z1 = max(a.bounds[2], b.bounds[2]), min(a.bounds[5], b.bounds[5])
    if z1 - z0 < .5:
        return ""
    z = z0 + min(1., (z1 - z0) / 2)
    pa, pb = a.footprint(z), b.footprint(z)
    if pa is None or pb is None:
        return ""
    hits = []
    for guid, center, low, high in doors:
        if max(z0,low) >= min(z1,high):
            continue
        # A nearby door is a hint, NOT confirmed direct connection.
        if pa.boundary.distance(center) < .8 and pb.boundary.distance(center) < .8:
            hits.append(guid[:12])
    return "Potential door in IFC: " + ", ".join(hits[:6]) if hits else ""


def _entity_key(entity):
    """Stable key for IFC entities, including IfcOpeningElement."""
    if entity is None:
        return None
    guid = getattr(entity, "GlobalId", None)
    if guid:
        return ("guid", str(guid))
    try:
        return ("id", entity.id())
    except Exception:
        return ("object", id(entity))


def _door_ifc_links(model):
    """Extract actual buildingSMART IFC relations without relying on names.

    Door -> opening: IfcRelFillsElement.
    Opening -> host wall: IfcRelVoidsElement.
    Space -> element: IfcRelSpaceBoundary.

    A door on a long shared wall is NOT sufficient by itself to assume a
    connection between two particular rooms: its exact position also matters.
    """
    opening_to_wall = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        opening = getattr(rel, "RelatedOpeningElement", None)
        host = getattr(rel, "RelatingBuildingElement", None)
        if opening is not None and host is not None:
            opening_to_wall[_entity_key(opening)] = _entity_key(host)

    door_to_wall = {}
    for rel in model.by_type("IfcRelFillsElement"):
        door = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if door is not None and door.is_a("IfcDoor") and opening is not None:
            host = opening_to_wall.get(_entity_key(opening))
            if host is not None:
                door_to_wall[str(door.GlobalId)] = host

    space_to_elements = defaultdict(set)
    door_to_spaces = defaultdict(set)
    explicitly_paired_doors = defaultdict(set)
    for rel in model.by_type("IfcRelSpaceBoundary"):
        room = getattr(rel, "RelatingSpace", None)
        element = getattr(rel, "RelatedBuildingElement", None)
        if room is None or not room.is_a("IfcSpace") or element is None:
            continue
        room_id = str(room.GlobalId)
        space_to_elements[room_id].add(_entity_key(element))
        if element.is_a("IfcDoor"):
            door_to_spaces[str(element.GlobalId)].add(room_id)
            opposite = getattr(rel, "CorrespondingBoundary", None)
            other = getattr(opposite, "RelatingSpace", None) if opposite else None
            if other is not None and other.is_a("IfcSpace") and other.GlobalId != room_id:
                explicitly_paired_doors[tuple(sorted((room_id, str(other.GlobalId))))].add(str(element.GlobalId))

    return door_to_wall, space_to_elements, door_to_spaces, explicitly_paired_doors


def _door_along_two_space_boundaries(adj: Adjacency, shapes, door):
    """Check the actual door coordinate against BOTH room boundaries.

    This is only used together with IFC wall/door/opening relationships.
    The distances allow for a normal interior partition's thickness.
    """
    if adj.direction != "horisontal" or adj.a not in shapes or adj.b not in shapes:
        return False
    _, center, door_zmin, door_zmax = door
    sa, sb = shapes[adj.a], shapes[adj.b]
    low = max(sa.bounds[2], sb.bounds[2], door_zmin)
    high = min(sa.bounds[5], sb.bounds[5], door_zmax)
    if high - low < .05:
        return False
    # Door centre is usually midway through the host wall. Check at its
    # vertical midpoint (inside both rooms and the door).
    z = (low + high) / 2
    pa, pb = sa.footprint(z), sb.footprint(z)
    if pa is None or pb is None or pa.is_empty or pb.is_empty:
        return False
    # With a verified IFC host wall, allow a thicker partition. Without the
    # host evidence remain strict; mere nearby door geometry is not enough.
    host_verified = adj.verified == "Bekræftet" and bool(adj.separator_keys)
    max_offset = .65 if host_verified else .40
    return (pa.boundary.distance(center) <= max_offset and
            pb.boundary.distance(center) <= max_offset and
            pa.distance(pb) <= (1.30 if host_verified else .55))


def _autodetect_direct_doors(model, found, shapes, door_geometry):
    """Assign automatic Ja only for positively identified DIRECT connections.

    No door found != no door: missing export links/geometry must remain Ukendt.
    """
    door_to_wall, space_to_elements, door_to_spaces, paired_doors = _door_ifc_links(model)
    geom_by_guid = {entry[0]: entry for entry in door_geometry}
    counters = {"ifc_direct": 0, "ifc_wall_and_position": 0,
                "ifc_wall_geometric_pair": 0, "still_unknown": 0}
    for adj in found.values():
        if adj.direction != "horisontal" or adj.door_source == "Manuel":
            continue
        pair = adj.key()
        # Strongest: IFC second-level corresponding room boundaries of a door.
        matched = paired_doors.get(pair, set())
        origin = "corresponding IfcRelSpaceBoundary on IfcDoor"
        if not matched:
            # Door explicitly referenced as room boundary on BOTH sides.
            matched = {guid for guid, rooms in door_to_spaces.items()
                       if adj.a in rooms and adj.b in rooms}
            origin = "IfcRelSpaceBoundary for both rooms on IfcDoor"
        if matched:
            guid = sorted(matched)[0]
            adj.door_choice = "Ja"
            adj.door_source = "IFC – rumgrænser"
            adj.door_evidence = f"IfcDoor {guid}: {origin}"
            counters["ifc_direct"] += 1
            continue

        # Often Revit exports a door->opening->wall chain, but no 2nd-level
        # door-related space boundaries. Combine structural wall evidence with
        # a strict position check on the two *actual* space boundaries.
        common_elements = space_to_elements.get(adj.a, set()) & space_to_elements.get(adj.b, set())
        # Two rooms can refer to the same long corridor wall even though that
        # wall does NOT separate them. Use the verified separator's host first.
        verified_hosts = (set(adj.separator_keys) if
                          adj.verified == "Bekræftet" and adj.separator_keys else set())
        # Use IFC wall/space boundaries where available. For Revit exports
        # without IfcRelSpaceBoundary, we may still match a genuine IFC door
        # and its host wall to the geometry of the TWO candidate rooms. The
        # candidate adjacency must remain unverified in this latter case.
        matches_with_boundary = []
        matches_from_geometry = []
        for guid, wall in door_to_wall.items():
            if guid not in geom_by_guid:
                continue
            if verified_hosts and wall not in verified_hosts:
                continue  # Hosted by a different wall, not this separator.
            if not _door_along_two_space_boundaries(adj, shapes, geom_by_guid[guid]):
                continue
            if wall in verified_hosts or (not verified_hosts and wall in common_elements):
                matches_with_boundary.append(guid)
            elif not verified_hosts and adj.evidence == "Geometrisk kandidat":
                matches_from_geometry.append(guid)
        if matches_with_boundary:
            guid = sorted(matches_with_boundary)[0]
            adj.door_choice = "Ja"
            adj.door_source = "IFC – væg og rumgrænser"
            adj.door_evidence = (f"IfcDoor {guid}: IfcRelFillsElement → "
                                 "IfcRelVoidsElement → wall in both rooms' "
                                 "IfcRelSpaceBoundary; door position verified")
            counters["ifc_wall_and_position"] += 1
        elif matches_from_geometry:
            guid = sorted(matches_from_geometry)[0]
            adj.door_choice = "Ja"
            adj.door_source = "IFC – dør i væg, rumgeometri"
            adj.door_evidence = (f"IfcDoor {guid}: direct IFC wall association via "
                                 "IfcRelFillsElement / IfcRelVoidsElement and "
                                 "door position at BOTH space boundaries. "
                                 "Adjacency is only a geometric candidate")
            counters["ifc_wall_geometric_pair"] += 1
        else:
            counters["still_unknown"] += 1
    return counters



def _autodetect_absent_doors(model, found, door_geometry, shapes=None):
    """Check *each verified shared partition* for a modelled door.

    This is deliberately NOT a whole-building door-completeness test. A door
    without a host/mesh somewhere else cannot invalidate an unrelated wall.
    A modeled door or opening with an ambiguous filling ON the relevant part
    of the partition prevents a negative result. A bare IFC void with no
    modeled door is documented as a potential acoustical issue, not a door.

    'Nej' means no IfcDoor found in the available IFC *at this room interface*;
    it does NOT mean that the separator is closed or acoustically sound.
    Missing objects in an incomplete export remain fundamentally unknowable.
    """
    shapes = shapes or {}
    door_to_wall, _, _, _ = _door_ifc_links(model)
    geometry_by_id = {str(d[0]): d for d in door_geometry}
    # Trust the IFC as the model of what is present. A verified wall with no
    # modelled door or unresolved opening can get "Nej" even if the entire
    # model contains no IfcDoor entities. An omitted export cannot be detected.

    doors_by_host = defaultdict(list)
    for guid, host in door_to_wall.items():
        doors_by_host[host].append(guid)

    # Opening -> host and opening -> fills (door, window, other element).
    openings_by_host = defaultdict(list)
    fills_by_opening = defaultdict(list)
    for rel in model.by_type('IfcRelVoidsElement'):
        opening = getattr(rel, 'RelatedOpeningElement', None)
        host = getattr(rel, 'RelatingBuildingElement', None)
        if opening is not None and host is not None:
            openings_by_host[_entity_key(host)].append(opening)
    for rel in model.by_type('IfcRelFillsElement'):
        opening = getattr(rel, 'RelatingOpeningElement', None)
        filler = getattr(rel, 'RelatedBuildingElement', None)
        if opening is not None and filler is not None:
            fills_by_opening[_entity_key(opening)].append(filler)

    opening_mesh_cache = {}
    settings = None

    def opening_position(opening):
        """Geometry position/extent of a void, if the export provides it."""
        nonlocal settings
        key = _entity_key(opening)
        if key not in opening_mesh_cache:
            try:
                import ifcopenshell.geom
                if settings is None:
                    settings = ifcopenshell.geom.settings()
                    settings.set(settings.USE_WORLD_COORDS, True)
                verts = ifcopenshell.geom.create_shape(settings, opening).geometry.verts
                if not verts:
                    raise ValueError('Opening has no usable vertices')
                xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
                opening_mesh_cache[key] = (
                    (key, Point((min(xs)+max(xs))/2, (min(ys)+max(ys))/2),
                     min(zs), max(zs)),
                    (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
            except Exception:
                opening_mesh_cache[key] = None
        return opening_mesh_cache[key]

    def located_at_pair(adj, loc):
        """True only if the feature is near BOTH actual room boundaries.

        For openings check the bounding footprint as well as the centre;
        a wide void can overlap the interface even when its centre does not.
        Missing room geometry must not be interpreted as exclusion.
        """
        if loc is None:
            return None
        position, bounds = loc
        if adj.a not in shapes or adj.b not in shapes:
            return None
        if _door_along_two_space_boundaries(adj, shapes, position):
            return True
        a, b = shapes[adj.a], shapes[adj.b]
        common_low = max(a.bounds[2], b.bounds[2], bounds[2])
        common_high = min(a.bounds[5], b.bounds[5], bounds[5])
        if common_high-common_low <= .02:
            return False
        from shapely.geometry import box as shapely_box
        z = (common_low + common_high) / 2
        pa, pb = a.footprint(z), b.footprint(z)
        if pa is None or pb is None:
            return None
        interface = pa.boundary.buffer(.65).intersection(pb.boundary.buffer(.65))
        if interface.is_empty:
            return False
        extent = shapely_box(bounds[0], bounds[1], bounds[3], bounds[4])
        return interface.intersects(extent)

    # With a known host, the actual door centre must be at the two-room
    # interface, not merely in a long wall also serving other rooms.
    def door_at_pair(adj, guid):
        door = geometry_by_id.get(guid)
        if door is None or adj.a not in shapes or adj.b not in shapes:
            return None
        # Cheap 3D bbox filter before computing expensive footprint sections.
        _, centre, low, high = door
        a, b = shapes[adj.a], shapes[adj.b]
        if (high <= max(a.bounds[2], b.bounds[2]) or
            low >= min(a.bounds[5], b.bounds[5])):
            return False
        for room in (a, b):
            x0, y0, _, x1, y1, _ = room.bounds
            if not (x0-.70 <= centre.x <= x1+.70 and
                    y0-.70 <= centre.y <= y1+.70):
                return False
        return _door_along_two_space_boundaries(adj, shapes, door)

    count = 0
    for adj in found.values():
        if (adj.direction != 'horisontal' or adj.verified != 'Bekræftet'
                or adj.door_choice != 'Ukendt' or adj.door_source == 'Manuel'):
            continue
        hosts = set(adj.separator_keys)
        if not hosts:
            continue

        unresolved = False
        reason = None
        unfilled_local = []
        for host in hosts:
            # Door on THIS wall but elsewhere is not a connection for this pair.
            for door_id in doors_by_host.get(host, ()):
                match = door_at_pair(adj, door_id)
                if match is not False:
                    unresolved = True
                    reason = (f"Door {door_id} is associated with the shared wall, "
                              "but its position relative to this room pair is unresolved.")
                    break
            if unresolved:
                break

            for opening in openings_by_host.get(host, ()):
                fill = fills_by_opening.get(_entity_key(opening), ())
                # Filled with an identifiable window etc.: not a door. An
                # IfcDoor is checked via the door-to-host mapping above.
                if fill and all(f.is_a('IfcWindow') for f in fill):
                    continue
                if fill and all(f.is_a('IfcDoor') for f in fill):
                    # A correctly linked door has already been checked. If a
                    # fill relation is malformed or missing an IFC Door, be
                    # conservative rather than silently claiming no door.
                    ids = [str(f.GlobalId) for f in fill]
                    if ids and all(door_to_wall.get(d) == host for d in ids):
                        continue
                # An IfcOpeningElement is a void, NOT evidence of an IfcDoor.
                # A modelled recess also cannot be a direct door opening.
                kind = str(getattr(opening, 'PredefinedType', None) or
                           getattr(opening, 'ObjectType', None) or '').upper()
                if 'RECESS' in kind:
                    continue
                match = located_at_pair(adj, opening_position(opening))
                if match is False:
                    continue
                opening_id = getattr(opening, 'GlobalId', str(_entity_key(opening)))
                if match is None:
                    # No reliable position for this opening; do not claim it
                    # belongs to another part of the host wall.
                    unresolved = True
                    reason = (f"Opening {opening_id} in the shared wall cannot be "
                              "located (geometry is missing).")
                    break
                if fill:
                    # Unknown/generic filling could actually represent a door.
                    unresolved = True
                    names = ', '.join(sorted({f.is_a() for f in fill}))
                    reason = (f"Opening {opening_id} is filled with {names}, "
                              "not unambiguously identified as a door or non-door.")
                    break
                # A void WITHOUT an IfcRelFillsElement / IfcDoor is not a
                # modelled door. Continue checking all actual door entities.
                # Keep the acoustic consequence visible: an unfilled through-
                # opening may prevent the partition from achieving its R'w.
                unfilled_local.append(opening_id)
            if unresolved:
                break
        if unresolved:
            adj.door_evidence = reason or 'Ambiguous door/opening in the shared wall.'
            continue

        # A corridor door with a KNOWN host on another wall is not a direct
        # connection through the verified separator, regardless of proximity.
        # Only doors without a known host need a location-based check.
        for door_id, door in geometry_by_id.items():
            if door_id in door_to_wall:
                continue  # Hosted elsewhere, or already checked above.
            if door_at_pair(adj, door_id):
                unresolved = True
                reason = (f"Door {door_id} is near both rooms but lacks "
                          "a reliable IFC wall association.")
                break
        if unresolved:
            adj.door_evidence = reason
            continue

        adj.door_choice = 'Nej'
        adj.door_source = 'IFC – lokal vægkontrol (forudsætning)'
        if unfilled_local:
            ids = ', '.join(sorted(set(unfilled_local))[:6])
            adj.door_evidence = (
                f'No IfcDoor on the shared wall between these rooms. '
                f'Opening(s) WITHOUT modelled filling: {ids}. '
                'Door Connection = No in the IFC, but an open passage, '
                'service penetration or other recess may affect actual '
                'sound insulation and MUST be checked. The R\'w value is only a '
                'requirement, not verified performance of the construction.')
        else:
            adj.door_evidence = (
                'No modelled door on the relevant shared wall segment. '
                'Door data on other walls do not affect this assessment. '
                'Assumes that doors/openings are included in the IFC export.')
        count += 1
    return count

def _geometry_pairs(shapes: dict, selected_guids: set | None = None, max_gap: float = .85):
    """Yield only potentially adjacent XY bounding-box pairs.

    With a selection, the spatial index is queried exclusively from the
    categorized seed rooms. Other rooms remain eligible as their neighbors.
    Supports both Shapely 1.x geometry hits and Shapely 2.x integer hits.
    """
    if selected_guids is None:
        ordered = sorted(shapes.values(), key=lambda s: s.bounds[0])
        for i, a in enumerate(ordered):
            for b in ordered[i+1:]:
                if b.bounds[0] > a.bounds[3] + max_gap:
                    break
                yield a, b
        return

    if not selected_guids:
        return
    from shapely.strtree import STRtree
    items = list(shapes.values())
    if not items:
        return
    envelopes = [box(s.bounds[0], s.bounds[1], s.bounds[3], s.bounds[4])
                 for s in items]
    tree = STRtree(envelopes)
    by_identity = {id(g): i for i, g in enumerate(envelopes)}
    seen = set()
    for seed in items:
        if seed.guid not in selected_guids:
            continue
        x0, y0, _, x1, y1, _ = seed.bounds
        for hit in tree.query(box(x0-max_gap, y0-max_gap, x1+max_gap, y1+max_gap)):
            if hasattr(hit, 'geom_type'):  # Shapely 1.x
                j = by_identity[id(hit)]
            else:  # Shapely 2.x
                j = int(hit)
            other = items[j]
            if seed.guid == other.guid:
                continue
            key = tuple(sorted((seed.guid, other.guid)))
            if key not in seen:
                seen.add(key)
                yield seed, other


def find_adjacencies(model, spaces: dict, *, selected_guids: set | None = None,
                     progress: Callable[[str], None] | None = None):
    """Return room pairs + diagnostics (read-only IFC).

    When selected_guids is supplied, only room pairs touching at least one
    categorized seed room are investigated. All rooms remain available as
    potential neighbors, even when uncategorized or on another IFC level.
    """
    def status(msg):
        if progress:
            progress(msg)
    import ifcopenshell.geom
    if selected_guids is not None:
        selected_guids = set(selected_guids) & set(spaces)
    status("Checking explicit IFC space boundaries...")
    explicit = _explicit_boundaries(model, selected_guids)
    status(f"Loading room geometry ({len(spaces)} IfcSpace)...")
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shapes = {}
    failed = []
    for index, (guid, space) in enumerate(spaces.items()):
        if index % 30 == 0:
            status(f"Loading room geometry: {index}/{len(spaces)}")
        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            item = shape_from_arrays(guid, shape.geometry.verts, shape.geometry.faces)
            if item:
                shapes[guid] = item
            else:
                failed.append(guid)
        except Exception:
            failed.append(guid)
    status("Checking shared IFC building elements (including without 2nd-level boundaries)...")
    from ifc_relation_analysis import add_boundary_candidates
    found = dict(explicit)
    boundary_candidates = add_boundary_candidates(
        model, found, shapes, selected_guids=selected_guids
    )
    status("Searching geometric adjacencies around categorized rooms...")
    for i, (a, b) in enumerate(_geometry_pairs(shapes, selected_guids, max_gap=.85)):
        if i % 35 == 0:
            status(f"Checking potential room pairs: {i}")
        key = tuple(sorted((a.guid, b.guid)))
        if key in found:
            continue
        candidate = _candidate_from_geometry(a, b, max_gap=.85)
        if candidate:
            direction, detail = candidate
            found[key] = Adjacency(*key, direction, "Geometrisk kandidat", detail)
    status("Verifying adjacency against walls and slabs...")
    from ifc_relation_analysis import verify_separators
    preflight = verify_separators(model, found, shapes, progress=status)
    status("Checking potential door positions...")
    doors = _door_bbox(model)
    for adj in found.values():
        adj.door_hints = _door_hints(adj, shapes, doors)
    status("Checking IFC relationships between doors, openings, walls, and rooms...")
    door_counts = _autodetect_direct_doors(model, found, shapes, doors)
    absent_counts = _autodetect_absent_doors(model, found, doors, shapes)
    status(f"Found {len(found)} adjacencies/candidates – "
           f"{door_counts['ifc_direct']+door_counts['ifc_wall_and_position']+door_counts['ifc_wall_geometric_pair']} door connections")
    return list(found.values()), {"geometriske_rum":len(shapes),
                                  "prioriterede_rum":(len(selected_guids) if selected_guids is not None else len(spaces)),
                                  "rum_uden_geometri":len(failed),
                                  "eksplicitte_grænser":len(explicit),
                                  "antal_døre":len(doors),
                                  "automatisk_fundne_dørforbindelser":sum(door_counts[k] for k in ("ifc_direct","ifc_wall_and_position","ifc_wall_geometric_pair")),
                                  "rum_uden_geometri_ids":failed,
                                  "kandidater_fra_faelles_bygningsdel": boundary_candidates,
                                  "automatisk_ingen_dor": absent_counts,
                                  **preflight}


def evaluate(adj: Adjacency, spaces: dict, categories: dict, selected_guids: set):
    """One row. Do not substitute unknown door status or unknown categories."""
    if adj.verified == "Afvist":
        return None
    # Only rows relevant to categorized rooms in currently selected levels.
    a_cat = categories.get(adj.a, UNCATEGORIZED)
    b_cat = categories.get(adj.b, UNCATEGORIZED)
    if a_cat == UNCATEGORIZED and b_cat == UNCATEGORIZED:
        return None
    if not ((adj.a in selected_guids and a_cat != UNCATEGORIZED) or
            (adj.b in selected_guids and b_cat != UNCATEGORIZED)):
        return None
    note = adj.detail
    if adj.door_evidence:
        note += ("; detected door: " if adj.door_choice == "Ja"
                 else "; door check: ") + adj.door_evidence
    elif adj.door_hints:
        note += "; " + adj.door_hints
    if a_cat == UNCATEGORIZED or b_cat == UNCATEGORIZED:
        reason = "Room A" if a_cat == UNCATEGORIZED else "Room B"
        if (adj.a if a_cat == UNCATEGORIZED else adj.b) not in selected_guids:
            reason += " (outside the selected levels)"
        return "", "Ikke beregnet", f"{reason} is uncategorized", "", note

    typ1, typ2 = rumtype(a_cat), rumtype(b_cat)
    if Rumtype.UKENDT in (typ1, typ2):
        return "", "Manuel vurdering", "Unknown BR18 room type", "", note

    # BR18 T3.1_FLEKSIBEL is a user-specified partition type, not a
    # door-dependent requirement. Other room pairs still require door review.
    flexible_open_pair = (adj.flexible_choice == "Ja"
                          and adj.direction == "horisontal"
                          and typ1 == Rumtype.AABENT and typ2 == Rumtype.AABENT)
    if adj.door_choice == "Ukendt" and adj.direction == "horisontal" and not flexible_open_pair:
        # Never silently treat 'unknown' as no door. Show both alternatives.
        vals = []
        for door in (False, True):
            r = bestem_lydisolation(Rumpar(Rum(adj.a, typ1), Rum(adj.b, typ2),
                                  adj.direction, doerforbindelse=door,
                                  fleksibel_adskillelse=(adj.flexible_choice=="Ja"),
                                  ekstern_saerlig_stoej=(None if adj.noisy_choice=="Ukendt"
                                                        else adj.noisy_choice=="Ja")))
            if r.krav_db is not None:
                vals.append((door, r.krav_db))
        if not vals:
            initial = bestem_lydisolation(Rumpar(
                Rum(adj.a, typ1), Rum(adj.b, typ2), adj.direction,
                fleksibel_adskillelse=(adj.flexible_choice == "Ja"),
                ekstern_saerlig_stoej=(None if adj.noisy_choice == "Ukendt"
                                      else adj.noisy_choice == "Ja")))
            return "", "Manuel vurdering", initial.forklaring, initial.regel, note
        if len(vals) == 2 and len(set(v for _, v in vals)) == 1:
            # Same number regardless of door, but geometry still needs review.
            note += "; door connection not verified (requirement identical in both cases)"
        else:
            summary = ", ".join(("with door" if door else "without door")+f": ≥{value} dB"
                                for door, value in vals)
            if len(vals) < 2:
                summary += "; alternative case requires manual assessment"
            return "", "Dør skal afklares", summary, "", note

    result = bestem_lydisolation(Rumpar(
        Rum(getattr(spaces.get(adj.a), "Name", "") or adj.a, typ1),
        Rum(getattr(spaces.get(adj.b), "Name", "") or adj.b, typ2),
        retning=adj.direction,
        doerforbindelse=adj.door_choice=="Ja",
        fleksibel_adskillelse=adj.flexible_choice=="Ja",
        ekstern_saerlig_stoej=(None if adj.noisy_choice=="Ukendt" else adj.noisy_choice=="Ja")))
    if result.bemaerkning:
        note += "; " + result.bemaerkning
    if result.krav_db is None:
        return "", "Manuel vurdering", result.forklaring, result.regel, note
    if adj.verified != "Bekræftet":
        return f"≥ {result.krav_db} (provisional)", "Naboskab skal bekræftes", result.forklaring, result.regel, note
    return f"≥ {result.krav_db}", "Beregnet", result.forklaring, result.regel, note
