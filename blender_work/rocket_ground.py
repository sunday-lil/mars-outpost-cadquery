"""火箭落地：目前箭体悬在着陆平台上方 127 m，靠细腿吊着 —— 不合理。

把箭体组整体下移，使发动机喷管底距平台 2 m；随后按新高度重建发射服务塔。
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
GROUP=("返回火箭","推进器机身","发动机喷管","加速器喷管","散热格栅","着陆平台")
grp=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(GROUP)]
rocket=[o for o in grp if not o.name.startswith("着陆平台")]
pad=[o for o in grp if o.name.startswith("着陆平台")]
pad_top = max(bb(o)[1].z for o in pad)
r_min  = min(bb(o)[0].z for o in rocket)
dz = (pad_top + 2.0) - r_min
for o in rocket: o.location.z += dz
print("ROCKET_GROUNDED dz=%.1f  pad_top=%.1f" % (dz, pad_top))

# 重建发射塔
for o in [o for o in bpy.data.objects if o.name.startswith("STR_Truss_LaunchTower")]:
    bpy.data.objects.remove(o, do_unlink=True)
M_STEEL = bpy.data.materials.get("R2_Steel")
mn,mx = bb(rocket[0])
bx = mn.x - 18.0; by=(mn.y+mx.y)/2
gz = 0.0
H = (mx.z - gz)*0.95
bm=bmesh.new()
def member(p1,p2,r,seg=5):
    p1,p2=Vector(p1),Vector(p2); dv=p2-p1; L=dv.length
    if L<1e-5: return
    m=Matrix.Translation((p1+p2)/2)@dv.to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Diagonal((r,r,L,1.0))
    bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=seg,radius1=1.0,radius2=1.0,depth=1.0,matrix=m)
W=7.0; PAN=14
offs=[(-1,-1),(1,-1),(1,1),(-1,1)]
def c3(t,o):
    w=W*(1-0.35*t)
    return Vector((bx+o[0]*w/2, by+o[1]*w/2, gz+H*t))
for o in offs:
    member(c3(0,o),c3(1,o),0.22,8)
for i in range(PAN+1):
    t=i/PAN
    for j in range(4):
        a,b=offs[j],offs[(j+1)%4]
        member(c3(t,a),c3(t,b),0.08,4)
        if i<PAN:
            t2=(i+1)/PAN
            member(c3(t,a),c3(t2,b),0.06,4)
            member(c3(t,b),c3(t2,a),0.06,4)
me=bpy.data.meshes.new("TOWER"); bm.to_mesh(me); bm.free()
ob=bpy.data.objects.new("STR_Truss_LaunchTower",me)
bpy.context.collection.objects.link(ob); ob.data.materials.append(M_STEEL)
bpy.context.view_layer.objects.active=ob; bpy.ops.object.shade_smooth()
wn=ob.modifiers.new("WN",'WEIGHTED_NORMAL'); wn.keep_sharp=True
print("LAUNCH_TOWER_REBUILT H=%.1f" % H)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("ROCKET_FIX_DONE")
