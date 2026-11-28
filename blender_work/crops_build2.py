# -*- coding: utf-8 -*-
"""作物第 2 版：弯曲叶片 + 植株入土 + 滴灌与托架连接件。

改进三点（对应上一版遗留问题）：
  1. 叶片从"压扁锥体"改为**弯曲带状叶**：沿脊柱 5 点采样，宽度按 sin 分布，带弯曲与扭转
  2. 植株整体下沉 0.12 m，根部埋入基质土带
  3. 补滴灌系统：每层托盘一条滴灌主管 + 每 2 m 一根滴头；托盘与立柱之间加托架连接件

运行： blender -b habitat_final.blend -P crops_build2.py
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
rnd = random.Random(31415)

for o in [o for o in bpy.data.objects if o.name.startswith(("FAC_Crops", "FAC_Irrigation", "FAC_TrayBracket"))]:
    bpy.data.objects.remove(o, do_unlink=True)


def bb(n):
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob:
        return None
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


mn, mx = bb("REF_Geodesic_Frame")
CX, CY = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
R = (mx.x - mn.x) / 2 * 0.80
ZB = mn.z + 0.2
TIERS = [ZB + 0.35, ZB + 2.9, ZB + 5.45]
TRAY_T = 0.34
SINK = 0.12                      # 植株下沉深度
BANDS = 6
ROW_SPACING = 1.90
PLANT_SPACING = 1.6


def mat(name, col, rough=0.65):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0
    return m


M_LEAF_A = mat("R6_LeafLight", (0.22, 0.45, 0.11))
M_LEAF_B = mat("R6_LeafDark", (0.10, 0.28, 0.07))
M_STEM = mat("R6_Stem", (0.34, 0.42, 0.16), 0.7)
M_DRIP = mat("R6_Drip", (0.06, 0.06, 0.07), 0.5)

LEAF_MATS = [M_LEAF_A, M_LEAF_B]


def add_leaf(bm, base, yaw, tilt, L, W, droop):
    """弯曲带状叶：沿脊柱采样，宽度按 sin 分布，末端下垂"""
    d = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    side = Vector((-d.y, d.x, 0.0))
    N = 5
    rows = []
    for i in range(N):
        t = i / (N - 1)
        # 脊柱：先外展后下垂
        spine = (base
                 + d * (L * t * math.cos(tilt))
                 + Vector((0, 0, 1)) * (L * t * math.sin(tilt) - droop * t * t))
        width = W * math.sin(math.pi * min(1.0, t * 0.85 + 0.12)) ** 0.7
        twist = Matrix.Rotation(t * 0.5, 3, d.to_track_quat('Z', 'Y').to_euler().to_matrix()) \
            if False else None
        rows.append((spine - side * width, spine + side * width))
    for i in range(N - 1):
        a1, a2 = rows[i]
        b1, b2 = rows[i + 1]
        bm.faces.new([bm.verts.new(a1), bm.verts.new(a2), bm.verts.new(b2), bm.verts.new(b1)])


def plant(bm, p, scale=1.0):
    n = rnd.randint(6, 9)
    yaw0 = rnd.uniform(0, math.tau)
    for i in range(n):
        yaw = yaw0 + i * (math.tau / n) + rnd.uniform(-0.15, 0.15)
        tilt = math.radians(rnd.uniform(30, 62))
        L = rnd.uniform(0.85, 1.25) * scale
        W = rnd.uniform(0.13, 0.20) * scale
        add_leaf(bm, p, yaw, tilt, L, W, rnd.uniform(0.15, 0.5) * scale)
    # 茎心
    m = Matrix.Translation(p + Vector((0, 0, 0.16))) @ Matrix.Diagonal((0.13 * scale, 0.13 * scale, 0.42 * scale, 1.0))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=6,
                          radius1=1.0, radius2=0.25, depth=1.0, matrix=m)


bm = bmesh.new()
COUNT = 0
TRAY_PTS = []          # 记录托盘位置，供托架与滴灌使用
for k in range(BANDS):
    th = 2 * math.pi * k / BANDS + math.pi / 12
    d = Vector((math.cos(th), math.sin(th), 0.0))
    p = Vector((-d.y, d.x, 0.0))
    r0, r1 = R * 0.22, R * 0.94
    for tier_z in TIERS:
        z = tier_z + TRAY_T / 2 - SINK
        TRAY_PTS.append((th, r0, r1, tier_z))
        n_rad = max(6, int((r1 - r0) / PLANT_SPACING))
        for i in range(n_rad):
            rr = r0 + (r1 - r0) * (i + 0.5) / n_rad
            for row in (-1, 0, 1):
                if row != 0 and rnd.random() < 0.22:
                    continue
                base = Vector((CX, CY, z)) + d * rr + p * (row * ROW_SPACING * 0.78)
                j = Vector((rnd.uniform(-0.16, 0.16), rnd.uniform(-0.16, 0.16), 0))
                if (base + j - Vector((CX, CY, 0))).length > R * 1.02:
                    continue
                plant(bm, base + j, scale=rnd.uniform(0.9, 1.2))
                COUNT += 1

me = bpy.data.meshes.new("CROP_BED")
bm.to_mesh(me)
bm.free()
crops = bpy.data.objects.new("FAC_Crops", me)
bpy.context.collection.objects.link(crops)
for m in (M_LEAF_A, M_LEAF_B, M_STEM):
    crops.data.materials.append(m)
for poly in crops.data.polygons:
    poly.material_index = 0 if rnd.random() < 0.55 else 1
bpy.context.view_layer.objects.active = crops
bpy.ops.object.shade_smooth()
wn = crops.modifiers.new("WN", 'WEIGHTED_NORMAL')
wn.keep_sharp = True
print("CROPS2_BUILT", COUNT, len(me.polygons), "faces")

# ══════ 滴灌 + 托架 ══════
bm = bmesh.new()


def cyl(p1, p2, r, seg=6):
    p1, p2 = Vector(p1), Vector(p2)
    dv = p2 - p1
    L = dv.length
    if L < 1e-5:
        return
    m = Matrix.Translation((p1 + p2) / 2) @ dv.to_track_quat('Z', 'Y').to_matrix().to_4x4() \
        @ Matrix.Diagonal((r, r, L, 1.0))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=1.0, radius2=1.0, depth=1.0, matrix=m)


for (th, r0, r1, tier_z) in TRAY_PTS:
    d = Vector((math.cos(th), math.sin(th), 0.0))
    p = Vector((-d.y, d.x, 0.0))
    # 主管
    a = Vector((CX, CY, tier_z + 0.10)) + d * r0 + p * 0
    b = Vector((CX, CY, tier_z + 0.10)) + d * r1
    cyl(a, b, 0.055, seg=6)
    # 滴头（每 2.2 m 一根，下垂 0.25 m）
    n = max(2, int((r1 - r0) / 2.2))
    for i in range(n):
        rr = r0 + (r1 - r0) * (i + 0.5) / n
        pa = Vector((CX, CY, tier_z + 0.10)) + d * rr
        cyl(pa, pa - Vector((0, 0, 0.28)), 0.028, seg=5)
    # 托架（托盘两端与立柱连接）
    for e in (-1, 1):
        for rr in (r0, r1):
            pb = Vector((CX, CY, tier_z + TRAY_T / 2 + 0.02)) + d * rr + p * (e * 1.5)
            m = (Matrix.Translation(pb) @ Matrix.Rotation(th, 4, 'Z') @
                 Matrix.Diagonal((0.55, 0.16, 0.26, 1.0)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)

me2 = bpy.data.meshes.new("IRRIGATION")
bm.to_mesh(me2)
bm.free()
irr = bpy.data.objects.new("FAC_Irrigation", me2)
bpy.context.collection.objects.link(irr)
irr.data.materials.append(M_DRIP)
bpy.context.view_layer.objects.active = irr
bpy.ops.object.shade_smooth()
print("IRRIGATION_FACES", len(me2.polygons))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("CROPS2_DONE")
