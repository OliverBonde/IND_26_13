"""IFC Room Classifier — BR18 section 3.1 (educational buildings).

Run: python main.py
Install: python -m pip install ifcopenshell
"""
from __future__ import annotations

import csv
import queue
import threading
import math
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from ui_english import (CATEGORIES_EN, category_en, category_internal, category_display,
                        ui_t)
from floor_plan_export import (visible_sheet_legend, legend_positions,
                               svg_floor_plan, level_filename, plan_point_transform)

try:
    import ifcopenshell
    import ifcopenshell.util.element
except ImportError:
    ifcopenshell = None

CATEGORIES = (
    "Ikke kategoriseret",
    "Undervisningsrum",
    "Fællesrum",
    "Åbne undervisningsområder",
    "Sløjdundervisningsrum",
    "Sang- og musikundervisningsrum",
    "Ekstern enhed/institution",
)
PSET_NAME = "Pset_BR18_RoomClassification"
PROPERTY_NAME = "BR18_RoomType"


class ClassifierApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = tk.StringVar(value="English")
        self.title(self.tr("IFC Room Classifier | BR18 Sections 3.1 and 3.2"))
        self.geometry("1160x660")
        self.minsize(840, 460)
        self.model = None
        self.filepath: Path | None = None
        self.spaces = {}
        self.all_spaces = {}
        self.selected_levels = set()
        self.categories = {}
        self.editor = None
        self.sort_column = "number"
        self.sort_reverse = False
        self.plan_window = None
        self.result_windows = []
        self.area_cache = {}
        self.category_filter = tk.StringVar(value="All Categories")
        self.search_text = tk.StringVar()
        self.info = tk.StringVar(value=self.tr("Select an IFC file to get started."))
        self.build_ui()
        self.search_text.trace_add("write", lambda *_: self.refresh())

    def tr(self, english):
        return ui_t(english, self.language.get())

    def category_label(self, category):
        return category_display(category, self.language.get())

    def change_language(self, _event=None):
        """Relabel existing windows without changing IFC data or calculations."""
        if self.editor is not None:
            self.editor.destroy()
            self.editor = None
        selected = self.table.selection() if hasattr(self, 'table') else ()
        current_filter = category_internal(self.category_filter.get())
        bulk = category_internal(self.bulk_category.get()) if hasattr(self, 'bulk_category') else "Undervisningsrum"
        for child in list(self.winfo_children()):
            if not isinstance(child, tk.Toplevel):
                child.destroy()
        self.title(self.tr("IFC Room Classifier | BR18 Sections 3.1 and 3.2"))
        self.category_filter.set(self.tr("All Categories") if current_filter in ("All Categories", "Alle kategorier") else self.category_label(current_filter))
        self.build_ui()
        self.bulk_category.set(self.category_label(bulk))
        self.refresh()
        restore = [gid for gid in selected if self.table.exists(gid)]
        if restore:
            self.table.selection_set(restore)
        if self.plan_window and self.plan_window.win.winfo_exists():
            self.plan_window.relocalize()
        for window in list(self.result_windows):
            if window.win.winfo_exists():
                window.relocalize()
            else:
                self.result_windows.remove(window)

    def build_ui(self):
        bar = ttk.Frame(self, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text=self.tr("Open IFC File"), command=self.open_ifc).pack(side="left")
        ttk.Button(bar, text=self.tr("Select Levels"), command=self.choose_levels_again).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text=self.tr("Show Floor Plan"), command=self.show_plan).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text=self.tr("Export CSV"), command=self.save_csv).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text=self.tr("Calculate Required R'w"), command=self.calculate_rw).pack(side="left", padx=(12, 0))
        lang_frame = ttk.Frame(bar)
        lang_frame.pack(side="right", padx=(5, 0))
        ttk.Label(lang_frame, text=self.tr("Language:")).pack(side="left", padx=(0, 6))
        language_box = ttk.Combobox(lang_frame, state="readonly", textvariable=self.language,
                                     values=("English", "Dansk"), width=9)
        language_box.pack(side="left")
        language_box.bind("<<ComboboxSelected>>", self.change_language)

        self.content = ttk.Frame(self)
        ttk.Label(self.content, text=self.tr("BR18 Room Classification – Educational Buildings"), font=("Segoe UI", 15, "bold"), padding=(12, 8)).pack(anchor="w")
        controls = ttk.Frame(self.content, padding=(12, 4))
        controls.pack(fill="x")
        ttk.Label(controls, text=self.tr("Search:")).pack(side="left")
        entry = ttk.Entry(controls, textvariable=self.search_text, width=28)
        entry.pack(side="left", padx=(5, 16))
        ttk.Label(controls, text=self.tr("Show:")).pack(side="left")
        filters = (self.tr("All Categories"),) + tuple(self.category_label(c) for c in CATEGORIES)
        filter_box = ttk.Combobox(controls, textvariable=self.category_filter, values=filters, state="readonly", width=28)
        filter_box.pack(side="left", padx=5)
        filter_box.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        holder = ttk.Frame(self.content, padding=(12, 8))
        holder.pack(fill="both", expand=True)
        cols = ("number", "name", "storey", "longname", "area", "category")
        self.table = ttk.Treeview(holder, columns=cols, show="headings", selectmode="extended")
        for col, heading, width in [
            ("number", self.tr("Room No."), 110), ("name", self.tr("IFC Room Name"), 200),
            ("storey", self.tr("Level"), 130), ("longname", self.tr("Description"), 210),
            ("area", self.tr("IFC Area (m²)"), 110), ("category", self.tr("BR18 Category"), 220),
        ]:
            self.table.heading(col, text=heading, command=lambda c=col: self.sort_by(c))
            self.table.column(col, width=width, minwidth=75, stretch=True)
        self.table.tag_configure("Undervisningsrum", background="#b7dfca", foreground="#172b25")
        self.table.tag_configure("Fællesrum", background="#ced8e5", foreground="#172b3a")
        self.table.tag_configure("Åbne undervisningsområder", background="#d6c7ed", foreground="#282037")
        self.table.tag_configure("Ikke kategoriseret", background="#f1e9d6", foreground="#292923")
        self.table.tag_configure("Sløjdundervisningsrum", background="#f9c9ab", foreground="#452b1b")
        self.table.tag_configure("Sang- og musikundervisningsrum", background="#f0b8c9", foreground="#452137")
        self.table.tag_configure("Ekstern enhed/institution", background="#e0d1bc", foreground="#382c1c")
        yscroll = ttk.Scrollbar(holder, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=yscroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.table.bind("<Double-1>", self.edit_category)
        self.table.bind("<<TreeviewSelect>>", self.table_selected)

        lower = ttk.Frame(self.content, padding=(12, 6))
        lower.pack(fill="x")
        ttk.Label(lower, text=self.tr("Category for Selected Rooms:")).pack(side="left")
        self.bulk_category = tk.StringVar(value=self.category_label("Undervisningsrum"))
        ttk.Combobox(lower, textvariable=self.bulk_category, values=tuple(self.category_label(c) for c in CATEGORIES), state="readonly", width=29).pack(side="left", padx=8)
        ttk.Button(lower, text=self.tr("Apply to Selected"), command=self.bulk_assign).pack(side="left")
        ttk.Label(lower, text=self.tr("Double-click a BR18 category to change an individual room."), foreground="#555").pack(side="right")
        # On language changes the UI is rebuilt, but the IFC data and selected
        # levels are retained. Restore the classifier table *before* the status
        # bar, just as activate_levels() does after the first level selection.
        if self.model is not None and self.selected_levels:
            self.content.pack(fill="both", expand=True)
        ttk.Label(self, textvariable=self.info, padding=(12, 12), relief="sunken", anchor="w").pack(fill="x")

    @staticmethod
    def levels_in_model(model, spaces):
        """List storey names plus an optional bucket for unassigned spaces.

        Counts describe IFC spatial assignment, not geometric overlap.
        """
        from collections import Counter
        counts = Counter(ClassifierApp.storey(space) or "Uden etage" for space in spaces)
        levels = []
        try:
            import ifcopenshell.util.placement
            import ifcopenshell.util.unit
            scale = ifcopenshell.util.unit.calculate_unit_scale(model)
        except Exception:
            scale = 1.0
        for floor in model.by_type("IfcBuildingStorey"):
            name = floor.Name or f"Level #{floor.id()}"
            try:
                elev = float(ifcopenshell.util.placement.get_local_placement(floor.ObjectPlacement)[2][3]) * scale
            except Exception:
                elev = float(floor.Elevation or 0) * scale
            if name not in [item[0] for item in levels]:
                levels.append((name, elev, counts[name]))
        levels.sort(key=lambda item: (item[1], item[0]))
        if counts["Uden etage"]:
            levels.append(("Uden etage", None, counts["Uden etage"]))
        # If an IFC has spaces but no valid storeys, still allow continuing.
        if not levels and spaces:
            levels = [("Uden etage", None, len(spaces))]
        return levels

    @staticmethod
    def default_checked_levels(levels, previously_selected=None):
        """Initially check only storeys with assigned IfcSpace objects.

        Explicit choices made in an earlier dialog take precedence, including
        selecting an otherwise empty storey.
        """
        if previously_selected is not None:
            return set(previously_selected)
        return {name for name, _elevation, count in levels if count > 0}

    def level_dialog(self, model, all_spaces, previously_selected=None):
        """Modal selection before the model/table is committed. None means cancel."""
        levels = self.levels_in_model(model, list(all_spaces.values()))
        if not levels:
            messagebox.showwarning(self.tr("No Levels Found"), self.tr("No levels or rooms were found in the IFC file."), parent=self)
            return None
        dialog = tk.Toplevel(self)
        dialog.title(self.tr("Select Revit Levels / IFC Storeys"))
        dialog.geometry("540x540")
        dialog.minsize(450, 420)
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=self.tr("Select Levels to Include"), font=("Segoe UI", 13, "bold"),
                  padding=(15, 15, 15, 6)).pack(anchor="w")
        ttk.Label(dialog, text=self.tr("Only spaces assigned to selected IFC levels will appear in the table.\n"
                 "Tall spaces may still appear on multiple selected floor plans."),
                  padding=(15, 0, 15, 12)).pack(anchor="w")
        outer = ttk.Frame(dialog, padding=(15, 0, 15, 8))
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        checklist = ttk.Frame(canvas)
        item_id = canvas.create_window((0, 0), window=checklist, anchor="nw")
        checklist.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item_id, width=e.width))
        defaults = self.default_checked_levels(levels, previously_selected)
        variables = {}
        for name, elevation, count in levels:
            var = tk.BooleanVar(value=name in defaults)
            variables[name] = var
            elev_text = f" · {self.tr('elevation')} {elevation:.2f} m" if elevation is not None else ""
            ttk.Checkbutton(checklist, text=f"{(self.tr('Unassigned Level') if name == 'Uden etage' else name)}{elev_text} · {count} {self.tr('assigned spaces')}",
                            variable=var).pack(fill="x", anchor="w", pady=5)
        choice = {"value": None}
        footer = ttk.Frame(dialog, padding=15)
        footer.pack(fill="x")
        def set_all(value):
            for var in variables.values():
                var.set(value)
        def accept():
            selected = {name for name, var in variables.items() if var.get()}
            if not selected:
                messagebox.showwarning(self.tr("Select Level"), self.tr("Select at least one level."), parent=dialog)
                return
            choice["value"] = selected
            dialog.destroy()
        ttk.Button(footer, text=self.tr("All"), command=lambda: set_all(True)).pack(side="left")
        ttk.Button(footer, text=self.tr("None"), command=lambda: set_all(False)).pack(side="left", padx=6)
        ttk.Button(footer, text=self.tr("Cancel"), command=dialog.destroy).pack(side="right")
        ttk.Button(footer, text=self.tr("Show Selected Levels"), command=accept).pack(side="right", padx=8)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.wait_window(dialog)
        return choice["value"]

    def activate_levels(self, selected):
        self.selected_levels = set(selected)
        self.spaces = {guid: space for guid, space in self.all_spaces.items()
                       if (self.storey(space) or "Uden etage") in self.selected_levels}
        for guid, space in self.spaces.items():
            if guid not in self.categories:
                try:
                    psets = ifcopenshell.util.element.get_psets(space)
                    stored = psets.get(PSET_NAME, {}).get(PROPERTY_NAME)
                except Exception:
                    stored = None
                self.categories[guid] = category_internal(stored) if category_internal(stored) in CATEGORIES else CATEGORIES[0]
        if not self.content.winfo_manager():
            self.content.pack(fill="both", expand=True)
        self.refresh()
        if self.plan_window is not None:
            self.plan_window.load()

    def choose_levels_again(self):
        if self.model is None:
            messagebox.showinfo(self.tr("No IFC File"), self.tr("Please select an IFC file first."))
            return
        selected = self.level_dialog(self.model, self.all_spaces, self.selected_levels)
        if selected is not None:
            self.activate_levels(selected)

    def open_ifc(self):
        if ifcopenshell is None:
            messagebox.showerror(self.tr("Missing Dependency"), "Install IfcOpenShell using:\npython -m pip install ifcopenshell")
            return
        filename = filedialog.askopenfilename(title="Select IFC File", filetypes=[("IFC Files", "*.ifc"), ("All Files", "*.*")])
        if not filename:
            return
        try:
            model = ifcopenshell.open(filename)
            spaces = {space.GlobalId: space for space in model.by_type("IfcSpace")}
        except Exception as exc:
            messagebox.showerror(self.tr("Failed to Read IFC File"), str(exc))
            return
        # Do not show or modify the current table before the user confirms levels.
        selected = self.level_dialog(model, spaces)
        if selected is None:
            return
        if self.plan_window is not None:
            self.plan_window.close()
        self.model = model
        self.filepath = Path(filename)
        self.all_spaces = spaces
        self.categories = {}
        self.area_cache = {}
        self.activate_levels(selected)
        if not spaces:
            messagebox.showwarning(self.tr("No Rooms Found"), self.tr("No IfcSpace objects were found."))

    @staticmethod
    def storey(space):
        try:
            for rel in space.Decomposes or []:
                parent = rel.RelatingObject
                if parent.is_a("IfcBuildingStorey"):
                    return parent.Name or ""
        except Exception:
            pass
        try:
            for rel in getattr(space, "ContainedInStructure", []) or []:
                parent = rel.RelatingStructure
                if parent.is_a("IfcBuildingStorey"):
                    return parent.Name or ""
        except Exception:
            pass
        return ""

    @staticmethod
    def _area_unit_to_m2(unit):
        """Convert explicit IFC area unit to square metres, if known."""
        if unit is None:
            return None
        prefixes = {"EXA": 1e18, "PETA": 1e15, "TERA": 1e12,
                    "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3,
                    "HECTO": 1e2, "DECA": 1e1, "DECI": 1e-1,
                    "CENTI": 1e-2, "MILLI": 1e-3,
                    "MICRO": 1e-6, "NANO": 1e-9}
        try:
            if unit.is_a("IfcSIUnit"):
                if unit.UnitType != "AREAUNIT" or unit.Name != "SQUARE_METRE":
                    return None
                prefix = prefixes.get(unit.Prefix, 1.0) if unit.Prefix else 1.0
                return prefix ** 2
            if unit.is_a("IfcConversionBasedUnit"):
                conversion = unit.ConversionFactor
                base_scale = ClassifierApp._area_unit_to_m2(conversion.UnitComponent)
                return (float(conversion.ValueComponent.wrappedValue) * base_scale
                        if base_scale is not None else None)
        except (AttributeError, TypeError, ValueError):
            pass
        return None

    def _project_area_scale(self):
        try:
            import ifcopenshell.util.unit
            return float(ifcopenshell.util.unit.calculate_unit_scale(self.model, "AREAUNIT"))
        except Exception:
            return None

    def _area_candidates(self, space):
        """Read actual IfcSpace quantity/property values, never plan geometry.

        Returns (priority, value_m2, source). Prefer an explicit IfcQuantityArea
        over properties. Do not treat a unitless property as m² blindly.
        """
        candidates = []
        project_scale = self._project_area_scale()
        def priority_of(name):
            n = re.sub(r"[^a-z0-9]", "", str(name or "").lower())
            return {"netfloorarea": 0, "netarea": 1, "roomarea": 2,
                    "spacearea": 3, "area": 4, "grossfloorarea": 5,
                    "grossarea": 6}.get(n)

        def add(name, raw, source, unit, is_quantity):
            prio = priority_of(name)
            if prio is None or raw is None or isinstance(raw, bool):
                return
            if hasattr(raw, "wrappedValue"):
                raw = raw.wrappedValue
            try:
                value = float(str(raw).replace(",", "."))
            except (ValueError, TypeError):
                return
            if not math.isfinite(value) or value <= 0:
                return
            scale = self._area_unit_to_m2(unit)
            if scale is None and is_quantity:
                scale = project_scale
            # For numeric properties with no declared unit, the data is ambiguous:
            # a value of 25,000,000 may be mm² or another unit. Do not export it
            # as 25,000,000 m². Prefer a proper quantity / explicit unit instead.
            if scale is None:
                return
            area_m2 = value * scale
            if math.isfinite(area_m2) and area_m2 > 0:
                candidates.append((prio + (0 if is_quantity else 100), area_m2, source))

        for rel in getattr(space, "IsDefinedBy", None) or ():
            try:
                if not rel.is_a("IfcRelDefinesByProperties"):
                    continue
                definition = rel.RelatingPropertyDefinition
                set_name = definition.Name or ""
                if definition.is_a("IfcElementQuantity"):
                    for item in definition.Quantities or ():
                        if item.is_a("IfcQuantityArea"):
                            add(item.Name, item.AreaValue,
                                f"{set_name}.{item.Name}", item.Unit, True)
                elif definition.is_a("IfcPropertySet"):
                    for prop in definition.HasProperties or ():
                        if prop.is_a("IfcPropertySingleValue"):
                            add(prop.Name, prop.NominalValue,
                                f"{set_name}.{prop.Name}", prop.Unit, False)
            except Exception:
                continue
        return sorted(candidates, key=lambda x: (x[0], x[2]))

    def area(self, guid):
        """Read IFC-reported area in m²; blank if unit cannot be verified."""
        if guid not in self.area_cache:
            candidates = self._area_candidates(self.spaces[guid])
            self.area_cache[guid] = candidates[0][1] if candidates else None
        return self.area_cache[guid]

    def room_number(self, space):
        # Revit exports differ; prefer explicit room-number property.
        try:
            psets = ifcopenshell.util.element.get_psets(space)
            for data in psets.values():
                if isinstance(data, dict):
                    for key in ("Number", "RoomNumber", "Room Number"):
                        if data.get(key) not in (None, ""):
                            return str(data[key])
        except Exception:
            pass
        return str(space.Description or "")

    def rows(self):
        for guid, space in self.spaces.items():
            yield (space.Name or "", space.LongName or "", self.storey(space), self.categories[guid], guid)

    def refresh(self):
        previously_selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        query = self.search_text.get().casefold().strip()
        filter_value = category_internal(self.category_filter.get())
        if filter_value == self.tr("All Categories"):
            filter_value = "All Categories"
        for name, longname, storey, category, guid in self.rows():
            space = self.spaces[guid]
            area = self.area(guid)
            values = (self.room_number(space), name, storey, longname,
                      f"{area:.2f}" if area is not None else "", self.category_label(category))
            if query and not any(query in str(x).casefold() for x in values):
                continue
            if filter_value not in ("All Categories", "Alle kategorier") and category != filter_value:
                continue
            self.table.insert("", "end", iid=guid, values=values, tags=(category,))
        self.apply_sort()
        restore = [guid for guid in previously_selected if self.table.exists(guid)]
        if restore:
            self.table.selection_set(restore)
        n = len(self.spaces)
        done = sum(v != CATEGORIES[0] for v in self.categories.values())
        source = self.filepath.name if self.filepath else self.tr("No File")
        self.info.set(f"{source}  |  {len(self.selected_levels)} {self.tr('selected levels')}  |  {n} IfcSpace {self.tr('on selected levels')}  |  {done}/{n} {self.tr('categorized')}  |  {len(self.table.get_children())} {self.tr('displayed')}")

    def apply_sort(self):
        col = self.sort_column
        elevations = ({name: elev for name, elev, _ in
                       self.levels_in_model(self.model, list(self.all_spaces.values()))}
                      if col == "storey" and self.model else {})
        def key(iid):
            value = self.table.set(iid, col).strip()
            if col == "storey":
                # Sort by numerical IFC storey elevation, not by level name.
                # Ascending => lowest elevation first, regardless of naming.
                floor = self.storey(self.spaces[iid])
                elev = elevations.get(floor)
                return (1, 0.0, floor.casefold()) if elev is None else (0, float(elev), floor.casefold())
            if col == "area":
                try:
                    return (0, float(value.replace(",", ".")))
                except ValueError:
                    return (1, 0)
            if col == "number":
                import re
                return tuple((0, int(t)) if t.isdigit() else (1, t.casefold())
                             for t in re.split(r"(\d+)", value))
            return value.casefold()
        rows = sorted(self.table.get_children(), key=key, reverse=self.sort_reverse)
        for i, iid in enumerate(rows):
            self.table.move(iid, "", i)
        for c in self.table["columns"]:
            self.table.heading(c, text={"number":self.tr("Room No."),"name":self.tr("IFC Room Name"), "storey":self.tr("Level"),
                                        "longname":self.tr("Description"), "area":self.tr("IFC Area (m²)"),
                                        "category":self.tr("BR18 Category")}[c] +
                               (" ▼" if self.sort_reverse else " ▲") if c == col else
                               {"number":self.tr("Room No."),"name":self.tr("IFC Room Name"), "storey":self.tr("Level"),
                                "longname":self.tr("Description"), "area":self.tr("IFC Area (m²)"),
                                "category":self.tr("BR18 Category")}[c])

    def sort_by(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.apply_sort()

    def edit_category(self, event):
        if self.table.identify_column(event.x) != "#6":
            return
        guid = self.table.identify_row(event.y)
        if not guid:
            return
        box = self.table.bbox(guid, "category")
        if not box:
            return
        if self.editor is not None:
            self.editor.destroy()
        x, y, width, height = box
        choice = tk.StringVar(value=self.category_label(self.categories[guid]))
        editor = ttk.Combobox(self.table, values=tuple(self.category_label(c) for c in CATEGORIES), textvariable=choice, state="readonly")
        self.editor = editor
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
        def apply(_=None):
            if self.editor is not editor:
                return
            self.categories[guid] = category_internal(choice.get())
            editor.destroy()
            self.editor = None
            self.refresh()
            if self.plan_window is not None:
                self.plan_window.draw()
        editor.bind("<<ComboboxSelected>>", apply)
        editor.bind("<Return>", apply)
        editor.bind("<Escape>", lambda _: editor.destroy())

    def bulk_assign(self):
        chosen = list(self.table.selection())
        if not chosen:
            messagebox.showinfo(self.tr("Select Rooms"), self.tr("Select one or more rooms in the table first (Ctrl/Shift)."))
            return
        for guid in chosen:
            self.categories[guid] = category_internal(self.bulk_category.get())
        self.refresh()
        if self.plan_window is not None:
            self.plan_window.draw()

    def show_plan(self):
        if not self.check_loaded():
            return
        if self.plan_window is None:
            self.plan_window = PlanWindow(self)
            self.plan_window.load()
        else:
            self.plan_window.win.lift()
        self.plan_window.select_guids(self.table.selection())

    def table_selected(self, _=None):
        if self.plan_window is None:
            return
        # Treeview already supports Ctrl/Shift multi-selection. Mirror ALL
        # selected GUIDs, not just the first, without changing zoom/pan.
        self.plan_window.select_guids(self.table.selection())

    def select_in_table(self, guid, additive=False):
        """Select a room from the plan; Ctrl+click toggles a table selection."""
        if not self.table.exists(guid):
            self.search_text.set("")
            self.category_filter.set(self.tr("All Categories"))
            self.refresh()
        if self.table.exists(guid):
            if additive:
                if guid in self.table.selection():
                    self.table.selection_remove(guid)
                else:
                    self.table.selection_add(guid)
            else:
                self.table.selection_set(guid)
            self.table.focus(guid)
            self.table.see(guid)
            # Also update explicitly for platforms where TreeviewSelect fires
            # after this callback rather than immediately.
            if self.plan_window is not None:
                self.plan_window.select_guids(self.table.selection())

    def check_loaded(self):
        if self.model is None:
            messagebox.showinfo(self.tr("No IFC File"), self.tr("Open an IFC file first."))
            return False
        return True

    def records(self):
        return [dict(GlobalId=guid, IFC_Name=space.Name or "", IFC_LongName=space.LongName or "",
                     IFC_Description=space.Description or "", RoomNo=self.room_number(space), Level=self.storey(space),
                     Area_m2=(f"{self.area(guid):.2f}".replace(".", ",")
                               if self.area(guid) is not None else ""),
                     BR18_Category=self.category_label(self.categories[guid]))
                for guid, space in self.spaces.items()]

    def save_csv(self):
        if not self.check_loaded():
            return
        filename = filedialog.asksaveasfilename(title=self.tr("Export Room Classifications to CSV"), defaultextension=".csv", initialfile=self.filepath.stem + "_BR18.csv", filetypes=[("CSV", "*.csv")])
        if not filename:
            return
        try:
            records = self.records()
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                columns = ["GlobalId", "IFC_Name", "IFC_LongName", "IFC_Description", "RoomNo", "Level", "Area_m2", "BR18_Category"]
                if self.language.get() == "Dansk":
                    labels = {"IFC_Name": "IFC_Navn", "IFC_LongName": "IFC_LangtNavn",
                              "IFC_Description": "IFC_Beskrivelse", "RoomNo": "RumNr",
                              "Level": "Etage", "BR18_Category": "BR18_kategori"}
                    localized = [{labels.get(key, key): row[key] for key in columns} for row in records]
                    columns = [labels.get(key, key) for key in columns]
                else:
                    localized = records
                writer = csv.DictWriter(f, fieldnames=columns, delimiter=";")
                writer.writeheader()
                writer.writerows(localized)
            messagebox.showinfo(self.tr("Saved Successfully"), (f"CSV gemt:\n{filename}" if self.language.get()=="Dansk" else f"CSV saved:\n{filename}"))
        except Exception as exc:
            messagebox.showerror(self.tr("Save Error"), str(exc))

    def calculate_rw(self):
        """Discover IFC adjacencies, then open a reviewable BR18 R'w result table."""
        if not self.check_loaded():
            return
        selected = {guid: category for guid, category in self.categories.items()
                    if guid in self.spaces and category != CATEGORIES[0]}
        if not selected:
            messagebox.showinfo(self.tr("No Categorized Rooms"),
                                self.tr("Categorize at least one room on the selected levels first."), parent=self)
            return
        try:
            import shapely
            from ifc_acoustics import find_adjacencies
            from br18_results_ui import ResultsWindow
        except ImportError as exc:
            messagebox.showerror(self.tr("Missing Dependency or Module"),
                f"Failed to load analysis modules: {exc}\n\n"
                "Ensure ifc_acoustics.py, br18_results_ui.py and "
                "br18_Rw_rules.py and ui_english.py are in the same folder.\n"
                "Install the geometry package with: python -m pip install shapely", parent=self)
            return
        model = self.model
        spaces = dict(self.all_spaces)
        categories = dict(self.categories)
        status = tk.Toplevel(self)
        status.title(self.tr("Finding Room Separations..."))
        status.geometry("520x145")
        status.transient(self)
        status.resizable(False, False)
        msg = tk.StringVar(value=(f"Indlæser {len(spaces)} rum fra IFC-modellen..." if self.language.get() == "Dansk" else f"Loading {len(spaces)} rooms from the IFC model..."))
        ttk.Label(status, text=self.tr("Room Separation Analysis"), font=("Segoe UI",12,"bold"),
                  padding=(16,12)).pack(anchor="w")
        ttk.Label(status, textvariable=msg, padding=(16,0), wraplength=490).pack(fill="x")
        ttk.Progressbar(status, mode="indeterminate").pack(fill="x", padx=16, pady=14)
        status.winfo_children()[-1].start(14)
        status.protocol("WM_DELETE_WINDOW", lambda: None)
        out = queue.Queue()
        def report(text):
            out.put(("progress", text))
        def worker():
            try:
                adjacencies, diag = find_adjacencies(
                    model, spaces, selected_guids=set(selected), progress=report
                )
                out.put(("ok", (adjacencies, diag)))
            except Exception as exc:
                out.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        def poll():
            finished = None
            try:
                while True:
                    kind, value = out.get_nowait()
                    if kind == "progress":
                        msg.set(value)
                    else:
                        finished = (kind, value)
            except queue.Empty:
                pass
            if finished is None:
                if status.winfo_exists():
                    status.after(120, poll)
                return
            status.destroy()
            if self.model is not model:
                messagebox.showwarning(self.tr("IFC File Changed"), self.tr("The IFC file changed during analysis. Please run it again."))
                return
            kind, value = finished
            if kind == "error":
                messagebox.showerror(self.tr("Analysis Error"), value, parent=self)
                return
            adjacencies, diag = value
            ResultsWindow(self, adjacencies, diag, categories)
            if diag["rum_uden_geometri"]:
                messagebox.showwarning(self.tr("Incomplete Geometric Analysis"),
                    f"{diag['rum_uden_geometri']} rooms could not be analyzed geometrically. "
                    "Some potential adjacencies may therefore be missing from the results. "
                    "Check these rooms in IFC/Revit.", parent=self)
        poll()



# --- Interaktiv plantegning (IFC-geometri) ---
import math
import re
from collections import defaultdict
from rw_heatmap import (PairOverlay, RW_COLORS, UNCERTAIN_COLOR, NEUTRAL_ROOM_COLOR,
                        overlay_color, create_level_overlays)


def slice_mesh(verts, faces, z):
    """Snit af trianguleret IFC-solid i et vandret plan (verdenskoordinater)."""
    segments = []
    for i in range(0, len(faces), 3):
        ids = faces[i:i+3]
        points = [(verts[3*j], verts[3*j+1], verts[3*j+2]) for j in ids]
        intersections = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            p, q = points[a], points[b]
            dz = q[2] - p[2]
            if abs(dz) < 1e-9:
                continue
            t = (z - p[2]) / dz
            if -1e-8 <= t <= 1+1e-8:
                x, y = p[0] + t*(q[0]-p[0]), p[1] + t*(q[1]-p[1])
                if not any(abs(x-u) + abs(y-v) < 1e-6 for u,v in intersections):
                    intersections.append((x, y))
        if len(intersections) == 2:
            a, b = intersections
            if math.dist(a, b) > 1e-6:
                segments.append((a, b))
    return segments


def segment_loops(segments, snap=0.008):
    """Find lukkede polygoner i mesh-snit; afrunding fjerner trekantsdelinger."""
    edges = set()
    points = {}
    for a,b in segments:
        ka = (round(a[0]/snap), round(a[1]/snap))
        kb = (round(b[0]/snap), round(b[1]/snap))
        if ka != kb:
            edges.add(tuple(sorted((ka,kb))))
            points[ka] = a
            points[kb] = b
    adjacency = defaultdict(set)
    for a,b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    loops = []
    unused = set(edges)
    while unused:
        e = next(iter(unused))
        start, nxt = e
        current, previous = nxt, start
        path = [start, nxt]
        unused.remove(e)
        for _ in range(len(edges)+1):
            if current == start:
                break
            candidates = [v for v in adjacency[current] if tuple(sorted((current,v))) in unused]
            if not candidates:
                break
            following = next((v for v in candidates if v != previous), candidates[0])
            unused.remove(tuple(sorted((current,following))))
            path.append(following)
            previous,current = current,following
        if current == start and len(path) >= 4:
            poly = [points[p] for p in path[:-1]]
            area = abs(sum(poly[k][0]*poly[(k+1)%len(poly)][1] - poly[(k+1)%len(poly)][0]*poly[k][1] for k in range(len(poly)))/2)
            if area > .015:
                loops.append((area, poly))
    return [poly for _,poly in sorted(loops, reverse=True)]


def geometry_slice(entity, z, settings):
    try:
        import ifcopenshell.geom
        shape = ifcopenshell.geom.create_shape(settings, entity)
        return slice_mesh(shape.geometry.verts, shape.geometry.faces, z)
    except Exception:
        return []


class PlanWindow:
    COLORS = {"Ikke kategoriseret":"#f1e9d6", "Undervisningsrum":"#b7dfca",
              "Fællesrum":"#ced8e5", "Åbne undervisningsområder":"#d6c7ed",
              "Sløjdundervisningsrum":"#f9c9ab", "Sang- og musikundervisningsrum":"#f0b8c9",
              "Ekstern enhed/institution":"#e0d1bc"}

    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app)
        self.win.title(self.app.tr("IFC Floor Plan – BR18 Classification"))
        self.win.geometry("1000x760+100+100")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.level = tk.StringVar()
        self.status = tk.StringVar(value=self.app.tr("Loading..."))
        self.plans = {}
        self.level_elevations = {}
        self.selected = None  # Legacy last-selected GUID for compatibility.
        self.selected_guids = set()
        self.rw_source = None   # ResultsWindow supplying live acoustic results
        self.selected_pair_id = None
        self.view_mode = "classification"  # classification | rw | both
        self.mode_display = tk.StringVar()
        self.wall_info = tk.StringVar(value="")
        self.rw_overlay_cache = {}
        self.scale = 35.0
        self.offset = [70., 70.]
        self.drag_start = None
        self.tasks = []
        self.job = None
        self.epoch = 0
        top = ttk.Frame(self.win, padding=8)
        top.pack(fill="x")
        self.level_label = ttk.Label(top, text=self.app.tr("Level:"))
        self.level_label.pack(side="left")
        self.level_box = ttk.Combobox(top, state="readonly", textvariable=self.level, width=30)
        self.level_box.pack(side="left", padx=6)
        self.level_box.bind("<<ComboboxSelected>>", lambda _: self.change_level())
        self.mode_label = ttk.Label(top, text=self.app.tr("View:"))
        self.mode_label.pack(side="left", padx=(12, 0))
        self.mode_box = ttk.Combobox(top, textvariable=self.mode_display, state="readonly", width=24)
        self.mode_box.pack(side="left", padx=6)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _e: self.change_view_mode())
        self.refresh_mode_list()
        self.fit_button = ttk.Button(top, text=self.app.tr("Fit Floor Plan to View"), command=self.fit)
        self.fit_button.pack(side="left", padx=6)
        # Export controls get their own row so both buttons remain visible
        # at the default 1000-pixel window width (also in Danish).
        export_bar = ttk.Frame(self.win, padding=(8, 0, 8, 6))
        export_bar.pack(fill="x")
        self.pdf_button = ttk.Button(export_bar, text=self.app.tr("Export All Floor Plans to PDF"), command=self.save_pdf)
        self.pdf_button.pack(side="left", padx=6)
        self.svg_button = ttk.Button(export_bar, text=self.app.tr("Export All Floor Plans to SVG"), command=self.save_svg)
        self.svg_button.pack(side="left", padx=6)
        self.canvas = tk.Canvas(self.win, background="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.legend = ttk.Frame(self.win, padding=(12, 5))
        self.legend.pack(fill="x")
        self.wall_info_label = ttk.Label(self.win, textvariable=self.wall_info, padding=(12, 5),
                                         wraplength=920, foreground="#333333")
        self.update_legend()
        ttk.Label(self.win, textvariable=self.status, relief="sunken", anchor="w", padding=8).pack(fill="x")
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<ButtonPress-3>", self.pan_start)
        self.canvas.bind("<B3-Motion>", self.pan_move)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-4>", lambda e:self.zoom_factor(e.x,e.y,1.15))
        self.canvas.bind("<Button-5>", lambda e:self.zoom_factor(e.x,e.y,1/1.15))
        self.canvas.bind("<Configure>", lambda _: self.draw())

    def relocalize(self):
        self.win.title(self.app.tr("IFC Floor Plan – BR18 Classification"))
        self.level_label.configure(text=self.app.tr("Level:"))
        self.fit_button.configure(text=self.app.tr("Fit Floor Plan to View"))
        self.pdf_button.configure(text=self.app.tr("Export All Floor Plans to PDF"))
        self.svg_button.configure(text=self.app.tr("Export All Floor Plans to SVG"))
        self.mode_label.configure(text=self.app.tr("View:"))
        self.refresh_mode_list()
        self.update_legend()
        self.update_wall_info()
        self.update_status()

    VIEW_MODES = {
        "classification": "Room Classification",
        "rw": "R'w Requirements",
        "both": "Both",
    }

    def refresh_mode_list(self):
        self.mode_box["values"] = tuple(self.app.tr(label) for label in self.VIEW_MODES.values())
        self.mode_display.set(self.app.tr(self.VIEW_MODES[self.view_mode]))

    def change_view_mode(self):
        chosen = self.mode_display.get()
        for internal, label in self.VIEW_MODES.items():
            if chosen == self.app.tr(label):
                self.set_view_mode(internal)
                break

    def set_view_mode(self, mode):
        if mode not in self.VIEW_MODES:
            raise ValueError(mode)
        if mode != "classification" and self.rw_source is None:
            mode = "classification"  # R'w analysis has not been run yet.
        self.view_mode = mode
        self.refresh_mode_list()
        self.update_legend()
        self.update_wall_info()
        self.draw()
        self.update_status()

    def update_legend(self):
        for child in self.legend.winfo_children():
            child.destroy()
        if self.view_mode in ("classification", "both"):
            categories = list(self.COLORS.items())
            # Wrap category names rather than clipping the last few at the
            # default 1000px floor-plan window width.
            for row_start in (0, 4):
                line = ttk.Frame(self.legend)
                line.pack(fill="x", anchor="w")
                ttk.Label(line, text=(self.app.tr("Room categories:") if row_start == 0 else "")).pack(side="left", padx=(0,5))
                for name, color in categories[row_start:row_start+4]:
                    tk.Label(line, bg=color, width=2, relief="solid", borderwidth=1).pack(side="left", padx=(5,2))
                    ttk.Label(line, text=self.app.category_label(name)).pack(side="left")
        if self.view_mode in ("rw", "both"):
            line = ttk.Frame(self.legend)
            line.pack(fill="x", anchor="w", pady=(4, 0))
            ttk.Label(line, text=self.app.tr("Required R'w:")).pack(side="left", padx=(0,5))
            for db, color in RW_COLORS.items():
                tk.Label(line, bg=color, width=3, relief="solid", borderwidth=1).pack(side="left", padx=(7,2))
                ttk.Label(line, text=f"≥ {db} dB").pack(side="left")
            tk.Label(line, bg=UNCERTAIN_COLOR, width=3, relief="solid", borderwidth=1).pack(side="left", padx=(10,2))
            ttk.Label(line, text=self.app.tr("Unresolved")).pack(side="left")
        if self.view_mode == "classification":
            self.wall_info_label.pack_forget()
        elif not self.wall_info_label.winfo_manager():
            self.wall_info_label.pack(fill="x", before=self.win.winfo_children()[-1])

    def set_rw_source(self, source, mode="both"):
        self.rw_source = source
        self.selected_pair_id = None
        self.invalidate_rw()
        self.set_view_mode(mode)

    def clear_rw_source(self, source):
        if self.rw_source is source:
            self.rw_source = None
            self.selected_pair_id = None
            self.invalidate_rw()
            self.set_view_mode("classification")

    def invalidate_rw(self):
        self.rw_overlay_cache = {}
        if self.view_mode in ("rw", "both"):
            self.update_wall_info()
            self.draw()

    def rw_pairs(self):
        if self.rw_source is None:
            return []
        pairs = []
        for iid, record in self.rw_source.records():
            adj = self.rw_source.by_id[iid]
            if adj.direction != "horisontal":
                continue
            pairs.append(PairOverlay(
                iid=str(iid), a=adj.a, b=adj.b, status=record["Status"],
                rw=record["Krav_Rw_db"], separator_keys=tuple(adj.separator_keys),
                description=record["Forklaring"], rule=record["BR18_rule_text"],
                direction=adj.direction,
            ))
        return pairs

    def rw_overlays(self, level=None):
        level = level or self.level.get()
        if self.rw_source is None:
            return [], 0
        plan = self.plans.get(level)
        if not plan or not plan.get("ready"):
            return [], 0
        if level not in self.rw_overlay_cache:
            self.rw_overlay_cache[level] = create_level_overlays(plan, self.rw_pairs())
        return self.rw_overlay_cache[level]

    def selected_pair(self):
        if self.rw_source is None or self.selected_pair_id not in self.rw_source.by_id:
            return None
        return self.rw_source.by_id[self.selected_pair_id]

    def set_selected_pair(self, iid):
        iid = str(iid)
        if iid != self.selected_pair_id:
            self.selected_pair_id = iid
            self.update_wall_info()
            if self.view_mode in ("rw", "both"):
                self.draw()

    def update_wall_info(self):
        if self.view_mode == "classification" or self.rw_source is None:
            self.wall_info.set("")
            return
        pair = self.selected_pair()
        if pair is None:
            self.wall_info.set(self.app.tr("Click a coloured wall to select its room pair and requirement."))
            return
        try:
            from ifc_acoustics import evaluate
            from br18_results_ui import room_display_label
            result = evaluate(pair, self.app.all_spaces, self.rw_source.categories,
                              self.rw_source.selected_ids)
            if result is None:
                self.wall_info.set("")
                return
            rw, status, _description, _rule, _detail = result
            name_a = room_display_label(self.app.all_spaces.get(pair.a), pair.a)
            name_b = room_display_label(self.app.all_spaces.get(pair.b), pair.b)
            from ui_english import status_display
            rw_text = f"R'w {rw} dB" if status == "Beregnet" else self.app.tr("Unresolved requirement")
            self.wall_info.set(f"{name_a}  ↔  {name_b}    |    {rw_text}    |    {status_display(status, self.app.language.get())}")
        except Exception:
            self.wall_info.set("")

    def close(self):
        if self.job:
            self.win.after_cancel(self.job)
        self.app.plan_window = None
        self.win.destroy()

    def storey_heights(self):
        import ifcopenshell.util.placement
        import ifcopenshell.util.unit
        scale = ifcopenshell.util.unit.calculate_unit_scale(self.app.model)
        heights = {}
        storeys = list(self.app.model.by_type("IfcBuildingStorey"))
        for floor in storeys:
            key = floor.Name or f"Level #{floor.id()}"
            if key not in self.app.selected_levels:
                continue
            try:
                z = float(ifcopenshell.util.placement.get_local_placement(floor.ObjectPlacement)[2][3]) * scale
            except Exception:
                z = float(floor.Elevation or 0) * scale
            heights[key] = z
        return heights

    def load(self):
        if self.job:
            self.win.after_cancel(self.job)
            self.job = None
        self.epoch += 1
        self.plans = {}
        self.invalidate_rw()
        self.level_elevations = self.storey_heights()
        for guid, space in self.app.spaces.items():
            home = self.app.storey(space) or "Uden etage"
            if home in self.app.selected_levels and home not in self.level_elevations:
                self.level_elevations[home] = None
        if not self.level_elevations:
            self.status.set(self.app.tr("No levels or spaces in the IFC file"))
            return
        ordered = sorted(self.level_elevations, key=lambda k: (self.level_elevations[k] is None,
                                                               self.level_elevations[k] or 0, k))
        known = [(n, self.level_elevations[n]) for n in ordered if self.level_elevations[n] is not None]
        for i, name in enumerate(ordered):
            elevation = self.level_elevations[name]
            if elevation is not None:
                higher = [z for n,z in known if z > elevation+0.05]
                # Use a height that stays below the next floor, avoids floor slab cutting.
                z = elevation + min(1.20, (min(higher)-elevation)*0.48) if higher else elevation + 1.2
            else:
                z = None
            self.plans[name] = {"spaces": {}, "walls": [], "wall_objects": [], "wall_by_guid": {}, "z": z, "ready": False,
                                "pending": 0, "guids": set(), "space_bounds": {}}
        self.level_box["values"] = ordered
        self.level.set(self.level.get() if self.level.get() in ordered else ordered[0])
        try:
            import ifcopenshell.geom
            import ifcopenshell.util.unit
            self.unit_scale = ifcopenshell.util.unit.calculate_unit_scale(self.app.model)
            self.settings = ifcopenshell.geom.settings()
            self.settings.set(self.settings.USE_WORLD_COORDS, True)
        except Exception as exc:
            self.status.set((f"IFC-geometri utilgængelig: {exc}" if self.app.language.get()=="Dansk" else f"IFC geometry unavailable: {exc}"))
            return
        # IMPORTANT: all geometry is examined against all floor elevations, not
        # just storey containment. That fixes walls assigned to another floor and
        # tall spaces that pass through several storeys.
        self.tasks = [("space", sp) for sp in self.app.spaces.values()]
        self.tasks += [("wall", wall) for wall in self.app.model.by_type("IfcWall")]
        self.tasks += [("column", col) for col in self.app.model.by_type("IfcColumn")]
        self.status.set((f"Genererer alle plantegninger: {len(self.tasks)} IFC-objekter ..." if self.app.language.get()=="Dansk" else f"Generating all floor plans: {len(self.tasks)} IFC objects ..."))
        self.process_next(self.epoch)

    def process_next(self, epoch):
        if epoch != self.epoch:
            return
        import ifcopenshell.geom
        for _ in range(5):
            if not self.tasks:
                for plan in self.plans.values():
                    plan["ready"] = True
                self.job = None
                self.invalidate_rw()
                self.fit()
                self.update_status()
                return
            typ, obj = self.tasks.pop(0)
            try:
                shape = ifcopenshell.geom.create_shape(self.settings, obj)
                # Geometry coords may be expressed in the model's length units.
                verts = [float(v) for v in shape.geometry.verts]
                faces = shape.geometry.faces
                zs = verts[2::3]
                if not zs:
                    continue
                zmin, zmax = min(zs), max(zs)
                home = self.app.storey(obj) if typ == "space" else None
                for name, plan in self.plans.items():
                    z = plan["z"]
                    if z is None:
                        if home == name:
                            z = (zmin+zmax)/2
                        else:
                            continue
                    if not (zmin+0.002 < z < zmax-0.002):
                        continue
                    segments = slice_mesh(verts, faces, z)
                    if not segments:
                        continue
                    if typ == "space":
                        loops = segment_loops(segments, snap=0.008)
                        if loops:
                            # Preserve multiple disconnected outlines for atypical spaces.
                            plan["spaces"][obj.GlobalId] = loops
                            plan["guids"].add(obj.GlobalId)
                    else:
                        if typ == "door":
                            continue  # doors should remain openings, not drawn as walls
                        plan["walls"].extend(segments)
                        if typ == "wall":
                            plan["wall_objects"].extend((obj.GlobalId, a, b) for a, b in segments)
                            plan["wall_by_guid"].setdefault(str(obj.GlobalId), []).extend(segments)
            except Exception:
                continue
        self.update_status()
        self.draw()
        self.job = self.win.after(5, lambda: self.process_next(epoch))

    def update_status(self):
        plan = self.plans.get(self.level.get(), {})
        left = len(self.tasks)
        text = f"{self.level.get()} · {len(plan.get('spaces',{}))} {self.app.tr('visible rooms')} · " \
               f"{len(plan.get('walls',[]))} {self.app.tr('geometry segments')}"
        if self.view_mode in ("rw", "both") and not left:
            overlay, missing = self.rw_overlays()
            mapped_label = self.app.tr("mapped R'w room pairs")
            text += f" · {len({p.iid for p, _seg in overlay})} {mapped_label}"
            if missing:
                text += f" · {missing} {self.app.tr('room pairs without a drawable wall')}"
        self.status.set(text + (f" · {self.app.tr('objects remaining')}: {left}" if left else ""))

    def change_level(self):
        self.fit()
        self.update_status()

    def select_guid(self, guid):
        # Keep this single-selection API for existing callers/tests.
        self.select_guids([guid] if guid else [])

    def select_guids(self, guids):
        """Highlight all selected spaces, preserving the user's current view."""
        selection = tuple(guids)
        self.selected_guids = set(selection)
        self.selected = selection[-1] if selection else None
        # Keep the current level when it includes any selected room; do not
        # jump between levels merely because several rows are selected.
        if self.selected_guids and not any(
                guid in self.plans.get(self.level.get(), {}).get("spaces", {})
                for guid in self.selected_guids):
            guid = selection[-1]
            containing = [n for n, p in self.plans.items()
                          if guid in p.get("spaces", {})]
            if containing:
                home = self.app.storey(self.app.spaces[guid])
                self.level.set(home if home in containing else containing[0])
                self.fit()  # A deliberate level switch can fit the new level.
                return
        self.draw()  # No automatic recenter or zoom when staying on the level.

    def coords(self, p):
        return (p[0]*self.scale+self.offset[0], -p[1]*self.scale+self.offset[1])

    def fit(self):
        plan = self.plans.get(self.level.get(), {})
        points = [p for loops in plan.get("spaces",{}).values() for poly in loops for p in poly]
        points += [p for a,b in plan.get("walls",[]) for p in (a,b)]
        if not points:
            self.draw()
            return
        x0,x1 = min(p[0] for p in points), max(p[0] for p in points)
        y0,y1 = min(p[1] for p in points), max(p[1] for p in points)
        w,h = max(self.canvas.winfo_width(),300),max(self.canvas.winfo_height(),300)
        self.scale = min((w-90)/max(x1-x0,.1),(h-90)/max(y1-y0,.1),110)
        self.offset = [w/2-(x0+x1)/2*self.scale,h/2+(y0+y1)/2*self.scale]
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        plan = self.plans.get(self.level.get())
        if not plan:
            return
        for guid, loops in plan["spaces"].items():
            for poly in loops:
                pts = [xy for p in poly for xy in self.coords(p)]
                chosen = guid in getattr(self, "selected_guids", {self.selected})
                fill = (self.COLORS[self.app.categories.get(guid, CATEGORIES[0])]
                        if self.view_mode in ("classification", "both") else NEUTRAL_ROOM_COLOR)
                c.create_polygon(*pts, fill=("#ffe18c" if chosen else fill),
                                 outline=("#d47b00" if chosen else "#687789"),
                                 width=3 if chosen else 1.2, tags=("room", "space_"+guid))
            poly = max(loops, key=lambda p: abs(polygon_area(p)))
            x,y = self.coords(polygon_centroid(poly))
            space = self.app.spaces[guid]
            label = (self.app.room_number(space) or space.Name or guid[:7])[:25]
            c.create_text(x,y,text=label,fill="#203047",font=("Segoe UI",9,"bold" if guid in getattr(self, "selected_guids", {self.selected}) else "normal"),
                          width=130,tags=("room", "space_"+guid))
        for a,b in plan["walls"]:
            c.create_line(*self.coords(a),*self.coords(b),fill="#303943",width=1.6,tags="wall")
        if self.view_mode in ("rw", "both"):
            overlays, _unmapped = self.rw_overlays()
            for pair, shape in overlays:
                selected = pair.iid == self.selected_pair_id
                # Filled partition area (bounded by the facing surfaces of
                # both rooms), not the individual triangular mesh edges.
                coords = [xy for p in list(shape.exterior.coords)[:-1]
                          for xy in self.coords(p)]
                if len(coords) >= 6:
                    c.create_polygon(*coords, fill=overlay_color(pair.status, pair.rw),
                                     outline=("#20252D" if selected else "#424950"),
                                     width=2 if selected else .7,
                                     tags=("rw_wall", "rw_pair_"+pair.iid))
            if self.rw_source and plan.get("ready") and not overlays:
                c.create_text(max(c.winfo_width(), 200)/2, 38,
                              text=self.app.tr("No mappable horizontal R'w wall segments on this level."),
                              fill="#666666")
        if not plan["spaces"] and not self.tasks:
            c.create_text(max(c.winfo_width(),200)/2,120,
                          text=self.app.tr("No rooms intersect this level's section plane."),fill="#777")

    def click(self,event):
        ids = self.canvas.find_overlapping(event.x,event.y,event.x,event.y)
        for item in reversed(ids):
            tags = self.canvas.gettags(item)
            if getattr(self, "view_mode", "classification") in ("rw", "both"):
                for tag in tags:
                    if tag.startswith("rw_pair_") and self.rw_source is not None:
                        iid = tag[len("rw_pair_"):]
                        self.set_selected_pair(iid)
                        self.rw_source.select_from_plan(iid)
                        return
            for tag in tags:
                if tag.startswith("space_"):
                    guid = tag[6:]
                    # Tk's Control modifier is bit 0x0004 on Windows/Linux.
                    additive = bool(getattr(event, "state", 0) & 0x0004)
                    if additive:
                        self.app.select_in_table(guid, additive=True)
                    else:
                        self.app.select_in_table(guid)
                    # Explicitly sync even in mock integrations where the
                    # Treeview selection event is not emitted.
                    if hasattr(self.app, "table"):
                        self.select_guids(self.app.table.selection())
                    else:
                        currently = set(getattr(self, "selected_guids", set()))
                        if additive:
                            if guid in currently:
                                currently.remove(guid)
                            else:
                                currently.add(guid)
                        else:
                            currently = {guid}
                        self.select_guids(currently)
                    return

    def pan_start(self,event):
        self.drag_start=(event.x,event.y)

    def pan_move(self,event):
        if not self.drag_start:
            return
        self.offset[0] += event.x-self.drag_start[0]
        self.offset[1] += event.y-self.drag_start[1]
        self.drag_start=(event.x,event.y)
        self.draw()

    def zoom(self,event):
        self.zoom_factor(event.x,event.y,1.15 if event.delta>0 else 1/1.15)

    def zoom_factor(self,x,y,factor):
        new = max(.5,min(self.scale*factor,350))
        ratio = new/self.scale
        self.offset = [x+(self.offset[0]-x)*ratio,y+(self.offset[1]-y)*ratio]
        self.scale = new
        self.draw()

    def save_svg(self):
        """Export one self-contained SVG per selected level, matching PDF."""
        if self.tasks:
            messagebox.showinfo(self.app.tr("Geometry Processing in Progress"),
                                self.app.tr("Floor plans are still being generated.\nTry again when processing has finished."))
            return
        base = filedialog.asksaveasfilename(
            title=self.app.tr("Export All Floor Plans to SVG"),
            defaultextension=".svg",
            initialfile=self.app.filepath.stem + "_BR18_floor_plans.svg",
            filetypes=[("SVG", "*.svg")])
        if not base:
            return
        try:
            used_names = set()
            created = []
            for name, plan in self.plans.items():
                output = level_filename(base, name, used_names)
                overlays = self.rw_overlays(name)[0] if self.view_mode in ("rw", "both") else []
                labels = {}
                for guid in plan.get("spaces", {}):
                    space = self.app.spaces.get(guid)
                    if space is not None:
                        labels[guid] = self.app.room_number(space) or space.Name or guid[:8]
                svg_floor_plan(
                    plan, name, self.app.filepath.name, labels, self.app.categories,
                    self.COLORS, self.view_mode, overlays, self.app.tr,
                    self.app.category_label, output)
                created.append(output)
            if not created:
                messagebox.showinfo(self.app.tr("No Levels Found"),
                                    self.app.tr("No levels or rooms were found in the IFC file."))
                return
            msg = (f"SVG-plantegninger gemt ({len(created)} filer):\n{created[0].parent}"
                   if self.app.language.get() == "Dansk" else
                   f"SVG floor plans saved ({len(created)} files):\n{created[0].parent}")
            messagebox.showinfo(self.app.tr("SVG Saved"), msg)
        except Exception as exc:
            messagebox.showerror(self.app.tr("SVG Error"), str(exc))

    def save_pdf(self):
        if self.tasks:
            messagebox.showinfo(self.app.tr("Geometry Processing in Progress"), self.app.tr("Floor plans are still being generated.\nTry again when processing has finished."))
            return
        try:
            from reportlab.pdfgen import canvas as pdfcanvas
            from reportlab.lib.colors import HexColor
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            messagebox.showerror(self.app.tr("Missing Dependency"), "Install the PDF library:\npython -m pip install reportlab")
            return
        filename = filedialog.asksaveasfilename(title=self.app.tr("Export All Floor Plans to PDF"), defaultextension=".pdf",
                                                initialfile=self.app.filepath.stem+"_BR18_floor_plans.pdf",
                                                filetypes=[("PDF", "*.pdf")])
        if not filename:
            return
        try:
            font = "Helvetica"
            import os
            for fpath in (r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
                if os.path.exists(fpath):
                    pdfmetrics.registerFont(TTFont("IFCUnicode", fpath))
                    font = "IFCUnicode"
                    break
            c = pdfcanvas.Canvas(filename, pagesize=landscape(A3))
            w,h = landscape(A3)
            margin = 42
            total_pages = len(self.plans)
            for page_num, (name, plan) in enumerate(self.plans.items(), start=1):
                c.setFont(font, 17)
                headline = (self.app.tr("BR18 – Room Classification") if self.view_mode == "classification"
                            else self.app.tr("BR18 – Required R'w on Floor Plans"))
                c.drawString(margin,h-42, headline)
                c.setFont(font, 11)
                c.drawString(margin,h-62, f"{self.app.tr('Level:')} {name}   |   IFC: {self.app.filepath.name}")
                points = [p for loops in plan["spaces"].values() for poly in loops for p in poly]
                points += [p for a,b in plan["walls"] for p in (a,b)]
                plot_x,plot_y = 55,125
                plot_w,plot_h = w-110,h-215
                if points:
                    xmin,xmax = min(p[0] for p in points),max(p[0] for p in points)
                    ymin,ymax = min(p[1] for p in points),max(p[1] for p in points)
                    factor = min(plot_w/max(xmax-xmin,.01),plot_h/max(ymax-ymin,.01))
                    factor = min(factor,250)
                    def point(p):
                        return (plot_x+(plot_w-(xmax-xmin)*factor)/2+(p[0]-xmin)*factor,
                                plot_y+(plot_h-(ymax-ymin)*factor)/2+(p[1]-ymin)*factor)
                    for guid, loops in plan["spaces"].items():
                        color = HexColor(self.COLORS[self.app.categories.get(guid,CATEGORIES[0])]
                                         if self.view_mode in ("classification", "both") else NEUTRAL_ROOM_COLOR)
                        for poly in loops:
                            if len(poly)<3: continue
                            path = c.beginPath()
                            x,y=point(poly[0]); path.moveTo(x,y)
                            for p in poly[1:]:
                                x,y=point(p); path.lineTo(x,y)
                            path.close()
                            c.setFillColor(color); c.setStrokeColor(HexColor("#687789"))
                            c.setLineWidth(.55);c.drawPath(path,fill=1,stroke=1)
                        if loops:
                            poly = max(loops,key=lambda p:abs(polygon_area(p)))
                            x,y=point(polygon_centroid(poly))
                            space=self.app.spaces[guid]
                            label=self.app.room_number(space) or space.Name or guid[:8]
                            c.setFillColorRGB(.1,.15,.2);c.setFont(font,7)
                            c.drawCentredString(x,y,str(label)[:26])
                    c.setStrokeColor(HexColor("#303943"));c.setLineWidth(.8)
                    for a,b in plan["walls"]:
                        x1,y1=point(a);x2,y2=point(b)
                        c.line(x1,y1,x2,y2)
                    if self.view_mode in ("rw", "both"):
                        drawn, _missing = self.rw_overlays(name)
                        for pair, shape in drawn:
                            pts = list(shape.exterior.coords)
                            if len(pts) < 4:
                                continue
                            path = c.beginPath()
                            x, y = point(pts[0]); path.moveTo(x, y)
                            for p in pts[1:]:
                                x, y = point(p); path.lineTo(x, y)
                            path.close()
                            c.setFillColor(HexColor(overlay_color(pair.status, pair.rw)))
                            c.setStrokeColor(HexColor("#424950"))
                            c.setLineWidth(.4)
                            c.drawPath(path, fill=1, stroke=1)
                # Only draw categories and R'w values actually mapped on
                # THIS level, not the full palette for the entire project.
                mapped = self.rw_overlays(name)[0] if self.view_mode in ("rw", "both") else []
                categories, rw_values = visible_sheet_legend(
                    plan, self.app.categories, self.COLORS, self.view_mode, mapped)
                categories = [(self.app.category_label(category), color)
                              for category, color in categories]
                rw_values = [(self.app.tr(text) if text == "Unresolved" else text, color)
                             for text, color in rw_values]
                rw_heading = self.app.tr("Required R'w:")
                cat_positions, rw_positions = legend_positions(
                    categories, rw_values, page_width=w,
                    measure=lambda value: pdfmetrics.stringWidth(value, font, 9),
                    rw_heading=rw_heading)
                c.setFont(font, 9)
                if rw_positions:
                    c.setFillColorRGB(.1, .1, .1)
                    c.drawString(margin, 60, rw_heading)
                for caption, color, x, y in cat_positions + rw_positions:
                    c.setFillColor(HexColor(color))
                    c.setStrokeColor(HexColor("#222222"))
                    c.setLineWidth(.6)
                    c.rect(x, y, 13, 11, fill=1, stroke=1)
                    c.setFillColorRGB(.1, .1, .1)
                    c.drawString(x+17, y+2, caption)
                c.setFont(font,8)
                note = (self.app.tr('Categories per BR18 Section 3.1') if self.view_mode == 'classification'
                        else self.app.tr('Model-based R\'w wall mapping'))
                c.drawString(margin,33,f"{self.app.tr('Rooms:')} {len(plan['spaces'])} | {note} | {self.app.tr('IFC geometry, automatically generated section')}")
                c.drawRightString(w-margin,33, self.app.tr("Drawing not to scale – verify against the original model"))
                # PDF only: centered page number; SVG deliberately excludes it.
                c.drawCentredString(w/2, 33, f"{page_num} / {total_pages}")
                c.showPage()
            c.save()
            messagebox.showinfo(self.app.tr("PDF Saved"),(f"Plantegninger gemt:\n{filename}" if self.app.language.get()=="Dansk" else f"Floor plans saved:\n{filename}"))
        except Exception as exc:
            messagebox.showerror(self.app.tr("PDF Error"),str(exc))


def polygon_area(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1] - poly[(i+1)%len(poly)][0]*poly[i][1]
               for i in range(len(poly)))/2


def polygon_centroid(poly):
    a = polygon_area(poly)
    if abs(a)<1e-10:
        return (sum(x for x,y in poly)/len(poly),sum(y for x,y in poly)/len(poly))
    cx = sum((poly[i][0]+poly[(i+1)%len(poly)][0]) *
             (poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1])
             for i in range(len(poly)))/(6*a)
    cy = sum((poly[i][1]+poly[(i+1)%len(poly)][1]) *
             (poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1])
             for i in range(len(poly)))/(6*a)
    return cx,cy

if __name__ == "__main__":
    ClassifierApp().mainloop()
