import ifcopenshell

path_to_model = r'C:\Users\sigur\OneDrive - Danmarks Tekniske Universitet\DTU\Advanced Building Information Modeling\41931 - Advanced BIM\A1\26-01-D-ARCH.ifc'
model = ifcopenshell.open(path_to_model)

spaces = model.by_type("IfcSpace")
room_names = []

import ifcopenshell
import tkinter as tk

# -----------------------
# Load IFC
# -----------------------

model = ifcopenshell.open(path_to_model)
spaces = model.by_type("IfcSpace")

# Unique LongNames
long_names = sorted({
    space.LongName
    for space in spaces
    if space.LongName
})

# -----------------------
# Categories
# -----------------------

categories = {
    1: ("Office", []),
    2: ("Meeting Room", []),
    3: ("Toilet", []),
    4: ("Corridor", []),
    5: ("Kitchen", []),
    6: ("Storage", []),
    7: ("Technical", []),
    8: ("Other", []),
    9: ("Ignore", [])
}

current_index = 0


# -----------------------
# UI
# -----------------------

root = tk.Tk()
root.title("IFC Space Sorter")
root.geometry("600x400")


title = tk.Label(
    root,
    text="Sort LongNames",
    font=("Arial", 20)
)
title.pack(pady=20)


current_label = tk.Label(
    root,
    text="",
    font=("Arial", 30)
)
current_label.pack(pady=30)


instructions = tk.Label(
    root,
    text="Press 1-9 to assign",
    font=("Arial", 14)
)
instructions.pack()


categories_label = tk.Label(
    root,
    text="",
    justify="left",
    font=("Arial", 12)
)
categories_label.pack(pady=20)


# -----------------------
# Show current LongName
# -----------------------

def update_ui():

    if current_index >= len(long_names):
        current_label.config(text="Finished!")
        instructions.config(text="")
        return

    current_label.config(
        text=long_names[current_index]
    )


# -----------------------
# Keyboard input
# -----------------------

def key_pressed(event):

    global current_index

    key = event.char

    if key not in "123456789":
        return

    category_number = int(key)

    category_name, category_list = categories[category_number]

    # Current LongName
    long_name = long_names[current_index]

    # Add to category
    category_list.append(long_name)

    # Move to next LongName
    current_index += 1

    update_ui()


# -----------------------
# Keyboard binding
# -----------------------

root.bind("<Key>", key_pressed)


# -----------------------
# Start
# -----------------------

update_ui()

root.mainloop()
#for space in spaces:

#    name = space.LongName

#    if name not in room_names:
#        room_names.append(name)

#print("list of all room names:")
#for i in room_names:
#    print(i)

#print("")
#print("list of all attributes: ", spaces[1].get_info())


