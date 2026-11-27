# A4A: Starter-framework version

Group 13 (IND_26_13) · Course 41934 Advanced BIM

This folder contains a small, reusable part of our IFC analysis tool adapted to the course's starter framework. The full tool, including the user interface and BR18 acoustic rules, is available in [`A4`](../A4).

## What it does

`window_count/src/main.py` contains one function, `analyse(model)`. It reads every room (`IfcSpace`) in an IFC model and returns the information shown in the room table of the full tool:

- **Room No.** – from the room number property (or IFC description if unavailable)
- **IFC Room Name** – from `IfcSpace.Name`
- **Level** – from the room's assigned `IfcBuildingStorey`
- **Description** – from `IfcSpace.LongName`
- **Space Area (m²)** – from IFC area quantities, converted to square metres

For `26-01-D-ARCH.ifc`, the model contains 70 rooms. The script has no user interface and does not modify the IFC file. Other Python scripts can reuse the function:

```python
from window_count.src.main import analyse
```

The folder is still named `window_count` because this was the original name in the starter template. The function now extracts room information, not window counts.

### Example output

The result is a JSON object containing the number of rooms and a list of their properties. For example (illustrative values):

```json
{
  "space_count": 70,
  "spaces": [
    {
      "room_no": "101",
      "ifc_room_name": "Room 101",
      "level": "Level 1",
      "description": "Materials library",
      "space_area_m2": 25.5
    }
  ]
}
```

If a room has no usable IFC area quantity, `space_area_m2` is `null`. The example above shows only one room; the actual output includes all rooms.

## How to run it (Windows)

Open a terminal in the `A4A` folder.

First time only, create a Python environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `MODEL_PATH` in `settings.py` to the location of your own IFC file. Keep the `r` before the quotation marks:

```python
MODEL_PATH = r"C:\path\to\26-01-D-ARCH.ifc"
```

Run the script:

```powershell
.\.venv\Scripts\python.exe runall.py
```

The result is automatically saved to `window_count/results/run-<timestamp>-<suffix>/result.json`.

The IFC model stays on your computer. It is read but never modified, and it does not need to be uploaded to GitHub. If the file path is incorrect or the file is missing, the program stops with an error.

## Files

| File | What it does |
|---|---|
| `window_count/src/main.py` | Reads room number, IFC room name, level, description and area; returns the data as a dictionary. |
| `runall.py` | Opens the IFC model, calls `analyse(model)` and saves the result as JSON. |
| `settings.py` | Specifies the local path to the IFC model. |
| `requirements.txt` | Lists the required Python packages. |
| `tests/` | Contains the original starter tests for counting windows; these have not been updated to test the room extraction. |
| `CHANGELOG.md` | Records changes to the project. |

## Limitations

The script only extracts room information. It does not display a table, classify rooms, calculate acoustic requirements or check BR18 compliance. Missing room properties or area quantities may result in empty values or `null` in the JSON output.

## Credit and licence

Based on the course's starter framework: https://github.com/timmcginley/node-comply-template

Licence: GPL-3.0
