"""现实性审查：找出悬空几何（离地且下方无支撑）。"""
import bpy, bmesh
from mathutils import Vector
def terr(x,y):
    ter = next((o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN"))), None)
    inv = ter.matrix_world.inverted()
    o = inv @ Vector((x,y,3000)); d = (inv.to_3x3() @ Vector((0,0,-1))).normalized()
    hit, loc, n, i = ter.ray_cast(o, d)
    return (ter.matrix_world @ loc).z if hit else 0.0

report=[]
for ob in [o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith(("火星地形","TERRAIN","FX_"))]:
    bm = bmesh.new(); bm.from_mesh(ob.data)
    # 连通分量
    seen=set(); islands=[]
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
        islands.append(comp)
    floating=0; worst=0
    for comp in islands:
        zmin = min((ob.matrix_world @ v.co).z for v in comp)
        cx = sum((ob.matrix_world @ v.co).x for v in comp)/len(comp)
        cy = sum((ob.matrix_world @ v.co).y for v in comp)/len(comp)
        g = terr(cx, cy)
        if zmin - g > 1.0:
            floating += 1
            worst = max(worst, zmin-g)
    bm.free()
    if floating:
        report.append((ob.name, len(islands), floating, round(worst,2)))
report.sort(key=lambda r:-r[3])
print("=== 悬空几何（离地 >1 m 的连通块）===")
for n,isl,fl,w in report[:18]:
    print(f"{n:26s} islands={isl:4d} floating={fl:4d} max_gap={w:7.2f} m")
print("TOTAL_FLOAT_OBJECTS", len(report))
