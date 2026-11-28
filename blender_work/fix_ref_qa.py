import bpy, bmesh
n_uv = n_geo = 0
for ob in [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith("REF_")]:
    # 清退化几何
    bm = bmesh.new(); bm.from_mesh(ob.data)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    if zero:
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(ob.data); ob.data.update(); n_geo += 1
    bm.free()
    # 补 UV
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        n_uv += 1
    except Exception:
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass
print("REF_FIX geo", n_geo, "uv", n_uv)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
