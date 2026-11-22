# -*- coding: utf-8 -*-
"""S8：① 车辙改到"环体外缘 → 设施门口"；② 全场景按集合分组（LOD/命名整理）。

运行： blender -b habitat_v3_s7.blend -P v3_stage8.py
"""
import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(pref):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(pref)), None)


def ground(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 1200)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


# ══════ ① 车辙：环体外缘 → 设施最近边缘（贴到门口）══════
for ob in [o for o in bpy.data.objects if o.name.startswith("FAC_Track")]:
    bpy.data.objects.remove(ob, do_unlink=True)

mt = bpy.data.materials.get("V3_Track")
ring = find("居住穹顶")
rings = {}
for name in ("科研实验舱", "返回火箭", "太阳能板", "火星车体", "气象站"):
    ob = find(name)
    if ob:
        rings[name] = bbox(ob)

if ring and mt:
    rmn, rmx = bbox(ring)
    rc = Vector(((rmn.x + rmx.x) / 2, (rmn.y + rmx.y) / 2, 0))
    r_radius = max(rmx.x - rmn.x, rmx.y - rmn.y) / 2

    for name, (fmn, fmx) in rings.items():
        fc = Vector(((fmn.x + fmx.x) / 2, (fmn.y + fmx.y) / 2, 0))
        d = fc - rc
        L = d.length
        if L < 1:
            continue
        d.normalize()
        # 起点：环体外缘外 3 m；终点：设施边缘再进 2 m（贴门口）
        start = rc + d * (r_radius + 3.0)
        f_half = min(fmx.x - fmn.x, fmx.y - fmn.y) / 2
        end = fc - d * (f_half * 0.55)
        seg = end - start
        Ls = seg.length
        if Ls < 5:
            continue
        n = max(8, int(Ls / 20))
        for side in (-1.4, 1.4):
            bmb = bmesh.new()
            left, right = [], []
            for i in range(n + 1):
                p = start + seg * (i / n)
                perp = Vector((-d.y, d.x, 0.0))
                lp = p + perp * (side + 0.3)
                rp = p + perp * (side - 0.3)
                left.append(bmb.verts.new((lp.x, lp.y, ground(lp.x, lp.y) + 0.06)))
                right.append(bmb.verts.new((rp.x, rp.y, ground(rp.x, rp.y) + 0.06)))
            for i in range(len(left) - 1):
                bmb.faces.new([left[i], left[i + 1], right[i + 1], right[i]])
            me = bpy.data.meshes.new(f"TCK_{name}")
            bmb.to_mesh(me)
            bmb.free()
            ob = bpy.data.objects.new(f"TCK_{name}_{'L' if side < 0 else 'R'}", me)
            bpy.context.collection.objects.link(ob)
            ob.data.materials.append(mt)

        # 门口铺装（矩形 apron）
        apron_w, apron_l = 12.0, 8.0
        bmb = bmesh.new()
        c0 = end
        ux, uy = -d.y, d.x
        quads = []
        for (a, b) in ((-apron_w / 2, -apron_l / 2), (apron_w / 2, -apron_l / 2),
                       (apron_w / 2, apron_l / 2), (-apron_w / 2, apron_l / 2)):
            px = c0.x + ux * a + d.x * b
            py = c0.y + uy * a + d.y * b
            quads.append(bmb.verts.new((px, py, ground(px, py) + 0.07)))
        bmb.faces.new(quads)
        me = bpy.data.meshes.new(f"TCK_Apron_{name}")
        bmb.to_mesh(me)
        bmb.free()
        ob = bpy.data.objects.new(f"TCK_Apron_{name}", me)
        bpy.context.collection.objects.link(ob)
        ob.data.materials.append(mt)

print("TRACKS_REBUILT", len([o for o in bpy.data.objects if o.name.startswith("TCK_")]))

# ══════ ② 集合分组（LOD / 命名整理）══════
GROUPS = {
    "00_ENV_环境": ("火星地形", "TERRAIN", "FX_", "天空"),
    "01_CORE_原始设施": ("居住穹顶", "科研实验舱", "加压廊道", "返回火箭", "推进器机身",
                        "发动机喷管", "加速器喷管", "塔架", "抛物面反射器", "天线馈源臂",
                        "着陆平台", "火星车体", "车轮", "机械臂", "太阳能板", "能源边框",
                        "火星岩石", "散热格栅", "气象站", "车顶帆板", "观察舷窗",
                        "穹顶肋", "顶部信标", "压痕路径", "相机镜片"),
    "02_STR_结构件": ("STR_",),
    "03_FAC_设施细节": ("FAC_",),
    "04_REF_人物参照": ("REF_",),
    "05_TCK_车辙道路": ("TCK_", "FAC_Track"),
}


def ensure(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


cols = {k: ensure(k) for k in GROUPS}
moved = 0
for ob in list(bpy.data.objects):
    if ob.type != 'MESH':
        continue
    target = None
    for cname, prefixes in GROUPS.items():
        if any(ob.name.startswith(p) for p in prefixes):
            target = cols[cname]
            break
    if target is None:
        target = cols["03_FAC_设施细节"]
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    target.objects.link(ob)
    moved += 1
print("COLLECTIONS_OK", moved, {k: len(v.objects) for k, v in cols.items()})

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s8.blend"))
print("S8_DONE")
