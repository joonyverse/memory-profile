import gdb
import os
import sys

def get_fields_recursive(gdb_type, offset_offset=0):
    fields_list = []
    try:
        gdb_type = gdb_type.strip_typedefs()
    except:
        pass

    if gdb_type.code in (gdb.TYPE_CODE_PTR, gdb.TYPE_CODE_REF):
        return fields_list

    try:
        fields = gdb_type.fields()
    except:
        return fields_list

    for f in fields:
        if not hasattr(f, "bitpos") or f.bitpos is None:
            continue
        
        field_offset = offset_offset + (f.bitpos // 8)
        field_size = f.type.sizeof
        
        field_info = {
            "name": f.name,
            "type": str(f.type),
            "offset": field_offset,
            "size": field_size,
            "children": []
        }
        
        if f.type.code in (gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION):
            field_info["children"] = get_fields_recursive(f.type, field_offset)
            
        fields_list.append(field_info)
        
    fields_list.sort(key=lambda x: x["offset"])
    return fields_list

def calculate_holes_and_padding(fields, total_size, start_offset=0):
    layout = []
    current_offset = start_offset
    
    for f in fields:
        if f["offset"] > current_offset:
            hole_size = f["offset"] - current_offset
            layout.append({
                "type": "hole",
                "name": f"/* XXX {hole_size} bytes hole */",
                "offset": current_offset,
                "size": hole_size,
                "children": []
            })
            current_offset = f["offset"]
            
        if f["children"]:
            f["children"] = calculate_holes_and_padding(f["children"], f["size"], f["offset"])
            
        layout.append({
            "type": "member",
            "name": f["name"],
            "type_str": f["type"],
            "offset": f["offset"],
            "size": f["size"],
            "children": f["children"]
        })
        current_offset += f["size"]
        
    end_offset = start_offset + total_size
    if current_offset < end_offset:
        padding_size = end_offset - current_offset
        layout.append({
            "type": "padding",
            "name": f"/* padding: {padding_size} bytes */",
            "offset": current_offset,
            "size": padding_size,
            "children": []
        })
        
    return layout

def print_tree(item, indent=0):
    ind = "  " * indent
    if item["type"] in ("hole", "padding"):
        print(f"{item["offset"]:4d} | {ind}{item["name"]}")
    else:
        print(f"{item["offset"]:4d} | {ind}{item["type_str"]} {item["name"]} ({item["size"]}B)")
        for child in item["children"]:
            print_tree(child, indent + 1)

def main():
    structs_str = os.environ.get("STRUCTS_TO_ANALYZE", "")
    structs = [s.strip() for s in structs_str.split() if s.strip()]
    
    if not structs and os.path.exists("structs_list.txt"):
        with open("structs_list.txt", "r") as f:
            structs = [line.strip() for line in f if line.strip()]
            
    if not structs:
        print("No structures to analyze. Specify via STRUCTS_TO_ANALYZE environment variable or structs_list.txt.")
        return

    print("====================================================")
    print(" GDB DWARF Memory Layout Analysis Report")
    print("====================================================")
    
    for sname in structs:
        t = None
        for prefix in ("", "struct ", "class "):
            try:
                t = gdb.lookup_type(prefix + sname)
                if t:
                    break
            except:
                pass
                
        if t is None:
            print(f"\n[ERROR] Struct/Class '{sname}' not found in DWARF info.\n")
            continue
                    
        total_size = t.sizeof
        fields = get_fields_recursive(t)
        layout = calculate_holes_and_padding(fields, total_size)
        
        holes_size = sum(x["size"] for x in layout if x["type"] == "hole")
        padding_size = sum(x["size"] for x in layout if x["type"] == "padding")
        total_waste = holes_size + padding_size
        waste_pct = (total_waste / total_size * 100) if total_size > 0 else 0
        
        print(f"\nstruct {sname} {{  /* size: {total_size} bytes, waste: {total_waste} bytes ({waste_pct:.1f}%) */")
        print("Offset | Member Declaration")
        print("-" * 50)
        for item in layout:
            print_tree(item)
        print("};")

if __name__ == "__main__":
    main()
