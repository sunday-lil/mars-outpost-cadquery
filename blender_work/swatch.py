# -*- coding: utf-8 -*-
"""E. 渲染一致性量化：同材质在不同物体上的实际渲染色差。

对每个"被 2 个以上核心物件共用"的材质，分别单独渲染两个物体（128×128），
保存为 ASCII 文件名，交给外部 PIL 脚本比较均值色。

运行： blender -b habitat_final.blend -P swatch.py
"""
import json
import os
from collections import defaultdict

import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
SW = os.path.join(HERE, "sw")
os.makedirs(SW, exist_ok=True)
for f in os.listdir(SW):
    os.remove(os.path.join(SW, f))

MESHES = [o for o in bpy.data.objects if o.type == 'MESH']
scene = bpy.context.scene
scene.render.resolution_x = 128
scene.render.resolution_y = 128
scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = 'PNG'
if scene.camera is None:
    cd = bpy.data.cameras.new("SwCam")
    cam = bpy.data.objects.new("SwCam", cd)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
cam = scene.camera

mat_users = defaultdict(list)
for ob in MESHES:
    for mat in ob.data.materials:
        if mat:
            mat_users[mat.name].append(ob)

CORE_SKIP = ("FAC_", "STR_", "TCK_", "REF_", "FX_")


def frame(ob):
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for c in ob.bound_box:
        p = ob.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
    c = (mn + mx) / 2
    r = max((mx - mn).length * 0.55, 0.05)
    cam.location = c + Vector((r, -r, r * 0.7))
    d = (c - cam.location).normalized()
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    cam.data.lens = 50


out = {}
idx = 0
for mat, users in sorted(mat_users.items(), key=lambda kv: -len(kv[1])):
    core = [u for u in users if not u.name.startswith(CORE_SKIP)]
    if len(core) < 2 or len(out) >= 5:
        continue
    idx += 1
    entries = []
    for j, ob in enumerate(core[:2]):
        for o in MESHES:
            o.hide_render = (o is not ob)
        frame(ob)
        name = f"m{idx}_{j}.png"
        full = os.path.join(SW, name)
        scene.render.filepath = full
        bpy.ops.render.render()
        try:
            bpy.data.images["Render Result"].save_render(full, scene=scene)
        except Exception as e:
            print("SAVE_FAIL", e)
        entries.append({"obj": ob.name, "file": name, "exists": os.path.exists(full),
                        "size": os.path.getsize(full) if os.path.exists(full) else 0})
    for o in MESHES:
        o.hide_render = False
    out[mat] = entries

with open(os.path.join(HERE, "swatch_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("SWATCH_DONE", len(out))
for k, v in out.items():
    print(" ", k, [(e["obj"], e["size"]) for e in v])
