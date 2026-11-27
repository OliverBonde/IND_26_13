
import ifcopenshell.util.element
import ifcopenshell.util.unit


def analyse(model):
    # Convert IFC area values to square metres.
    area_scale = ifcopenshell.util.unit.calculate_unit_scale(model, "AREAUNIT")
    rooms = []

    for space in model.by_type("IfcSpace"):
        # Find the building level assigned to the room.
        parents = [rel.RelatingObject for rel in (space.Decomposes or [])]
        parents += [rel.RelatingStructure for rel in (getattr(space, "ContainedInStructure", None) or [])]
        level = next((p.Name for p in parents if p.is_a("IfcBuildingStorey")), "")

        # Read the room number from IFC properties.
        properties = ifcopenshell.util.element.get_psets(space, psets_only=True)
        number = next((str(data[key]) for data in properties.values()
                       for key in ("Number", "RoomNumber", "Room Number")
                       if data.get(key) not in (None, "")), space.Description or "")

        # Read the IFC-reported room area, preferring net floor area.
        quantities = ifcopenshell.util.element.get_psets(space, qtos_only=True)
        area = next((data[key] for key in
                     ("NetFloorArea", "NetArea", "RoomArea", "SpaceArea", "Area",
                      "GrossFloorArea", "GrossArea")
                     for data in quantities.values()
                     if isinstance(data.get(key), (int, float))), None)

        rooms.append({
            "room_no": number,
            "ifc_room_name": space.Name or "",
            "level": level or "",
            "description": space.LongName or "",
            "space_area_m2": round(area * area_scale, 2) if area is not None else None,
        })

    return {"space_count": len(rooms), "spaces": rooms}
