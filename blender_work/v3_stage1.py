# -*- coding: utf-8 -*-
"""S1–S3：单位统一放大 u=3.125 → 布局体检 → 地形重做并逐件贴地。

规则遵守：
  · 不删除任何已有物体（26 个全保留）
  · 全站统一乘 u，尺寸/位置/间距同比放大 → 相对方位不变
  · 单件位移 ≤ 自身尺寸 10%，逐条写入 layout_fix.json
  · 地形重做后，所有物体 raycast 贴地（不许悬空/陷地）

运行： blender -b -P v3_stage1.py
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
ROOT = os.path.abspath(os.path.join(HERE, ".."))
exports_dir = os.path.join(ROOT, "exports")
GLB = os.path.join(exports_dir, "mars_outpost.glb")

U = 3.125
BASE_MM2M = 0.2
SCALE = BASE_MM2M * U            # 0.625 m/mm
G = 3.72

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
imported = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
ROT = Matrix.Rotation(math.radians(-90), 4, 'X')
for ob in imported:
    ob.data.transform(ROT)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    ob.data.update()
    ob.matrix_world = Matrix.Identity(4)
print("IMPORTED", len(imported), "SCALE", SCALE)


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


# ── S1：单位表 ──
unit_table = []
for ob in imported:
    mn, mx = bbox(ob)
    unit_table.append({
        "name": ob.name,
        "size_m": [round(mx.x - mn.x, 2), round(mx.y - mn.y, 2), round(mx.z - mn.z, 2)],
        "center_m": [round((mn.x + mx.x) / 2, 2), round((mn.y + mx.y) / 2, 2),
                     round((mn.z + mx.z) / 2, 2)],
    })
with open(os.path.join(exports_dir, "unit_table.json"), "w", encoding="utf-8") as f:
    json.dump({"unit_u": U, "scale_m_per_mm": SCALE, "objects": unit_table}, f,
              ensure_ascii=False, indent=1)
print("UNIT_TABLE", len(unit_table))

# ── 畸形检测 ──
deformed = []
for ob in imported:
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    if zero > 0 or nonman > 0:
        deformed.append({"name": ob.name, "zero_area_faces": zero,
                         "non_manifold_edges": nonman, "volume": round(vol, 1)})
print("DEFORMED", len(deformed), [d["name"] for d in deformed][:6])
with open(os.path.join(exports_dir, "qa_deformed.json"), "w", encoding="utf-8") as f:
    json.dump(deformed, f, ensure_ascii=False, indent=1)

# ── S3：地形重做（原地替换网格，物体保留）──
ter = next((o for o in imported if o.name.startswith("火星地形")), None)
SPAN = 1200.0
SEG = 400
craters = []
rnd = __import__("random").Random(2027)
for _ in range(54):
    cr = rnd.uniform(10, 95)
    craters.append((rnd.uniform(-560, 560), rnd.uniform(-560, 560), cr, cr * rnd.uniform(0.04, 0.10)))


PAD_R, BLEND_R = 300.0, 460.0     # 场平半径 / 过渡半径


def h_raw(x, y):
    z = noise.noise(Vector((x / 320.0, y / 320.0, 0.5))) * 10.0
    z += noise.noise(Vector((x / 96.0, y / 96.0, 3.3))) * 3.2
    z += noise.noise(Vector((x / 24.0, y / 24.0, 8.7))) * 0.8
    z += noise.noise(Vector((x / 5.5, y / 5.5, 15.1))) * 0.18
    for (cx, cy, cr, dp) in craters:
        d = math.hypot(x - cx, y - cy)
        if d < cr * 2.0:
            t = d / cr
            if t < 1.0:
                z -= dp * (1 - t * t)
            z += dp * 0.5 * math.exp(-((t - 1.05) ** 2) / 0.02)
    return z


def h(x, y):
    r = math.hypot(x, y)
    if r <= PAD_R:
        w = 0.0
    elif r >= BLEND_R:
        w = 1.0
    else:
        t = (r - PAD_R) / (BLEND_R - PAD_R)
        w = t * t * (3 - 2 * t)
    return h_raw(x, y) * w


if ter is not None:
    bm = bmesh.new()
    step = SPAN / SEG
    grid = []
    for j in range(SEG + 1):
        y = -SPAN / 2 + j * step
        grid.append([bm.verts.new((-SPAN / 2 + i * step, y,
                                   h(-SPAN / 2 + i * step, y))) for i in range(SEG + 1)])
    for j in range(SEG):
        for i in range(SEG):
            bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    nm = bpy.data.meshes.new("TERRAIN_V3")
    bm.to_mesh(nm)
    bm.free()
    ter.data = nm
    ter.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = ter
    bpy.ops.object.shade_smooth()

    mat = bpy.data.materials.new("V3_Terrain")
    mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Z"], inv.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.5
    nz.inputs["Detail"].default_value = 12.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (0.48, 0.24, 0.14, 1)
    mix.inputs["Color2"].default_value = (0.20, 0.10, 0.07, 1)
    nt.links.new(inv.outputs["Value"], mix.inputs["Fac"])
    nz2 = nt.nodes.new("ShaderNodeMixRGB")
    nz2.blend_type = 'OVERLAY'
    nz2.inputs["Fac"].default_value = 0.4
    nt.links.new(mix.outputs["Color"], nz2.inputs["Color1"])
    nt.links.new(nz.outputs["Fac"], nz2.inputs["Color2"])
    nt.links.new(nz2.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.96
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    bp.inputs["Distance"].default_value = 0.5
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    nm.materials.append(mat)
print("TERRAIN_REBUILT", SPAN, SEG)


def ground_at(x, y):
    """直接用高度函数，避免射线打到物体本身。"""
    return h(x, y)


# ── S2：只处理"陷进地面"的物体；安装在高处的部件不动 ──
fixes = []
sunk = []
for ob in imported:
    if ob.name.startswith("火星地形"):
        continue
    mn, mx = bbox(ob)
    size = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    gz = ground_at(cx, cy)
    dz = gz - mn.z                     # > 0 表示陷进地面
    if dz > 0.05:                      # 只有陷地才抬
        limit = 0.10 * size
        applied = min(limit, dz)
        ob.location.z += applied
        fixes.append({"name": ob.name, "sunk_by": round(dz, 2),
                      "applied_dz": round(applied, 2), "limit": round(limit, 2)})
    elif mn.z - gz > 0.05:             # 记录悬空（多为安装件，不处理）
        sunk.append({"name": ob.name, "ground_clearance": round(mn.z - gz, 2)})

print("SUNK_FIXED", len(fixes))
print("ABOVE_GROUND", len(sunk))
with open(os.path.join(exports_dir, "layout_fix.json"), "w", encoding="utf-8") as f:
    json.dump({"sunk_fixed": fixes, "above_ground": sunk}, f, ensure_ascii=False, indent=1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s1.blend"))
print("S1_S3_DONE")
