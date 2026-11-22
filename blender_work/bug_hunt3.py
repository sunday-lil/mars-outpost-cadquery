# -*- coding: utf-8 -*-
"""变态级 3.0：渲染一致性量化 + 法线逐面统计 + 几何精度审计。

  E. 渲染一致性：同材质在不同物体上的实际渲染色差（64×64 小样 + 均值比较）
  F. 法线逐面：找出与邻面相反的"孤岛翻转面"并纠正
  G. 几何精度：圆柱面弦高误差（>0.5 mm 判不合格）、倒角宽度是否超局部尺寸

运行： blender -b habitat_final.blend -P bug_hunt3.py
"""
import json
import math
import os
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

MESHES = [o for o in bpy.data.objects if o.type == 'MESH']
R = defaultdict(list)
FIXED = defaultdict(int)
SAG_LIMIT = 0.0005          # 0.5 mm
BEVEL_RATIO = 0.25

# ══════ F. 法线逐面：孤岛翻转 ══════
for ob in MESHES:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bad = []
    for f in bm.faces:
        if not f.edges:
            continue
        agree = 0
        total = 0
        for e in f.edges:
            for nf in e.link_faces:
                if nf is f:
                    continue
                total += 1
                if f.normal.dot(nf.normal) > 0:
                    agree += 1
        if total >= 2 and agree == 0:
            bad.append(f)
    if bad:
        R["F_孤岛翻转面"].append({"obj": ob.name, "faces": len(bad)})
        for f in bad:
            f.normal_flip()
        bm.to_mesh(ob.data)
        ob.data.update()
        FIXED["翻转面"] += len(bad)
    bm.free()

# ══════ G. 几何精度 ══════
for ob in MESHES:
    me = ob.data
    if len(me.polygons) > 150000:
        continue
    # G1 弦高误差：用一圈面拟合圆，n = 该环面数，R = 环半径
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    worst = 0.0
    worst_info = None
    for f in bm.faces:
        if len(f.verts) > 8:
            continue
        # 邻接同法线面数量近似环向分段
        ring = 1
        for e in f.edges:
            for nf in e.link_faces:
                if nf is not f and f.normal.dot(nf.normal) > 0.8:
                    ring += 1
        if ring < 6:
            continue
        c = f.calc_center_median()
        rad = max((v.co - c).length for v in f.verts)
        if rad < 1e-4:
            continue
        sag = rad * (1 - math.cos(math.pi / max(8, ring * 4)))
        if sag > worst:
            worst = sag
            worst_info = (len(f.verts), round(rad, 3))
    bm.free()
    if worst > SAG_LIMIT:
        R["G_弦高超标"].append({"obj": ob.name, "sag_mm": round(worst * 1000, 2),
                                "info": worst_info})

# G2 倒角宽度 vs 局部尺寸
for ob in MESHES:
    bevs = [m for m in ob.modifiers if m.type == 'BEVEL']
    if not bevs:
        continue
    me = ob.data
    if len(me.edges) == 0:
        continue
    min_edge = min((me.vertices[e.vertices[0]].co - me.vertices[e.vertices[1]].co).length
                   for e in me.edges[:5000])
    for m in bevs:
        if min_edge > 1e-6 and m.width > min_edge * BEVEL_RATIO:
            R["G_倒角过大"].append({"obj": ob.name, "width": round(m.width, 3),
                                    "min_edge": round(min_edge, 3)})
            if m.width > min_edge * 0.9:
                m.width = min_edge * 0.4
                FIXED["倒角收敛"] += 1

# ══════ E. 渲染一致性（小样采样）══════
mat_users = defaultdict(list)
for ob in MESHES:
    for mat in ob.data.materials:
        if mat:
            mat_users[mat.name].append(ob)

scene = bpy.context.scene
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.eevee.taa_render_samples = 16
cam = bpy.data.objects.get("C") or bpy.data.objects.get("DuskCam")
if cam is None:
    cd = bpy.data.cameras.new("QCam")
    cam = bpy.data.objects.new("QCam", cd)
    bpy.context.collection.objects.link(cam)
scene.camera = cam


def frame_object(ob):
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for c in ob.bound_box:
        p = ob.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
    c = (mn + mx) / 2
    r = (mx - mn).length * 0.7 + 0.001
    cam.location = c + Vector((r, -r, r * 0.8))
    d = (c - cam.location).normalized()
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    cam.data.lens = 50


samples = {}
checked = 0
for mat, users in sorted(mat_users.items(), key=lambda kv: -len(kv[1])):
    core = [u for u in users if not u.name.startswith(("FAC_", "STR_", "TCK_", "REF_"))]
    if len(core) < 2:
        continue
    if checked >= 4:
        break
    checked += 1
    vals = []
    for ob in core[:2]:
        for o in MESHES:
            o.hide_render = (o is not ob)
        frame_object(ob)
        path = os.path.join(HERE, f"_sw_{checked}_{ob.name[:8]}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        vals.append((ob.name, path))
    for o in MESHES:
        o.hide_render = False
    samples[mat] = vals

# 用 PIL 比较（venv 有 PIL；Blender 没有 → 存路径，交给外部脚本）
with open(os.path.join(HERE, "swatch_list.json"), "w", encoding="utf-8") as f:
    json.dump(samples, f, ensure_ascii=False, indent=1)

summary = {k: len(v) for k, v in sorted(R.items())}
print("=== DEEP3 SUMMARY ===")
for k, v in summary.items():
    print(f"{k:16s} {v}")
print("FIXED", dict(FIXED))
print("SWATCH_GROUPS", len(samples))
with open(os.path.join(EXPORTS, "qa_deep3.json"), "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "detail": {k: v[:40] for k, v in R.items()},
               "fixed": dict(FIXED), "swatches": list(samples.keys())},
              f, ensure_ascii=False, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("DEEP3_DONE")
