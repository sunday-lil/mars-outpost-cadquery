import bpy, bmesh
from mathutils import Vector
def bb(n):
    ob = bpy.data.objects.get(n)
    if not ob: return
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    print(f"{n:26s} x[{min(p.x for p in pts):7.1f},{max(p.x for p in pts):7.1f}] "
          f"y[{min(p.y for p in pts):7.1f},{max(p.y for p in pts):7.1f}] "
          f"z[{min(p.z for p in pts):6.1f},{max(p.z for p in pts):6.1f}]")
for n in ("REF_Geodesic_Frame","REF_Glass_Glazing","REF_Green_Crops","REF_Greenhouse_Corridor",
          "FAC_HydroRack","FAC_HydroLamp","TCK_科研实验舱_L","STR_HubPedestal"):
    bb(n)
# 作物连通块高度分布
ob = bpy.data.objects.get("REF_Green_Crops")
if ob:
    bm = bmesh.new(); bm.from_mesh(ob.data)
    seen=set(); zs=[]
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
        zs.append(round(min((ob.matrix_world @ v.co).z for v in comp),1))
    bm.free()
    zs.sort()
    print("CROP_ISLANDS", len(zs), "z-min 分布:", zs[:6], "...", zs[-6:])
