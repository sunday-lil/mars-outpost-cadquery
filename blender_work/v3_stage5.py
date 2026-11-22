# -*- coding: utf-8 -*-
"""S5：材质真实化 + 其余设施细节 + 尘暴体积光。

规则：只加不减；新增件前缀 FAC_/STR_；不改动已有物体的位置。
运行： blender -b habitat_v3_s4.blend -P v3_stage5.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

# ══════ 1. 材质真实化：漆膜 + 边缘磨损 + 污渍流向 ══════
def paint_mat(name, color, metal=0.15, rough=0.38, wear=0.55, dirt=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")

    # 漆膜色
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough

    # 污渍：各向异性拉伸噪声（沿 Z 拉长 = 雨痕/尘流）
    map1 = nt.nodes.new("ShaderNodeMapping")
    map1.inputs["Scale"].default_value = (1.0, 1.0, 0.12)
    nt.links.new(tc.outputs["Object"], map1.inputs["Vector"])
    streak = nt.nodes.new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value = 6.0
    streak.inputs["Detail"].default_value = 10.0
    nt.links.new(map1.outputs["Vector"], streak.inputs["Vector"])

    dirtmask = nt.nodes.new("ShaderNodeValToRGB")
    dirtmask.color_ramp.elements[0].position = 0.40
    dirtmask.color_ramp.elements[0].color = (0, 0, 0, 1)
    dirtmask.color_ramp.elements[1].position = 0.72
    dirtmask.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(streak.outputs["Fac"], dirtmask.inputs["Fac"])

    # 边缘磨损：菲涅尔当"边缘遮罩"（EEVEE 可用）
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    edge = nt.nodes.new("ShaderNodeValToRGB")
    edge.color_ramp.elements[0].position = 0.55
    edge.color_ramp.elements[0].color = (0, 0, 0, 1)
    edge.color_ramp.elements[1].position = 0.95
    edge.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(lw.outputs["Facing"], edge.inputs["Fac"])

    # 颜色 = 漆色 → 泥色（污渍）→ 裸金属（边缘）
    mix_dirt = nt.nodes.new("ShaderNodeMixRGB")
    mix_dirt.blend_type = 'MIX'
    mix_dirt.inputs["Fac"].default_value = dirt
    mix_dirt.inputs["Color1"].default_value = (*color, 1)
    mix_dirt.inputs["Color2"].default_value = (0.46, 0.26, 0.16, 1)
    nt.links.new(dirtmask.outputs["Color"], mix_dirt.inputs["Fac"])

    mix_wear = nt.nodes.new("ShaderNodeMixRGB")
    mix_wear.blend_type = 'MIX'
    mix_wear.inputs["Fac"].default_value = wear
    mix_wear.inputs["Color2"].default_value = (0.52, 0.53, 0.55, 1)
    nt.links.new(mix_dirt.outputs["Color"], mix_wear.inputs["Color1"])
    nt.links.new(edge.outputs["Color"], mix_wear.inputs["Fac"])
    nt.links.new(mix_wear.outputs["Color"], b.inputs["Base Color"])

    # 金属度/粗糙度随磨损变化
    mmet = nt.nodes.new("ShaderNodeMixRGB")
    mmet.inputs["Color1"].default_value = (metal,) * 3 + (1,)
    mmet.inputs["Color2"].default_value = (0.9, 0.9, 0.9, 1)
    nt.links.new(edge.outputs["Color"], mmet.inputs["Fac"])
    nt.links.new(mmet.outputs["Color"], b.inputs["Metallic"])

    mrough = nt.nodes.new("ShaderNodeMixRGB")
    mrough.inputs["Color1"].default_value = (rough,) * 3 + (1,)
    mrough.inputs["Color2"].default_value = (0.24, 0.24, 0.24, 1)
    nt.links.new(edge.outputs["Color"], mrough.inputs["Fac"])
    nt.links.new(mrough.outputs["Color"], b.inputs["Roughness"])

    # 细节凹凸：两层噪声
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 42.0
    fine.inputs["Detail"].default_value = 12.0
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    mixh = nt.nodes.new("ShaderNodeMixRGB")
    mixh.blend_type = 'ADD'
    mixh.inputs["Fac"].default_value = 0.45
    nt.links.new(fine.outputs["Fac"], mixh.inputs["Color1"])
    nt.links.new(streak.outputs["Fac"], mixh.inputs["Color2"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(mixh.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


M_HULL = paint_mat("R2_Hull", (0.80, 0.80, 0.77), 0.15, 0.38, 0.55, 0.40)
M_STEEL = paint_mat("R2_Steel", (0.58, 0.60, 0.63), 0.92, 0.26, 0.25, 0.25)
M_DARK = paint_mat("R2_Dark", (0.09, 0.09, 0.10), 0.72, 0.44, 0.30, 0.30)
print("MATERIALS_REBUILT")

# ══════ 2. 其余设施细节（全部新增）══════
NEW = []


def _mat(ob, mat):
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


def torus(major, minor, loc, rot=(0, 0, 0), mat=M_STEEL, mj=48, mn=10, name="FAC_t"):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=mj, minor_segments=mn,
                                     location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    return _mat(ob, mat)


def cyl(r, h, loc, rot=(0, 0, 0), mat=M_STEEL, v=32, name="FAC_c"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v,
                                        location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    return _mat(ob, mat)


def box(sx, sy, sz, loc, rot=(0, 0, 0), mat=M_STEEL, name="FAC_b"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    bv = ob.modifiers.new("Bev", 'BEVEL')
    bv.width = 0.05
    bv.segments = 2
    return _mat(ob, mat)


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(prefix):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefix)), None)


# 2a. 科研实验舱：环箍 + 舱门框 + 设备箱 + 管线
lab = find("科研实验舱")
if lab:
    mn, mx = bbox(lab)
    c = (mn + mx) / 2
    L = max(mx.x - mn.x, mx.y - mn.y)
    R = min(mx.y - mn.y, mx.z - mn.z) / 2
    axis = 'X' if (mx.x - mn.x) == L else 'Y'
    for i in range(8):
        t = (i + 0.5) / 8
        if axis == 'X':
            px = mn.x + (mx.x - mn.x) * t
            torus(R * 1.02, 0.22, (px, c.y, c.z), rot=(0, math.pi / 2, 0), name=f"FAC_LabBand{i}")
        else:
            py = mn.y + (mx.y - mn.y) * t
            torus(R * 1.02, 0.22, (c.x, py, c.z), rot=(math.pi / 2, 0, 0), name=f"FAC_LabBand{i}")
    # 舱门框（侧向）
    box(0.5, 6.0, 5.0, (c.x, mn.y - 0.4, c.z), mat=M_DARK, name="FAC_LabHatch")
    # 设备箱
    for i in range(3):
        box(3.0, 2.0, 2.4, (c.x - 5 + i * 5, c.y - R - 1.4, mn.z + 3.0), mat=M_STEEL,
            name=f"FAC_LabEquip{i}")
    # 管线束
    cyl(0.35, (mx.x - mn.x) * 0.8, (c.x, c.y, mx.z + 0.8), rot=(0, math.pi / 2, 0),
        name="FAC_LabPipe")

# 2b. 返回火箭：级间环 + 环向加劲 + 电缆整流罩
rk = find("返回火箭")
if rk:
    mn, mx = bbox(rk)
    c = (mn + mx) / 2
    R = (mx.x - mn.x) / 2
    for i in range(4):
        z = mn.z + (mx.z - mn.z) * (0.18 + i * 0.2)
        torus(R * 1.01, 0.20, (c.x, c.y, z), rot=(0, 0, 0), name=f"FAC_RockRing{i}")
    box(0.8, 1.2, (mx.z - mn.z) * 0.55, (c.x + R * 0.98, c.y, c.z), mat=M_DARK,
        name="FAC_RockRaceway")
    for i in range(4):                        # 栅格翼铰座
        th = math.pi / 4 + i * math.pi / 2
        box(1.2, 1.2, 1.6, (c.x + R * math.cos(th), c.y + R * math.sin(th), mn.z + (mx.z - mn.z) * 0.30),
            rot=(0, 0, th), mat=M_DARK, name=f"FAC_RockFinHinge{i}")

# 2c. 加压廊道：波纹补偿段 + 支架
tn = find("加压廊道")
if tn:
    mn, mx = bbox(tn)
    c = (mn + mx) / 2
    R = min(mx.y - mn.y, mx.z - mn.z) / 2 * 0.95
    n = 10
    for i in range(n):
        t = (i + 0.5) / n
        px = mn.x + (mx.x - mn.x) * t
        torus(R * 1.05, 0.18, (px, c.y, c.z), rot=(0, math.pi / 2, 0), name=f"FAC_TunnelBellows{i}")
    for i in range(3):
        px = mn.x + (mx.x - mn.x) * (0.2 + i * 0.3)
        cyl(0.4, c.z - mn.z, (px, c.y, (c.z + mn.z) / 2), name=f"FAC_TunnelTrestle{i}")

# 2d. 深空天线：背架桁架 + 馈源三脚架
dish = find("抛物面反射器")
if dish:
    mn, mx = bbox(dish)
    c = (mn + mx) / 2
    R = (mx.x - mn.x) / 2
    for i in range(6):
        th = 2 * math.pi * i / 6
        box(0.35, R * 0.9, 0.35,
            (c.x + R * 0.5 * math.cos(th), c.y + R * 0.5 * math.sin(th), mn.z - 1.2),
            rot=(0, math.radians(35), th), mat=M_STEEL, name=f"FAC_DishStrut{i}")
    for i in range(3):
        th = 2 * math.pi * i / 3
        box(0.3, 0.3, 6.0, (c.x + 3 * math.cos(th), c.y + 3 * math.sin(th), c.z + 4),
            rot=(math.radians(12), 0, th), mat=M_DARK, name=f"FAC_FeedLeg{i}")

# 2e. 太阳能阵：接线盒 + 跟踪推杆
sol = find("太阳能板")
if sol:
    mn, mx = bbox(sol)
    c = (mn + mx) / 2
    for i in range(4):
        box(1.7, 1.2, 1.0, (mn.x + (mx.x - mn.x) * (0.15 + i * 0.22), mn.y - 1.0, mn.z + 1.0),
            mat=M_DARK, name=f"FAC_SolarJBox{i}")
    cyl(0.28, 8.0, (c.x, mn.y - 1.6, mn.z + 2.0), rot=(math.radians(35), 0, 0),
        name="FAC_SolarActuator")

print("DETAILS_ADDED", len(NEW))

# ══════ 3. 尘暴体积光 ══════
scene = bpy.context.scene
fog = bpy.data.objects.get("FX_Dust")
if fog:
    m = fog.data.materials[0]
    for n in m.node_tree.nodes:
        if n.type == 'PRINCIPLED_VOLUME':
            n.inputs["Density"].default_value = 0.00075
            n.inputs["Anisotropy"].default_value = 0.72
            n.inputs["Color"].default_value = (0.90, 0.72, 0.55, 1)
# 第二盏对角线光，制造光柱
sd2 = bpy.data.lights.new("DustSun", 'SUN')
sd2.energy = 2.2
sd2.angle = math.radians(2.5)
sd2.color = (1.0, 0.85, 0.68)
sun2 = bpy.data.objects.new("DustSun", sd2)
bpy.context.collection.objects.link(sun2)
sun2.rotation_euler = (Vector((0, 0, 0)) - Vector((-0.55, -0.45, 0.35)).normalized()).to_track_quat('-Z', 'Y').to_euler()

scene.eevee.taa_render_samples = 128
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.15
try:
    scene.eevee.use_volumetric_shadows = True
    scene.eevee.volumetric_start = 1.0
    scene.eevee.volumetric_end = 4000.0
    scene.eevee.volumetric_sample_distribution = 0.9
except Exception:
    pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s5.blend"))
print("S5_DONE")
