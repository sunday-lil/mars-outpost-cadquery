"""定点修复：重复管段、缺 UV、法线朝向、重名。"""
import bpy, bmesh
# ① 完全重叠的管段（.002 与原件同位）→ 移到下一段位置
moved = 0
for base, target in (("REF_LCH4_Pipe.002", (157.0, 100.0)),
                     ("REF_LOX_Pipe.002", (150.0, 100.0))):
    ob = bpy.data.objects.get(base)
    if ob:
        ob.location.y = target[1]     # 原在 y=40，移到 y=100 补末端
        moved += 1
print("MOVED_DUP", moved)

# ② 缺 UV / 法线朝内：补 UV + 重算法线
targets = ["FAC_HydroLamp","FAC_HydroRack","FAC_ISRU_Aux","FAC_PipeRack",
           "STR_Truss_DishBack","STR_Truss_Lab","STR_Truss_LaunchTower",
           "STR_Truss_Spokes","STR_Truss_Towers","加速器喷管","散热格栅"]
n_uv = n_norm = 0
for name in targets:
    ob = bpy.data.objects.get(name)
    if not ob or ob.type != 'MESH':
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free(); n_norm += 1
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT'); n_uv += 1
    except Exception:
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass

# ③ 名称去序号
for ob in [o for o in bpy.data.objects if "." in o.name]:
    base = ob.name.split(".")[0]
    if base not in bpy.data.objects:
        ob.name = base
print("FIXED uv", n_uv, "norm", n_norm)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FIX_ROUND2_DONE")
