"""English presentation layer. Danish legacy classifications/engine states stay stable."""
from __future__ import annotations

CATEGORIES_EN = {
    "Ikke kategoriseret": "Uncategorized",
    "Undervisningsrum": "Teaching Room",
    "Fællesrum": "Common Area",
    "Åbne undervisningsområder": "Open-Plan Teaching Areas",
    "Sløjdundervisningsrum": "Woodworking Classroom",
    "Sang- og musikundervisningsrum": "Music and Singing Classroom",
    "Ekstern enhed/institution": "External Unit/Institution",
}
CATEGORIES_DA = {v:k for k,v in CATEGORIES_EN.items()}
STATUSES_EN = {
    "Beregnet": "Determined",
    "Ikke beregnet": "Not Determined",
    "Dør skal afklares": "Door Connection Requires Review",
    "Naboskab skal bekræftes": "Adjacency Requires Confirmation",
    "Manuel vurdering": "Manual Assessment Required",
}
STATUS_FILTERS_EN = {
    "Alle": "All",
    "Kategoriseret rum": "Categorized Room Pairs",
    **STATUSES_EN,
}
STATUS_FILTERS_DA = {v:k for k,v in STATUS_FILTERS_EN.items()}
CHOICES_EN = {
    "Ja": "Yes", "Nej": "No", "Ukendt": "Unknown",
    "Ubekræftet": "Unconfirmed", "Bekræftet": "Confirmed", "Afvist": "Rejected",
    "horisontal": "Horizontal", "vertikal": "Vertical",
    "Manuelt afklaret": "Manually Resolved", "Ikke afklaret": "Unresolved",
    "IFC-grænse": "IFC Boundary", "Geometrisk kandidat": "Geometric Candidate",
    "IFC – rumgrænser": "IFC – Space Boundaries",
    "IFC – væg og rumgrænser": "IFC – Wall and Space Boundaries",
    "IFC – dør i væg, rumgeometri": "IFC – Door in Wall, Room Geometry",
    "IFC – lokal vægkontrol (forudsætning)": "IFC – Local Wall Check (Assumption)",
}

def category_en(value):
    return CATEGORIES_EN.get(value, value)

def category_internal(value):
    return CATEGORIES_DA.get(value, value)

def status_en(value):
    return STATUSES_EN.get(value, value)

def filter_internal(value):
    return STATUS_FILTERS_DA.get(value, value)

def choice_en(value):
    return CHOICES_EN.get(value, value)

def choice_internal(value):
    return {v:k for k,v in CHOICES_EN.items()}.get(value, value)

# v6.8: The IFC/BR18 data model stays in legacy Danish; only presentation changes.
# Language setting is per application window, not a global calculation setting.
DANISH_UI = {
    "IFC Room Classifier | BR18 Sections 3.1 and 3.2": "IFC Rumklassifikation | BR18 afsnit 3.1 og 3.2",
    "Language:": "Sprog:",
    "Open IFC File": "Åbn IFC-fil", "Select Levels": "Vælg etager",
    "Show Floor Plan": "Vis plantegning", "Export CSV": "Gem CSV",
    "Calculate Required R'w": "Beregn R'w-krav",
    "BR18 Room Classification – Educational Buildings": "BR18 rumklassifikation – undervisningsbygninger",
    "Search:": "Søg:", "Show:": "Vis:",
    "Room No.": "Rum nr.", "IFC Room Name": "IFC-rumnavn", "Level": "Etage",
    "Description": "Beskrivelse", "IFC Area (m²)": "IFC-areal (m²)",
    "BR18 Category": "BR18-kategori", "Category for Selected Rooms:": "Kategori for valgte rum:",
    "Apply to Selected": "Tildel til markerede",
    "Double-click a BR18 category to change an individual room.": "Dobbeltklik på BR18-kategorien for at ændre et enkelt rum.",
    "Select an IFC file to get started.": "Vælg en IFC-fil for at begynde.",
    "No File": "Ingen fil", "selected levels": "valgte etager", "on selected levels": "på valgte etager",
    "categorized": "kategoriseret", "displayed": "vist", "room pairs": "rumpar",
    "Select Revit Levels / IFC Storeys": "Vælg Revit-levels / IFC-etager",
    "Select Levels to Include": "Vælg etager, som skal medtages",
    "Only spaces assigned to selected IFC levels will appear in the table.\nTall spaces may still appear on multiple selected floor plans.":
       "Kun rum, der tilhører de valgte IFC-etager, vises i tabellen.\nHøje rum kan stadig vises på flere valgte plantegninger.",
    "Unassigned Level": "Uden etage", "elevation": "kote", "assigned spaces": "tilknyttede spaces",
    "All": "Alle", "None": "Ingen", "Cancel": "Annuller",
    "Show Selected Levels": "Vis valgte etager",
    "No Levels Found": "Ingen etager fundet", "No levels or rooms were found in the IFC file.": "Ingen etager eller rum blev fundet i IFC-filen.",
    "Select Level": "Vælg etage", "Select at least one level.": "Vælg mindst én etage.",
    "No IFC File": "Ingen IFC-fil", "Please select an IFC file first.": "Vælg først en IFC-fil.",
    "Open an IFC file first.": "Åbn først en IFC-fil.",
    "Missing Dependency": "Manglende pakke", "Failed to Read IFC File": "Kunne ikke læse IFC-fil",
    "No Rooms Found": "Ingen rum fundet", "No IfcSpace objects were found.": "Ingen IfcSpace-objekter blev fundet.",
    "Select Rooms": "Vælg rum", "Select one or more rooms in the table first (Ctrl/Shift).":
       "Vælg først et eller flere rum i tabellen (Ctrl/Shift).",
    "No Categorized Rooms": "Ingen kategoriserede rum",
    "Categorize at least one room on the selected levels first.": "Kategorisér først mindst ét rum på de valgte etager.",
    "Missing Dependency or Module": "Manglende pakke eller modul",
    "Finding Room Separations...": "Finder rumadskillelser...",
    "Room Separation Analysis": "Analyse af rumadskillelser",
    "IFC File Changed": "IFC-filen er ændret",
    "The IFC file changed during analysis. Please run it again.": "IFC-filen blev ændret under analysen. Kør analysen igen.",
    "Analysis Error": "Analysefejl", "Incomplete Geometric Analysis": "Ufuldstændig geometrisk analyse",
    "Saved Successfully": "Gemt", "Save Error": "Fejl ved gemning",
    "Export Room Classifications to CSV": "Gem rumklassifikationer som CSV",
    "IFC Floor Plan – BR18 Classification": "IFC-plantegning – BR18-klassifikation",
    "View:": "Visning:",
    "Room Classification": "Rumklassifikation",
    "R'w Requirements": "R'w-krav",
    "Both": "Begge",
    "Room categories:": "Rumkategorier:",
    "Required R'w:": "Krævet R'w:",
    "BR18 – Required R'w on Floor Plans": "BR18 – R'w-krav på plantegninger",
    "Model-based R'w wall mapping": "Modelbaseret farvelægning af R'w på vægge",
    "Unresolved": "Uafklaret",
    "Unresolved requirement": "Uafklaret krav",
    "Show R'w on Floor Plan": "Vis R'w på plantegning",
    "Click a coloured wall to select its room pair and requirement.": "Klik på en farvet væg for at vælge rumpar og krav.",
    "No mappable horizontal R'w wall segments on this level.": "Ingen vandrette R'w-rumadskillelser med tegnbar væggeometri på denne etage.",
    "mapped R'w room pairs": "rumpar vist med R'w-farve",
    "room pairs without a drawable wall": "rumpar uden tegnbar væg",
    "Level:": "Etage:", "Fit Floor Plan to View": "Tilpas plantegning til vindue",
    "Export All Floor Plans to PDF": "Eksportér alle plantegninger til PDF",
    "Export All Floor Plans to SVG": "Eksportér alle plantegninger til SVG",
    "SVG Saved": "SVG gemt", "SVG Error": "SVG-fejl",
    "Loading...": "Indlæser...", "visible rooms": "synlige rum", "geometry segments": "geometrisegmenter",
    "objects remaining": "objekter tilbage", "No levels or spaces in the IFC file": "Ingen etager eller rum i IFC-filen",
    "No rooms intersect this level's section plane.": "Ingen rum gennemskæres af snitplanet på denne etage.",
    "Geometry Processing in Progress": "Geometriberegning i gang",
    "Floor plans are still being generated.\nTry again when processing has finished.":
       "Plantegningerne bliver stadig genereret.\nPrøv igen, når beregningen er afsluttet.",
    "PDF Saved": "PDF gemt", "PDF Error": "PDF-fejl",
    "BR18 – Room Classification": "BR18 – Rumklassifikation",
    "Rooms:": "Rum:", "Categories per BR18 Section 3.1": "Kategorier iht. BR18 afsnit 3.1",
    "IFC geometry, automatically generated section": "IFC-geometri, automatisk snit",
    "Drawing not to scale – verify against the original model": "Ikke målfast – kontrollér mod originalmodellen",
    "BR18 – Required R'w Between Adjacent Rooms": "BR18 – R'w-krav mellem tilstødende rum",
    "BR18 – Required R'w Between Rooms": "BR18 – R'w-krav mellem rum",
    "Export Results to CSV": "Gem resultater som CSV",
    "Room A": "Rum A", "Room B": "Rum B", "Category A": "Kategori A", "Category B": "Kategori B",
    "Separation Type": "Adskillelsestype", "Required R'w (dB)": "Krav R'w (dB)",
    "BR18 Rule": "BR18-regel", "Adjacency Source": "Naboskab fra",
    "Adjacency": "Naboskab", "Door Connection?": "Dørforbindelse?",
    "Flexible Partition?": "Fleksibel rumadskillelse?",
    "Particularly Disturbing Noise?": "Særlig støj?", "Status": "Status",
    "More Information": "Yderligere info", "Hide Additional Information": "Skjul yderligere info",
    "Status Legend:": "Statusforklaring:", "Details and Assessment": "Detaljer og vurdering",
    "Determined": "Beregnet", "Manual Assessment Required": "Manuel vurdering",
    "Door/Adjacency Requires Review": "Dør/naboskab skal afklares", "Not Determined": "Ikke beregnet",
    "Categorized Room Pairs": "Kategoriseret rum", "Door Connection Requires Review": "Dør skal afklares",
    "Adjacency Requires Confirmation": "Naboskab skal bekræftes",
    "Yes": "Ja", "No": "Nej", "Unknown": "Ukendt", "Confirmed": "Bekræftet",
    "Unconfirmed": "Ubekræftet", "Rejected": "Afvist", "Horizontal": "Horisontal",
    "Vertical": "Vertikal", "Manually Resolved": "Manuelt afklaret", "Unresolved": "Ikke afklaret",
    "No Results": "Ingen resultater",
    "No relevant room pairs to export.": "Ingen relevante rumpar at eksportere.",
    "CSV Error": "CSV-fejl", "Explanation": "Begrundelse", "IFC Geometry": "IFC-geometri",
    "Supporting Evidence": "Dokumentation", "not determined": "ikke bestemt",
    "Rule": "Regel", "Categorized": "Kategoriseret", "Room Pairs": "Rumpar",
    "Door Connection": "Dørforbindelse",
    "The table does not specify a general R'w requirement between two common areas.":
       "Tabellen angiver ikke et generelt R'w-krav mellem to fællesrum.",
    "A direct door connection across a vertical separation is not a standard case in Table 3.1.":
       "Dørforbindelse gennem en vertikal adskillelse er ikke et standardtilfælde i tabel 3.1.",
    "No unambiguous BR18 Table 3.1 rule applies to this room pair.":
       "Ingen entydig regel i BR18 tabel 3.1 gælder for dette rumpar.",
    "At least one room type is unknown; classify the room function first.":
       "Mindst én rumtype er ukendt; klassificér rummets funktion først.",
    "An open-plan teaching area without a specified flexible partition requires a separate assessment.":
       "Åbent undervisningsområde uden angivet fleksibel adskillelse kræver særskilt vurdering.",
    "The 20 dB rule only applies to flexible partitions in open-plan teaching areas.":
       "20 dB-reglen gælder kun for fleksible adskillelser i åbne undervisningsområder.",
    "Music and woodworking rooms with a direct door connection: special rules may overlap; professional assessment is required.":
       "Musik og sløjd med direkte dørforbindelse kræver faglig vurdering af overlappende særregler.",
    "The 60 dB rule for external units requires particularly disturbing noise; determine the requirement through acoustic design.":
       "60 dB-reglen for eksterne enheder forudsætter særligt generende støj; fastlæg kravet ved akustisk projektering.",
    "The table does not specify a general R'w requirement between two common areas.":
       "Tabellen angiver ikke et generelt R'w-krav mellem to fællesrum.",
}


def ui_t(english, language="English"):
    """Translate a UI string; internal IFC identifiers and category values are not changed."""
    return DANISH_UI.get(english, english) if language == "Dansk" else english


def category_display(value, language="English"):
    return value if language == "Dansk" else category_en(value)


def status_display(value, language="English"):
    return value if language == "Dansk" else status_en(value)


def choice_display(value, language="English"):
    return value if language == "Dansk" else choice_en(value)


def filter_display(value, language="English"):
    internal = filter_internal(value)
    return internal if language == "Dansk" else STATUS_FILTERS_EN.get(internal, internal)


def category_internal(value):
    # Accept existing values, English labels and older stored IFC properties.
    return CATEGORIES_DA.get(value, value)

DANISH_UI.update({
    "All Categories": "Alle kategorier",
    "Adjacency is automatically confirmed using IFC space boundaries or physically verified walls/slabs. When data is insufficient, adjacency remains Unconfirmed. Double-click Adjacency / Door Connection to resolve exceptions.":
        "Naboskab bekræftes automatisk via IFC-rumgrænser eller kontrollerede vægge/dæk. Ved utilstrækkelige data står naboskabet som ubekræftet. Dobbeltklik på Naboskab / Dørforbindelse? for at afklare undtagelser.",
    "Required R'w concerns the overall room-separating construction. It does not verify the actual sound insulation performance. Check the model, doors, service penetrations and specialized rooms.":
        "Krævet R'w gælder den samlede rumadskillelse, men dokumenterer ikke den faktiske lydisolation. Kontrollér modellen, døre, gennemføringer og særlige rum.",
    "Export BR18 R'w Results": "Gem BR18 R'w-resultater",
    "Teaching room adjacent to another teaching room or common area.":
        "Undervisningsrum mod undervisningsrum eller fællesrum side om side.",
    "Teaching room above or below another teaching room or common area.":
        "Undervisningsrum mod undervisningsrum eller fællesrum over/under hinanden.",
    "Teaching rooms with a direct door connection.":
        "Undervisningsrum med direkte dørforbindelse.",
    "Teaching room and common area with a direct door connection.":
        "Undervisningsrum mod fællesrum med direkte dørforbindelse.",
    "Flexible partition within an open-plan teaching area.":
        "Fleksibel rumadskillelse i åbent undervisningsområde.",
    "Woodworking room adjacent to another teaching room or common area.":
        "Sløjdrum mod undervisningsrum eller fællesrum.",
    "Woodworking room and common area with a direct door connection.":
        "Sløjdrum mod fællesrum med direkte dørforbindelse.",
    "Music room adjacent to another music room, teaching room, or common area.":
        "Musikrum mod musikrum, undervisningsrum eller fællesrum.",
    "Music room and teaching/music room with a direct door connection.":
        "Musikrum mod undervisningsrum/musikrum med direkte dørforbindelse.",
    "Music room and common area with a direct door connection.":
        "Musikrum mod fællesrum med direkte dørforbindelse.",
    "Teaching room adjacent to an external unit/institution with particularly disturbing noise.":
        "Undervisningsrum mod ekstern enhed/institution med særligt generende støj.",
    "Music room adjacent to woodworking room: the 65 dB music requirement is stricter than the 60 dB woodworking requirement.":
        "Musikrum mod sløjdrum: musikkravet på 65 dB er strengere end sløjdkravet på 60 dB.",
    "Woodworking room with a door to a teaching/woodworking room: Table 3.1 has no specific door rule for this pair; interpretation requires review.":
        "Sløjdrum mod undervisningsrum/sløjdrum med dør: tabel 3.1 angiver ikke en særskilt dørregel; kræver fortolkning.",
    "This combination with an external unit is not unambiguously covered by the standard rule.":
        "Denne kombination med ekstern enhed er ikke entydigt dækket af standardreglen.",
    "An open-plan teaching area without a specified flexible partition requires a separate assessment.":
        "Et åbent undervisningsområde uden angivet fleksibel adskillelse kræver særskilt vurdering.",
    "The 20 dB rule only applies to flexible partitions in open-plan teaching areas.":
        "20 dB-reglen gælder kun fleksible adskillelser i åbne undervisningsområder.",
    "Unknown BR18 room type": "Ukendt BR18-rumtype",
    "Room A is uncategorized": "Rum A er ikke kategoriseret",
    "Room B is uncategorized": "Rum B er ikke kategoriseret",
})


def explanation_display(message, language="English"):
    """Translate rule-engine explanations, including composed unknown-door cases."""
    if language != "Dansk":
        return message
    exact = DANISH_UI.get(message)
    if exact is not None:
        return exact
    converted = str(message)
    for english, danish in (
        ("alternative case requires manual assessment", "andet tilfælde kræver manuel vurdering"),
        ("without door", "uden dør"), ("with door", "med dør"),
        ("(outside the selected levels)", "(uden for valgte etager)"),
        ("Room A", "Rum A"), ("Room B", "Rum B"),
        ("is uncategorized", "er ikke kategoriseret"),
    ):
        converted = converted.replace(english, danish)
    return converted
