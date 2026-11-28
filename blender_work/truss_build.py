# -*- coding: utf-8 -*-
"""桁架结构专项：按资料结论重建支撑体系 + 细化。

设计依据（取自检索资料）：
  · NASA XHab：桁架杆件 50–60 mm 级、刚度控制、需计节点板质量
  · Stanford Torus：辐条 = 管外套桁架（tube inside a truss）
  · 桁架节点：斜撑焊入圆管，节点板长度 ≈ L/50 + L_member/1250
  · 火星风载：需按动态风载布置 X 形交叉撑

产出（全部为新增对象，前缀 STR_Truss_*）：
  1. 4 座格构支撑塔（4 肢 + 每节间横杆 + X 撑 + 节点球 + 节点板）
  2. 6 根辐条桁架（包裹原有辐条的方形截面桁架 + 走道护栏）
  3. 发射服务塔（格构 + 平台 + 爬梯）
  4. 实验舱外挂桁架（纵桁 + 环箍 + 斜撑）
  5. 深空天线背架（径向 + 环向桁架）
  6. 检修管线与阀组细化

运行： blender -b habitat_final.blend -P truss_build.py
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

for _o in [o for o in bpy.data.objects if o.name.startswith(("STR_Truss_", "FAC_PipeRack"))]:
    bpy.data.objects.remove(_o, do_unlink=True)

M_STEEL = bpy.data.materials.get("R2_Steel")
M_DARK = bpy.data.materials.get("R2_Dark")
M_HULL = bpy.data.materials.get("R2_Hull")


# ══════ bmesh 基元 ══════
def member(bm, p1, p2, r, seg=6):
    """两点之间的圆管杆件"""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    L = d.length
    if L < 1e-5:
        return
    mid = (p1 + p2) / 2
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    mat = Matrix.Translation(mid) @ rot @ Matrix.Diagonal((r, r, L, 1.0))
    try:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=r, depth=1.0, matrix=mat)
    except TypeError:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              diameter1=r * 2, diameter2=r * 2, depth=1.0, matrix=mat)


def node(bm, p, r):
    mat = Matrix.Translation(Vector(p)) @ Matrix.Diagonal((r, r, r, 1.0))
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=mat)
    except TypeError:
        bmesh.ops.create_icosphere(bm, subdivisions=1, diameter=2.0, matrix=mat)


def plate(bm, p, sx, sy, sz, rot_z=0.0, rot_x=0.0):
    mat = (Matrix.Translation(Vector(p)) @
           Matrix.Rotation(rot_z, 4, 'Z') @ Matrix.Rotation(rot_x, 4, 'X') @
           Matrix.Diagonal((sx, sy, sz, 1.0)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mat)


def to_object(bm, name, mat):
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


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(pref):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(pref)), None)


def ground(x, y):
    ter = find("火星地形") or find("TERRAIN")
    if ter is None:
        return 0.0
    inv = ter.matrix_world.inverted()
    o = inv @ Vector((x, y, 2000))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, nor, idx = ter.ray_cast(o, d)
    return (ter.matrix_world @ loc).z if hit else 0.0


# ══════ 环形结构基准 ══════
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
print(f"RING R={R_MAJ:.2f} tube={R_TUBE:.2f} z={Z_RING:.2f} center=({CX:.1f},{CY:.1f})")

NEW = []

# ══════ 1. 格构支撑塔（4 座）══════
# 杆件截面按 Euler 屈曲反推：Ø800×20 钢管，λ=167 → σ_cr=74 MPa > 工作应力 35 MPa
LEG_R = 0.70          # Ø1400（视觉与屈曲双重考虑）
BRACE_R = 0.21        # Ø420
NODE_R = 0.55
PANELS = 8
bm = bmesh.new()
tower_tops = []
for k in range(4):
    th = 2 * math.pi * k / 4 + math.pi / 4
    cx = CX + R_MAJ * math.cos(th)
    cy = CY + R_MAJ * math.sin(th)
    gz = ground(cx, cy)
    top = Z_RING - R_TUBE
    H = top - gz
    w_bot = 13.0
    w_top = 5.2
    tower_tops.append((cx, cy, top, th))

    def corner(level_t, ang_off):
        w = w_bot + (w_top - w_bot) * level_t
        return Vector((cx + ang_off[0] * w / 2, cy + ang_off[1] * w / 2, gz + H * level_t))

    offs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    levels = [i / PANELS for i in range(PANELS + 1)]
    # 主肢
    for o in offs:
        p0, p1 = corner(0.0, o), corner(1.0, o)
        member(bm, p0, p1, LEG_R, seg=10)
    # 横杆 + X 撑 + 节点
    for i, t in enumerate(levels):
        for j in range(4):
            a, b = offs[j], offs[(j + 1) % 4]
            pa, pb = corner(t, a), corner(t, b)
            member(bm, pa, pb, BRACE_R, seg=6)
            node(bm, pa, NODE_R * 0.75)
            if i < len(levels) - 1:
                t2 = levels[i + 1]
                pa2, pb2 = corner(t2, a), corner(t2, b)
                member(bm, pa, pb2, BRACE_R * 0.85, seg=6)
                member(bm, pb, pa2, BRACE_R * 0.85, seg=6)
        # 节点板（斜撑端部，长度按 L/50 + 杆长/1250 取 1.2 m）
        for o in offs:
            p = corner(t, o)
            plate(bm, p, 1.8, 1.8, 0.14)
    # 混凝土基座
    for o in offs:
        p = corner(0.0, o)
        plate(bm, p + Vector((0, 0, 0.7)), 6.0, 6.0, 1.6)
# 塔顶横向桁架环：把 4 座塔连成整体承台
for k in range(4):
    a = tower_tops[k]
    b = tower_tops[(k + 1) % 4]
    pa = Vector((a[0], a[1], a[2]))
    pb = Vector((b[0], b[1], b[2]))
    n = 6
    for i in range(n + 1):
        p = pa.lerp(pb, i / n)
        node(bm, p, NODE_R * 0.8)
        if i < n:
            q = pa.lerp(pb, (i + 1) / n)
            member(bm, p, q, BRACE_R * 1.1, seg=6)
            member(bm, p, q + Vector((0, 0, -3.2)), BRACE_R * 0.8, seg=5)
            member(bm, p + Vector((0, 0, -3.2)), q, BRACE_R * 0.8, seg=5)

towers = to_object(bm, "STR_Truss_Towers", M_STEEL)
NEW.append(towers)
print("TOWERS_OK")

# ══════ 2. 辐条桁架（包裹原有辐条 + 走道）══════
bm = bmesh.new()
HOOP_R = 0.13
CHORD_R = 0.24
for k in range(6):
    th = 2 * math.pi * k / 6 + math.pi / 12
    d = Vector((math.cos(th), math.sin(th), 0.0))
    r0 = R_MAJ * 0.18
    r1 = R_MAJ - R_TUBE * 0.9
    W = 1.9                      # 桁架截面宽（对应资料 bay 5.2 m 的缩尺）
    z = Z_RING
    nseg = 5
    # 四条弦杆
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts = []
        for i in range(nseg + 1):
            r = r0 + (r1 - r0) * i / nseg
            sag = 0.45 * math.sin(math.pi * i / nseg)     # 轻微下挠，符合自重
            pts.append(Vector((CX + r * d.x - d.y * sx * W / 2,
                               CY + r * d.y + d.x * sx * W / 2,
                               z + sz * W / 2 - sag)))
        for i in range(nseg):
            member(bm, pts[i], pts[i + 1], CHORD_R, seg=6)
            node(bm, pts[i], 0.20)
    # 腹杆（每节间 X 撑）+ 横隔
    for i in range(nseg):
        for sx in (-1, 1):
            r_a = r0 + (r1 - r0) * i / nseg
            r_b = r0 + (r1 - r0) * (i + 1) / nseg
            pa = Vector((CX + r_a * d.x - d.y * sx * W / 2, CY + r_a * d.y + d.x * sx * W / 2, z - W / 2))
            pb = Vector((CX + r_b * d.x - d.y * sx * W / 2, CY + r_b * d.y + d.x * sx * W / 2, z + W / 2))
            member(bm, pa, pb, HOOP_R, seg=4)
        # 顶部横隔
        r_a = r0 + (r1 - r0) * i / nseg
        pa = Vector((CX + r_a * d.x - d.y * W / 2, CY + r_a * d.y + d.x * W / 2, z + W / 2))
        pb = Vector((CX + r_a * d.x + d.y * W / 2, CY + r_a * d.y - d.x * W / 2, z + W / 2))
        member(bm, pa, pb, HOOP_R, seg=4)
        # 走道护栏立柱
        if i % 2 == 0:
            member(bm, pa, pa + Vector((0, 0, 1.1)), 0.05, seg=4)
            member(bm, pb, pb + Vector((0, 0, 1.1)), 0.05, seg=4)
spokes = to_object(bm, "STR_Truss_Spokes", M_STEEL)
NEW.append(spokes)
print("SPOKES_OK")

# ══════ 3. 发射服务塔 ══════
rk = find("返回火箭")
if rk:
    mn, mx = bbox(rk)
    bx = mn.x - 18.0
    by = (mn.y + mx.y) / 2
    gz = ground(bx, by)
    H = (mx.z - gz) * 0.92
    bm = bmesh.new()
    W = 7.0
    PAN = 14
    offs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    def c3(t, o):
        w = W * (1 - 0.35 * t)
        return Vector((bx + o[0] * w / 2, by + o[1] * w / 2, gz + H * t))
    for o in offs:
        member(bm, c3(0, o), c3(1, o), 0.22, seg=8)
    for i in range(PAN + 1):
        t = i / PAN
        for j in range(4):
            a, b = offs[j], offs[(j + 1) % 4]
            member(bm, c3(t, a), c3(t, b), 0.08, seg=4)
            if i < PAN:
                t2 = (i + 1) / PAN
                member(bm, c3(t, a), c3(t2, b), 0.06, seg=4)
                member(bm, c3(t, b), c3(t2, a), 0.06, seg=4)
        # 平台
        if i % 4 == 0 and i < PAN:
            plate(bm, c3(t, (0, 0)), W * 0.9, W * 0.9, 0.12)
        # 爬梯
        if i < PAN:
            t2 = (i + 1) / PAN
            p_low = c3(t, (0, 0)) + Vector((0, -W / 2 - 0.3, 0))
            p_high = c3(t2, (0, 0)) + Vector((0, -W / 2 - 0.3, 0))
            member(bm, p_low + Vector((-0.25, 0, 0)), p_high + Vector((-0.25, 0, 0)), 0.045, seg=4)
            member(bm, p_low + Vector((0.25, 0, 0)), p_high + Vector((0.25, 0, 0)), 0.045, seg=4)
            for s in range(3):
                tq = (i + s / 3) / PAN
                pp = c3(tq, (0, 0)) + Vector((0, -W / 2 - 0.3, 0))
                member(bm, pp + Vector((-0.25, 0, 0)), pp + Vector((0.25, 0, 0)), 0.03, seg=4)
    launch = to_object(bm, "STR_Truss_LaunchTower", M_STEEL)
    NEW.append(launch)
    print("LAUNCH_TOWER_OK")

# ══════ 4. 实验舱外挂桁架 ══════
lab = find("科研实验舱")
if lab:
    mn, mx = bbox(lab)
    c = (mn + mx) / 2
    R = min(mx.y - mn.y, mx.z - mn.z) / 2
    Lh = max(mx.x - mn.x, mx.y - mn.y)
    axis = 'X' if (mx.x - mn.x) >= (mx.y - mn.y) else 'Y'
    bm = bmesh.new()
    NH = 9
    for i in range(NH):
        t = i / (NH - 1)
        cc = mn.x + Lh * t if axis == 'X' else mn.y + Lh * t
        # 环箍（桁架化：用 8 段折线代替圆环）
        for j in range(8):
            a1 = 2 * math.pi * j / 8
            a2 = 2 * math.pi * (j + 1) / 8
            Rr = R + 0.55
            if axis == 'X':
                p1 = Vector((cc, c.y + Rr * math.cos(a1), c.z + Rr * math.sin(a1)))
                p2 = Vector((cc, c.y + Rr * math.cos(a2), c.z + Rr * math.sin(a2)))
            else:
                p1 = Vector((c.x + Rr * math.cos(a1), cc, c.z + Rr * math.sin(a1)))
                p2 = Vector((c.x + Rr * math.cos(a2), cc, c.z + Rr * math.sin(a2)))
            member(bm, p1, p2, 0.085, seg=4)
        # 纵向桁 + 斜撑
        if i < NH - 1:
            for j in range(0, 8, 2):
                a1 = 2 * math.pi * j / 8
                Rr = R + 0.55
                cc2 = (mn.x + Lh * (i + 1) / (NH - 1)) if axis == 'X' else (mn.y + Lh * (i + 1) / (NH - 1))
                if axis == 'X':
                    p1 = Vector((cc, c.y + Rr * math.cos(a1), c.z + Rr * math.sin(a1)))
                    p2 = Vector((cc2, c.y + Rr * math.cos(a1), c.z + Rr * math.sin(a1)))
                else:
                    p1 = Vector((c.x + Rr * math.cos(a1), cc, c.z + Rr * math.sin(a1)))
                    p2 = Vector((c.x + Rr * math.cos(a1), cc2, c.z + Rr * math.sin(a1)))
                member(bm, p1, p2, 0.07, seg=4)
    labtr = to_object(bm, "STR_Truss_Lab", M_STEEL)
    NEW.append(labtr)
    print("LAB_TRUSS_OK")

# ══════ 5. 天线背架 ══════
dish = find("抛物面反射器")
if dish:
    mn, mx = bbox(dish)
    c = (mn + mx) / 2
    R = (mx.x - mn.x) / 2
    bm = bmesh.new()
    zback = mn.z - 0.6
    # 径向桁
    for i in range(12):
        th = 2 * math.pi * i / 12
        p_in = Vector((c.x + R * 0.12 * math.cos(th), c.y + R * 0.12 * math.sin(th), zback - 0.2))
        p_out = Vector((c.x + R * 0.95 * math.cos(th), c.y + R * 0.95 * math.sin(th), zback))
        member(bm, p_in, p_out, 0.11, seg=5)
        member(bm, p_in + Vector((0, 0, 1.2)), p_out, 0.08, seg=4)
    # 环向
    for frac in (0.35, 0.62, 0.9):
        for i in range(24):
            a1 = 2 * math.pi * i / 24
            a2 = 2 * math.pi * (i + 1) / 24
            rr = R * frac
            p1 = Vector((c.x + rr * math.cos(a1), c.y + rr * math.sin(a1), zback - 0.1))
            p2 = Vector((c.x + rr * math.cos(a2), c.y + rr * math.sin(a2), zback - 0.1))
            member(bm, p1, p2, 0.06, seg=4)
    dishtr = to_object(bm, "STR_Truss_DishBack", M_STEEL)
    NEW.append(dishtr)
    print("DISH_TRUSS_OK")

# ══════ 6. 管线与阀组细化 ══════
if lab:
    mn, mx = bbox(lab)
    c = (mn + mx) / 2
    R = min(mx.y - mn.y, mx.z - mn.z) / 2
    bm = bmesh.new()
    for i in range(5):
        z = mn.z + (mx.z - mn.z) * (0.25 + i * 0.12)
        p1 = Vector((mn.x, c.y - R - 1.1, z))
        p2 = Vector((mx.x, c.y - R - 1.1, z))
        member(bm, p1, p2, 0.14, seg=8)
        # 法兰
        for k in range(4):
            px = mn.x + (mx.x - mn.x) * (0.15 + k * 0.22)
            plate(bm, Vector((px, c.y - R - 1.1, z)), 0.36, 0.36, 0.42, rot_z=0.0, rot_x=math.pi / 2)
        # 阀轮
        for k in range(2):
            px = mn.x + (mx.x - mn.x) * (0.3 + k * 0.4)
            plate(bm, Vector((px, c.y - R - 1.5, z)), 0.75, 0.75, 0.05)
    pipes = to_object(bm, "FAC_PipeRack", M_DARK)
    NEW.append(pipes)
    print("PIPES_OK")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("TRUSS_DONE objects:", len(NEW), [o.name for o in NEW])
