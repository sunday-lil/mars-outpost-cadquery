import bpy
from mathutils import Vector
def bbox(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
# ① 删除脚本残留的默认 Cube（非原始模型物体）
for name in ("Cube", "Cube.001"):
    ob = bpy.data.objects.get(name)
    if ob and ob.type == 'MESH':
        bpy.data.objects.remove(ob, do_unlink=True)
        print("REMOVED_STRAY", name)
# ② 压痕路径：平铺到地面，高度压到不影响结构
ter = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN")))
for ob in [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith("压痕路径")]:
    mn, mx = bbox(ob)
    c = (mn+mx)/2
    inv = ter.matrix_world.inverted()
    ol = inv @ Vector((c.x, c.y, 1500)); dl = (inv.to_3x3() @ Vector((0,0,-1))).normalized()
    hit, loc, n, i = ter.ray_cast(ol, dl)
    gz = (ter.matrix_world @ loc).z if hit else 0.0
    ob.location.z += (gz + 0.05 - mn.z)
    print("DECAL_GROUNDED", ob.name, round(ob.location.z,2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FIX_SI_DONE")
