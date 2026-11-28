import bpy
from mathutils import Vector
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
names = ["REF_Geodesic_Frame","REF_Glass_Glazing","REF_Green_Crops","REF_ISRU_Station",
         "REF_LOX_Pipe","REF_LCH4_Pipe","气象站","机械臂","太阳能板","火星车体"]
for n in names:
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob:
        print("MISSING", n); continue
    mn,mx = bb(ob)
    print(f"{n:20s} x[{mn.x:7.1f},{mx.x:7.1f}] y[{mn.y:7.1f},{mx.y:7.1f}] z[{mn.z:6.1f},{mx.z:6.1f}]")
