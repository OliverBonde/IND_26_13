import ifcopenshell

path_to_model = r'C:\Users\sigur\OneDrive - Danmarks Tekniske Universitet\DTU\Advanced Building Information Modeling\41931 - Advanced BIM\A1\26-01-D-ARCH.ifc'
model = ifcopenshell.open(path_to_model)

walls = model.by_type("IfcWall")


from ifcopenshell.util.element import get_psets

for wall in walls:
    psets = get_psets(wall)

    if psets.get("Pset_WallCommon", {}).get("Reference") == "new wall":
        print(psets.get("Pset_WallCommon", {}).get("ThermalTransmittance"))


