# -*- coding: utf-8 -*-
"""现实性修复：车辙被放到 480 m 高空、穹顶悬空 5.6 m、作物与种植架错层。

根因：
  · 车辙 z 用了 scene.ray_cast，命中了 FX_Dust 体积盒顶面（z=480）
  · 穹顶框架 min z = 5.6（导入件自带抬升），落位时按"组包围盒"对齐导致悬空
  · 作物是参考模型自带的散点（5616 个连通块，z 0–11.6），与我们的种植架错层

运行： blender -b habitat_final.blend -P realism_fix2.py
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
M_STEEL = bpy.data.materials.get("R2_Steel")


def bb(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


TER = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(("火星地形", "TERRAIN")))


def terr(x, y):
    inv = TER.matrix_world.inverted()
    o = inv @ Vector((x, y, 3000))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, n, i = TER.ray_cast(o, d)
    return (TER.matrix_world @ loc).z if hit else 0.0


# ══════ ① 车辙回到地面 ══════
fixed_tracks = 0
for ob in [o for o in bpy.data.objects if o.name.startswith("TCK_")]:
    mn, mx = bb(ob)
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    dz = terr(cx, cy) + 0.06 - mn.z
    ob.location.z += dz
    fixed_tracks += 1
print("TRACKS_GROUNDED", fixed_tracks)

# ══════ ② 穹顶落到地面 ══════
dome_targets = ("REF_Geodesic_Frame", "REF_Glass_Glazing")
for name in dome_targets:
    ob = next((o for o in bpy.data.objects if o.name.startswith(name)), None)
    if not ob:
        continue
    mn, mx = bb(ob)
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    dz = terr(cx, cy) + 0.45 - mn.z        # 落在垫层顶面
    ob.location.z += dz
    print("DOME_GROUNDED", name, round(dz, 2))

# ══════ ③ 重建种植架（按新穹顶内净空）══════
for o in [o for o in bpy.data.objects if o.name.startswith(("FAC_HydroRack", "FAC_HydroLamp"))]:
    bpy.data.objects.remove(o, do_unlink=True)

dome = next((o for o in bpy.data.objects if o.name.startswith("REF_Geodesic_Frame")), None)
fr = bb(dome)
cx, cy = (fr[0].x + fr[1].x) / 2, (fr[0].y + fr[1].y) / 2
R = (fr[1].x - fr[0].x) / 2 * 0.80
ZB = fr[0].z + 0.2                    # 地面
TIERS = [ZB + 0.35, ZB + 2.9, ZB + 5.45]
TRAY_T = 0.34


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


def box(bm, p, sx, sy, sz, rz=0.0):
    m = Matrix.Translation(Vector(p)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Diagonal((sx, sy, sz, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


bm = bmesh.new()
bm_lamp = bmesh.new()
BANDS = 6
for k in range(BANDS):
    th = 2 * math.pi * k / BANDS + math.pi / 12
    d = Vector((math.cos(th), math.sin(th), 0.0))
    p = Vector((-d.y, d.x, 0.0))
    r0, r1 = R * 0.22, R * 0.94
    half = 1.45
    for t, z in enumerate(TIERS):
        mid = Vector((cx, cy, z)) + d * ((r0 + r1) / 2)
        box(bm, mid, (r1 - r0), half * 2, TRAY_T, rz=th)
        # 立柱（到最高层）
        for e in (-1, 1):
            for rr in (r0, r1):
                base = Vector((cx, cy, ZB)) + d * rr + p * (e * half)
                member(bm, base, base + Vector((0, 0, TIERS[-1] - ZB + 0.4)), 0.09, seg=5)
        # 水培管
        pa = Vector((cx, cy, z + 0.18)) + d * r0 + p * (half * 0.7)
        pb = Vector((cx, cy, z + 0.18)) + d * r1 + p * (half * 0.7)
        member(bm, pa, pb, 0.08, seg=5)
        # 灯带
        box(bm_lamp, mid + Vector((0, 0, 0.95)), (r1 - r0) * 0.9, 0.4, 0.12, rz=th)


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


to_obj(bm, "FAC_HydroRack", M_STEEL)

# 温室地面土层
bpy.ops.mesh.primitive_cylinder_add(radius=R * 1.02, depth=0.4, vertices=64,
                                    location=(cx, cy, ZB - 0.2))
soil = bpy.context.object
soil.name = "FAC_GreenhouseSoil"
M_SOIL = bpy.data.materials.new("R5_Soil")
M_SOIL.use_nodes = True
_bs = next(n for n in M_SOIL.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_bs.inputs["Base Color"].default_value = (0.16, 0.10, 0.07, 1)
_bs.inputs["Roughness"].default_value = 0.95
soil.data.materials.append(M_SOIL)
bpy.ops.object.shade_smooth()
lamp_mat = bpy.data.materials.get("V3_WinLamp") or M_STEEL
to_obj(bm_lamp, "FAC_HydroLamp", lamp_mat)
print("RACKS_REBUILT tiers", [round(z, 2) for z in TIERS])

# ══════ ④ 作物落到种植架 ══════
crops = next((o for o in bpy.data.objects if o.name.startswith("REF_Green_Crops")), None)
if crops:
    bm = bmesh.new()
    bm.from_mesh(crops.data)
    seen = set()
    islands = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        comp = []
        while stack:
            c = stack.pop()
            if c.index in seen:
                continue
            seen.add(c.index)
            comp.append(c)
            for e in c.link_edges:
                o2 = e.other_vert(c)
                if o2.index not in seen:
                    stack.append(o2)
        islands.append(comp)

    # 只保留 1/3 体量：每个架子层放 1/3 的植株，其余删除以符合真实密度
    islands.sort(key=lambda comp: min((crops.matrix_world @ v.co).z for v in comp))
    keep = islands[: max(1, int(len(islands) * 0.85))]
    drop = islands[len(keep):]
    drop_verts = [v for comp in drop for v in comp]
    bmesh.ops.delete(bm, geom=drop_verts, context='VERTS')

    # 分层吸附：按序轮流放到三个层
    # 先把作物簇重分布到整个穹顶：相对簇心做极坐标重映射
    allw = [crops.matrix_world @ v.co for comp in keep for v in comp]
    ccx = sum(p.x for p in allw) / len(allw)
    ccy = sum(p.y for p in allw) / len(allw)
    rmax = max(math.hypot(p.x - ccx, p.y - ccy) for p in allw) or 1.0
    k_scale = (R * 0.92) / rmax
    mw0 = crops.matrix_world
    inv0 = mw0.inverted()
    for comp in keep:
        for v in comp:
            w = mw0 @ v.co
            w.x = cx + (w.x - ccx) * k_scale
            w.y = cy + (w.y - ccy) * k_scale
            v.co = inv0 @ w

    assign = 0
    mw = crops.matrix_world
    inv = mw.inverted()
    for comp in keep:
        if not comp:
            continue
        zmin = min((mw @ v.co).z for v in comp)
        target = TIERS[assign % len(TIERS)] + TRAY_T / 2
        assign += 1
        dz = target - zmin
        if abs(dz) < 1e-4:
            continue
        for v in comp:
            w = mw @ v.co
            w.z += dz
            v.co = inv @ w
    bm.to_mesh(crops.data)
    crops.data.update()
    bm.free()
    print("CROPS_PLACED islands", len(keep), "removed", len(drop))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("REALISM_FIX_DONE")
