"""Automatic IFC separator verification; no assumptions based on storey names.

Evidence order:
  * Pairwise corresponding IFC space boundaries (handled in ifc_acoustics).
  * Shared IFC space-boundary host with corroborating physical geometry.
  * Physical wall/slab geometry separating the actual 3D room solids.

When no reliable evidence exists the pair remains a *candidate*.

IfcOpenShell meshes produced by create_shape use SI metres unless explicitly
configured otherwise. The caller must NOT rescale the returned vertices again.
"""
from __future__ import annotations

from collections import defaultdict
from bisect import bisect_right

# Shapely/IfcOpenShell are supplied by the existing application.


def _id(entity):
    if entity is None:
        return None
    guid = getattr(entity, 'GlobalId', None)
    return ('guid', str(guid)) if guid else ('id', entity.id())


def _kind(entity):
    if entity is None:
        return None
    for cls, kind in (("IfcWall", "horisontal"), ("IfcSlab", "vertikal"),
                      ("IfcRoof", "vertikal"), ("IfcCurtainWall", "horisontal")):
        try:
            if entity.is_a(cls):
                return kind
        except Exception:
            pass
    return None


def get_boundary_index(model):
    """Returns maps of room-to-elements and element-to-relations.

    Never infer adjacency from sharing an element alone: a long host wall
    can adjoin many spaces on the same side or on different levels.
    """
    per_room = defaultdict(set)
    per_element = defaultdict(list)
    elements = {}
    counts = defaultdict(int)
    for rel in model.by_type("IfcRelSpaceBoundary"):
        space = getattr(rel, 'RelatingSpace', None)
        element = getattr(rel, 'RelatedBuildingElement', None)
        if space is None or element is None or not space.is_a('IfcSpace'):
            continue
        element_key = _id(element)
        room_key = str(space.GlobalId)
        per_room[room_key].add(element_key)
        per_element[element_key].append((room_key, rel))
        elements[element_key] = element
        if rel.is_a('IfcRelSpaceBoundary2ndLevel'):
            counts['2nd'] += 1
        elif rel.is_a('IfcRelSpaceBoundary1stLevel'):
            counts['1st'] += 1
        else:
            counts['generic'] += 1
    return per_room, per_element, elements, dict(counts)


def horizontal_match(a, b, wall, *, tolerance=1.25, min_shared_length=0.75):
    """Wall slice must lie *on the facing portion* of BOTH space boundaries.

    This rejects rooms that only touch at a corner or share a long wall id but
    touch completely different portions of that wall.
    """
    low, high = max(a.bounds[2], b.bounds[2], wall.bounds[2]), min(a.bounds[5], b.bounds[5], wall.bounds[5])
    if high-low < .30:
        return False
    # Try several heights: a doorway creates a hole in a wall's geometry.
    for ratio in (.54, .78, .28):
        z = low + (high-low)*ratio
        pa, pb, pw = a.footprint(z), b.footprint(z), wall.footprint(z)
        if pa is None or pb is None or pw is None:
            continue
        if pa.is_empty or pb.is_empty or pw.is_empty or pa.distance(pb) > tolerance:
            continue
        if pa.intersection(pb).area > max(.25, min(pa.area, pb.area)*.07):
            continue
        face_a = pa.boundary.intersection(pb.boundary.buffer(tolerance))
        face_b = pb.boundary.intersection(pa.boundary.buffer(tolerance))
        if face_a.length < min_shared_length or face_b.length < min_shared_length:
            continue
        wall_region = pw.buffer(.20)
        overlap_a = face_a.intersection(wall_region).length
        overlap_b = face_b.intersection(wall_region).length
        if min(overlap_a, overlap_b) >= min_shared_length:
            return True
    return False


def vertical_match(a, b, slab):
    """Physical slab must span the gap and cover the rooms' shared XY area."""
    lower, upper = (a, b) if a.bounds[2] < b.bounds[2] else (b, a)
    gap_start, gap_end = lower.bounds[5], upper.bounds[2]
    # A large space intersecting a storey does not make it a vertical neighbour
    # of every room on that level.
    if not (-.12 <= gap_end - gap_start <= .75):
        return False
    if slab.bounds[5] < gap_start-.12 or slab.bounds[2] > gap_end+.12:
        return False
    if slab.bounds[5] - slab.bounds[2] < .01:
        return False
    z_slab = (slab.bounds[2]+slab.bounds[5])/2
    z_low = lower.bounds[5]-min(.25, (lower.bounds[5]-lower.bounds[2])*.2)
    z_up = upper.bounds[2]+min(.25, (upper.bounds[5]-upper.bounds[2])*.2)
    ps = slab.footprint(z_slab)
    pl, pu = lower.footprint(z_low), upper.footprint(z_up)
    if any(g is None or g.is_empty for g in (ps, pl, pu)):
        return False
    shared = pl.intersection(pu)
    if shared.area < .75 or shared.area < min(pl.area, pu.area)*.10:
        return False
    return shared.intersection(ps).area >= max(.65, shared.area*.65)


def add_boundary_candidates(model, found, shapes, *, selected_guids=None):
    """Include 1st-level shared host walls/slabs even if room-to-room link absent.

    A shared wall ID alone is NOT confirmation. A candidate is emitted when
    floor-height/plan proximity supports a potential physical separation, and
    subsequently must pass separator verification or user review.
    """
    from itertools import combinations
    from ifc_acoustics import Adjacency, _candidate_from_geometry

    _, per_element, elements, _ = get_boundary_index(model)
    added = 0
    for host_key, rows in per_element.items():
        kind = _kind(elements.get(host_key))
        if kind is None:
            continue
        guids = sorted({room for room, _ in rows})
        # Avoid an unbounded Cartesian explosion on a wall spanning a whole
        # atrium. Use the actual room location whenever available.
        if selected_guids is None:
            pairs = combinations(guids, 2)
        else:
            seeds = [g for g in guids if g in selected_guids]
            others = [g for g in guids if g not in selected_guids]
            # Only examine seed/seed and seed/other pairs; never other/other.
            from itertools import chain, product
            pairs = chain(combinations(seeds, 2), product(seeds, others))
        for a, b in pairs:
            key = tuple(sorted((a,b)))
            if key in found:
                continue
            sa, sb = shapes.get(a), shapes.get(b)
            if sa is not None and sb is not None:
                if kind == 'horisontal':
                    # Include thick walls, but only reasonably close room edges.
                    candidate = _candidate_from_geometry(sa, sb, max_gap=1.25)
                    if candidate is None or candidate[0] != 'horisontal':
                        continue
                else:
                    candidate = _candidate_from_geometry(sa, sb, max_gap=1.25)
                    if candidate is None or candidate[0] != 'vertikal':
                        continue
            adj = Adjacency(*key, kind, 'Shared IFC building element (requires verification)',
                            'Same building element in space boundaries; physical separator being verified')
            adj.separator_keys = (host_key,)
            found[key] = adj
            added += 1
    return added


def _overlaps_bbox(b1, b2, pad=.28):
    return all((b1[i] <= b2[i+3]+pad and b2[i] <= b1[i+3]+pad) for i in range(3))


def verify_separators(model, adjacencies, shapes, *, progress=None):
    """Auto-confirm room pairs only with *specific* physical wall/slab evidence.

    `adjacencies` values are mutable Adjacency objects from ifc_acoustics.
    Returns diagnostics. `separator_keys` identifies host wall/slab for door lookup.
    """
    from ifc_acoustics import shape_from_arrays
    import ifcopenshell.geom

    per_room, per_element, elements, boundary_counts = get_boundary_index(model)
    if progress:
        progress('Checking space boundaries and shared walls/slabs ...')
    for adj in adjacencies.values():
        common = per_room.get(adj.a, set()) & per_room.get(adj.b, set())
        if common:
            valid = sorted((key for key in common if _kind(elements.get(key)) == adj.direction), key=str)
            if valid:
                adj.separator_keys = tuple(valid)
    # Build geometry of physical separators, regardless of their assigned Revit level.
    all_components = {}
    for cls in ('IfcWall', 'IfcSlab', 'IfcRoof', 'IfcCurtainWall'):
        for element in model.by_type(cls):
            key = _id(element)
            if key not in all_components:
                all_components[key] = element
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    components = []
    failures = 0
    for n, (key, el) in enumerate(all_components.items()):
        if n % 75 == 0 and progress:
            progress(f'Checking wall/slab geometry: {n}/{len(all_components)}')
        kind = _kind(el)
        if kind is None:
            continue
        try:
            geom = ifcopenshell.geom.create_shape(settings, el).geometry
            sh = shape_from_arrays(str(key), geom.verts, geom.faces)
            if sh:
                components.append((key, kind, sh))
            else:
                failures += 1
        except Exception:
            failures += 1

    # Sorted by minimum x. Range query avoids comparing every pair to every wall.
    components.sort(key=lambda entry: entry[2].bounds[0])
    xmins = [e[2].bounds[0] for e in components]
    confirmed = {'shared_ifc': 0, 'separator_geometry': 0,
                 'corresponding': sum(a.verified == 'Bekræftet' for a in adjacencies.values())}
    for idx, adj in enumerate(adjacencies.values()):
        if idx % 75 == 0 and progress:
            progress(f'Verifying room pairs: {idx}/{len(adjacencies)}')
        a, b = shapes.get(adj.a), shapes.get(adj.b)
        if not a or not b:
            continue
        previously_confirmed = adj.verified == 'Bekræftet'
        # Keys from a merely proposed shared boundary are not verified yet;
        # keys from corresponding 2nd-level boundaries are positive evidence.
        existing_keys = tuple(adj.separator_keys) if previously_confirmed else ()
        common_keys = per_room.get(adj.a, set()) & per_room.get(adj.b, set())
        max_x = max(a.bounds[3], b.bounds[3]) + .28
        limit = bisect_right(xmins, max_x)
        matched = []
        for key, kind, sep in components[:limit]:
            if kind != adj.direction:
                continue
            if not _overlaps_bbox(sep.bounds, a.bounds) or not _overlaps_bbox(sep.bounds, b.bounds):
                continue
            if adj.direction == 'horisontal':
                good = horizontal_match(a, b, sep)
            else:
                good = vertical_match(a, b, sep)
            if good:
                # Never stop at the first wall. Two rooms may share multiple
                # distinct wall elements, possibly oriented at 90 degrees.
                matched.append(key)
        if matched:
            # Retain explicit corresponding boundaries even when a particular
            # element cannot be re-sliced at the sampled elevations.
            adj.separator_keys = tuple(dict.fromkeys((*existing_keys, *matched)))
            if not previously_confirmed:
                is_shared = any(key in common_keys for key in matched)
                flag = 'shared_ifc' if is_shared else 'separator_geometry'
                adj.verified = 'Bekræftet'
                adj.evidence = ('Shared IFC wall/slab + 3D geometry' if is_shared
                                else 'Shared wall/slab verified geometrically')
                adj.detail += '; identified IFC separation(s): ' + ', '.join(str(k[1]) for k in matched)
                confirmed[flag] += 1
    return {
        'space_boundaries': boundary_counts,
        'fysiske_bygningsdele': len(components),
        'bygningsdele_uden_geometri': failures,
        'naboskab_verificeret': confirmed,
        'naboskab_ubekraeftet': sum(a.verified != 'Bekræftet' for a in adjacencies.values()),
    }
