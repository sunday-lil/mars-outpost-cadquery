# -*- coding: utf-8 -*-
"""结构逻辑修正：把"塔顶住转环"改成"塔→静态轭环→滚轮→转环"。

修正项：
  1. 4 座桁架塔移到 R_SUP（转环外侧 6 m），塔顶托起一圈**静态支承轭环**（桁架）
  2. 轭环与转环之间加 8 组滚轮（3 轮一组，带间隙），让"转动"这件事看得见
  3. 中央柱底部加**回转支承**（轴承座 + 法兰 + 地脚螺栓圈）
  4. 太阳能阵改双柱 A 形架 + 扭矩管，板面不再单点悬挑
  5. 加压廊道与轮毂之间加**气闸环**（说明廊道接的是静止的轮毂，不是转环）

运行： blender -b habitat_final.blend -P structure_fix.py
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
M_STEEL = bpy.data.materials.get("R2_Steel")
M_DARK = bpy.data.materials.get("R2_Dark")
M_HULL = bpy.data.materials.get("R2_Hull")
M_PAD = bpy.data.materials.get("R2_Pad") or M_STEEL

# 清掉上一版自建塔/滚轮
for o in [o for o in bpy.data.objects if o.name.startswith(("STR_Truss_Towers", "STR_Yoke", "STR_Roller",
                                                            "STR_Bearing", "STR_Airlock", "STR_SolarFrame"))]:
    bpy.data.objects.remove(o, do_unlink=True)


def bb(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(n):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(n)), None)


def ground(x, y):
    ter = find("火星地形") or find("TERRAIN")
    inv = ter.matrix_world.inverted()
    o = inv @ Vector((x, y, 3000))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, n, i = ter.ray_cast(o, d)
    return (ter.matrix_world @ loc).z if hit else 0.0


ring = find("居住穹顶")
vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
CX = (max(v.x for v in vs) + min(v.x for v in vs)) / 2
CY = (max(v.y for v in vs) + min(v.y for v in vs)) / 2
RXY = [math.hypot(v.x - CX, v.y - CY) for v in vs]
R_OUT = max(RXY)
near = [v.z for v, r in zip(vs, RXY) if r > 0.88 * R_OUT]
Z_RING = (max(near) + min(near)) / 2
R_TUBE = max(0.8, (max(near) - min(near)) / 2)
R_MAJ = R_OUT - R_TUBE
R_SUP = R_OUT + 6.0            # 静态轭环半径
print(f"RING R={R_MAJ:.2f} tube={R_TUBE:.2f} z={Z_RING:.2f} Rout={R_OUT:.2f} -> Rsup={R_SUP:.2f}")


def member(bm, p1, p2, r, seg=6):
    p1, p2 = Vector(p1), Vector(p2)
    dv = p2 - p1
    L = dv.length
    if L < 1e-5:
        return
    m = Matrix.Translation((p1 + p2) / 2) @ dv.to_track_quat('Z', 'Y').to_matrix().to_4x4() \
        @ Matrix.Diagonal((r, r, L, 1.0))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=1.0, radius2=1.0, depth=1.0, matrix=m)


def node(bm, p, r):
    m = Matrix.Translation(Vector(p)) @ Matrix.Diagonal((r, r, r, 1.0))
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=m)


def box(bm, p, sx, sy, sz, rz=0.0):
    m = Matrix.Translation(Vector(p)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Diagonal((sx, sy, sz, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def to_obj(bm, name, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
    wn.keep_sharp = True
    return ob


# ══════ ① 静态支承轭环（三条弦 + 斜撑 + 竖杆，共 48 段）══════
bm = bmesh.new()
Z_TOP = Z_RING + R_TUBE * 0.75
Z_BOT = Z_RING - R_TUBE * 0.75
NSEG = 48
for zc, rchord in ((Z_TOP, 0.30), (Z_RING, 0.34), (Z_BOT, 0.30)):
    for i in range(NSEG):
        a1 = 2 * math.pi * i / NSEG
        a2 = 2 * math.pi * (i + 1) / NSEG
        p1 = Vector((CX + R_SUP * math.cos(a1), CY + R_SUP * math.sin(a1), zc))
        p2 = Vector((CX + R_SUP * math.cos(a2), CY + R_SUP * math.sin(a2), zc))
        member(bm, p1, p2, rchord, seg=6)
# 竖向 + 斜撑
for i in range(NSEG):
    a1 = 2 * math.pi * i / NSEG
    a2 = 2 * math.pi * (i + 1) / NSEG
    p_top1 = Vector((CX + R_SUP * math.cos(a1), CY + R_SUP * math.sin(a1), Z_TOP))
    p_bot1 = Vector((CX + R_SUP * math.cos(a1), CY + R_SUP * math.sin(a1), Z_BOT))
    p_top2 = Vector((CX + R_SUP * math.cos(a2), CY + R_SUP * math.sin(a2), Z_TOP))
    p_bot2 = Vector((CX + R_SUP * math.cos(a2), CY + R_SUP * math.sin(a2), Z_BOT))
    member(bm, p_top1, p_bot1, 0.14, seg=5)
    member(bm, p_top1, p_bot2, 0.11, seg=5)
    member(bm, p_bot1, p_bot2, 0.11, seg=5)
    if i % 2 == 0:
        node(bm, p_top1, 0.42)
        node(bm, p_bot1, 0.42)
print("YOKE_RING_OK")

# ══════ ② 4 座塔移到 R_SUP，顶托轭环 ══════
for k in range(4):
    th = 2 * math.pi * k / 4 + math.pi / 4
    px = CX + R_SUP * math.cos(th)
    py = CY + R_SUP * math.sin(th)
    gz = ground(px, py)
    top = Z_RING
    H = top - gz
    w_bot, w_top = 14.0, 6.0
    offs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    PAN = 8

    def corner(t, o):
        w = w_bot + (w_top - w_bot) * t
        return Vector((px + o[0] * w / 2, py + o[1] * w / 2, gz + H * t))

    for o in offs:
        member(bm, corner(0, o), corner(1, o), 0.62, seg=9)
    for i in range(PAN + 1):
        t = i / PAN
        for j in range(4):
            a, b = offs[j], offs[(j + 1) % 4]
            member(bm, corner(t, a), corner(t, b), 0.20, seg=6)
            if i < PAN:
                t2 = (i + 1) / PAN
                member(bm, corner(t, a), corner(t2, b), 0.15, seg=5)
                member(bm, corner(t, b), corner(t2, a), 0.15, seg=5)
            node(bm, corner(t, a), 0.42)
    # 塔顶与轭环之间的水平连杆（把塔和环形托架连成整体）
    for o in offs:
        top_pt = corner(1.0, o)
        radial = Vector((top_pt.x - CX, top_pt.y - CY, 0)).normalized()
        yoke_pt = Vector((CX + R_SUP * math.cos(th), CY + R_SUP * math.sin(th), Z_RING))
        member(bm, top_pt, yoke_pt, 0.26, seg=6)
    # 混凝土基座
    for o in offs:
        p = corner(0.0, o)
        box(bm, p + Vector((0, 0, 0.8)), 7.0, 7.0, 1.8)
print("TOWERS_AT_YOKE_OK")

yoke = to_obj(bm, "STR_Yoke", M_STEEL)

# ══════ ③ 滚轮组：轭环 ↔ 转环，8 组 × 3 轮，留 0.35 m 间隙 ══════
bm = bmesh.new()
GAP = 0.35
for k in range(8):
    th = 2 * math.pi * k / 8 + math.pi / 16
    d = Vector((math.cos(th), math.sin(th), 0.0))
    # 支架（固定在轭环内缘）
    base = Vector((CX, CY, Z_RING)) + d * (R_SUP - 0.6)
    box(bm, base, 1.4, 0.9, 1.6, rz=th)
    for dz in (-R_TUBE * 0.42, 0.0, R_TUBE * 0.42):
        rp = base + Vector((0, 0, dz)) - d * 0.9
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.55,
                                  matrix=Matrix.Translation(rp))
    member(bm, base + Vector((0, 0, -R_TUBE * 0.42)), base + Vector((0, 0, R_TUBE * 0.42)), 0.16, seg=6)
rollers = to_obj(bm, "STR_Rollers", M_DARK)
print("ROLLERS_OK")

# ══════ ④ 中央回转支承 ══════
bm = bmesh.new()
hub_top = Z_RING - R_TUBE
box(bm, Vector((CX, CY, 0.9)), 26.0, 26.0, 1.8)          # 基础
member(bm, Vector((CX, CY, 1.8)), Vector((CX, CY, 6.2)), 7.2, seg=24)   # 轴承座
box(bm, Vector((CX, CY, 6.6)), 19.0, 19.0, 0.9)          # 上法兰
for i in range(16):                                       # 地脚螺栓圈
    a = 2 * math.pi * i / 16
    p = Vector((CX + 10.5 * math.cos(a), CY + 10.5 * math.sin(a), 1.4))
    member(bm, p, p + Vector((0, 0, 1.2)), 0.22, seg=6)
box(bm, Vector((CX, CY, hub_top - 2.0)), 15.0, 15.0, 1.2)  # 顶部承压环
bearing = to_obj(bm, "STR_Bearing", M_STEEL)
print("BEARING_OK")

# ══════ ⑤ 太阳能阵：双柱 A 形架 + 扭矩管 ══════
sol = find("太阳能板")
if sol:
    mn, mx = bb(sol)
    bm = bmesh.new()
    # 沿板阵长度方向每 12 m 一组支架
    span = mx.y - mn.y
    n = max(2, int(span / 12))
    for i in range(n):
        y = mn.y + span * (i + 0.5) / n
        gz = ground((mn.x + mx.x) / 2, y)
        top_z = mn.z + (mx.z - mn.z) * 0.45
        for sx in (-3.2, 3.2):
            x = (mn.x + mx.x) / 2 + sx
            member(bm, Vector((x, y, gz)), Vector((x, y, top_z)), 0.42, seg=8)
            member(bm, Vector((x, y, gz)), Vector((x + (2.6 if sx > 0 else -2.6), y, gz + 0.4)), 0.22, seg=5)
    # 扭矩管
    member(bm, Vector(((mn.x + mx.x) / 2, mn.y, mn.z + (mx.z - mn.z) * 0.45)),
           Vector(((mn.x + mx.x) / 2, mx.y, mn.z + (mx.z - mn.z) * 0.45)), 0.35, seg=10)
    solar_frame = to_obj(bm, "STR_SolarFrame", M_STEEL)
    print("SOLAR_FRAME_OK", n, "bays")

# ══════ ⑥ 廊道 ↔ 轮毂 气闸环 ══════
corr = find("加压廊道")
if corr:
    mn, mx = bb(corr)
    near_x = mx.x if abs(mx.x - CX) < abs(mn.x - CX) else mn.x
    bm = bmesh.new()
    for i in range(3):
        bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=32,
                              radius1=7.0 - i * 0.4, radius2=7.0 - i * 0.4, depth=1.2,
                              matrix=Matrix.Translation(Vector((near_x + i * 1.6, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2)))
                              @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    airlock = to_obj(bm, "STR_Airlock", M_HULL)
    print("AIRLOCK_OK")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("STRUCTURE_FIX_DONE")
