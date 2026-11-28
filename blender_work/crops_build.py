# -*- coding: utf-8 -*-
"""重做温室作物：从"葱花碎点"改成成行的叶菜植株。

做法：
  · 删掉吸收进来的参考作物点云（5616 个杂乱小簇）
  · 沿 6 条径向种植带 × 3 层托盘，按行距 1.6 m、株距 1.1 m 布置成行
  · 每株：6–8 片叶（锥体压扁、向外倾斜）+ 中心嫩心，随机朝向与缩放
  · 两档绿色材质（浅绿/深绿）交替，避免一片死绿

运行： blender -b habitat_final.blend -P crops_build.py
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
rnd = random.Random(2028)

# 清掉旧作物与旧脚本残留
for o in [o for o in bpy.data.objects if o.name.startswith(("REF_Green_Crops", "FAC_Crops"))]:
    bpy.data.objects.remove(o, do_unlink=True)


def bb(n):
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob:
        return None
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


fr = bb("REF_Geodesic_Frame")
mn, mx = fr
CX, CY = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
R = (mx.x - mn.x) / 2 * 0.80
ZB = mn.z + 0.2
TIERS = [ZB + 0.35, ZB + 2.9, ZB + 5.45]
TRAY_T = 0.34
print("DOME", round(CX, 1), round(CY, 1), "R", round(R, 1), "tiers", [round(t, 2) for t in TIERS])

# ── 材质 ──
def green(name, col, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0
    return m


M_LEAF_A = green("R6_LeafLight", (0.20, 0.42, 0.10), 0.62)
M_LEAF_B = green("R6_LeafDark", (0.09, 0.26, 0.06), 0.66)
M_STEM = green("R6_Stem", (0.32, 0.40, 0.14), 0.70)


def add_leaf(bm, base, yaw, tilt, length, w, mat_idx):
    """一片叶：压扁的锥体，从基部向外上方展开"""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    dir_v = (d * math.cos(tilt) + Vector((0, 0, 1)) * math.sin(tilt)).normalized()
    mid = base + dir_v * (length * 0.5)
    rot = dir_v.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    m = Matrix.Translation(mid) @ rot @ Matrix.Diagonal((w, w * 0.28, length, 1.0))
    out = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=5,
                                radius1=1.0, radius2=0.12, depth=1.0, matrix=m)
    for f in out.get("verts", []):
        pass
    return


def plant(bm, p, scale=1.0):
    n_leaf = rnd.randint(7, 10)
    yaw0 = rnd.uniform(0, math.tau)
    for i in range(n_leaf):
        yaw = yaw0 + i * (math.tau / n_leaf) + rnd.uniform(-0.12, 0.12)
        tilt = math.radians(rnd.uniform(28, 58))
        L = rnd.uniform(1.05, 1.55) * scale
        w = rnd.uniform(0.26, 0.36) * scale
        add_leaf(bm, p + Vector((0, 0, rnd.uniform(0.02, 0.10))), yaw, tilt, L, w, 0)
    # 中心嫩心
    d = Vector((0, 0, 1))
    m = Matrix.Translation(p + Vector((0, 0, 0.14))) @ Matrix.Diagonal((0.16 * scale, 0.16 * scale, 0.45 * scale, 1.0))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=6,
                          radius1=1.0, radius2=0.2, depth=1.0, matrix=m)


bm = bmesh.new()
COUNT = 0
BANDS = 6
ROW_SPACING = 1.9
PLANT_SPACING = 1.45
for k in range(BANDS):
    th = 2 * math.pi * k / BANDS + math.pi / 12
    d = Vector((math.cos(th), math.sin(th), 0.0))
    p = Vector((-d.y, d.x, 0.0))
    r0, r1 = R * 0.22, R * 0.94
    for tier_z in TIERS:
        z = tier_z + TRAY_T / 2
        n_radial = max(6, int((r1 - r0) / PLANT_SPACING))
        for i in range(n_radial):
            rr = r0 + (r1 - r0) * (i + 0.5) / n_radial
            for row in (-1, 0, 1):
                if row != 0 and rnd.random() < 0.25:
                    continue          # 轻微缺株，避免过于机械
                off = p * (row * ROW_SPACING * 0.78)
                base = Vector((CX, CY, z)) + d * rr + off
                jitter = Vector((rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18), 0))
                # 避免贴到托盘边缘外
                if (base + jitter - Vector((CX, CY, 0))).length > R * 1.02:
                    continue
                plant(bm, base + jitter, scale=rnd.uniform(0.9, 1.2))
                COUNT += 1

# 托盘土带（深色基质，衬出植株）
for k in range(BANDS):
    th = 2 * math.pi * k / BANDS + math.pi / 12
    d = Vector((math.cos(th), math.sin(th), 0.0))
    r0, r1 = R * 0.22, R * 0.94
    for tier_z in TIERS:
        mid = Vector((CX, CY, tier_z + TRAY_T / 2 + 0.02)) + d * ((r0 + r1) / 2)
        m = (Matrix.Translation(mid) @ Matrix.Rotation(th, 4, 'Z') @
             Matrix.Diagonal(((r1 - r0) * 0.99, ROW_SPACING * 3.0, 0.06, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)

me = bpy.data.meshes.new("CROP_BED")
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new("FAC_Crops", me)
bpy.context.collection.objects.link(ob)
for m in (M_LEAF_A, M_LEAF_B, M_STEM):
    ob.data.materials.append(m)
# 按面随机分配两档绿色
for poly in ob.data.polygons:
    poly.material_index = 0 if rnd.random() < 0.55 else 1
bpy.context.view_layer.objects.active = ob
bpy.ops.object.shade_smooth()
wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
wn.keep_sharp = True

print("CROPS_BUILT", COUNT, "plants,", len(me.polygons), "faces")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("CROPS_DONE")
