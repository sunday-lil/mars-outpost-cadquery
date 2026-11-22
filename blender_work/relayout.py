# -*- coding: utf-8 -*-
"""v2.1 场地重排：按设施分组把物件移到环体外侧，消除穿模。

环体占位：以 (-12, 0) 为心、半径 34–46 m 的圆环带，z 24–36 m。
任何设施只要不在这个环带体积内，就不会与环体相交。

运行： blender -b habitat_v2.blend -P relayout.py
"""
import math

import bpy
from mathutils import Vector

RING_C = Vector((-12.0, 0.0, 0.0))
R_IN, R_OUT = 34.0, 46.0
Z_LO, Z_HI = 24.0, 36.0

# 分组 → 目标中心 (x, y)
GROUPS = {
    "rocket": (("返回火箭", "推进器机身", "发动机喷管", "加速器喷管", "散热格栅",
                "着陆平台", "塔架"), (150.0, 70.0)),
    "dish": (("抛物面反射器", "天线馈源臂"), (-150.0, 85.0)),
    "lab": (("科研实验舱",), (132.0, -62.0)),
    "solar": (("太阳能板", "能源边框"), (-132.0, -92.0)),
    "rover": (("火星车体", "车轮", "机械臂", "车顶帆板", "相机镜片"), (-26.0, -122.0)),
    "weather": (("气象站",), (-146.0, 12.0)),
}


def bbox(objs):
    pts = []
    for ob in objs:
        pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def terrain_z(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 800)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for gname, (prefixes, target) in GROUPS.items():
    grp = [o for o in meshes if any(o.name.startswith(p) for p in prefixes)]
    if not grp:
        print("MISSING", gname)
        continue
    mn, mx = bbox(grp)
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    dx, dy = target[0] - cx, target[1] - cy
    for ob in grp:
        ob.location.x += dx
        ob.location.y += dy
    # 重新落地
    mn2, mx2 = bbox(grp)
    gz = terrain_z(target[0], target[1])
    dz = gz - mn2.z
    for ob in grp:
        ob.location.z += dz
    print(f"MOVED {gname:8s} -> ({target[0]:.0f},{target[1]:.0f})  objects={len(grp)}  dz={dz:.2f}")

# ── 校验：所有物体是否与环带体积相交 ──
def in_ring_band(mn, mx):
    # 圆环带近似：物体包围盒到环心的最近/最远距离
    cx = min(max(RING_C.x, mn.x), mx.x)
    cy = min(max(RING_C.y, mn.y), mx.y)
    near = math.hypot(cx - RING_C.x, cy - RING_C.y)
    far = max(math.hypot(px - RING_C.x, py - RING_C.y)
              for px in (mn.x, mx.x) for py in (mn.y, mx.y))
    zhit = not (mx.z < Z_LO or mn.z > Z_HI)
    return zhit and not (far < R_IN or near > R_OUT)


bad = []
for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
    if ob.name.startswith(("RING_", "RingRib", "RingPort", "Spoke", "HUB", "Tower", "Pad", "火星地形", "TERRAIN")):
        continue
    mn, mx = bbox([ob])
    if in_ring_band(mn, mx):
        bad.append(ob.name)
print("RING_INTERSECT", len(bad), bad[:10])

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("RELAYOUT_DONE")
