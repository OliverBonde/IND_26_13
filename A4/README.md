# A4: Tool – Acoustic requirement classification (BR18)

**Course:** 41934 Advanced Building Information Modeling (BIM)  
**Focus area:** Building acoustics / architectural design  
**Tool:** BR18 R'w Requirements checker <br>
**Group:** 13 <br>
**Case model:** `26-01-D-ARCH.ifc`, however the tools works on any IFC.

## 1. About the tool

### <ins>Problem / claim

**Claim to investigate:** <br>
*The designers of the building claim that the current internal separating walls, in the IFC-model, comply with the acoustic requirements of BR18 §368 - §376 for sound transmission between rooms.* (from A2)



#### Where the problem / claim was indentified 

The problem/claim isn't found in a particular IFC-file, since no measured/tested wall performance has been supplied/calculated. Instead, the sound insulation requirements for interior separating walls in a given IFC-file are established.


### What the Tool Does and How It Is Used

The tool relies heavily on user input and is therefore intended to support, rather than replace, the acoustician. It provides an overview of the IFC building model, allowing the user to assign the appropriate function (e.g. teaching room) to each room (i.e. IfcSpace). Based on this information, the tool automatically analyzes the building model and determines the relevant acoustic requirements for airborne sound insulation (R'w) in accordance with [BR18 §368 – §376 Guidelines for Educational Buildings](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/).

## How to run the tool

### <ins>Step 0: Before Running the Tool</ins>

1. Ensure that **Python 3.10 or newer** is installed. We recommend using an IDE (e.g. VS Code) with the Python extension to run the tool.

2. Place all the provided Python files in the same folder.

3. Install the required Python packages by running the following command in the terminal:

   ```powershell
   python -m pip install ifcopenshell shapely reportlab
   ```

   The required packages are:
   - `ifcopenshell` – IFC model processing
   - `shapely` – Geometric analysis and visualization
   - `reportlab` – PDF export

4. Once the packages are installed, the tool is ready to run using `main.py`, as described in the following sections.



### <ins>Step 1: Run `main.py` and Load an IFC Model

Start by running `main.py` and once the user interface is loaded, select Open IFC File and choose the an IFC model of your choosing.

![Figure 1: Run.](images/1.png)
Figure 1. Run main.py to start program

![Figure 2: Load ifc.](images/2.png)
Figure 2. [Open IFC file] and load IFC.

### <ins>Step 2: Select Levels to Include

The program prompts the user to select which building levels should be included in the analysis. This step is necessary because IFC models may contain unused levels, that are not relevant to the project.  Initially, only the levels including at least one space are selected. Additionally, the tool displays the number of spaces associated with each level to assist the user in making the correct selection.

![Figure 3: Levels.](images/3.png)

Figure 3. Select levels to include from dialog.

### <ins>Step 3: Assign a foom function to each space


Once the desired levels are selected, the table on the right side of the figure below appears. Here, all IFC-spaces are listed with their associated number, level, description and area. This information assists the user in determining the appropriate BR18 function for the space. However, it remains the responsibility of the user to assess the intended room function and select the correct function from the drop-down menu at the bottom of the window. The descriptions, provided by the architect, serve as guidance for the acoustician when assigning the appropriate BR18 room function.

To help the user identify and locate spaces within the building, the tool generates floor plans (see the left side of the figure below) from the IFC model when "Show Floor Plan" is selected. These floor plans are created by extracting the 3D geometry of spaces and building elements, such as walls and doors, and generating horizontal sections at each selected level.

The floor plans are linked to the room classification table, allowing users to select and highlight spaces in either view. This makes it easier to understand the relationships between rooms and assign the appropriate BR18 functions.


![Figure 3. Space overview and room category assignment interface.](images/4.png)

Figure 3. Space overview and room category assignment interface.


### <ins>Step 4: Complete the Categorization of the Rooms

Using the drop-down menu at the bottom of the right side of the figure below, the rooms may be categorized based on their function. 

The example shown in the figure below is intended solely to demonstrate the tool's functionality. The IFC model (`26-01-D-ARCH.ifc`) contains offices and other room functions that are not covered in [BR18 §368 – §376 Guidelines for Educational Buildings](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/). Therefore, the example should not be interpreted as an assessment of `26-01-D-ARCH.ifc`'s actual compliance with these requirements.

**Note:** Not all spaces need to be categorized. The tool analyzes only categorized spaces and their adjacent rooms, allowing the user to determine the required R'w for a single room pair, a selected group of rooms, or all relevant interior separating walls.

![Figure 4. Plan view displaying spaces and building elements.](images/5.png)

Figure 4. Plan view displaying spaces and building elements.

For educational buildings, the following room categories/functions are used in the tool, based on [BR18 §368 – §376 Guidelines for Educational Buildings section 3.1 and 3.2](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/definitioner-af-rumtyper-for-undervisningsbygninger/#5036b98b-248e-48ea-8f22-d081436c63b7):

- **Teaching Rooms (Undervisningsrum)** – Classrooms, offices, group rooms, auditoriums, libraries, etc.
- **Common Areas (Fællesrum)** – Corridors, stairwells, canteens, toilets, technical rooms, etc.
- **Open-Plan Teaching Areas (Åbne undervisningsområder)** – Areas where multiple classes or groups are taught without being separated into enclosed rooms.
- **Woodworking Classrooms (Sløjdundervisningsrum)** 
- **Music and Singing Classrooms (Sang- og musikundervisningsrum)** 
- **External Units/Institutions (Eksterne enheder/institutioner)** – Adjacent rooms belonging to businesses or other institutions.
- **Uncategorized (ikke kategoriseret)** – For rooms that aren't examined or have a function yet.

### <ins>Step 5: Calculate Acoustic Requirements

Once the rooms have been categorized, press "Calculate Required R'w" to evaluate the applicable acoustic requirements for airborne sound insulation in accordance with BR18 §368 – §376.

The outcome of this is firsly the table shown in the figure below. Here each room-pair is listed by the room number and its categorized function as well as the separation type, required R'w (i.e. the result of the calculations) and the applicable BR18 rule following [BR18 §368 – §376 Guidelines for Educational Buildings, Table 3.1](https://www.bygningsreglementet.dk/tekniske-bestemmelser/17/vejledninger/undervisningsbygninger/lydisolation-for-undervisningsbygninger/#127bd002-d895-4fe3-b7c5-41d10afcf285)

*Horizontal separation type means that the rooms are adjacent on the same floor (i.e. they share at least one wall).*

![Figure 5. Calculation of acoustic requirements based on the assigned room functions.](images/6.png)

Figure 5. Calculation of acoustic requirements based on the assigned room categories.

### <ins>Step 6: Review and Export Results

After the calculations have been completed, the results can be visualized directly in the plan view. The data can also be exported for further documentation, review, and integration into the acoustic design process.

![Figure 6. Visualization and export of calculated acoustic requirements.](images/7.svg)

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