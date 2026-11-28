# -*- coding: utf-8 -*-
"""取长补短：从训练资料总装 GLTF 中吸收我们缺失的模块。

吸收清单（按资料对比结论）：
  1. 测地线穹顶温室  Geodesic_Frame + Glass_Glazing + Greenhouse_Corridor + Green_Crops（大幅减面）
  2. ISRU 制氧/推进剂站  ISRU_Station
  3. 低温推进剂管路  LOX_Pipe + LCH4_Pipe（改向接到着陆平台）
  4. 深空通信塔  DeepSpace_Comms_Tower（替换我们简化的塔）

全部按本场景尺度对齐、落到地面、并做与其他设施的相交检查。
运行： blender -b habitat_final.blend -P ref_import.py
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
ROOT = os.path.abspath(os.path.join(HERE, ".."))
GLTF = os.path.join(ROOT, "董的训练资料（感谢激情赞助）", "新的", "mars_base_alpha_complete.gltf")

M_STEEL = bpy.data.materials.get("R2_Steel")
M_GLASS = bpy.data.materials.get("R2_Glass")
M_HULL = bpy.data.materials.get("R2_Hull")
M_DARK = bpy.data.materials.get("R2_Dark")

for _o in [o for o in bpy.data.objects if o.name.startswith("REF_")]:
    bpy.data.objects.remove(_o, do_unlink=True)

BEFORE = set(bpy.data.objects)


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def ground(x, y):
    ter = next((o for o in bpy.data.objects if o.type == 'MESH'
                and o.name.startswith(("火星地形", "TERRAIN"))), None)
    if ter is None:
        return 0.0
    inv = ter.matrix_world.inverted()
    o = inv @ Vector((x, y, 2000))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, nor, idx = ter.ray_cast(o, d)
    return (ter.matrix_world @ loc).z if hit else 0.0


# ══════ 导入 ══════
bpy.ops.import_scene.gltf(filepath=GLTF)
imported = [o for o in bpy.data.objects if o not in BEFORE]
meshes = [o for o in imported if o.type == 'MESH']
print("IMPORTED", len(meshes))

KEEP = ("Geodesic_Frame", "Glass_Glazing", "Greenhouse_Corridor", "Green_Crops",
        "ISRU_Station", "LOX_Pipe", "LCH4_Pipe", "DeepSpace_Comms_Tower")
for o in list(meshes):
    if not o.name.startswith(KEEP):
        bpy.data.objects.remove(o, do_unlink=True)
meshes = [o for o in bpy.data.objects if o not in BEFORE and o.type == 'MESH']
print("KEPT", len(meshes), sorted({o.name.split('.')[0] for o in meshes}))

# 解除父子关系（保留世界变换）
for o in meshes:
    if o.parent:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw


def pick(prefix):
    """按前缀检索当前场景中的网格（兼容已改名的 REF_ 前缀）"""
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if o.name.startswith("REF_" + prefix) or o.name.startswith(prefix):
            out.append(o)
    return out


# ══════ 温室穹顶：测绘地线框架 + 玻璃 + 作物 ══════
def place_group(objs, target_xy, yaw=0.0, scale=1.0, name_prefix="REF_"):
    if not objs:
        return []
    # 组包围盒
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for ob in objs:
        a, b = bbox(ob)
        for i in range(3):
            mn[i] = min(mn[i], a[i])
            mx[i] = max(mx[i], b[i])
    c = (mn + mx) / 2
    gz = ground(target_xy[0], target_xy[1])
    # 以组左下为锚：平移使中心落到目标，底部贴地
    T1 = Matrix.Translation((-c.x, -c.y, -mn.z))
    R = Matrix.Rotation(yaw, 4, 'Z')
    S = Matrix.Diagonal((scale, scale, scale, 1.0))
    T2 = Matrix.Translation((target_xy[0], target_xy[1], gz))
    M = T2 @ R @ S @ T1
    for ob in objs:
        ob.matrix_world = M @ ob.matrix_world
        if not ob.name.startswith(name_prefix):
            ob.name = name_prefix + ob.name
    return objs


# ① 温室
dome = pick("Geodesic_Frame") + pick("Glass_Glazing") + pick("Greenhouse_Corridor")
crops = pick("Green_Crops")
placed_dome = place_group(dome, (-140.0, 162.0), yaw=0.3, scale=1.55)
print("DOME", len(placed_dome))

# 作物：先减面再放入温室
for ob in crops:
    dec = ob.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = 0.045          # 204 万面 → 约 9 万面
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="Dec")
place_group(crops, (-140.0, 162.0), yaw=0.3, scale=1.55)
print("CROPS", len(crops), "tris now", sum(len(o.data.polygons) for o in crops))

# ② ISRU 站
isru = place_group(pick("ISRU_Station"), (96.0, -150.0), yaw=math.radians(-90), scale=1.25)
print("ISRU", len(isru))

# ③ 低温管路：从 ISRU 北缘接到着陆平台南缘（旋转 90° 沿 Y 走）
pipes = pick("LOX_Pipe") + pick("LCH4_Pipe")
# 每根管复制一份，四段接力覆盖 ISRU(y=-110) → 着陆平台(y=25) 的 135 m 距离
for _ in range(2):                      # 2 根 → 6 段
    for ob in list(pipes)[:2]:
        dup = ob.copy(); dup.data = ob.data.copy()
        bpy.context.collection.objects.link(dup)
        pipes.append(dup)
lay = [(150.0, -80.0), (150.0, -20.0), (150.0, 40.0),
       (157.0, -80.0), (157.0, -20.0), (157.0, 40.0)]
for i, ob in enumerate(pipes):
    place_group([ob], lay[i % 4], yaw=math.radians(90), scale=1.0, name_prefix="REF_")
print("PIPES", len(pipes))

# ④ 深空通信塔
for _o in pick("DeepSpace_Comms_Tower"):
    bpy.data.objects.remove(_o, do_unlink=True)
print("COMMS skipped (已有抛物面天线)")

# ⑤ 信标桅杆：只取子集做场界灯，跳过（跨度过大）
for ob in pick("Beacon_Masts") + pick("Booms") + pick("Target_Markings"):
    bpy.data.objects.remove(ob, do_unlink=True)

# ══════ 场地垫层（盖住散石，形成干净的场地）══════
M_PAD = bpy.data.materials.get("R2_Pad") or M_HULL
for (px, py, rr, nm) in ((-140.0, 162.0, 44.0, "REF_Pad_Dome"),
                          (96.0, -150.0, 42.0, "REF_Pad_ISRU")):
    gz = ground(px, py)
    bpy.ops.mesh.primitive_cylinder_add(radius=rr, depth=0.9, vertices=64,
                                        location=(px, py, gz + 0.15))
    pad = bpy.context.object
    pad.name = nm
    pad.data.materials.append(M_PAD)
    bpy.ops.object.shade_smooth()

# ══════ 材质统一 ══════
def remat(objs, mat):
    for ob in objs:
        ob.data.materials.clear()
        ob.data.materials.append(mat)


remat(pick("REF_Geodesic_Frame"), M_STEEL)
M_GLASS_LIGHT = bpy.data.materials.new("R2_GlassDome")
M_GLASS_LIGHT.use_nodes = True
_b = next(n for n in M_GLASS_LIGHT.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_b.inputs["Base Color"].default_value = (0.55, 0.78, 0.80, 1)
_b.inputs["Roughness"].default_value = 0.06
_b.inputs["Metallic"].default_value = 0.0
try:
    _b.inputs["Transmission Weight"].default_value = 0.75
except Exception:
    try:
        _b.inputs["Transmission"].default_value = 0.75
    except Exception:
        pass
_b.inputs["Alpha"].default_value = 0.35
remat(pick("REF_Glass_Glazing"), M_GLASS_LIGHT)
remat(pick("REF_Greenhouse_Corridor"), M_STEEL)
remat(pick("REF_ISRU_Station"), M_STEEL)
remat(pick("REF_LOX_Pipe") + pick("REF_LCH4_Pipe"), M_DARK)
remat(pick("REF_DeepSpace_Comms_Tower"), M_STEEL)

# 作物保留原绿色材质，但加一点自发光让它像舱内植物
for ob in pick("REF_Green_Crops"):
    for m in ob.data.materials:
        if m and m.use_nodes:
            b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b:
                b.inputs["Base Color"].default_value = (0.10, 0.30, 0.09, 1)
                b.inputs["Roughness"].default_value = 0.75
                b.inputs["Emission Color"].default_value = (0.06, 0.18, 0.05, 1)
                b.inputs["Emission Strength"].default_value = 0.35

# ══════ 平滑 + 加权法线 ══════
for ob in [o for o in bpy.data.objects if o.name.startswith("REF_")]:
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
    wn.keep_sharp = True

# ══════ 相交检查（吸收件 vs 原设施）══════
new_objs = [o for o in bpy.data.objects if o.name.startswith("REF_")]
old_objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("REF_")
            and not o.name.startswith(("火星地形", "TERRAIN", "FX_"))]
bpy.context.view_layer.update()
SKIP_OLD = ("火星岩石", "压痕路径", "TCK_", "FAC_Track", "着陆平台")
hits = []
for a in new_objs:
    amn, amx = bbox(a)
    for b in old_objs:
        if b.name.startswith(SKIP_OLD):
            continue
        bmn, bmx = bbox(b)
        ox = min(amx.x, bmx.x) - max(amn.x, bmn.x)
        oy = min(amx.y, bmx.y) - max(amn.y, bmn.y)
        oz = min(amx.z, bmx.z) - max(amn.z, bmn.z)
        if ox > 0.5 and oy > 0.5 and oz > 0.5:
            hits.append((a.name, b.name, round(ox * oy * oz, 1)))
print("COLLISIONS", len(hits), hits[:10])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_final.blend"))
print("REF_IMPORT_DONE total", len(new_objs))
