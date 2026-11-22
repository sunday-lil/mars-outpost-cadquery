# -*- coding: utf-8 -*-
"""S4-R2：环体细节重做 + 光影/材质/结构细节加强。

修正上一轮三处问题：
  1. 舷窗挖孔：刀具改为"沿径向贯穿整根环管"（depth = 2*tube + 4），不会再切出槽口
  2. 环肋：沿截面扫掠 12 段（而非 4 段），并给 0.35 m 壁厚 → 实体带，不再有摩尔纹
  3. 材质：曲面不再用 trim 图集（避免木纹），改用细腻噪声漆面 + 分缝法线

另外补：三点布光 + 体积尘 + GTAO + 更细的辐条节点板 / 散热片 / 检修口

运行： blender -b habitat_v3_s1.blend -P v3_stage3.py
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
G = 3.72

LEGACY = ("压痕路径", "相机镜片", "顶部信标", "观察舷窗", "穹顶肋")
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and ob.name.startswith(LEGACY):
        bpy.data.objects.remove(ob, do_unlink=True)

KEEP = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("TERRAIN")]


# ══ 材质：漆面（细噪声，无图集）/ 金属 / 玻璃 / 太阳能 ══
def pbr(name, color, metal, rough, bump=0.15, scale=9.0, dust=0.0, paint=False):
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
    nz.inputs["Detail"].default_value = 12.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    if paint:
        # 稀细分缝：条纹噪声叠加，模拟蒙皮分块
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = 0.25
        wave.inputs["Distortion"].default_value = 0.0
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.blend_type = 'MULTIPLY'
        mx.inputs["Fac"].default_value = 0.12
        mx.inputs["Color1"].default_value = (*color, 1)
        nt.links.new(wave.outputs["Fac"], mx.inputs["Color2"])
        nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    if dust > 0:
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.inputs["Fac"].default_value = dust
        mx.inputs["Color2"].default_value = (0.55, 0.31, 0.19, 1)
        if paint:
            nt.links.new(b.inputs["Base Color"].links[0].from_socket, mx.inputs["Color1"])
        else:
            mx.inputs["Color1"].default_value = (*color, 1)
        nt.links.new(nz.outputs["Fac"], mx.inputs["Fac"])
        nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.06
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (rough * 0.65,) * 3 + (1,)
    rr.color_ramp.elements[1].color = (min(1.0, rough * 1.4),) * 3 + (1,)
    nt.links.new(nz.outputs["Fac"], rr.inputs["Fac"])
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    return m


M_HULL = pbr("R2_Hull", (0.80, 0.80, 0.77), 0.22, 0.38, 0.12, 6.0, dust=0.06, paint=True)
M_STEEL = pbr("R2_Steel", (0.58, 0.60, 0.63), 0.94, 0.24, 0.14, 14.0)
M_DARK = pbr("R2_Dark", (0.08, 0.08, 0.09), 0.75, 0.42, 0.16, 18.0)
M_GLASS = pbr("R2_Glass", (0.015, 0.05, 0.11), 0.6, 0.04, 0.0)
M_SOLAR = pbr("R2_Solar", (0.03, 0.06, 0.14), 0.7, 0.12, 0.06, 22.0)
M_PAD = pbr("R2_Pad", (0.54, 0.51, 0.47), 0.05, 0.86, 0.25, 3.0)

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
        bv.width = 0.05
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(25)
        wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
print("SURFACE_OK")

# ══ 环体测量（在 XY 平面内）══
ring = next(o for o in KEEP if o.name.startswith("居住穹顶"))
vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
cx = (max(v.x for v in vs) + min(v.x for v in vs)) / 2
cy = (max(v.y for v in vs) + min(v.y for v in vs)) / 2
rxy = [math.hypot(v.x - cx, v.y - cy) for v in vs]
R_OUT = max(rxy)
near = [v.z for v, r in zip(vs, rxy) if r > 0.88 * R_OUT]
Z_RING = (max(near) + min(near)) / 2
R_TUBE = max(0.8, (max(near) - min(near)) / 2)
R_MAJ = R_OUT - R_TUBE
OM = math.sqrt(G / R_MAJ)
print(f"RING Rout={R_OUT:.1f} R={R_MAJ:.1f} tube={R_TUBE:.2f} z={Z_RING:.1f}")
print(f"OMEGA {OM:.4f} rad/s = {OM*60/(2*math.pi):.2f} rpm  HOOP {7850*G*R_MAJ/1e6:.2f} MPa")

NEW = []


def reg(ob, mat, name):
    ob.name = name
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


# ══ 舷窗：径向贯穿挖孔 + 法兰 + 玻璃 ══
HOLE_R = min(2.4, R_TUBE * 0.30)
for k in range(16):
    th = 2 * math.pi * k / 16 + math.pi / 32
    dark = Vector((math.cos(th), math.sin(th), 0.0))
    center = Vector((cx + R_MAJ * dark.x, cy + R_MAJ * dark.y, Z_RING))
    # 刀具：轴向沿径向，长度 2*tube+4 → 必然贯穿
    bpy.ops.mesh.primitive_cylinder_add(radius=HOLE_R, depth=2 * R_TUBE + 4.0, vertices=40,
                                        location=center, rotation=(0, math.pi / 2, th))
    cut = bpy.context.object
    md = ring.modifiers.new("hole", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = cut
    md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ring
    bpy.ops.object.modifier_apply(modifier="hole")
    bpy.data.objects.remove(cut, do_unlink=True)

    # 外法兰（贴在 R_OUT 处）+ 内法兰 + 玻璃
    for rf, off, nm, mat in ((HOLE_R * 1.08, 0.02, "FAC_PortOut", M_STEEL),
                             (HOLE_R * 0.98, -R_TUBE * 0.55, "FAC_PortIn", M_STEEL)):
        rr = R_MAJ + (R_TUBE * 2.0 if off > 0 else 0)
        px = cx + (R_OUT - 0.05 if off > 0 else R_MAJ - R_TUBE * 0.55) * dark.x
        py = cy + (R_OUT - 0.05 if off > 0 else R_MAJ - R_TUBE * 0.55) * dark.y
        bpy.ops.mesh.primitive_torus_add(major_radius=rf, minor_radius=HOLE_R * 0.09,
                                          major_segments=36, minor_segments=8,
                                          location=(px, py, Z_RING),
                                          rotation=(0, math.pi / 2, th))
        reg(bpy.context.object, mat, f"{nm}{k}")
    gx = cx + (R_MAJ + R_TUBE * 0.45) * dark.x
    gy = cy + (R_MAJ + R_TUBE * 0.45) * dark.y
    bpy.ops.mesh.primitive_circle_add(radius=HOLE_R * 0.97, vertices=36, fill_type='NGON',
                                      location=(gx, gy, Z_RING),
                                      rotation=(0, math.pi / 2, th))
    reg(bpy.context.object, M_GLASS, f"FAC_PortGlass{k}")

# ══ 环肋：12 段扫掠的实体带（0.35 m 凸起）══
R_RIB = R_TUBE + 0.35
prof = [(R_MAJ + R_RIB * math.cos(2 * math.pi * i / 32),
         Z_RING + R_RIB * math.sin(2 * math.pi * i / 32)) for i in range(32)]
for k in range(24):
    th0 = 2 * math.pi * k / 24
    bmb = bmesh.new()
    steps = 12
    prev = None
    for i in range(steps + 1):
        th = th0 + math.radians(1.6) * i / steps
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
    ob = bpy.data.objects.new(f"STR_Rib{k}", me)
    bpy.context.collection.objects.link(ob)
    reg(ob, M_STEEL, f"STR_Rib{k}")

# ══ 散热片 + 检修口 + 支撑塔 ══
for k in range(24):
    th = 2 * math.pi * k / 24 + math.pi / 48
    d = Vector((math.cos(th), math.sin(th), 0.0))
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(cx + (R_OUT + 0.6) * d.x, cy + (R_OUT + 0.6) * d.y, Z_RING),
        rotation=(0, 0, th))
    ob = bpy.context.object
    ob.scale = (0.3, 3.0, R_TUBE * 0.5)
    bpy.ops.object.transform_apply(scale=True)
    reg(ob, M_STEEL, f"FAC_Radiator{k}")


def ground(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 1200)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


for k in range(4):
    th = 2 * math.pi * k / 4 + math.pi / 4
    d = Vector((math.cos(th), math.sin(th), 0.0))
    px, py = cx + R_MAJ * d.x, cy + R_MAJ * d.y
    gz = ground(px, py)
    top = Z_RING - R_TUBE
    hgt = top - gz
    if hgt <= 1:
        continue
    bpy.ops.mesh.primitive_cylinder_add(radius=R_TUBE * 0.2, depth=hgt, vertices=28,
                                        location=(px, py, gz + hgt / 2))
    reg(bpy.context.object, M_STEEL, f"STR_Tower{k}")
    bpy.ops.mesh.primitive_cylinder_add(radius=R_TUBE * 0.85, depth=1.4, vertices=48,
                                        location=(px, py, gz + 0.7))
    reg(bpy.context.object, M_PAD, f"STR_Pad{k}")
    for i in range(1, max(2, int(hgt / 10))):
        z = gz + i * 10
        bpy.ops.mesh.primitive_torus_add(major_radius=R_TUBE * 0.22, minor_radius=0.2,
                                          major_segments=28, minor_segments=8,
                                          location=(px, py, z))
        reg(bpy.context.object, M_DARK, f"STR_TowerBand{k}_{i}")

print("DETAIL_OK", len(NEW))

# ══ 光影：三点布光 + 体积尘 + GTAO ══
scene = bpy.context.scene
w = bpy.data.worlds.new("MarsSky3")
scene.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
sk = nt.nodes.new("ShaderNodeTexSky")
sk.sky_type = 'MULTIPLE_SCATTERING'
sk.sun_elevation = math.radians(24)
sk.sun_rotation = math.radians(205)
sk.altitude = 1200.0
sk.air_density = 0.85
sk.aerosol_density = 3.6
mul = nt.nodes.new("ShaderNodeMixRGB")
mul.blend_type = 'MULTIPLY'
mul.inputs["Fac"].default_value = 1.0
mul.inputs["Color2"].default_value = (1.05, 0.62, 0.42, 1)
nt.links.new(sk.outputs["Color"], mul.inputs["Color1"])
mx = nt.nodes.new("ShaderNodeMixRGB")
mx.inputs["Fac"].default_value = 0.28
mx.inputs["Color2"].default_value = (0.58, 0.33, 0.21, 1)
nt.links.new(mul.outputs["Color"], mx.inputs["Color1"])
nt.links.new(mx.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.30
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

# 主光：太阳
sd = bpy.data.lights.new("KeySun", 'SUN')
sd.energy = 4.2
sd.angle = math.radians(0.9)
sd.color = (1.0, 0.92, 0.80)
sun = bpy.data.objects.new("KeySun", sd)
bpy.context.collection.objects.link(sun)
sun_dir = Vector((0.45, -0.52, 0.55)).normalized()
sun.rotation_euler = (Vector((0, 0, 0)) - sun_dir).to_track_quat('-Z', 'Y').to_euler()

# 补光：大面积暖色
fd = bpy.data.lights.new("FillArea", 'AREA')
fd.energy = 2.8e5
fd.size = 260.0
fd.color = (1.0, 0.86, 0.72)
fill = bpy.data.objects.new("FillArea", fd)
bpy.context.collection.objects.link(fill)
fill.location = (cx - 260, cy - 320, 200)
fill.rotation_euler = (Vector((cx, cy, 60)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

# 轮廓光：冷色背光
rd = bpy.data.lights.new("RimArea", 'AREA')
rd.energy = 1.8e5
rd.size = 180.0
rd.color = (0.62, 0.74, 1.0)
rim = bpy.data.objects.new("RimArea", rd)
bpy.context.collection.objects.link(rim)
rim.location = (cx + 300, cy + 300, 220)
rim.rotation_euler = (Vector((cx, cy, 60)) - rim.location).to_track_quat('-Z', 'Y').to_euler()

# 体积尘
m_fog = bpy.data.materials.new("R2_Dust")
m_fog.use_nodes = True
_f = m_fog.node_tree
_f.nodes.clear()
_o = _f.nodes.new("ShaderNodeOutputMaterial")
_v = _f.nodes.new("ShaderNodeVolumePrincipled")
_v.inputs["Density"].default_value = 0.00035
_v.inputs["Anisotropy"].default_value = 0.55
_v.inputs["Color"].default_value = (0.88, 0.70, 0.54, 1)
_f.links.new(_v.outputs["Volume"], _o.inputs["Volume"])
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 220))
fog = bpy.context.object
fog.name = "FX_Dust"
fog.scale = (1600, 1600, 520)
bpy.ops.object.transform_apply(scale=True)
fog.data.materials.append(m_fog)

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 96
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -0.25
for attr, val in (("use_gtao", True), ("gtao_distance", 3.0), ("use_soft_shadows", True),
                  ("use_shadow_high_bitdepth", True), ("use_volumetric_lights", True),
                  ("volumetric_tile_size", '4')):
    try:
        setattr(scene.eevee, attr, val)
    except Exception:
        pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s3.blend"))
print("S3_DONE")
