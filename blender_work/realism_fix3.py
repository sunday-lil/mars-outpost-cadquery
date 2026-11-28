"""定点修复：重复管段、悬空碎石、走廊悬空端、旧环箍错位。"""
import bpy, bmesh
from mathutils import Vector
TER = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN")))
def terr(x,y):
    inv = TER.matrix_world.inverted()
    o = inv @ Vector((x,y,3000)); d=(inv.to_3x3() @ Vector((0,0,-1))).normalized()
    hit, loc, n, i = TER.ray_cast(o,d)
    return (TER.matrix_world @ loc).z if hit else 0.0
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))

# ① 删除我自己复制出来的两段重复管路（.002 与原段重合后又被移开，成了悬空件）
for n in ("REF_LOX_Pipe.002", "REF_LCH4_Pipe.002"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
        print("DUP_PIPE_REMOVED", n)

# ② 碎石落地（按连通块逐个贴地）
rocks = next((o for o in bpy.data.objects if o.name.startswith("火星岩石")), None)
if rocks:
    bm = bmesh.new(); bm.from_mesh(rocks.data)
    seen=set(); n_fix=0
    for v in bm.verts:
        if v.index in seen: continue
        stack=[v]; comp=[]
        while stack:
            c=stack.pop()
            if c.index in seen: continue
            seen.add(c.index); comp.append(c)
            for e in c.link_edges:
                o2=e.other_vert(c)
                if o2.index not in seen: stack.append(o2)
        pts=[rocks.matrix_world @ vv.co for vv in comp]
        zmin=min(p.z for p in pts)
        cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts)
        g=terr(cx,cy)
        if zmin-g > 0.4:
            dz=g - zmin
            inv=rocks.matrix_world.inverted()
            for vv in comp:
                w=rocks.matrix_world @ vv.co; w.z += dz; vv.co = inv @ w
            n_fix+=1
    bm.to_mesh(rocks.data); rocks.data.update(); bm.free()
    print("ROCKS_GROUNDED", n_fix)

# ③ 温室走廊：缩短成短接段，避免伸到空中
corr = next((o for o in bpy.data.objects if o.name.startswith("REF_Greenhouse_Corridor")), None)
if corr:
    mn, mx = bb(corr)
    L = mx.y - mn.y
    if L > 20:
        k = 16.0 / L
        corr.scale.y *= k
        print("CORRIDOR_SHORTENED", round(L,1), "->", round(L*k,1))

# ④ 旧环箍对齐到居住环
hoop = next((o for o in bpy.data.objects if o.name.startswith("穹顶肋")), None)
ring = next((o for o in bpy.data.objects if o.name.startswith("居住穹顶")), None)
if hoop and ring:
    a_mn, a_mx = bb(hoop); b_mn, b_mx = bb(ring)
    ac = (a_mn+a_mx)/2; bc = (b_mn+b_mx)/2
    d = bc - ac
    hoop.location += Vector((d.x, d.y, 0))
    print("HOOPS_ALIGNED", [round(v,1) for v in (d.x, d.y)])

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("REALISM_FIX3_DONE")
