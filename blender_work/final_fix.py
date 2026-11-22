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

# ① 太阳能板（含边框）整体落地
for pref in ("太阳能板","能源边框"):
    grp=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(pref)]
    if not grp: continue
    mn = min((bbox(o)[0].z for o in grp))
    mx = max((bbox(o)[1].z for o in grp))
    cx = sum((bbox(o)[0].x+bbox(o)[1].x)/2 for o in grp)/len(grp)
    cy = sum((bbox(o)[0].y+bbox(o)[1].y)/2 for o in grp)/len(grp)
    dz = terr(cx,cy) - mn
    for o in grp: o.location.z += dz
    print("SETTLE", pref, round(dz,2))

# ② 相机镜片：属于火星车，跟着车体落地
cam = next((o for o in bpy.data.objects if o.name.startswith("相机镜片")), None)
rov = next((o for o in bpy.data.objects if o.name.startswith("火星车体")), None)
if cam and rov:
    dz = bbox(rov)[0].z - bbox(cam)[0].z
    cam.location.z += dz
    print("SETTLE 相机镜片", round(dz,2))

# ③ REF 重名：加 AB 后缀
import itertools
for stem in ("REF_Arm","REF_Leg"):
    idx = {}
    for o in [o for o in bpy.data.objects if o.name.startswith(stem)]:
        key = o.name.replace(stem,"").replace(".001","")
        idx.setdefault(key, []).append(o)
    for key, objs in idx.items():
        for i, o in enumerate(objs):
            if i > 0:
                o.name = f"{stem}{key}_{'AB'[i-1]}"
print("RENAMED_REF")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FINAL_FIX_OK")
