"""Shared per-level legend and dependency-free vector SVG export.

Each page is an A3 landscape drawing with the same content as the PDF export.
One SVG is produced for each level (SVG does not support PDF-style pages).
"""
from __future__ import annotations

from pathlib import Path
import re
from xml.etree import ElementTree as ET

from rw_heatmap import RW_COLORS, UNCERTAIN_COLOR, NEUTRAL_ROOM_COLOR, overlay_color, rw_value

PAGE_WIDTH = 1190.5511811023623   # A3 landscape, points
PAGE_HEIGHT = 841.8897637795277
MARGIN = 42


def visible_sheet_legend(plan, categories, category_colors, mode, overlays=()):
    """Return only classified categories and mapped R'w colours on THIS level.

    Uncategorized rooms are still drawn in beige, but intentionally omitted
    from the classification legend (the user's documentation convention).
    Requirements not actually drawable on this plan are not listed either.
    """
    present = {categories.get(guid, "Ikke kategoriseret") for guid in plan.get("spaces", {})}
    category_items = ([(name, color) for name, color in category_colors.items()
                       if name != "Ikke kategoriseret" and name in present]
                      if mode in ("classification", "both") else [])
    rw_items = []
    if mode in ("rw", "both"):
        available = {rw_value(pair.rw) for pair, _shape in overlays
                     if overlay_color(pair.status, pair.rw) != UNCERTAIN_COLOR}
        rw_items = [(f"≥ {db} dB", color) for db, color in RW_COLORS.items() if db in available]
        if any(overlay_color(pair.status, pair.rw) == UNCERTAIN_COLOR
               for pair, _shape in overlays):
            rw_items.append(("Unresolved", UNCERTAIN_COLOR))
    return category_items, rw_items


def legend_positions(category_items, rw_items, page_width=PAGE_WIDTH, measure=None, rw_heading="Required R'w:"):
    """Yield legend swatches as (text, colour, x, y_baseline_of_swatch).

    Positions use PDF bottom-left coordinates for consistent PDF/SVG output.
    """
    if measure is None:
        measure = lambda text: len(text) * 5.3
    cat_pos, rw_pos = [], []
    if category_items:
        x, y = MARGIN, 88 if rw_items else 64
        for caption, color in category_items:
            need = 17 + measure(caption) + 16
            if x > MARGIN and x + need > page_width - MARGIN:
                x, y = MARGIN, y - 18
            cat_pos.append((caption, color, x, y))
            x += need
    if rw_items:
        x, y = MARGIN + measure(rw_heading) + 12, 58
        for caption, color in rw_items:
            need = 17 + measure(caption) + 15
            if x > MARGIN and x + need > page_width - MARGIN:
                x, y = MARGIN, y - 18
            rw_pos.append((caption, color, x, y))
            x += need
    return cat_pos, rw_pos


def plan_point_transform(plan, width=PAGE_WIDTH, height=PAGE_HEIGHT):
    """Return a reusable model-coordinate -> PDF page-coordinate mapping."""
    points = [p for loops in plan.get("spaces", {}).values() for poly in loops for p in poly]
    points += [p for a, b in plan.get("walls", ()) for p in (a, b)]
    if not points:
        return None
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    plot_x, plot_y = 55, 125
    plot_w, plot_h = width - 110, height - 215
    factor = min(plot_w / max(xmax-xmin, .01), plot_h / max(ymax-ymin, .01), 250)
    x0 = plot_x + (plot_w - (xmax-xmin)*factor)/2
    y0 = plot_y + (plot_h - (ymax-ymin)*factor)/2
    return lambda p: (x0 + (p[0]-xmin)*factor, y0 + (p[1]-ymin)*factor)


def level_filename(base_path: str | Path, name: str, used_names: set[str] | None = None) -> Path:
    """Return a safe, collision-free .svg filename based on an IFC level name."""
    base = Path(base_path)
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f] |\s+', "_", str(name), flags=re.VERBOSE).strip(" ._")[:65] or "level"
    candidate = base.with_name(f"{base.stem}_{safe}.svg")
    if used_names is not None:
        start, index = candidate.stem, 2
        while candidate.name.casefold() in used_names:
            candidate = candidate.with_name(f"{start}_{index}.svg")
            index += 1
        used_names.add(candidate.name.casefold())
    return candidate


def svg_floor_plan(plan, level, filename, room_labels, categories, category_colors,
                   view_mode, overlays, translate, category_label, output_path):
    """Write a self-contained, editable vector floor plan SVG.

    `room_labels` is a mapping from IFC GUID to the visible room number/name.
    The page matches PDF geometry, lettering, colouring and page legends.
    No page number is included in SVG as requested.
    """
    width, height = PAGE_WIDTH, PAGE_HEIGHT
    root = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "version": "1.1",
        "width": f"{width:.3f}pt", "height": f"{height:.3f}pt",
        "viewBox": f"0 0 {width:.3f} {height:.3f}",
    })
    ET.SubElement(root, "title").text = (translate("BR18 – Room Classification")
        if view_mode == "classification" else translate("BR18 – Required R'w on Floor Plans"))
    ET.SubElement(root, "rect", {
        "x": "0", "y": "0", "width": f"{width:.3f}", "height": f"{height:.3f}",
        "fill": "#FFFFFF"
    })

    def text(x, y, value, size, fill="#222222", anchor=None, weight="normal"):
        props = {"x": f"{x:.3f}", "y": f"{height-y:.3f}", "font-size": str(size),
                 "font-family": "Arial, DejaVu Sans, sans-serif", "font-weight": weight,
                 "fill": fill}
        if anchor:
            props["text-anchor"] = anchor
        ET.SubElement(root, "text", props).text = str(value)

    def rect(x, y, w, h, fill, stroke=None, stroke_width="0.6"):
        attrs = {"x": f"{x:.3f}", "y": f"{height-y-h:.3f}",
                 "width": f"{w:.3f}", "height": f"{h:.3f}", "fill": fill}
        if stroke:
            attrs.update({"stroke": stroke, "stroke-width": stroke_width})
        ET.SubElement(root, "rect", attrs)

    def polygon(points, fill, stroke, stroke_width):
        if len(points) < 3:
            return
        path = " ".join(f"{x:.3f},{height-y:.3f}" for x,y in points)
        ET.SubElement(root, "polygon", {"points": path, "fill": fill,
                                        "stroke": stroke, "stroke-width": str(stroke_width),
                                        "stroke-linejoin": "round"})

    headline = (translate("BR18 – Room Classification") if view_mode == "classification"
                else translate("BR18 – Required R'w on Floor Plans"))
    text(MARGIN, height-42, headline, 17, weight="bold")
    text(MARGIN, height-62, f"{translate('Level:')} {level}   |   IFC: {filename}", 11)

    point = plan_point_transform(plan, width, height)
    if point is not None:
        for guid, loops in plan.get("spaces", {}).items():
            fill = category_colors.get(categories.get(guid, "Ikke kategoriseret"),
                                       category_colors.get("Ikke kategoriseret", "#F1E9D6")) \
                if view_mode in ("classification", "both") else NEUTRAL_ROOM_COLOR
            for poly in loops:
                if len(poly) >= 3:
                    polygon([point(p) for p in poly], fill, "#687789", ".55")
            if loops:
                largest = max(loops, key=lambda poly: abs(_polygon_area(poly)))
                x,y = point(_polygon_centroid(largest))
                text(x, y, str(room_labels.get(guid, guid[:8]))[:26], 7,
                     fill="#203047", anchor="middle")

        for a,b in plan.get("walls", ()):
            x1,y1 = point(a); x2,y2 = point(b)
            ET.SubElement(root, "line", {"x1": f"{x1:.3f}", "y1": f"{height-y1:.3f}",
                                         "x2": f"{x2:.3f}", "y2": f"{height-y2:.3f}",
                                         "stroke": "#303943", "stroke-width": ".8"})
        if view_mode in ("rw", "both"):
            for pair, shape in overlays:
                polygon([point(p) for p in list(shape.exterior.coords)],
                        overlay_color(pair.status,pair.rw), "#424950", ".4")

    cat_entries, rw_entries = visible_sheet_legend(plan, categories, category_colors,
                                                     view_mode, overlays)
    cat_entries = [(category_label(name), color) for name, color in cat_entries]
    rw_entries = [(translate(label) if label == "Unresolved" else label, color)
                  for label, color in rw_entries]
    rw_heading = translate("Required R'w:")
    cat_pos, rw_pos = legend_positions(cat_entries, rw_entries, page_width=width, rw_heading=rw_heading)
    for caption, color, x, y in cat_pos + rw_pos:
        rect(x, y, 13, 11, color, "#222222")
        text(x+17, y+2, caption, 9, fill="#1A1A1A")

    if rw_pos:
        text(MARGIN, 60, rw_heading, 9, fill="#1A1A1A")
    note = (translate("Categories per BR18 Section 3.1") if view_mode == "classification"
            else translate("Model-based R'w wall mapping"))
    text(MARGIN, 33, f"{translate('Rooms:')} {len(plan.get('spaces',{}))} | {note} | "
         f"{translate('IFC geometry, automatically generated section')}", 8)
    text(width-MARGIN,33,translate("Drawing not to scale – verify against the original model"),
         8, anchor="end")

    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return Path(output_path)


def _polygon_area(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1] - poly[(i+1)%len(poly)][0]*poly[i][1]
               for i in range(len(poly)))/2


def _polygon_centroid(poly):
    area = _polygon_area(poly)
    if not poly:
        return (0.0,0.0)
    if abs(area) < 1e-10:
        return (sum(x for x,y in poly)/len(poly), sum(y for x,y in poly)/len(poly))
    cx = sum((poly[i][0]+poly[(i+1)%len(poly)][0]) *
             (poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1])
             for i in range(len(poly))) / (6*area)
    cy = sum((poly[i][1]+poly[(i+1)%len(poly)][1]) *
             (poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1])
             for i in range(len(poly))) / (6*area)
    return cx,cy
