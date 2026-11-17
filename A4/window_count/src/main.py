def analyse(model):
    spaces = model.by_type("IfcSpace")
    return {
        "space_count": len(spaces),
        "spaces": [
            {"globalid": s.GlobalId, "name": s.Name, "long_name": s.LongName}
            for s in spaces
        ],
    }