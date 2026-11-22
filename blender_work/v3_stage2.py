# -*- coding: utf-8 -*-
"""S4–S7：删除旧附属件 + 设施 AAA 化 + 结构件补全 + QA 报告。

运行： blender -b habitat_v3_s1.blend -P v3_stage2.py
"""
import json
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
G = 3.72

# ══════ 0. 删除旧附属件（已获授权）══════
LEGACY = ("压痕路径", "相机镜片", "顶部信标", "观察舷窗", "穹顶肋")
removed = []
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and ob.name.startswith(LEGACY):
        removed.append(ob.name)
        bpy.data.objects.remove(ob, do_unlink=True)
print("LEGACY_REMOVED", len(removed), removed)

KEEP = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("TERRAIN")]
print("KEEP", len(KEEP))


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


# ══════ 1. trim atlas（由 .venv 的 PIL 预先生成）══════
TRIM = os.path.join(EXPORTS, "trim_atlas.png")
assert os.path.exists(TRIM), "trim_atlas.png 缺失"
print("TRIM_OK", TRIM)


def pbr(name, color, metal, rough, bump=0.25, scale=6.0, dust=0.0, use_trim=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 10.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    src = None
    if use_trim:
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(TRIM)
        mapn = nt.nodes.new("ShaderNodeMapping")
        mapn.inputs["Scale"].default_value = (1, 1, 1)
        nt.links.new(tc.outputs["Object"], mapn.inputs["Vector"])
        nt.links.new(mapn.outputs["Vector"], img.inputs["Vector"])
        src = img.outputs["Color"]
    if dust > 0:
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.inputs["Fac"].default_value = dust
        if src:
            nt.links.new(src, mx.inputs["Color1"])
        else:
            mx.inputs["Color1"].default_value = (*color, 1)
        mx.inputs["Color2"].default_value = (0.56, 0.32, 0.19, 1)
        nt.links.new(nz.outputs["Fac"], mx.inputs["Fac"])
        nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    elif src:
        nt.links.new(src, b.inputs["Base Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.08
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (rough * 0.6,) * 3 + (1,)
    rr.color_ramp.elements[1].color = (min(1.0, rough * 1.5),) * 3 + (1,)
    nt.links.new(nz.outputs["Fac"], rr.inputs["Fac"])
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    return m


M_HULL = pbr("V3_Hull", (0.80, 0.80, 0.77), 0.20, 0.40, 0.24, 2.0, dust=0.08, use_trim=True)
M_STEEL = pbr("V3_Steel", (0.57, 0.59, 0.62), 0.92, 0.26, 0.2, 10.0)
M_DARK = pbr("V3_Dark", (0.09, 0.09, 0.10), 0.7, 0.45, 0.24, 14.0)
M_GLASS = pbr("V3_Glass", (0.02, 0.06, 0.12), 0.6, 0.05, 0.0)
M_SOLAR = pbr("V3_Solar", (0.03, 0.06, 0.14), 0.65, 0.15, 0.1, 18.0)
M_PAD = pbr("V3_Pad", (0.55, 0.52, 0.48), 0.05, 0.85, 0.3, 2.0)

NAME_MAT = [("居住穹顶", M_HULL), ("科研实验舱", M_STEEL), ("加压廊道", M_STEEL),
            ("返回火箭", M_HULL), ("推进器机身", M_STEEL), ("发动机喷管", M_DARK),
            ("加速器喷管", M_STEEL), ("塔架", M_STEEL), ("抛物面反射器", M_HULL),
            ("天线馈源臂", M_STEEL), ("着陆平台", M_STEEL), ("火星车体", M_HULL),
            ("车轮", M_DARK), ("机械臂", M_STEEL), ("太阳能板", M_SOLAR),
            ("能源边框", M_STEEL), ("火星岩石", M_HULL), ("散热格栅", M_STEEL),
            ("气象站", M_STEEL), ("车顶帆板", M_SOLAR)]

for ob in KEEP:
    for key, mat in NAME_MAT:
        if ob.name.startswith(key):
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            break
    try:
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width = 0.06
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(30)
        wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
print("SURFACE_OK")

# ══════ 2. 居住环测量 ══════
ring = next((o for o in KEEP if o.name.startswith("居住穹顶")), None)
vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
cx = sum(v.x for v in vs) / len(vs)
cy = sum(v.y for v in vs) / len(vs)
rxy_all = [math.hypot(v.x - cx, v.y - cy) for v in vs]
r_max = max(rxy_all)
outer = [v.z for v, r in zip(vs, rxy_all) if r > 0.90 * r_max]   # 只取环外缘顶点
R_TUBE = max(0.5, (max(outer) - min(outer)) / 2.0)
R_MAJ = r_max - R_TUBE
Z_RING = (max(outer) + min(outer)) / 2.0
n = len(rxy_all)
OMEGA = math.sqrt(G / R_MAJ)
print(f"RING R={R_MAJ:.2f} tube={R_TUBE:.2f} z={Z_RING:.2f}")
print(f"OMEGA {OMEGA:.4f} rad/s = {OMEGA*60/(2*math.pi):.2f} rpm")
HOOP = 7850 * G * R_MAJ
print(f"HOOP {HOOP/1e6:.3f} MPa")

NEW = []


def reg(ob, mat):
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


# ══════ 3. 环体：真挖孔舷窗 + 贴合环肋 + 散热片 ══════
HOLE_R = min(2.2, R_TUBE * 0.34)
for k in range(16):
    th = 2 * math.pi * k / 16
    px = cx + R_MAJ * math.cos(th)
    py = cy + R_MAJ * math.sin(th)
    # 挖孔（沿径向贯穿外层）
    bpy.ops.mesh.primitive_cylinder_add(radius=HOLE_R, depth=R_TUBE * 0.55, vertices=32,
                                        location=(px + (R_TUBE * 0.28) * math.cos(th),
                                                  py + (R_TUBE * 0.28) * math.sin(th), Z_RING),
                                        rotation=(0, math.pi / 2, th))
    cut = bpy.context.object
    md = ring.modifiers.new("hole", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = cut
    md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ring
    bpy.ops.object.modifier_apply(modifier="hole")
    bpy.data.objects.remove(cut, do_unlink=True)

    # 法兰 + 玻璃（贴在孔口）
    bpy.ops.mesh.primitive_torus_add(major_radius=HOLE_R * 1.06, minor_radius=HOLE_R * 0.10,
                                     major_segments=32, minor_segments=8,
                                     location=(px + (R_TUBE * 0.30) * math.cos(th),
                                               py + (R_TUBE * 0.30) * math.sin(th), Z_RING),
                                     rotation=(0, math.pi / 2, th))
    reg(bpy.context.object, M_STEEL)
    NEW[-1].name = f"FAC_RingPort{k}"
    bpy.ops.mesh.primitive_circle_add(radius=HOLE_R * 0.98, vertices=32, fill_type='NGON',
                                      location=(px + (R_TUBE * 0.24) * math.cos(th),
                                                py + (R_TUBE * 0.24) * math.sin(th), Z_RING),
                                      rotation=(0, math.pi / 2, th))
    reg(bpy.context.object, M_GLASS)
    NEW[-1].name = f"FAC_RingGlass{k}"

# 贴合环肋：沿截面轮廓扫掠的窄带（24 道）
prof = []
for i in range(24):
    a = 2 * math.pi * i / 24
    prof.append((R_MAJ + (R_TUBE + 0.10) * math.cos(a), Z_RING + (R_TUBE + 0.10) * math.sin(a)))
for k in range(24):
    th0 = 2 * math.pi * k / 24
    bmb = bmesh.new()
    segs = 4
    prev = None
    for i in range(segs + 1):
        th = th0 + math.radians(1.0) * i / segs
        ca, sa = math.cos(th), math.sin(th)
        cur = [bmb.verts.new((r * ca, r * sa, z)) for (r, z) in prof]
        if prev:
            for q in range(len(cur)):
                q2 = (q + 1) % len(cur)
                bmb.faces.new([prev[q], prev[q2], cur[q2], cur[q]])
        prev = cur
    bmesh.ops.recalc_face_normals(bmb, faces=bmb.faces)
    me = bpy.data.meshes.new(f"RIB{k}")
    bmb.to_mesh(me)
    bmb.free()
    ob = bpy.data.objects.new(f"STR_RingRib{k}", me)
    bpy.context.collection.objects.link(ob)
    reg(ob, M_STEEL)

# 外缘散热片
for k in range(24):
    th = 2 * math.pi * k / 24 + math.pi / 48
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(cx + (R_MAJ + R_TUBE * 0.95) * math.cos(th),
                  cy + (R_MAJ + R_TUBE * 0.95) * math.sin(th), Z_RING),
        rotation=(0, 0, th))
    ob = bpy.context.object
    ob.name = f"FAC_Radiator{k}"
    ob.scale = (0.25, 2.4, R_TUBE * 0.55)
    bpy.ops.object.transform_apply(scale=True)
    reg(ob, M_STEEL)

print("RING_DETAIL_OK", len(NEW))

# ══════ 4. 支撑塔 + 垫板（从地面到环底）══════
def ground(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 900)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


for k in range(4):
    th = 2 * math.pi * k / 4 + math.pi / 4
    px = cx + R_MAJ * math.cos(th)
    py = cy + R_MAJ * math.sin(th)
    gz = ground(px, py)
    top = Z_RING - R_TUBE
    hgt = top - gz
    if hgt <= 1:
        continue
    bpy.ops.mesh.primitive_cylinder_add(radius=R_TUBE * 0.22, depth=hgt, vertices=24,
                                        location=(px, py, gz + hgt / 2))
    reg(bpy.context.object, M_STEEL)
    NEW[-1].name = f"STR_Tower{k}"
    bpy.ops.mesh.primitive_cylinder_add(radius=R_TUBE * 0.75, depth=1.2, vertices=40,
                                        location=(px, py, gz + 0.6))
    reg(bpy.context.object, M_PAD)
    NEW[-1].name = f"STR_Pad{k}"
    nb = max(2, int(hgt / 8))
    for i in range(1, nb):
        bpy.ops.mesh.primitive_torus_add(major_radius=R_TUBE * 0.24, minor_radius=0.16,
                                         major_segments=24, minor_segments=6,
                                         location=(px, py, gz + i * 8))
        reg(bpy.context.object, M_DARK)
        NEW[-1].name = f"STR_TowerBand{k}_{i}"
print("SUPPORT_OK")

# ══════ 5. QA ══════
qa = {"legacy_removed": removed, "new_objects": len(NEW), "deformed": [], "overlaps": []}
for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    if zero or nonman:
        qa["deformed"].append({"name": ob.name, "zero_area": zero, "non_manifold": nonman})

ms = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("TERRAIN")]
for i in range(len(ms)):
    for j in range(i + 1, len(ms)):
        a, b = ms[i], ms[j]
        amn, amx = bbox(a)
        bmn, bmx = bbox(b)
        ox = min(amx.x, bmx.x) - max(amn.x, bmn.x)
        oy = min(amx.y, bmx.y) - max(amn.y, bmn.y)
        oz = min(amx.z, bmx.z) - max(amn.z, bmn.z)
        if ox > 0 and oy > 0 and oz > 0:
            vol = ox * oy * oz
            if vol > 50:
                qa["overlaps"].append({"a": a.name, "b": b.name, "approx_m3": round(vol, 1)})
qa["physics"] = {"R_m": round(R_MAJ, 2), "tube_R_m": round(R_TUBE, 2),
                 "omega_rad_s": round(OMEGA, 4), "rpm": round(OMEGA * 60 / (2 * math.pi), 2),
                 "hoop_MPa": round(HOOP / 1e6, 3)}
with open(os.path.join(EXPORTS, "qa_report.json"), "w", encoding="utf-8") as f:
    json.dump(qa, f, ensure_ascii=False, indent=1)
print("QA deformed=%d overlaps=%d" % (len(qa["deformed"]), len(qa["overlaps"])))
print("PHYSICS", qa["physics"])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s2.blend"))
print("S2_DONE")
