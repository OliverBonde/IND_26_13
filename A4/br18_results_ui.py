"""Resultatvindue til IFC Room Classifier / BR18 R'w-analyse."""
from __future__ import annotations

import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont

from ifc_acoustics import evaluate, UNCATEGORIZED
from ui_english import (category_en, status_en, choice_en, choice_internal,
                        filter_internal, STATUS_FILTERS_EN, ui_t,
                        category_display, status_display, choice_display, filter_display, explanation_display)
from br18_rule_labels import rule_description


# Same status colors for table rows and the horizontal legend.
STATUS_COLORS = {
    "Beregnet": "#d9f3e1",
    "Ikke beregnet": "#f8e0df",
    "Dør skal afklares": "#fff2ce",
    "Naboskab skal bekræftes": "#fff2ce",
    "Manuel vurdering": "#f6e7ff",
}

# Both yellow statuses mean that an input must be clarified before finalizing.
STATUS_LEGEND = (
    ("Determined", "Beregnet"),
    ("Manual Assessment Required", "Manuel vurdering"),
    ("Door/Adjacency Requires Review", "Dør skal afklares"),
    ("Not Determined", "Ikke beregnet"),
)


def measured_column_widths(columns, rows, measure_body, measure_heading):
    """Fit every column to its longest *visible* value or heading (in pixels).

    The caller supplies actual Tk font measurements. Recompute after each
    refresh, including edits in the result-table dropdowns and filter changes.
    """
    widths = {}
    for index, (key, heading, _initial_width) in enumerate(columns):
        # Treeview cells may contain explicit line breaks. Measure the longest
        # *line*, not the entire string, otherwise wrapping would not reduce
        # the column width.
        largest = max((max((measure_body(line) for line in str(
            row[index] if row[index] is not None else "").split("\n")), default=0)
                       for row in rows), default=0)
        widths[key] = max(72, measure_heading(heading) + 32, largest + 26)
    return widths


def wrap_rule_two_lines(value, measure):
    """Split a BR18 rule at a word boundary into at most two balanced lines.

    This affects *only* Treeview presentation. CSV export and detail text keep
    the original, single-line rule wording from BR18 Table 3.1.
    """
    text = " ".join(str(value or "").split())
    words = text.split(" ")
    if len(words) < 2 or text == "—":
        return text
    # One short label fits fine on one line; longer descriptions get two.
    if measure(text) <= 280:
        return text
    best = None
    for i in range(1, len(words)):
        first = " ".join(words[:i])
        second = " ".join(words[i:])
        score = (max(measure(first), measure(second)),
                 abs(measure(first) - measure(second)))
        if best is None or score < best[0]:
            best = (score, first, second)
    return best[1] + "\n" + best[2]


def is_categorized_pair(record):
    """Only show a pair if both rooms have an assigned BR18 category."""
    return all(
        record.get(key) not in (None, "", UNCATEGORIZED)
        for key in ("BR18_kategori_A", "BR18_kategori_B")
    )


def matches_view_filter(record, view_filter):
    """Preserve the existing status filters and add the categorized-pair view."""
    view_filter = filter_internal(view_filter)
    if view_filter == "Alle":
        return True
    if view_filter == "Kategoriseret rum":
        return is_categorized_pair(record)
    return record["Status"] == view_filter


def room_display_label(space, fallback):
    """Match the classifier columns: IFC-rumnavn: Beskrivelse."""
    if space is None:
        return fallback[:10]
    name = str(getattr(space, "Name", None) or "").strip()
    description = str(
        getattr(space, "LongName", None) or getattr(space, "Description", None) or ""
    ).strip()
    if name and description and name.casefold() != description.casefold():
        return f"{name}: {description}"
    return name or description or fallback[:10]




CSV_HEADERS_EN = {
    "Rum_A": "Room_A", "IFC_GUID_A": "IFC_GUID_A", "BR18_kategori_A": "BR18_Category_A",
    "Rum_B": "Room_B", "IFC_GUID_B": "IFC_GUID_B", "BR18_kategori_B": "BR18_Category_B",
    "Retning": "Separation_Type", "Naboskab_kilde": "Adjacency_Source",
    "Naboskab": "Adjacency", "Doerforbindelse": "Door_Connection",
    "Doerforbindelse_kilde": "Door_Connection_Source", "Doerforbindelse_IFC_bevis": "Door_IFC_Evidence",
    "Fælles_bygningsdele": "Shared_Building_Elements",
    "Fleksibel_adskillelse": "Flexible_Partition", "Saerlig_stoej": "Particularly_Disturbing_Noise",
    "Krav_Rw_db": "Required_Rw_dB", "Krav_Rw_minimum_db": "Minimum_Required_Rw_dB",
    "Status": "Status", "BR18_regel": "BR18_Rule_ID", "BR18_rule_text": "BR18_Rule", "Forklaring": "Explanation",
    "IFC_indikation": "IFC_Evidence",
}

def export_record_en(record):
    """Translate column headings and human-facing values, preserve GUIDs/rule IDs."""
    categories = {"BR18_kategori_A", "BR18_kategori_B"}
    choices = {"Retning", "Naboskab_kilde", "Naboskab", "Doerforbindelse",
               "Doerforbindelse_kilde", "Fleksibel_adskillelse", "Saerlig_stoej"}
    translated = {}
    for key, value in record.items():
        if key in categories:
            value = category_en(value)
        elif key in choices:
            value = choice_en(value)
        elif key == "Status":
            value = status_en(value)
        if key == "BR18_rule_text":
            value = rule_description(record.get("BR18_regel", ""), "English")
        translated[CSV_HEADERS_EN.get(key, key)] = value
    translated.setdefault("BR18_Rule", rule_description(record.get("BR18_regel", ""), "English"))
    return translated


def export_record_localized(record, language="English"):
    """Keep acoustic values and rule IDs unchanged; localize visible metadata."""
    if language != "Dansk":
        return export_record_en(record)
    headers = {
        "Rum_A": "Rum_A", "BR18_kategori_A": "BR18_kategori_A",
        "Rum_B": "Rum_B", "BR18_kategori_B": "BR18_kategori_B",
        "Retning": "Adskillelsestype", "Naboskab_kilde": "Naboskab_kilde",
        "Naboskab": "Naboskab", "Doerforbindelse": "Dørforbindelse",
        "Doerforbindelse_kilde": "Dørforbindelse_kilde", "Doerforbindelse_IFC_bevis": "Dør_IFC_bevis",
        "Fælles_bygningsdele": "Fælles_bygningsdele",
        "Fleksibel_adskillelse": "Fleksibel_rumadskillelse", "Saerlig_stoej": "Særlig_støj",
        "Krav_Rw_db": "Krav_Rw_dB", "Krav_Rw_minimum_db": "Minimum_Rw_dB",
        "Status": "Status", "BR18_regel": "BR18_regel_ID",
        "BR18_rule_text": "BR18_regel", "Forklaring": "Begrundelse", "IFC_indikation": "IFC_indikation",
    }
    result = {}
    for key, val in record.items():
        if key == "BR18_rule_text":
            val = rule_description(record.get("BR18_regel", ""), "Dansk")
        elif key == "Forklaring":
            val = explanation_display(val, "Dansk")
        result[headers.get(key, key)] = val
    result.setdefault("BR18_regel", rule_description(record.get("BR18_regel", ""), "Dansk"))
    return result


class ResultsWindow:
    # Keep keys stable for editor, sort and exports; order is important.
    COLUMNS = (
        ("a", "Room A", 145),
        ("a_cat", "Category A", 145),
        ("b", "Room B", 145),
        ("b_cat", "Category B", 145),
        ("direction", "Separation Type", 95),
        ("rw", "Required R'w (dB)", 135),
        ("rule", "BR18 Rule", 630),
        ("source", "Adjacency Source", 145),
        ("verified", "Adjacency", 110),
        ("door", "Door Connection?", 125),
        ("flexible", "Flexible Partition?", 180),
        ("noisy", "Particularly Disturbing Noise?", 150),
        ("status", "Status", 185),
    )
    MAIN_KEYS = ("a", "a_cat", "b", "b_cat", "direction", "rw", "rule")

    def __init__(self, app, adjacencies, diagnostic, categories):
        self.app = app
        self.adjacencies = adjacencies
        self.diagnostic = diagnostic
        self.categories = categories.copy()
        self.selected_ids = set(app.spaces)
        self.by_id = {str(i): item for i, item in enumerate(adjacencies)}
        self.sort_column = "a"
        self.reverse = False
        self.win = tk.Toplevel(app)
        self.expanded = False
        if hasattr(app, "result_windows"):
            app.result_windows.append(self)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.title(self.tr("BR18 – Required R'w Between Adjacent Rooms"))
        self.win.geometry("1470x780")
        self.win.minsize(900, 570)
        self.summary = tk.StringVar()
        self.filter = tk.StringVar(value=filter_display("Kategoriseret rum", self.language()))
        self.editor = None
        self.build()
        self.refresh()

    def tr(self, text):
        return ui_t(text, getattr(getattr(getattr(self, 'app', None), 'language', None), 'get', lambda: 'English')())

    def language(self):
        return getattr(getattr(getattr(self, 'app', None), 'language', None), 'get', lambda: 'English')()

    def columns_localized(self):
        return tuple((key, self.tr(title), width) for key, title, width in self.COLUMNS)

    def visible_keys(self):
        return tuple(key for key, _, _ in self.COLUMNS) if getattr(self, 'expanded', False) else self.MAIN_KEYS

    def close(self):
        if hasattr(self.app, 'result_windows') and self in self.app.result_windows:
            self.app.result_windows.remove(self)
        plan = getattr(getattr(self, "app", None), "plan_window", None)
        if plan is not None:
            plan.clear_rw_source(self)
        self.win.destroy()

    def relocalize(self):
        """Rebuild result widgets in the chosen language without rerunning geometry."""
        selected = self.table.selection()
        current_filter = filter_internal(self.filter.get())
        self.editor = None
        for child in self.win.winfo_children():
            child.destroy()
        self.win.title(self.tr("BR18 – Required R'w Between Adjacent Rooms"))
        self.filter.set(filter_display(current_filter, self.language()))
        self.build()
        self.refresh()
        if selected and self.table.exists(selected[0]):
            self.table.selection_set(selected[0])
            self.update_detail()

    def toggle_details(self):
        self.expanded = not self.expanded
        self.table.configure(displaycolumns=self.visible_keys())
        self.more_button.configure(text=self.tr("Hide Additional Information") if self.expanded else self.tr("More Information"))
        if self.expanded:
            self.footer.pack(fill="x", padx=12, pady=(0, 10), before=self.disclaimer)
        else:
            self.footer.pack_forget()
        self.refresh()

    def build(self):
        top = ttk.Frame(self.win, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text=self.tr("BR18 – Required R'w Between Rooms"), font=("Segoe UI", 15, "bold")).pack(side="left")
        ttk.Button(top, text=self.tr("Export Results to CSV"), command=self.save_csv).pack(side="right")
        ttk.Button(top, text=self.tr("Show R'w on Floor Plan"), command=self.show_rw_on_plan).pack(side="right", padx=(0, 8))
        self.more_button = ttk.Button(top, text=self.tr("Hide Additional Information") if self.expanded
                                      else self.tr("More Information"), command=self.toggle_details)
        self.more_button.pack(side="right", padx=(0, 8))
        info = ("Adjacency is automatically confirmed using IFC space boundaries or physically "
                "verified walls/slabs. When data is insufficient, adjacency remains Unconfirmed. "
                "Double-click Adjacency / Door Connection to resolve exceptions.")
        ttk.Label(self.win, text=self.tr(info), padding=(12, 2), foreground="#82570d", wraplength=1300).pack(fill="x")
        controls = ttk.Frame(self.win, padding=(12, 8))
        controls.pack(fill="x")
        ttk.Label(controls, text=self.tr("Show:")).pack(side="left")
        choice = ttk.Combobox(controls, state="readonly", textvariable=self.filter, width=35,
                              values=tuple(filter_display(x, self.language()) for x in STATUS_FILTERS_EN))
        choice.pack(side="left", padx=8)
        choice.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        ttk.Label(controls, textvariable=self.summary).pack(side="left", padx=15)

        # Horizontal status legend between filters/summary and the result grid.
        legend = ttk.Frame(self.win, padding=(12, 0, 12, 7))
        legend.pack(fill="x")
        ttk.Label(legend, text=self.tr("Status Legend:")).pack(side="left", padx=(0, 10))
        for label, status in STATUS_LEGEND:
            tk.Label(legend, text=self.tr(label), bg=STATUS_COLORS[status], fg="#202020",
                     font=("Segoe UI", 9), padx=10, pady=4,
                     relief="solid", borderwidth=1).pack(side="left", padx=(0, 8))

        holder = ttk.Frame(self.win, padding=(12, 0, 12, 8))
        holder.pack(fill="both", expand=True)
        # Treeview does not automatically increase row height for newlines.
        # Give the result table (not the classifier table) space for two lines.
        results_style = ttk.Style(self.win)
        row_font = tkfont.nametofont("TkDefaultFont", root=self.win)
        rowheight = max(43, row_font.metrics("linespace") * 2 + 12)
        results_style.configure("BR18Results.Treeview", rowheight=rowheight)
        self.table = ttk.Treeview(holder, columns=[c[0] for c in self.COLUMNS],
                                  displaycolumns=self.visible_keys(), show="headings",
                                  selectmode="browse", style="BR18Results.Treeview")
        for key, label, width in self.columns_localized():
            self.table.heading(key, text=label, command=lambda c=key: self.sort_by(c))
            self.table.column(key, width=width, minwidth=65, stretch=False)
        for status, color in STATUS_COLORS.items():
            self.table.tag_configure(status, background=color)
        ys = ttk.Scrollbar(holder, orient="vertical", command=self.table.yview)
        xs = ttk.Scrollbar(holder, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        self.table.bind("<Double-1>", self.edit_cell)
        self.table.bind("<<TreeviewSelect>>", self.update_detail)
        self.footer = ttk.LabelFrame(self.win, text=self.tr("Details and Assessment"), padding=(12, 8))
        if self.expanded:
            self.footer.pack(fill="x", padx=12, pady=(0, 10))
        self.detail = tk.Text(self.footer, wrap="word", height=6, font=("Segoe UI", 10))
        self.detail.pack(fill="both")
        self.detail.configure(state="disabled")
        self.disclaimer = ttk.Label(self.win, text=("Required R'w concerns the overall room-separating construction. It does not "
                                  "verify the actual sound insulation performance. Check the model, "
                                  "doors, service penetrations and specialized rooms."),
                  padding=(12, 5), foreground="#585858")
        self.disclaimer.configure(text=self.tr(self.disclaimer.cget('text')))
        self.disclaimer.pack(fill="x")

    def show_rw_on_plan(self):
        """Reuse the existing floor-plan window; never open a duplicate map."""
        if getattr(self.app, "plan_window", None) is None:
            self.app.show_plan()
        plan = getattr(getattr(self, "app", None), "plan_window", None)
        if plan is not None:
            plan.set_rw_source(self, mode="both")
            selected = self.table.selection()
            if selected:
                plan.set_selected_pair(selected[0])
            plan.win.lift()

    def select_from_plan(self, iid):
        """A click on a coloured wall selects the matching result row."""
        iid = str(iid)
        if not self.table.exists(iid):
            self.filter.set(filter_display("Alle", self.language()))
            self.refresh()
        if self.table.exists(iid):
            self.table.selection_set(iid)
            self.table.focus(iid)
            self.table.see(iid)
            self.update_detail()

    def describe(self, guid):
        return room_display_label(self.app.all_spaces.get(guid), guid)

    def records(self):
        for iid, adj in self.by_id.items():
            result = evaluate(adj, self.app.all_spaces, self.categories, self.selected_ids)
            if result is None:
                continue
            rw, status, description, rule, detail = result
            record = dict(
                Rum_A=self.describe(adj.a), IFC_GUID_A=adj.a,
                BR18_kategori_A=self.categories.get(adj.a, UNCATEGORIZED),
                Rum_B=self.describe(adj.b), IFC_GUID_B=adj.b,
                BR18_kategori_B=self.categories.get(adj.b, UNCATEGORIZED),
                Retning=adj.direction, Naboskab_kilde=adj.evidence,
                Naboskab=adj.verified, Doerforbindelse=adj.door_choice,
                Doerforbindelse_kilde=adj.door_source,
                Doerforbindelse_IFC_bevis=adj.door_evidence,
                Fælles_bygningsdele=" | ".join(str(k[1]) for k in adj.separator_keys),
                Fleksibel_adskillelse=adj.flexible_choice, Saerlig_stoej=adj.noisy_choice,
                Krav_Rw_db=rw,
                Krav_Rw_minimum_db=(rw[2:] if status == "Beregnet" and rw.startswith("≥ ") else ""),
                Status=status, BR18_regel=rule, BR18_rule_text=rule_description(rule, self.language()),
                Forklaring=description, IFC_indikation=detail)
            yield iid, record

    def auto_size_columns(self, visible_values):
        """Size columns to the table's current contents and column headings."""
        style = ttk.Style(self.win)
        body_spec = (style.lookup("BR18Results.Treeview", "font")
                     or style.lookup("Treeview", "font") or "TkDefaultFont")
        heading_spec = style.lookup("Treeview.Heading", "font") or body_spec
        try:
            body_font = tkfont.Font(root=self.win, font=body_spec)
        except tk.TclError:
            body_font = tkfont.nametofont("TkDefaultFont", root=self.win)
        try:
            heading_font = tkfont.Font(root=self.win, font=heading_spec)
        except tk.TclError:
            heading_font = body_font
        visible = self.visible_keys()
        positions = {key: i for i, (key, _, _) in enumerate(self.COLUMNS)}
        widths = measured_column_widths(
            [c for c in self.columns_localized() if c[0] in visible],
            [tuple(row[positions[key]] for key in visible) for row in visible_values],
            body_font.measure, heading_font.measure
        )
        for key, width in widths.items():
            # BR18 rule values are explicitly split into two measured lines.
            self.table.column(key, width=width, minwidth=72, stretch=False)

    def rule_text_measure(self):
        """Use the table's font for wrapping; allow headless table tests."""
        try:
            style = ttk.Style(self.win)
            spec = (style.lookup("BR18Results.Treeview", "font")
                    or style.lookup("Treeview", "font") or "TkDefaultFont")
            try:
                return tkfont.Font(root=self.win, font=spec).measure
            except tk.TclError:
                return tkfont.nametofont("TkDefaultFont", root=self.win).measure
        except (AttributeError, tk.TclError):
            return lambda value: len(value) * 8

    def refresh(self):
        selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        rows = list(self.records())
        counts = {}
        shown = 0
        visible_values = []
        measure_rule = self.rule_text_measure()
        for iid, rec in rows:
            counts[rec["Status"]] = counts.get(rec["Status"], 0) + 1
            if not matches_view_filter(rec, self.filter.get()):
                continue
            shown += 1
            lang = self.language()
            values = (rec["Rum_A"], category_display(rec["BR18_kategori_A"], lang),
                      rec["Rum_B"], category_display(rec["BR18_kategori_B"], lang),
                      choice_display(rec["Retning"], lang), rec["Krav_Rw_db"],
                      wrap_rule_two_lines(rule_description(rec["BR18_regel"], lang), measure_rule),
                      choice_display(rec["Naboskab_kilde"], lang), choice_display(rec["Naboskab"], lang),
                      choice_display(rec["Doerforbindelse"], lang),
                      choice_display(rec["Fleksibel_adskillelse"], lang),
                      choice_display(rec["Saerlig_stoej"], lang), status_display(rec["Status"], lang))
            self.table.insert("", "end", iid=iid, values=values, tags=(rec["Status"],))
            visible_values.append(values)
        self.auto_size_columns(visible_values)
        self.sort_rows()
        if selected and self.table.exists(selected[0]):
            self.table.selection_set(selected[0])
        else:
            first = self.table.get_children()
            if first:
                self.table.selection_set(first[0])
        self.update_detail()
        plan = getattr(getattr(self, "app", None), "plan_window", None)
        if plan is not None and plan.rw_source is self:
            plan.invalidate_rw()
        if self.language() == "Dansk":
            self.summary.set((f"{shown} vist af {len(rows)} rumpar  ·  "
                              f"{counts.get('Beregnet',0)} beregnet  ·  "
                              f"{counts.get('Ikke beregnet',0)} mangler kategori  ·  "
                              f"{counts.get('Dør skal afklares',0)} uafklarede dørforbindelser  ·  "
                              f"{counts.get('Naboskab skal bekræftes',0)} naboskaber til kontrol"))
        else:
            self.summary.set((f"{shown} displayed of {len(rows)} room pairs  ·  "
                              f"{counts.get('Beregnet',0)} determined  ·  "
                              f"{counts.get('Ikke beregnet',0)} missing classification  ·  "
                              f"{counts.get('Dør skal afklares',0)} unresolved door connections  ·  "
                              f"{counts.get('Naboskab skal bekræftes',0)} adjacencies requiring review"))

    def sort_by(self, column):
        self.reverse = not self.reverse if column == self.sort_column else False
        self.sort_column = column
        self.sort_rows()

    def sort_rows(self):
        def key(iid):
            val = self.table.set(iid, self.sort_column)
            if self.sort_column == "rw":
                import re
                m = re.search(r"\d+", val)
                return (0, int(m.group())) if m else (1, 0)
            return val.casefold()
        for position, iid in enumerate(sorted(self.table.get_children(), key=key, reverse=self.reverse)):
            self.table.move(iid, "", position)

    def update_detail(self, _=None):
        chosen = self.table.selection()
        if not chosen:
            return
        adj = self.by_id[chosen[0]]
        res = evaluate(adj, self.app.all_spaces, self.categories, self.selected_ids)
        if res is None:
            return
        rw, status, desc, rule, detail = res
        lang = self.language()
        rule_text = rule_description(rule, lang)
        if lang == "Dansk":
            message = (f"Rum A: {self.describe(adj.a)} [{adj.a}]\n"
                       f"Rum B: {self.describe(adj.b)} [{adj.b}]\n"
                       f"Status: {status_display(status, lang)} | R'w: {rw or '–'} | BR18-regel: {rule_text}\n"
                       f"Begrundelse: {explanation_display(desc, lang)}\n"
                       f"IFC-geometri: {detail}\n"
                       f"Dørforbindelse: {choice_display(adj.door_choice, lang)} ({choice_display(adj.door_source, lang)})\n"
                       f"Dokumentation: {choice_display(adj.evidence, lang)}; fælles bygningsdele: "
                       f"{', '.join(str(k[1]) for k in adj.separator_keys) or 'ikke bestemt'}\n"
                       "IFC-modellen er ikke en fysisk bygningskontrol. Kontrollér usikre tilfælde og forudsætningen om en fuldstændig døreksport.")
        else:
            message = (f"Room A: {self.describe(adj.a)} [{adj.a}]\n"
                       f"Room B: {self.describe(adj.b)} [{adj.b}]\n"
                       f"Status: {status_display(status, lang)} | R'w: {rw or '–'} | Rule: {rule_text}\n"
                       f"Explanation: {desc}\n"
                       f"IFC geometry: {detail}\n"
                       f"Door Connection: {choice_display(adj.door_choice, lang)} ({choice_display(adj.door_source, lang)})\n"
                       f"Supporting Evidence: {choice_display(adj.evidence, lang)}; shared building elements: "
                       f"{', '.join(str(k[1]) for k in adj.separator_keys) or 'not determined'}\n"
                       "The IFC is a model, not a site inspection. Check uncertain cases "
                       "and the assumption of a complete door export.")
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", message)
        self.detail.configure(state="disabled")
        plan = getattr(getattr(self, "app", None), "plan_window", None)
        if plan is not None and plan.rw_source is self:
            plan.set_selected_pair(chosen[0])

    def edit_cell(self, event):
        iid = self.table.identify_row(event.y)
        column = self.table.identify_column(event.x)
        if not iid or not column:
            return
        index = int(column[1:]) - 1
        keys = self.visible_keys()
        if index < 0 or index >= len(keys):
            return
        key = keys[index]
        attrs = {
            "verified": ("verified", ("Ubekræftet", "Bekræftet", "Afvist")),
            "door": ("door_choice", ("Ukendt", "Ja", "Nej")),
            "flexible": ("flexible_choice", ("Nej", "Ja")),
            "noisy": ("noisy_choice", ("Ukendt", "Ja", "Nej")),
        }
        if key not in attrs:
            return
        attr, options = attrs[key]
        bbox = self.table.bbox(iid, key)
        if not bbox:
            return
        if self.editor is not None:
            self.editor.destroy()
        adj = self.by_id[iid]
        var = tk.StringVar(value=choice_display(getattr(adj, attr), self.language()))
        editor = ttk.Combobox(self.table, values=tuple(choice_display(x, self.language()) for x in options),
                              textvariable=var, state="readonly")
        self.editor = editor
        x, y, width, height = bbox
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
        def finish(_=None):
            if self.editor is not editor:
                return
            setattr(adj, attr, choice_internal(var.get()))
            if key == "door":
                adj.door_source = "Manuelt afklaret" if choice_internal(var.get()) != "Ukendt" else "Ikke afklaret"
                if choice_internal(var.get()) != "Ja":
                    adj.door_evidence = ""
            editor.destroy()
            self.editor = None
            self.refresh()
            if self.table.exists(iid):
                self.table.selection_set(iid)
                self.table.see(iid)
                self.update_detail()
        def cancel(_=None):
            if self.editor is editor:
                editor.destroy()
                self.editor = None
        editor.bind("<<ComboboxSelected>>", finish)
        editor.bind("<Return>", finish)
        editor.bind("<Escape>", cancel)


    def save_csv(self):
        name = self.app.filepath.stem if self.app.filepath else "IFC"
        path = filedialog.asksaveasfilename(
            parent=self.win, title=self.tr("Export BR18 R'w Results"), defaultextension=".csv",
            initialfile=f"{name}_Rw_results.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        rows = [row for _, row in self.records()]
        if not rows:
            messagebox.showinfo(self.tr("No Results"), self.tr("No relevant room pairs to export."), parent=self.win)
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                localized = [export_record_localized(row, self.language()) for row in rows]
                writer = csv.DictWriter(f, fieldnames=list(localized[0]), delimiter=";")
                writer.writeheader()
                writer.writerows(localized)
            messagebox.showinfo(self.tr("Saved Successfully"), (f"Resultater gemt:\n{path}" if self.language()=="Dansk" else f"Results saved:\n{path}"), parent=self.win)
        except Exception as exc:
            messagebox.showerror(self.tr("CSV Error"), str(exc), parent=self.win)
