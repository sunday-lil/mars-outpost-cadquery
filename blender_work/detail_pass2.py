# -*- coding: utf-8 -*-
"""细化第 2 轮：按资料脚本补温室内部水培种植架 + ISRU 散热/放空/管桥。

资料依据：`火星生态温室大棚.py` 内部三层水培种植架；`ISRU ...储罐站.py` 顶部连通管桥、
立式冷凝分馏塔与散热片、储罐加强箍与阀门接口。

运行： blender -b habitat_final.blend -P detail_pass2.py
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

# 清理上一轮
for _o in [o for o in bpy.data.objects if o.name.startswith(("FAC_Hydro", "FAC_ISRU_"))]:
    bpy.data.objects.remove(_o, do_unlink=True)


def member(bm, p1, p2, r, seg=6):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    L = d.length
    if L < 1e-5:
        return
    m = Matrix.Translation((p1 + p2) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4() \
        @ Matrix.Diagonal((r, r, L, 1.0))
    try:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=r, depth=1.0, matrix=m)
    except TypeError:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              diameter1=r * 2, diameter2=r * 2, depth=1.0, matrix=m)


def box(bm, p, sx, sy, sz, rz=0.0, rx=0.0):
    m = (Matrix.Translation(Vector(p)) @ Matrix.Rotation(rz, 4, 'Z') @
         Matrix.Rotation(rx, 4, 'X') @ Matrix.Diagonal((sx, sy, sz, 1.0)))
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


def bb(n):
    ob = next((o for o in bpy.data.objects if o.name.startswith(n)), None)
    if not ob:
        return None
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


NEW = []

# ══════ 1. 温室内部：三层水培种植架 ══════
fr = bb("REF_Geodesic_Frame")
if fr:
    mn, mx = fr
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    R = (mx.x - mn.x) / 2 * 0.82
    zb = mn.z + 1.2
    bm = bmesh.new()
    bm_lamp = bmesh.new()
    # 6 条径向种植带，每条 3 层
    for k in range(6):
        th = 2 * math.pi * k / 6 + math.pi / 12
        d = Vector((math.cos(th), math.sin(th), 0.0))
        p = Vector((-d.y, d.x, 0.0))
        for tier in range(3):
            z = zb + tier * 2.6
            r0, r1 = R * 0.25, R * 0.95
            half_w = 1.5
            # 托盘（长条）
            mid = Vector((cx, cy, 0)) + d * ((r0 + r1) / 2) + Vector((0, 0, z))
            box(bm, mid, (r1 - r0), half_w * 2, 0.22, rz=th)
            # 立柱 4 根
            for e in (-1, 1):
                for rr in (r0, r1):
                    base = Vector((cx, cy, 0)) + d * rr + p * (e * half_w) + Vector((0, 0, zb - 0.1))
                    member(bm, base, base + Vector((0, 0, 3.0 * 2.6)), 0.09, seg=5)
            # 灯带（发光件单独材质）
            lamp = mid + Vector((0, 0, 0.85))
            box(bm_lamp, lamp, (r1 - r0) * 0.92, 0.42, 0.12, rz=th)
            # 水培管
            pa = Vector((cx, cy, 0)) + d * r0 + p * (half_w * 0.7) + Vector((0, 0, z + 0.18))
            pb = Vector((cx, cy, 0)) + d * r1 + p * (half_w * 0.7) + Vector((0, 0, z + 0.18))
            member(bm, pa, pb, 0.08, seg=5)
    racks = to_obj(bm, "FAC_HydroRack", M_STEEL)
    NEW.append(racks)
    lamp_mat = bpy.data.materials.get("V3_WinLamp") or M_HULL
    lamps = to_obj(bm_lamp, "FAC_HydroLamp", lamp_mat)
    NEW.append(lamps)
    print("HYDRO_OK", len(racks.data.polygons), len(lamps.data.polygons))

# ══════ 2. ISRU：散热片 + 放空塔 + 顶部管桥 + 储罐加强箍 ══════
isru = bb("REF_ISRU_Station")
if isru:
    mn, mx = isru
    bm = bmesh.new()
    # 散热片组（东侧，8 片）
    for i in range(8):
        px = mx.x + 2.5 + i * 1.1
        box(bm, Vector((px, (mn.y + mx.y) / 2, mn.z + 26)), 0.35, 26.0, 14.0)
    # 放空塔 ×2
    for i, off in enumerate((-14.0, 14.0)):
        px = mx.x + 1.2
        py = (mn.y + mx.y) / 2 + off
        member(bm, Vector((px, py, mn.z)), Vector((px, py, mn.z + 40)), 0.55, seg=8)
        member(bm, Vector((px, py, mn.z + 40)), Vector((px, py, mn.z + 44)), 0.85, seg=8)
    # 顶部管桥
    pa = Vector((mn.x + 6, (mn.y + mx.y) / 2, mx.z - 6))
    pb = Vector((mx.x - 4, (mn.y + mx.y) / 2, mx.z - 6))
    member(bm, pa, pb, 0.35, seg=8)
    for i in range(5):
        q = pa.lerp(pb, i / 4)
        member(bm, q, q + Vector((0, 0, -6)), 0.12, seg=5)
    isru_fac = to_obj(bm, "FAC_ISRU_Aux", M_DARK)
    NEW.append(isru_fac)
    print("ISRU_AUX_OK", len(isru_fac.data.polygons))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("DETAIL2_DONE", [o.name for o in NEW])
