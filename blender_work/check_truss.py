import bpy
from mathutils import Vector
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
for n in ("STR_Truss_Towers","STR_Truss_Spokes","STR_Truss_LaunchTower","STR_Truss_Lab","STR_Truss_DishBack","FAC_PipeRack"):
    ob = bpy.data.objects.get(n)
    if not ob: print("MISSING", n); continue
    mn,mx = bb(ob)
    print(f"{n:26s} verts={len(ob.data.vertices):6d} faces={len(ob.data.polygons):6d} "
          f"size=({mx.x-mn.x:.1f},{mx.y-mn.y:.1f},{mx.z-mn.z:.1f}) zmin={mn.z:.1f} zmax={mx.z:.1f} hide={ob.hide_render}")
