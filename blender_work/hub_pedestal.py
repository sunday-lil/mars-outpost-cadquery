"""补轮毂基座：把中央柱下方的 8.75 m 空档填实（工程上的轮毂承台）。"""
import bpy, bmesh
from mathutils import Vector, Matrix
def bb(n):
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob: return None
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
r = bb("居住穹顶")
if r:
    mn, mx = r
    cx, cy = (mn.x+mx.x)/2, (mn.y+mx.y)/2
    # 找中央柱：用居住穹顶自身在中心区域的横向范围近似
    H = mn.z                      # 柱底悬空高度
    M = bpy.data.materials.get("R2_Pad") or bpy.data.materials.get("R2_Steel")
    bpy.ops.mesh.primitive_cylinder_add(radius=9.0, depth=H + 0.6, vertices=48,
                                        location=(cx, cy, H/2))
    ob = bpy.context.object
    ob.name = "STR_HubPedestal"
    ob.data.materials.append(M)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(radius=14.0, depth=1.6, vertices=64,
                                        location=(cx, cy, 0.8))
    pad = bpy.context.object
    pad.name = "STR_HubPad"
    pad.data.materials.append(M)
    bpy.ops.object.shade_smooth()
    print("HUB_PEDESTAL_OK h=%.2f at (%.1f,%.1f)" % (H, cx, cy))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
