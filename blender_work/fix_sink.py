import bpy
from mathutils import Vector
def bbox(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
ter = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN")))
def terr(x,y):
    inv = ter.matrix_world.inverted()
    ol = inv @ Vector((x,y,1500)); dl = (inv.to_3x3() @ Vector((0,0,-1))).normalized()
    hit, loc, n, i = ter.ray_cast(ol, dl)
    return (ter.matrix_world @ loc).z if hit else 0.0

groups = {
 "火星车": ("火星车体","车轮","机械臂","车顶帆板","相机镜片"),
 "气象站": ("气象站",),
}
for gname, prefs in groups.items():
    grp=[o for o in bpy.data.objects if o.type=='MESH' and any(o.name.startswith(p) for p in prefs)]
    if not grp: continue
    lows=[(o, bbox(o)) for o in grp]
    mn = min(b[0].z for o,b in lows)
    cx = sum((b[0].x+b[1].x)/2 for o,b in lows)/len(lows)
    cy = sum((b[0].y+b[1].y)/2 for o,b in lows)/len(lows)
    dz = terr(cx,cy) - mn
    if abs(dz) > 0.05:
        for o in grp: o.location.z += dz
        print("RAISED", gname, round(dz,2))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FIX_SINK_DONE")
