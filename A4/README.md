# A4 — Tool: Automated Acoustic Requirement Classification from IFC

**Course:** 41934 Advanced Building Information Modeling (BIM)  
**Focus area:** Building acoustics / architectural design  
**Tool:** IFC Room Classifier — BR18 R'w Requirements (v7.5)  
**Group:** 13 <br>
**Case model:** `26-01-D-ARCH.ifc` (demonstration model; **not included in the repository**)

> **Submission status:** Draft ready for screenshots, references to the group's original A1/A2 submission, and BPMN diagrams. Values in square brackets must be completed from an actual run. This tool determines **required** airborne sound insulation; it does not measure or verify the **achieved** sound insulation of walls or slabs.

## 1. About the tool

### 1.1 Problem / claim

**Claim to investigate:** *The required apparent weighted airborne sound insulation (R'w) of room-separating building elements in an educational building can be determined consistently from the functions of adjacent spaces, their separation type and relevant door/partition conditions, using BR18.*

Before a separating wall or floor can be designed, the acoustic requirement for the particular pair of adjacent rooms must be known. In a large IFC model this involves identifying room functions, finding actual shared boundaries, checking doors and special cases, and applying the relevant row of **BR18, section 3.2, Table 3.1**. This is laborious and vulnerable to omissions if performed manually for many room pairs.

The objective is **not** to demonstrate that the as-built wall achieves its required R'w. Instead, the tool provides a model-based, traceable **design requirement** for each supported room separation, together with cases that need professional assessment.

### 1.2 Where the problem was identified

This use case follows the acoustic requirement issue defined in **A2**: the required sound insulation of room separations depends on the functions of the adjoining spaces, their spatial relationship and whether the separation has a direct door connection or special configuration. It builds on **A1's review of BIM/report information** and the BR18 requirements for educational buildings.

**Exact A1 evidence to complete before submission:** [INSERT REPORT TITLE, BUILDING/TEAM NUMBER, PAGE/SECTION AND THE ORIGINAL ISSUE OR CLAIM FROM YOUR A1 README]. The present draft does **not** assert that a particular wall was incorrectly designed, since no measured/tested wall performance has been supplied.

Regulatory basis:

- [BR18 §368–§376 — guidance, section 3.1: Definitions of room types in educational buildings](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/definitioner-af-rumtyper-for-undervisningsbygninger/)
- [BR18 — guidance, section 3.2: Sound insulation in educational buildings, Table 3.1](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/lydisolation-for-undervisningsbygninger/)

### 1.3 Description of the tool

The **IFC Room Classifier** is a standalone, bilingual (English/Danish) Python desktop application developed using **IfcOpenShell**. Its purpose is to assign BR18 room categories and derive the minimum required R'w values between adjacent rooms.

Its workflow is:

1. **Read the IFC model.** The user selects an IFC file and the relevant `IfcBuildingStorey` levels; levels containing spaces are preselected. `IfcSpace` names, room identifiers, descriptions and stored IFC areas are displayed in a sortable table.
2. **Classify spaces.** The user assigns the appropriate BR18 room category. The application shows an interactive, category-coloured floor plan and supports multi-selection. Uncategorized spaces are retained as possible neighbours, but a definitive requirement is not assigned to a pair with an uncategorized room.
3. **Find adjacent room pairs.** The tool prioritizes IFC space-boundary and building-element relationships, including `IfcRelSpaceBoundary`; where these are unavailable, it uses geometric analysis of rooms, walls and slabs. The analysis only compares pairs involving at least one categorized space and can identify multiple separating walls for one room pair.
4. **Check door connections.** Where possible, `IfcDoor`, `IfcOpeningElement`, `IfcRelFillsElement` and `IfcRelVoidsElement` are used together with location checks to determine whether the **specific shared wall section** contains a directly connecting door. Ambiguous model evidence is marked for review.
5. **Determine the requirement.** The rule module applies BR18 Table 3.1 to category, horizontal/vertical separation, door connection, flexible partitions in open-plan teaching areas, and special noise cases where relevant. Users can review or override unresolved conditions in the results table.
6. **Present and export results.** A results table shows the room pair, categories, separation type, required R'w and corresponding BR18 rule. Additional controls and evidence can be expanded. Horizontal wall separations are visualized using discrete colours on the same floor plan, with grey for unresolved cases. Floor plans can be exported as PDF or individual SVG files, with level-specific legends. Room classifications and results can be exported as CSV; classified spaces can be saved in a new IFC file.

A new IFC export stores each selected space's category in `Pset_BR18_RoomClassification.BR18_RoomType`. **The current tool does not write calculated R'w requirements back onto `IfcWall` objects.** The requirement is provided in the results and visual documentation.

Example requirement values from BR18 Table 3.1 include **≥ 48 dB** for ordinary horizontal teaching-room separations without direct doors, **≥ 51 dB** for corresponding vertical separations and **≥ 20 dB** for flexible partitions in open-plan teaching areas. Other entries depend on the room classes and door connection; the program uses these distinctions rather than a single value for every wall.

### 1.4 How to run the tool

**Prerequisites:** Python, IfcOpenShell and Shapely; ReportLab is needed for PDF export. Tkinter must be available for the graphical interface.

From the folder containing the Python modules, run:

```powershell
python -m pip install ifcopenshell shapely reportlab
python main.py
```

`main.py` is a small launcher provided for this A4 submission; the original application can also be started with `python ifc_room_classifier.py`.

In the user interface:

1. Select **Open IFC File** and the relevant levels.
2. Classify the spaces; use the accompanying floor plan to identify and select rooms.
3. Click **Calculate Required R'w** and inspect the result table. Only categorized room pairs are shown by default; review ambiguous adjacencies, door connections or exceptional cases as needed.
4. Click **Show R'w on Floor Plan** and select **Room Classification**, **R'w Requirements** or **Both**.
5. Export CSV, PDF or SVG documentation. Optionally export a **new** IFC containing room classification properties; the original IFC is not overwritten.

The IFC model is selected at runtime rather than being hard-coded. **Do not commit the IFC project model to GitHub**, in accordance with the A4 instructions.

## 2. Advanced Building Design application

### 2.1 Relevant stage (A, B, C or D)

The tool is **most useful in Stage B (evaluating design options) and Stage C (integrating the selected outline design)**, when room layouts and partition locations are established but can still be changed. Requirements can be assigned before choosing wall and door constructions. **Stage D** is relevant for reviewing the updated model and preparing acoustic requirement drawings for final documentation. It can be used earlier in Stage A only where enough reliable room and boundary data exists.

This is consistent with the earlier A2 choice of the **planning/design phases**. It is mainly an **Analyze** BIM purpose (extract relationships and apply rules), supported by **Generate** (produce requirement tables, classified IFC properties and colour-coded drawings) and **Communicate** (share the resulting floor plans). The closest BIM use case is **Code Validation**, with the narrower name *Acoustic Requirement Classification*. Unlike a full code-compliance checker, this version does not compare the wall's tested or specified acoustic performance against the requirement.

### 2.2 Potential users / subjects

- **Architecture / building acoustics:** Classify room use, establish the separation requirements and review layouts.
- **Acoustic consultant:** Examine unusual noise sources, open-plan partitions and cases needing manual assessment.
- **Structural / building-element design:** Use the required R'w as a design input when selecting walls and floors, in coordination with the other disciplines.
- **PM/ICT and BIM coordination:** Check model readiness and communicate requirement drawings and unresolved cases.

### 2.3 Information required in the IFC model

| Model information | IFC classes / attributes / relationships | Use and necessity |
|---|---|---|
| Rooms and identities | `IfcSpace`, `GlobalId`, `Name`, `LongName`, `Description` | Needed to identify the spaces and display them for manual classification. Descriptive fields improve usability; their presence varies. |
| Storeys and elevations | `IfcBuildingStorey`, spatial containment/reference relationships, `Elevation` and placements where available | Select and order levels and identify candidate floors. A room spanning several levels may require geometry checks. |
| Room geometry | Geometric representation of `IfcSpace` | Required for geometric adjacency fallback and meaningful floor-plan visualization. |
| Walls and floor slabs | `IfcWall`, `IfcSlab`, geometry and `GlobalId` | Identify the actual room-separating building elements (horizontal and vertical separation). |
| Space boundaries | `IfcRelSpaceBoundary` (1st/2nd level), corresponding boundaries and related elements where present | Preferred evidence for adjacency; **not mandatory** if usable geometry is available. |
| Doors and openings | `IfcDoor`, `IfcOpeningElement`, `IfcRelFillsElement`, `IfcRelVoidsElement` and placement/geometry where available | Determine whether a direct door exists in the particular shared wall segment. No doors are required in a doorless building. |
| Areas | IFC area quantities/properties, where available | Display and CSV export; the tool does **not** recalculate missing areas from geometry. |
| BR18 room function | User-assigned category, optionally `Pset_BR18_RoomClassification.BR18_RoomType` | Allows room-specific rule selection. Function cannot reliably be inferred from an arbitrary room name alone. |
| Special conditions | User review of flexible partition and disturbing noise | These conditions are not necessarily encoded in ordinary IFC data. |

The application is designed to inspect available IFC relations per room pair and fall back to geometry when necessary. Nevertheless, **lack of usable room or element geometry can cause some adjacencies to be missed**. A valid IFC or an IDS pass alone does not guarantee a valid acoustic analysis.

## 3. Information Delivery Specification (IDS)

The accompanying file [`acoustic_model_readiness.ids`](acoustic_model_readiness.ids) is an **IDS 1.0 preflight specification** for an IFC model intended for the standard room-to-wall analysis workflow. It requires:

1. At least one `IfcSpace` with a populated `Name`, enabling rooms to be identified in the table.
2. At least one `IfcBuildingStorey` with a populated `Name`, enabling a meaningful level selection.
3. At least one `IfcWall` for wall-separation analysis.

These are **basic model-delivery checks**, not a complete test of usability. Space geometry, actual adjacency, relevant wall/slab geometry, completeness of opening/door relationships, and validity of classification choices must additionally be checked by the tool or by a professional. Door and space-boundary instances are deliberately **not required in the IDS**, because a valid project might lack doors or space-boundary exports, and the tool has fallback approaches. IFC area properties are also not obligatory for the core R'w analysis.

The IDS can be tested against the locally stored IFC file using **IfcTester** (if installed):

```powershell
python -m pip install ifctester
python -m ifctester acoustic_model_readiness.ids "C:\\path\\to\\building.ifc"
```

**IDS validation result:** [INSERT IDS CHECK SCREENSHOT OR SUMMARY: passed/failed model requirements, software used and tested IFC version]. The IDS file's XML syntax is provided here, but its performance against the project model must be recorded separately.

## 4. Results and demonstration evidence

> **Insert current outputs from the final tool version below.** Export the floor plans with **Both** enabled where appropriate. Use identical room classifications in the screenshots and exported drawings. Ensure that sensitive project information is cleared for sharing.

### 4.1 Room classification and level selection

**[INSERT FIGURE 1 — `figures/01_room_classification.png`]**  
*Capture the main classification table and floor plan with BR18 room categories on the selected storey. The figure should demonstrate that the application correctly finds spaces and links a selected room to the plan.*

### 4.2 R'w result table and traceability

**[INSERT FIGURE 2 — `figures/02_rw_results_table.png`]**  
*Show the results window with Room A/Room B, Separation Type, Required R'w and the applicable BR18 rule. Include at least one automatically determined result and, if present, a case flagged for review. Prefer also showing the More Information details for one room pair.*

### 4.3 Spatial visualization of requirements

**[INSERT FIGURE 3 — `figures/03_basement_heatmap.png`]**  
*Insert the basement floor plan with **Both** displayed: room classifications as fills and horizontal wall segments coloured by their R'w requirement. The figure must include the per-floor legend and grey unresolved segments where relevant. Exported floor plans are illustrative and not to scale.*

### 4.4 Multiple walls between the same rooms

**[INSERT FIGURE 4 — `figures/04_multiple_walls_113_154.png`]**  
*Zoom to rooms **113 and 154** in the example model. Demonstrate that the same room pair may share two differently oriented wall segments and that both are identified and coloured according to the same requirement. Record the exact R'w result from the current run in the caption.*

### 4.5 Flexible open-plan teaching areas

**[INSERT FIGURE 5 — `figures/05_flexible_partition_110_185.png`]**  
*Show the result for rooms **110 and 185** after classifying both as open-plan teaching areas and selecting **Flexible Partition? = Yes**. When adjacency is verified and the condition applies, the relevant rule yields **R'w ≥ 20 dB**. Include both the changed result row and its mapped wall on the floor plan.*

### 4.6 Exported documentation

**[INSERT FIGURE 6 — `figures/06_pdf_svg_exports.png`]**  
*Demonstrate a PDF and a corresponding SVG export. Point out page numbering in the PDF (but not SVG), and legends filtered to the categories and requirement values **actually shown on that particular storey**.*

### 4.7 Summary of the demonstration run

Complete this table from **one documented run** of the application. Do not treat these as already measured values.

| Measure | Observed result |
|---|---|
| IFC model / schema | `[FILE / IFC VERSION]` |
| Selected storeys | `[LIST]` |
| Spaces detected / spaces categorized | `[N / N]` |
| Adjacencies found involving categorized spaces | `[N]` |
| Room pairs with determined R'w | `[N]` |
| Room pairs requiring review | `[N]` |
| Uncategorized neighbour cases | `[N]` |
| Horizontal separations mapped to wall segments | `[N]` |
| Horizontal pairs not mappable to the floor plan | `[N]` |
| IDS verification result | `[PASS/FAIL AND DETAILS]` |

**Verification method.** Manually inspect a small, reproducible sample of model room pairs against the original IFC/Revit geometry and BR18 Table 3.1. Include at least: (i) two teaching rooms without a door; (ii) a teaching room and common area with a direct door; (iii) a pair sharing two wall segments; and (iv) the flexible open-plan condition. Record any discrepancies and unresolved cases rather than declaring universal accuracy from a single model.

**Important limitation.** The tool determines **regulatory design-input values** and visualizes them on the model. It does **not** calculate actual airborne sound insulation of a construction, test its products, establish flanking transmission, or issue a final compliance certificate. The colour-coded walls on the plan are mapped requirements, not evidence that the wall meets them.

### 4.8 How to assess whether the tool improves the workflow

A4 asks how the tool helps **analyse the design and substantiate an improvement**. The relevant improvement demonstrated here is the **process of assigning acoustic design requirements**, not proof that the proposed building performs better acoustically. A fair comparison is to review the *same sample of room pairs* using (a) a manual BR18-and-drawings workflow and (b) the software:

| Comparison measure | Manual workflow | IFC Room Classifier |
|---|---|---|
| Time to assign requirements to the selected sample | `[MINUTES]` | `[MINUTES]` |
| Number of applicable pairs identified | `[N]` | `[N]` |
| Agreement with independently checked BR18 requirements | `[N/N]` | `[N/N]` |
| Missed or falsely detected adjacencies | `[N]` | `[N]` |
| Cases requiring a professional decision | `[N]` | `[N]` |

Report the exact test sample and checking method. Any claim of time saving or greater completeness should be supported by these measurements; no numerical improvement is claimed in this draft. If the **building design** itself is to be claimed as improved, that requires additional evidence about the selected wall systems and their achieved acoustic performance, which this tool does not compute.

## 5. BPMN diagrams — reserved for completion

### 5.1 As-is BPMN

**[INSERT AS-IS BPMN DIAGRAM (`figures/as_is_bpmn.svg`) — TO BE COMPLETED LATER]**  
*Document the existing process: identify spaces and shared elements, consult BR18, manually decide the governing row and communicate the requirements. Include stakeholder roles and information exchanges.*

### 5.2 To-be BPMN

**[INSERT TO-BE BPMN DIAGRAM (`figures/to_be_bpmn.svg`) — TO BE COMPLETED LATER]**  
*Document the implemented workflow: select IFC file → inspect and classify spaces → IFC relation/geometric adjacency detection → door/exception evaluation → BR18 requirement table → human review only for unresolved cases → floor-plan visualization and exports. Show the IFC exchange and relevant actors.*

## 6. Peer presentation — suggested sequence

For the A4 peer presentation, use the **as-is BPMN**, the tool's **aim**, the **to-be BPMN**, a brief live demonstration of **classification → requirement calculation → heatmap**, and the exported **outputs** in Section 4. These correspond to the suggested structure on the A4 assignment page. BPMN slides/diagrams remain outstanding by request.

## 7. References

1. DTU, **41934 — A4: Tool**: https://timmcginley.github.io/41934/Assignments/A4.html
2. DTU, **41934 — A1: Forensic BIM**: https://timmcginley.github.io/41934/Assignments/A1.html
3. DTU, **41934 — A2: Use Case**: https://timmcginley.github.io/41934/Assignments/A2.html
4. DTU, **41936 — Advanced Building Design, Part B/C/D**: https://timmcginley.github.io/41936/Assignments/B.html ; https://timmcginley.github.io/41936/Assignments/C.html ; https://timmcginley.github.io/41936/Assignments/D.html
5. The Danish Building Regulations (BR18), **Guidance for educational buildings**, sections 3.1 and 3.2, Table 3.1 (links in Section 1.2).
6. buildingSMART, **Information Delivery Specification (IDS) 1.0**: https://github.com/buildingSMART/IDS
7. **IFC Room Classifier v7.5**: source code and tests distributed with this A4 folder.

---

**Before submission:** fill in group metadata; replace Figure 1–6 placeholders; add the original A1 report/page reference; record actual run statistics and IDS result; insert both BPMN diagrams when ready; check that the submitted code is the same version as the screenshots. Keep all `.ifc` files out of the repository.
