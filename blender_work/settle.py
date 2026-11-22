"""把全体设施整体下移到场平垫上（统一平移，相对关系不变）。"""
import bpy
from mathutils import Vector
def bbox(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
ter = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN")))
core = [o for o in bpy.data.objects if o.type=='MESH' and o is not ter
        and o.name.startswith(("居住穹顶","科研实验舱","加压廊道","返回火箭","着陆平台",
                               "太阳能板","能源边框","火星车体","车轮","机械臂","气象站",
                               "塔架","抛物面反射器","推进器机身","发动机喷管","加速器喷管",
                               "散热格栅","穹顶肋","观察舷窗","顶部信标","车顶帆板","火星岩石"))]
gaps = []
for o in core:
    mn, mx = bbox(o)
    gaps.append(mn.z)
gaps.sort()
shift = -gaps[len(gaps)//2]      # 中位数
print("MEDIAN_GAP", round(shift,2))
for o in bpy.data.objects:
    if o.type=='MESH' and o is not ter and not o.name.startswith("FX_"):
        o.location.z += shift
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SETTLED", round(shift,2))
