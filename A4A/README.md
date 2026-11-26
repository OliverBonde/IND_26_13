# A4A: Starter-framework version

Group 13 (IND_26_13) · Course 41934 Advanced BIM

This folder is the small, reusable version made for the course's starter framework. The full tool, with the user interface and the BR18 rules, is in [`A4`](../A4).

## What it does

`window_count/src/main.py` has one function, `analyse(model)`. It lists every room (`IfcSpace`) in the model with its GlobalId, room number and long name. On `26-01-D-ARCH.ifc` it finds 70 rooms.

It has no user interface and does not change the model, so other scripts can import and reuse it:

```python
from window_count.src.main import analyse
```

The folder is still called `window_count` because that is the starter's original name. It now lists rooms, not windows.

The result looks like this (one room shown, the list continues for all rooms):

```json
{
  "space_count": 70,
  "spaces": [
    {"globalid": "3SIDVtMID5MAPa0EsdTtg5", "name": "101", "long_name": "Materials library"}
  ]
}
```

## How to run it (Windows)

Open a terminal in this `A4A` folder.

First time only:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `MODEL_PATH` in `settings.py` to your own copy of the model. Keep the `r` before the quotes:

```python
MODEL_PATH = r"C:\path\to\26-01-D-ARCH.ifc"
```

Run:

```powershell
.\.venv\Scripts\python.exe runall.py
```

The result is saved in `window_count/results/run-<time>/result.json`. If the model file is missing, the program stops with an error. The model is only read, never changed, and it is not part of this repository.

## Files

| File | What it does |
|---|---|
| `window_count/src/main.py` | The `analyse(model)` function |
| `runall.py` | Opens the model, runs `analyse(model)` and saves the result |
| `settings.py` | The path to the IFC model on your own computer |
| `requirements.txt` | The Python packages to install |
| `tests/` | Tests that came with Tim's starter. They were written for the window-count example, so they do not match the room lister in `window_count/src/main.py`. |
| `CHANGELOG.md` | List of changes |

## Credit and licence

Based on the course's starter example: https://github.com/timmcginley/node-comply-template

Licence: GPL-3.0