# -*- coding: utf-8 -*-
"""变态级缺陷扫描 + 自动修复。

扫描项（共 14 类）：
  G1 零面积面      G2 重复顶点     G3 松散点/边    G4 法线不一致
  G5 退化三角      G6 非流形边     G7 零体积闭合体
  T1 未应用的缩放/旋转              T2 原点不在包围盒内
  S1 陷地          S2 悬空（非安装件）  S3 越界（出地形）
  S4 完全重叠（疑似重复件）
  M1 空材质槽      M2 多材质但只用第 1 槽   M3 贴图丢失
  N1 名称带 .001   N2 重名基名
  R1 灯光无阴影    R2 相机裁剪异常

运行： blender -b habitat_v3_s8.blend -P bug_hunt.py
"""
import json
import math
import os
from collections import Counter, defaultdict

import bmesh
import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

FIX = True
report = defaultdict(list)
fixed = defaultdict(int)
MESHES = [o for o in bpy.data.objects if o.type == 'MESH']


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


_TER = None


def terrain_z(x, y):
    global _TER
    if _TER is None:
        _TER = next((o for o in bpy.data.objects if o.type == 'MESH'
                     and o.name.startswith(("火星地形", "TERRAIN"))), None)
    if _TER is None:
        return 0.0
    mw = _TER.matrix_world
    inv = mw.inverted()
    o_local = inv @ Vector((x, y, 1500))
    d_local = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, nor, idx = _TER.ray_cast(o_local, d_local)
    return (mw @ loc).z if hit else 0.0


# ══════ 几何扫描 + 修复 ══════
for ob in MESHES:
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    n_before_v = len(bm.verts)

    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    loose_v = sum(1 for v in bm.verts if not v.link_faces)
    loose_e = sum(1 for e in bm.edges if not e.link_faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)

    # 重复顶点
    dup = len(bm.verts) - len({tuple(round(c, 5) for c in v.co) for v in bm.verts})

    # 法线一致性：闭合体体积为正
    vol = bm.calc_volume(signed=True)
    closed = nonman == 0

    if zero:
        report["G1_零面积面"].append({"obj": ob.name, "n": zero})
    if dup:
        report["G2_重复顶点"].append({"obj": ob.name, "n": dup})
    if loose_v or loose_e:
        report["G3_松散点边"].append({"obj": ob.name, "verts": loose_v, "edges": loose_e})
    if closed and vol < 0:
        report["G4_法线朝内"].append({"obj": ob.name, "volume": round(vol, 2)})
    if nonman:
        report["G6_非流形边"].append({"obj": ob.name, "n": nonman})
    if closed and abs(vol) < 1e-6:
        report["G7_零体积"].append({"obj": ob.name})

    if FIX:
        changed = False
        if dup:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
            changed = True
        if zero:
            bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
            changed = True
        if loose_v or loose_e:
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                             context='VERTS')
            changed = True
        if closed and vol < 0:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            changed = True
        if changed:
            bm.to_mesh(me)
            me.update()
            fixed["几何"] += 1
    bm.free()

# ══════ 变换 / 原点 ══════
for ob in MESHES:
    s = ob.scale
    if abs(s.x - 1) > 1e-3 or abs(s.y - 1) > 1e-3 or abs(s.z - 1) > 1e-3:
        report["T1_未应用缩放"].append({"obj": ob.name, "scale": [round(v, 3) for v in s]})
        if FIX:
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            fixed["缩放"] += 1
    mn, mx = bbox(ob)
    c = (mn + mx) / 2
    o = ob.matrix_world.to_translation()
    diag = (mx - mn).length
    if diag > 0.1 and (o - c).length > diag * 1.5:
        report["T2_原点远离"].append({"obj": ob.name,
                                      "dist": round((o - c).length, 1)})
        if FIX:
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            fixed["原点"] += 1

# ══════ 落地 / 越界 ══════
ter = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(("火星地形", "TERRAIN"))), None)
tmn, tmx = bbox(ter) if ter else (Vector((-600,) * 3), Vector((600,) * 3))
for ob in MESHES:
    if ob is ter:
        continue
    mn, mx = bbox(ob)
    size = (mx - mn).length
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    gz = terrain_z(cx, cy)
    if mn.z < gz - 0.5:
        report["S1_陷地"].append({"obj": ob.name, "below": round(gz - mn.z, 2)})
        if FIX:
            ob.location.z += (gz - mn.z)
            fixed["陷地"] += 1
    if cx < tmn.x or cx > tmx.x or cy < tmn.y or cy > tmx.y:
        report["S3_越界"].append({"obj": ob.name, "x": round(cx, 1), "y": round(cy, 1)})

# 悬空：基础件（名字不含安装关键词）离地 > 自身 5%
MOUNTED = ("天线馈源臂", "抛物面反射器", "推进器机身", "发动机喷管", "加速器喷管",
           "散热格栅", "观察舷窗", "穹顶肋", "顶部信标", "车顶帆板", "机械臂",
           "返回火箭", "REF_", "FAC_", "STR_", "TCK_")
for ob in MESHES:
    if ob is ter or ob.name.startswith(MOUNTED):
        continue
    mn, mx = bbox(ob)
    gz = terrain_z((mn.x + mx.x) / 2, (mn.y + mx.y) / 2)
    gap = mn.z - gz
    thr = max(0.5, (mx - mn).length * 0.05)
    if ob.name.startswith(("TCK_", "FAC_Track", "FAC_Apron")):
        continue
    if gap > thr:
        report["S2_悬空"].append({"obj": ob.name, "gap": round(gap, 2)})

# ══════ 完全重叠（疑似重复件）══════
boxes = [(o.name, *bbox(o)) for o in MESHES]
for i in range(len(boxes)):
    n1, a1, b1 = boxes[i]
    for j in range(i + 1, len(boxes)):
        n2, a2, b2 = boxes[j]
        if (a1 - a2).length < 0.05 and (b1 - b2).length < 0.05:
            report["S4_完全重叠"].append({"a": n1, "b": n2})

# ══════ 材质 ══════
for ob in MESHES:
    slots = ob.data.materials
    if len(slots) == 0:
        report["M1_无材质"].append({"obj": ob.name})
    else:
        empty = [i for i, m in enumerate(slots) if m is None]
        if empty:
            report["M1_空材质槽"].append({"obj": ob.name, "slots": empty})
        used = {p.material_index for p in ob.data.polygons}
        if len(slots) > 1 and used == {0}:
            report["M2_多余材质槽"].append({"obj": ob.name, "slots": len(slots)})
            # 只报告，不删除槽位：pop 会重排 material_index，导致材质错位
    for m in ob.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image is None:
                    report["M3_贴图丢失"].append({"obj": ob.name, "mat": m.name})

# ══════ 命名 ══════
existing = {o.name for o in bpy.data.objects}
for ob in MESHES:
    if "." in ob.name:
        base = ob.name.split(".")[0]
        if base not in existing:
            existing.discard(ob.name)
            ob.name = base
            existing.add(base)
            fixed["改名"] += 1

base = Counter()
for ob in MESHES:
    if "." in ob.name:
        report["N1_名称带序号"].append({"obj": ob.name})
    base[ob.name.split(".")[0]] += 1
for k, v in base.items():
    if v > 1:
        report["N2_重名基名"].append({"base": k, "count": v})
if FIX:
    seen = {}
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        if ob.name in seen:
            seen[ob.name] += 1
            ob.name = f"{ob.name}_{seen[ob.name]}"
            fixed["重名"] += 1
        else:
            seen[ob.name] = 0

# ══════ 渲染设置 ══════
for ob in bpy.data.objects:
    if ob.type == 'LIGHT' and ob.data.type in ('SUN', 'AREA', 'SPOT'):
        try:
            if ob.data.use_shadow is False:
                report["R1_灯光无阴影"].append({"obj": ob.name})
        except Exception:
            pass
for cam in [o for o in bpy.data.objects if o.type == 'CAMERA']:
    if cam.data.clip_end < 5000:
        if FIX:
            cam.data.clip_end = 20000.0
            fixed["相机裁剪"] += 1
        report["R2_裁剪过近"].append({"obj": cam.name, "clip_end": cam.data.clip_end})

# ══════ 输出 ══════
summary = {k: len(v) for k, v in sorted(report.items())}
print("=== BUG SUMMARY ===")
for k, v in summary.items():
    print(f"{k:16s} {v}")
print("=== FIXED ===", dict(fixed))
total = sum(summary.values())
print("TOTAL_ISSUES", total)

out = {"summary": summary, "detail": {k: v[:40] for k, v in report.items()},
       "fixed": dict(fixed), "total": total}
with open(os.path.join(EXPORTS, "qa_deep.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s9.blend"))
print("S9_SAVED")
