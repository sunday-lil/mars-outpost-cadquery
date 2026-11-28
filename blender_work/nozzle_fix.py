"""喷管修正：发动机喷管 Z 向被拉成 191 m，按真实钟形喷管高度收敛。"""
import bpy
from mathutils import Vector
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
rk = next((o for o in bpy.data.objects if o.name.startswith("返回火箭")), None)
rmn, rmx = bb(rk)
for name, target_h in (("发动机喷管", 22.0), ("加速器喷管", 16.0)):
    ob = next((o for o in bpy.data.objects if o.name.startswith(name)), None)
    if not ob: continue
    mn, mx = bb(ob)
    h = mx.z - mn.z
    if h > target_h * 1.6:
        ob.scale.z *= target_h / h
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mn2, mx2 = bb(ob)
        ob.location.z += (rmn.z - mx2.z)      # 喷管顶接到箭体底
        print(f"NOZZLE_FIX {name}: {h:.1f} -> {target_h:.1f} m")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("NOZZLE_DONE")
