"""支撑性审查：对每个连通块向下打射线，若 1 m 内无任何几何支撑 → 判悬空。"""
import bpy, bmesh
from mathutils import Vector
dg = bpy.context.evaluated_depsgraph_get()
objs = [o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith(("FX_",))]
def down_hit(origin):
    hit, loc, nor, idx, ob, mw = bpy.context.scene.ray_cast(dg, origin, Vector((0,0,-1)))
    return (loc.z, ob.name) if hit else (None, None)

rows=[]
for ob in objs:
    if ob.name.startswith(("火星地形","TERRAIN")): continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
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
    unsupported=0; worst_gap=0.0
    for comp in islands:
        pts=[ob.matrix_world @ v.co for v in comp]
        zmin=min(p.z for p in pts)
        cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts)
        z, hitname = down_hit(Vector((cx, cy, zmin-0.05)))
        if z is None:
            unsupported+=1; worst_gap=max(worst_gap, 999)
        elif zmin - z > 1.0:
            unsupported+=1; worst_gap=max(worst_gap, zmin-z)
    bm.free()
    if unsupported:
        rows.append((ob.name, len(islands), unsupported, round(worst_gap,1)))
rows.sort(key=lambda r:-r[2])
print("=== 无支撑连通块 ===")
for n,a,b,g in rows[:16]:
    print(f"{n:26s} islands={a:4d} unsupported={b:4d} max_gap={g}")
print("TOTAL", len(rows))
