# A4: Tool – Acoustic requirement classification (BR18)

**Group 13** (IND_26_13) · Indoor & Energy / Acoustic / Daylight · Analysts
**Test model:** `26-01-D-ARCH.ifc` (building 2601). The model is **not** in this repository.

## 1. About the tool

### The claim

**Claim to investigate:** *The designers of the building claim that the current internal separating walls, in the IFC-model, comply with the acoustic requirements of BR18 §368 - §376 for sound transmission between rooms.* (from A2)


### The problem

### What the Tool Does and How It Is Used

The tool relies heavily on user input and is therefore intended to support, rather than replace, the acoustic engineer. It provides an overview of the IFC building model, allowing the user to assign the appropriate function and usage category to each room or space. Based on this information, the tool automatically analyzes the building model and determines the relevant acoustic requirements in accordance with BR18.

#### Step 1: Run `main.py` and Load the IFC Model

Start the program and wait for the user interface to appear. Once the interface is loaded, select Open IFC File and choose the appropriate IFC model.

![Figure 1. Main window with the IFC import functionality highlighted.]image−1.pngimage-1.pngimage−1.png

Figure 1. Main window with the IFC import functionality highlighted.

#### Step 2: Select Levels to Include

The program prompts the user to select which building levels should be included in the analysis. This step is necessary because IFC models may contain unused levels that are not relevant to the project. The tool displays the spaces associated with each identified level to assist the user in making the correct selection.

![Figure 2. Dialog showing the identified levels and associated spaces.]image−2.pngimage-2.pngimage−2.png

Figure 2. Dialog showing the identified levels and associated spaces.

#### Step 3: Assign a Room Category to Each Space

The program displays all spaces identified in the IFC model, together with their associated level, area, room number, and room name. This information assists the user in determining the appropriate space category. However, it remains the responsibility of the user to assess the intended room function and select the correct category from the drop-down menu.

![Figure 3. Space overview and room category assignment interface.]image−3.pngimage-3.pngimage−3.png

Figure 3. Space overview and room category assignment interface.

#### Step 4: Use the Plan View to Complete the Categorization

Open the plan view within the program. A new window will display the selected building level, including walls, doors, windows, and spaces. The plan view works together with the space list, helping the user understand the location and context of each room within the building and thereby supporting the categorization process.

![Figure 4. Plan view displaying spaces and building elements.]image−4.pngimage-4.pngimage−4.png

Figure 4. Plan view displaying spaces and building elements.

#### Step 5: Calculate Acoustic Requirements

Once all spaces have been categorized, the calculation process can begin. This automated procedure evaluates the applicable acoustic requirements defined in BR18 and determines the required airborne sound insulation performance between adjacent rooms and spaces.

![Figure 5. Calculation of acoustic requirements based on the assigned room categories.]images\1 Kategorisering af rum.png
Figure 5. Calculation of acoustic requirements based on the assigned room categories.

#### Step 6: Review and Export Results

After the calculations have been completed, the results can be visualized directly in the plan view. The data can also be exported for further documentation, review, and integration into the acoustic design process.

![Figure 6. Visualization and export of calculated acoustic requirements.]image−6.pngimage-6.pngimage−6.png

Figure 6. Visualization and export of calculated acoustic requirements.


### What is in this folder

| File | What it does |
|---|---|
| `window_count/src/main.py` | The core function `analyse(model)`. It lists every room (GlobalId, number, name). On 26-01 it finds 70 rooms. It has no user interface, so other scripts can import and reuse it. |
| `runall.py` | Opens the model, runs `analyse(model)` and saves the result as JSON. Stops with an error if the model file is missing. |
| `settings.py` | The path to the IFC model on your own computer. |
| `acoustic_model_readiness.ids` | IDS check (see section 3). |
| [ADD: the full application files and what they do, once pushed] | |

### How to run it (Windows)

Open a terminal in this `A4` folder.

First time only:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `MODEL_PATH` in `settings.py` to your copy of the model, keeping the `r` before the quotes:

```python
MODEL_PATH = r"C:\path\to\26-01-D-ARCH.ifc"
```

Run:

```powershell
.\.venv\Scripts\python.exe runall.py
```

The result is saved in `window_count/results/run-<time>/result.json`. The model is only read, never changed.

## 2. Advanced Building Design

**Stage:** mainly **B** (comparing design options) and **C** (outline design), when the room layout is set but walls can still change. It is also useful in **D** to review the final model.

**Who might use it:**
- Architects and acoustic engineers, to set wall requirements early.
- Structural and building-element designers, who use the required R'w to choose wall types.
- BIM coordinators, to check that a model has the information needed.

**Information the model must contain:**

| Needed | Why |
|---|---|
| `IfcSpace` with a name and geometry | The rooms, and where they are |
| `IfcBuildingStorey` | To group rooms by level |
| `IfcWall` (and `IfcSlab` for vertical separation) | The separating elements |
| `IfcDoor` and wall openings | Doors change the requirement. Not needed if the building has no doors. |
| `IfcRelSpaceBoundary` | Optional. Geometry is used when it's missing. |

## 3. IDS

`acoustic_model_readiness.ids` checks that a model has the basics before the tool is run:

1. At least one `IfcSpace`, and every one has a `Name`.
2. At least one `IfcBuildingStorey`, and every one has a `Name`.
3. At least one `IfcWall`.

It checks that the information **exists**, not that it is correct, and it can't check geometry.

To run it:

```powershell
.\.venv\Scripts\python.exe -m pip install ifctester
.\.venv\Scripts\python.exe -m ifctester --no-color acoustic_model_readiness.ids "C:\path\to\26-01-D-ARCH.ifc"
```

**Result on 26-01:** [ADD: PASS/FAIL for each check]

## 4. Result

[ADD: screenshot of the output on 26-01]

## 5. Process (BPMN)

The as-is process is in our A2: [`A2/Images/diagram.svg`](../A2/Images/diagram.svg).
[ADD: to-be BPMN, if the process changed]

## Limitations

- The tool gives the **requirement**, not the wall's actual performance, and it does not prove that a wall complies.
- Room function comes from the user, so a wrong category gives a wrong requirement.
- Without usable geometry, some neighbouring rooms may be missed.
- Only the educational-building table in BR18 is covered.

## References

- BR18, guidance for educational buildings, 3.1 Room type definitions: https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/definitioner-af-rumtyper-for-undervisningsbygninger/
- BR18, guidance for educational buildings, 3.2 Sound insulation, Table 3.1: https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/lydisolation-for-undervisningsbygninger/
- 41934 A4: Tool: https://timmcginley.github.io/41934/Assignments/A4.html
- buildingSMART IDS 1.0: https://github.com/buildingSMART/IDS

## Licence

GPL-3.0