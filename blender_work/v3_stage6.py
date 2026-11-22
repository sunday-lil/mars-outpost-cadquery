# -*- coding: utf-8 -*-
"""S6：地形风蚀纹理 + 舷窗内景 + 人形比例尺（全部新增，不改已有物体位置）。

运行： blender -b habitat_v3_s5.blend -P v3_stage6.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

NEW = []


def reg(ob, mat, name):
    ob.name = name
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


def cyl(r, h, loc, rot=(0, 0, 0), mat=None, v=24, name="REF_c"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v, location=loc, rotation=rot)
    return reg(bpy.context.object, mat, name)


def sph(r, loc, mat, name="REF_s"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=20, ring_count=12, location=loc)
    return reg(bpy.context.object, mat, name)


def box(sx, sy, sz, loc, rot=(0, 0, 0), mat=None, name="REF_b"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    bv = ob.modifiers.new("Bev", 'BEVEL'); bv.width = 0.02; bv.segments = 2
    return reg(ob, mat, name)


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(pref):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(pref)), None)


# ══════ 1. 地形风蚀纹理 ══════
ter = find("火星地形") or find("TERRAIN")
if ter:
    mat = bpy.data.materials.new("V3_TerrainWind")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")

    # ① 坡度遮罩：平地 = 细尘，陡坡 = 裸岩
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Z"], inv.inputs[1])
    slope = nt.nodes.new("ShaderNodeValToRGB")
    slope.color_ramp.elements[0].position = 0.10
    slope.color_ramp.elements[0].color = (0, 0, 0, 1)
    slope.color_ramp.elements[1].position = 0.45
    slope.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(inv.outputs["Value"], slope.inputs["Fac"])

    # ② 风蚀波纹：Wave + 扭曲
    map1 = nt.nodes.new("ShaderNodeMapping")
    map1.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    nt.links.new(tc.outputs["Object"], map1.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 0.04
    wave.inputs["Distortion"].default_value = 8.0
    wave.inputs["Detail"].default_value = 4.0
    nt.links.new(map1.outputs["Vector"], wave.inputs["Vector"])

    # ③ 多尺度颗粒
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 1.6
    grain.inputs["Detail"].default_value = 14.0
    grain.inputs["Roughness"].default_value = 0.75
    nt.links.new(map1.outputs["Vector"], grain.inputs["Vector"])
    gravel = nt.nodes.new("ShaderNodeTexVoronoi")
    gravel.inputs["Scale"].default_value = 0.55
    gravel.feature = 'F1'
    nt.links.new(map1.outputs["Vector"], gravel.inputs["Vector"])

    # 颜色链：细尘 ↔ 裸岩 → 叠加波纹明暗 → 叠加砾石
    c1 = nt.nodes.new("ShaderNodeMixRGB")
    c1.inputs["Color1"].default_value = (0.50, 0.26, 0.15, 1)     # 细尘
    c1.inputs["Color2"].default_value = (0.19, 0.10, 0.075, 1)    # 裸岩
    nt.links.new(slope.outputs["Color"], c1.inputs["Fac"])

    c2 = nt.nodes.new("ShaderNodeMixRGB")
    c2.blend_type = 'OVERLAY'
    c2.inputs["Fac"].default_value = 0.35
    nt.links.new(c1.outputs["Color"], c2.inputs["Color1"])
    nt.links.new(wave.outputs["Color"], c2.inputs["Color2"])

    c3 = nt.nodes.new("ShaderNodeMixRGB")
    c3.blend_type = 'MULTIPLY'
    c3.inputs["Fac"].default_value = 0.25
    nt.links.new(c2.outputs["Color"], c3.inputs["Color1"])
    nt.links.new(gravel.outputs["Distance"], c3.inputs["Color2"])
    nt.links.new(c3.outputs["Color"], b.inputs["Base Color"])

    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = 0.97

    # 凹凸：波纹 + 颗粒 双层
    h1 = nt.nodes.new("ShaderNodeMixRGB")
    h1.blend_type = 'ADD'
    h1.inputs["Fac"].default_value = 0.5
    nt.links.new(wave.outputs["Color"], h1.inputs["Color1"])
    nt.links.new(grain.outputs["Fac"], h1.inputs["Color2"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.75
    bump.inputs["Distance"].default_value = 0.35
    nt.links.new(h1.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])

    ter.data.materials.clear()
    ter.data.materials.append(mat)
    print("TERRAIN_WIND_OK")

# ══════ 2. 舷窗内景：内筒 + 舱内灯 ══════
M_INNER = bpy.data.materials.new("V3_WinInner")
M_INNER.use_nodes = True
_ib = next(n for n in M_INNER.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_ib.inputs["Base Color"].default_value = (0.25, 0.26, 0.28, 1)
_ib.inputs["Roughness"].default_value = 0.55
M_LAMP = bpy.data.materials.new("V3_WinLamp")
M_LAMP.use_nodes = True
_lb = next(n for n in M_LAMP.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_lb.inputs["Base Color"].default_value = (1, 0.95, 0.85, 1)
_lb.inputs["Emission Color"].default_value = (1.0, 0.90, 0.74, 1)
_lb.inputs["Emission Strength"].default_value = 12.0

ring = find("居住穹顶")
if ring:
    vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
    cx = (max(v.x for v in vs) + min(v.x for v in vs)) / 2
    cy = (max(v.y for v in vs) + min(v.y for v in vs)) / 2
    rxy = [math.hypot(v.x - cx, v.y - cy) for v in vs]
    R_OUT = max(rxy)
    near = [v.z for v, r in zip(vs, rxy) if r > 0.88 * R_OUT]
    Z_RING = (max(near) + min(near)) / 2
    R_TUBE = max(0.8, (max(near) - min(near)) / 2)
    R_MAJ = R_OUT - R_TUBE
    HOLE_R = min(2.4, R_TUBE * 0.30)
    for k in range(16):
        th = 2 * math.pi * k / 16 + math.pi / 32
        d = Vector((math.cos(th), math.sin(th), 0.0))
        # 内筒（从外壁到内壁）
        mid_r = R_MAJ + R_TUBE * 0.05
        cyl(HOLE_R * 0.99, R_TUBE * 1.75, (cx + mid_r * d.x, cy + mid_r * d.y, Z_RING),
            rot=(0, math.pi / 2, th), mat=M_INNER, v=28, name=f"FAC_WinTube{k}")
        # 内端灯环
        bpy.ops.mesh.primitive_torus_add(major_radius=HOLE_R * 0.85, minor_radius=HOLE_R * 0.10,
                                         major_segments=24, minor_segments=8,
                                         location=(cx + (R_MAJ - R_TUBE * 0.72) * d.x,
                                                   cy + (R_MAJ - R_TUBE * 0.72) * d.y, Z_RING),
                                         rotation=(0, math.pi / 2, th))
        reg(bpy.context.object, M_LAMP, f"FAC_WinLamp{k}")
    print("WINDOW_INTERIOR_OK")

# ══════ 3. 人形比例尺（1.8 m）══════
M_SUIT = bpy.data.materials.get("R2_Hull")
M_VISOR = bpy.data.materials.get("R2_Glass")
M_PACK = bpy.data.materials.get("R2_Dark")


def astronaut(x, y, z, yaw=0.0, tag=""):
    base = Vector((x, y, z))
    # 腿
    for sx in (-0.13, 0.13):
        cyl(0.09, 0.86, (base.x + sx, base.y, base.z + 0.43), mat=M_SUIT, v=12,
            name=f"REF_Leg{tag}")
    # 躯干
    box(0.42, 0.26, 0.62, (base.x, base.y, base.z + 1.18), rot=(0, 0, yaw), mat=M_SUIT,
        name=f"REF_Torso{tag}")
    # 背包
    box(0.34, 0.20, 0.44, (base.x - 0.22 * math.sin(yaw), base.y - 0.22 * math.cos(yaw),
                           base.z + 1.20), rot=(0, 0, yaw), mat=M_PACK, name=f"REF_Pack{tag}")
    # 头盔
    sph(0.15, (base.x, base.y, base.z + 1.62), M_SUIT, f"REF_Helmet{tag}")
    # 面罩
    sph(0.11, (base.x + 0.10 * math.sin(yaw), base.y + 0.10 * math.cos(yaw), base.z + 1.63),
        M_VISOR, f"REF_Visor{tag}")
    # 手臂
    for sx in (-0.26, 0.26):
        cyl(0.07, 0.55, (base.x + sx, base.y, base.z + 1.10), rot=(0, math.radians(12), 0),
            mat=M_SUIT, v=10, name=f"REF_Arm{tag}")


# 在环体支撑塔基座旁放 3 个人
for i, (dx, dy) in enumerate(((6, 4), (-7, 5), (2, -6))):
    px = cx + R_MAJ * math.cos(math.pi / 4) + dx * 3
    py = cy + R_MAJ * math.sin(math.pi / 4) + dy * 3
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((px, py, 900)), Vector((0, 0, -1)))
    gz = loc.z if hit else 0.0
    astronaut(px, py, gz, yaw=i * 1.1, tag=str(i))
print("ASTRONAUTS_OK", len([o for o in NEW if o.name.startswith("REF_")]))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s6.blend"))
print("S6_DONE total_new", len(NEW))
