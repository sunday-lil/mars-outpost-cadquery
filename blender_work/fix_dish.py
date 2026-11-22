import bpy, math
from mathutils import Vector
def bbox(objs):
    pts = []
    for ob in objs:
        pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))
def terr(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 900)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0

# 抛物面 + 馈源臂：落到地面并补一根基座立柱
dish = [o for o in bpy.data.objects if o.type == 'MESH'
        and o.name.startswith(("抛物面反射器", "天线馈源臂"))]
if dish:
    mn, mx = bbox(dish)
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    gz = terr(cx, cy)
    dz = gz - mn.z
    for o in dish:
        o.location.z += dz
    mn2, mx2 = bbox(dish)
    h = mn2.z - gz
    if h > 0.5:
        bpy.ops.mesh.primitive_cylinder_add(radius=1.6, depth=h, vertices=24,
                                            location=(cx, cy, gz + h / 2))
        col = bpy.context.object
        col.name = "DishPedestal"
        m = bpy.data.materials.get("V2_Steel")
        if m: col.data.materials.append(m)
        bpy.ops.object.shade_smooth()
    print("DISH_GROUNDED dz=%.2f h=%.2f" % (dz, h))

# 舷窗：贴到外壁表面，避免"悬空小环"
for ob in bpy.data.objects:
    if ob.name.startswith(("RingPort", "RingPortGlass")):
        d = Vector((ob.location.x + 12.0, ob.location.y, 0))
        if d.length > 1e-3:
            d.normalize()
        ob.location.x = -12.0 + d.x * 45.95
        ob.location.y = d.y * 45.95
print("PORTS_FLUSHED")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FIX_DONE")
