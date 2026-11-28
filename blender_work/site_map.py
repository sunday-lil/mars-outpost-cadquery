import bpy
from mathutils import Vector
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
print("=== 现有设施占位 ===")
for n in ("居住穹顶","科研实验舱","加压廊道","返回火箭","着陆平台","太阳能板","火星车体","气象站","塔架","抛物面反射器"):
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob: continue
    mn,mx = bb(ob)
    print(f"{n:8s} x[{mn.x:7.1f},{mx.x:7.1f}] y[{mn.y:7.1f},{mx.y:7.1f}] z[{mn.z:6.1f},{mx.z:6.1f}]")
