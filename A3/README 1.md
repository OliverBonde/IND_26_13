# A3: Teach

**Group 13** · Focus area: Indoor & Energy / Acoustic / Daylight

## Title

From an Interest to a Buildable BIM Tool Idea

## Summary

A general guide for turning a subject you are interested in into a BIM tool idea that is possible and useful, by examining what an IFC model contains, what it lacks, and limiting scope. Example: acoustics.

## Target

| | |
|---|---|
| **Who it is for** | Our peers, present and future: students who know which subject interests them, but not what tool to build |
| **Learning need** | "How do we come up with a tool that is actually possible to create and solves a practical problem?" |
| **Role and level** | OpenBIM Analyst, level 1: only a few lines of example code |
| **Focus area** | Indoor & Energy / Acoustic / Daylight |
| **BIM use** | Defining a BIM use from the information available in an IFC model |
| **Our example** | A tool that finds the sound insulation requirements between spaces |
| **Formats** | This README, and **TODO** a second format (for example a short video) |

---

## From an interest to a tool idea

Many BIM tool projects start the same way: you know *what you are interested in*, but not *what the tool should be* or *what it should do*. This section describes how to get from that starting point to a tool idea that is both **possible to build** and **useful for a real problem**. It is written so it can be used for any subject. Our own project, a tool for acoustics, is used as the example throughout.

The steps are:

1. Start from an interest or a problem
2. Find out what information is accessible
3. Find out what information is *not* accessible, and limit the scope
4. Understand the challenges in the information you have
5. Choose a scope and a tool idea

---

### 1. Start from an interest or a problem

Most projects begin with a subject, not a solution. That is fine. The important move is to turn the interest into a **process that clearly needs improving**: something people do today that is slow, manual, error-prone or often skipped.

The fastest way to find one is to **ask someone who knows the subject**. A person with experience can usually point to a task they find tedious or unreliable. That task is a much better starting point than a general wish to "make a smart tool".

At this point you will probably have a vision but no idea how to carry it out. That is normal. The next steps are what turn the vision into something concrete.

> **In our case:** we were interested in acoustics (part of indoor climate) and wanted a tool that could help with acoustic calculations, but we had no idea what kind of tool or which functions. One group member with acoustics knowledge described a process that clearly needed improving: working out which sound insulation each wall needs, based on the rooms on either side. That gave us our vision.

---

### 2. Find out what information is accessible

Before deciding what a tool should do, find out **what you have to work with**. A tool can only use the information that is actually in the model. If you are new to the IFC format, as we were, this step is essential.

A simple way to do it:

1. **Look at the model.** Open the IFC file in Blender (with the Bonsai add-on) for a visual overview, and browse the elements and their properties.
2. **List the information with a short script.** A few lines of Python with IfcOpenShell can list every element of a given type and its attributes. For example, to list all rooms:

```python
import ifcopenshell

# Open the IFC file
model = ifcopenshell.open("building.ifc")

# Get all rooms (spaces)
spaces = model.by_type("IfcSpace")

# Print each room's ID and name
for space in spaces:
    print(f"ID: {space.GlobalId}, Name: {space.Name}")
```

Change `"IfcSpace"` to `"IfcWall"`, `"IfcDoor"`, `"IfcWindow"` or `"IfcSlab"` to explore other elements.

3. **Write down what you find**, as a list of parameters. Depending on the model, this can include room names and sizes, wall information such as material layers, the placement of doors and windows, and information about facades, structure and building services.

This list becomes the raw material for your tool.

> **In our case:** we found that we could list all rooms by name, find their size, read information about the walls (including their material layers), and see where doors and windows are placed.

---

### 3. Find out what is *not* accessible, and limit the scope

Just as important as what is in the model is **what is missing or unreliable**. Models are made by people, at a particular design stage, and they can contain modelling errors, empty properties or information that is only added later.

So ask:

- Which information does my idea **depend on**? Is it really there?
- Which information is **typed by hand** (and could be missing, misspelled or wrong)?
- Would my tool still work on **another building's model**, or only on this one?

If your tool depends on critical information that may not exist, it will fail as soon as it meets a different model. The safer choice is to limit the scope to information that can be found **in general**, in most models, and not only in the one you happen to be testing.

> **In our case:** we realised the model could contain modelling errors, and that we could not build a tool that depends on critical information from one particular modelling phase. We therefore limited ourselves to information that can be extracted in a general way, so the tool could be applied to many kinds of buildings, not just ours.

---

### 4. Understand the challenges in the information you have

Having information is not the same as being able to use it. For each parameter on your list, sort it into:

- **Ready to use:** clear, reliable and in a usable form.
- **Usable with work:** present, but needs processing first (for example, combining several elements, or interpreting geometry).
- **Unreliable or missing:** cannot be trusted on its own.

Then connect the parameters to the **requirement or question** you are interested in. Ask: *which pieces of information does this particular requirement need?* Different requirements in the same subject often need different information.

> **In our case:** to find the sound insulation requirement between rooms, we needed to know three things: **what each room is used for**, **how large it is**, and **what separates it from the neighbouring rooms** (walls, doors, windows). Room function turned out to be the hardest, because a room's name is typed by a person and cannot be fully trusted.

---

### 5. Choose a scope and a tool idea

With a list of what is accessible, what is not, and what is challenging, you can now choose a claim and a tool idea that the information can actually support. Choose a problem that is:

- **Useful:** it improves a real process, not just an interesting idea.
- **Possible:** it relies on information that is generally available in models.
- **General:** it works on other buildings, not just your test model.
- **Clear about its challenges:** you know which parts still need further work.

Write the idea down in one sentence, together with the parameters it uses and the challenges you know about. That is your basis for developing the tool.

> **In our case:** we chose a tool that looks at the **sound insulation requirements between different spaces**. It uses four parameters: **space function**, **space size**, **space separation** (which spaces are next to each other) and **which separating elements are present** (walls, doors, windows). From there we could develop the concept on a solid basis: we knew which information we could work with, and which challenges, especially identifying room function, we would need to look into further.

---

### Summary

| Step | Question to ask | Result |
|---|---|---|
| 1. Interest or problem | Which process in my subject clearly needs improving? Who can tell me? | A vision |
| 2. Accessible information | What is actually in the model? | A list of parameters |
| 3. Inaccessible information | What is missing or unreliable, and would my idea work on other models? | A limited, general scope |
| 4. Challenges | Which parameters are ready, need work, or can't be trusted? Which does my requirement need? | A clear view of what is hard |
| 5. Scope and tool idea | What useful, possible and general tool does this information support? | A tool idea in one sentence |

---

## Peer testing and feedback

**TODO** after Show & Tell: who tested the tutorial, what was unclear, and what we changed. This feeds the reflection in A5.

| Tester | Date | What worked | What was unclear | Change made |
|---|---|---|---|---|
| **TODO** | | | | |

## AI acknowledgement

This tutorial was written from our own project notes, with help from Claude for structure and wording.

## Sources

- Course assignment A3: <https://timmcginley.github.io/41934/Assignments/A3.html>
- IfcOpenShell documentation: <https://docs.ifcopenshell.org/>
- Bonsai (Blender add-on) documentation: <https://docs.bonsaibim.org/>
