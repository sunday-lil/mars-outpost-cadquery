# -*- coding: utf-8 -*-
"""修复进阶检查发现的问题：UV 重建 + 法线重算。

运行： blender -b habitat_final.blend -P fix_advanced.py
"""
import json
import os

import bmesh
import bpy

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

data = json.load(open(os.path.join(EXPORTS, "qa_advanced.json"), encoding="utf-8"))
detail = data["detail"]

targets = set()
for key in ("B_缺UV", "B_零面积UV", "B_UV翻转", "B_UV越界", "D_法线朝内偏多"):
    for item in detail.get(key, []):
        targets.add(item["obj"])
print("TARGETS", len(targets))

fixed_uv, fixed_n = 0, 0
for name in sorted(targets):
    ob = bpy.data.objects.get(name)
    if not ob or ob.type != 'MESH':
        continue
    # 超过 20 万面的跳过（重建 UV 太慢）
    if len(ob.data.polygons) > 200000:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    # UV：立方投影重建（0..1 归一）
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        fixed_uv += 1
    except Exception:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

    # 法线：重算朝外
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    fixed_n += 1

print("UV_REBUILT", fixed_uv, "NORMALS_RECALC", fixed_n)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("FIX_ADV_DONE")
