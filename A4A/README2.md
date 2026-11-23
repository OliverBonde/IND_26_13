# A4: Tool – Acoustic requirement classification (BR18)

**Group 13** (IND_26_13) · Indoor & Energy / Acoustic / Daylight · Analysts
**Test model:** `26-01-D-ARCH.ifc` (building 2601). The model is **not** in this repository.

## 1. About the tool

### The claim

**Claim to investigate:** *The designers of the building claim that the current internal separating walls, in the IFC-model, comply with the acoustic requirements of BR18 §368 - §376 for sound transmission between rooms.* (from A2)


### The problem

The problem addressed by our tool is to assist acoustic engineers in the task of classifying walls according to the sound insulation requirements defined in the Danish Building Regulations. This process can be highly repetitive, particularly in large buildings containing hundreds of walls. Therefore, we identified significant potential for improving efficiency and optimizing the workflow.

In BR18 this depends on what the rooms on either side are used for, whether they are side by side or above each other, and whether there is a door between them. Working this out by hand for every room pair in a large building is slow and easy to get wrong.

Examples from BR18, guidance for educational buildings, section 3.2, Table 3.1:

| Separation | Required R'w |
|---|---|
| Teaching room – teaching or common room, side by side | ≥ 48 dB |
| The same, above each other | ≥ 51 dB |
| Teaching room – teaching room, with a door | ≥ 44 dB |
| Flexible divider in an open teaching area | ≥ 20 dB |

### What the tool does

For each pair of neighbouring rooms, the tool gives the **required** R'w from BR18. It does **not** calculate how much insulation a wall actually provides.

1. **Find the rooms:** read every `IfcSpace` from the model.
2. **Set room function:** room names are typed by hand and can't be trusted, so the user assigns a BR18 room category. The name is shown only as a hint.
3. **Find neighbouring rooms:** use `IfcRelSpaceBoundary` if the model has it. Otherwise use room and wall geometry. Building 2601 has no space boundaries.
4. **Check doors:** find doors in the shared wall, because a door changes the requirement.
5. **Look up the requirement** in BR18 Table 3.1, and flag pairs that can't be decided for a person to review.

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