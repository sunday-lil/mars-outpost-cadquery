# -*- coding: utf-8 -*-
"""第五轮定点修复：未应用缩放 / 重名 / 空材质槽 / 缺 UV / 单面叶片。"""

import bpy

log = []

# ① 未应用缩放
for name in ("REF_Geodesic_Frame", "REF_Glass_Glazing", "REF_Greenhouse_Corridor",
             "REF_ISRU_Station"):
    ob = bpy.data.objects.get(name)
    if ob and any(abs(v - 1.0) > 1e-3 for v in ob.scale):
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        log.append(f"scale {name}")

# ② 重名去序号
for old, new in (("REF_LCH4_Pipe.001", "REF_LCH4_Pipe_B"),
                 ("REF_LOX_Pipe.001", "REF_LOX_Pipe_B")):
    ob = bpy.data.objects.get(old)
    if ob and new not in bpy.data.objects:
        ob.name = new
        log.append(f"rename {old}->{new}")
for old, new in (("REF_LCH4_Pipe", "REF_LCH4_Pipe_A"), ("REF_LOX_Pipe", "REF_LOX_Pipe_A")):
    ob = bpy.data.objects.get(old)
    if ob:
        ob.name = new
        log.append(f"rename {old}->{new}")

# ③ 空材质槽（仅当无面使用该槽）
ring = bpy.data.objects.get("居住穹顶")
if ring:
    used = {p.material_index for p in ring.data.polygons}
    slots = list(ring.data.materials)
    for i in range(len(slots) - 1, -1, -1):
        if slots[i] is None and i not in used:
            ring.data.materials.pop(index=i)
            log.append(f"drop empty slot {i} on 居住穹顶")
            break

# ④ 缺 UV → 立方投影
for name in ("FAC_Crops", "FAC_HydroLamp", "FAC_HydroRack", "FAC_Irrigation"):
    ob = bpy.data.objects.get(name)
    if not ob:
        continue
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        log.append(f"uv {name}")
    except Exception:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

# ⑤ 叶片单面 → 加薄实体（两面向外法线）
crops = bpy.data.objects.get("FAC_Crops")
if crops and not any(m.type == 'SOLIDIFY' for m in crops.modifiers):
    sol = crops.modifiers.new("Thickness", 'SOLIDIFY')
    sol.thickness = 0.012
    sol.offset = 0.0
    log.append("solidify FAC_Crops")

print("FIX5_DONE", log)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
