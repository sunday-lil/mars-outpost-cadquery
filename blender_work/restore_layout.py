# -*- coding: utf-8 -*-
"""回到原始布局，只做表面升级 —— 不移动、不删除任何已有物体。

做三件事：
  1. 材质：全套 PBR（漆面/拉丝金属/玻璃/太阳能/地形）
  2. 网格：每个物体加倒角 + 加权法线 + 平滑着色
  3. 地形：原地加细密噪声（≤0.15 m）+ 坡度材质；物体仅按同名高度微调（≤0.15 m）
  4. 居住环：按实测半径生成"贴合式"环肋与舷窗，不移动环体本身

运行： blender -b -P restore_layout.py
"""
import math

import bpy
from mathutils import Matrix, Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
GLB = HERE + "/../exports/mars_outpost.glb"
SCALE = 0.2

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
imported = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
ROT = Matrix.Rotation(math.radians(-90), 4, 'X')
for ob in imported:
    ob.data.transform(ROT)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    ob.data.update()
    ob.matrix_world = Matrix.Identity(4)
print("IMPORTED", len(imported))


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


ORIG = {o.name: bbox(o) for o in imported}

# ── 材质 ──
def pbr(name, color, metal, rough, bump=0.22, scale=6.0, dust=0.0):
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
    if dust > 0:
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.inputs["Fac"].default_value = dust
        mx.inputs["Color1"].default_value = (*color, 1)
        mx.inputs["Color2"].default_value = (0.58, 0.33, 0.20, 1)
        nt.links.new(nz.outputs["Fac"], mx.inputs["Fac"])
        nt.links.new(mx.outputs["Color"], b.inputs["Base Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.04
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (rough * 0.62,) * 3 + (1,)
    rr.color_ramp.elements[1].color = (min(1.0, rough * 1.45),) * 3 + (1,)
    nt.links.new(nz.outputs["Fac"], rr.inputs["Fac"])
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    return m


M_HULL = pbr("S_Hull", (0.80, 0.80, 0.77), 0.2, 0.40, 0.24, 3.0, dust=0.10)
M_STEEL = pbr("S_Steel", (0.57, 0.59, 0.62), 0.92, 0.26, 0.2, 12.0)
M_DARK = pbr("S_Dark", (0.09, 0.09, 0.10), 0.7, 0.45, 0.24, 16.0)
M_GLASS = pbr("S_Glass", (0.02, 0.06, 0.12), 0.6, 0.05, 0.0)
M_SOLAR = pbr("S_Solar", (0.03, 0.06, 0.14), 0.65, 0.15, 0.1, 20.0)

NAME_MAT = [("居住穹顶", M_HULL), ("穹顶肋", M_STEEL), ("科研实验舱", M_STEEL),
            ("加压廊道", M_STEEL), ("返回火箭", M_HULL), ("推进器机身", M_STEEL),
            ("发动机喷管", M_DARK), ("加速器喷管", M_STEEL), ("塔架", M_STEEL),
            ("抛物面反射器", M_HULL), ("天线馈源臂", M_STEEL), ("着陆平台", M_STEEL),
            ("火星车体", M_HULL), ("车轮", M_DARK), ("机械臂", M_STEEL),
            ("太阳能板", M_SOLAR), ("能源边框", M_STEEL), ("观察舷窗", M_GLASS),
            ("火星岩石", M_HULL), ("散热格栅", M_STEEL), ("气象站", M_STEEL),
            ("相机镜片", M_GLASS), ("车顶帆板", M_SOLAR), ("顶部信标", M_DARK)]

for ob in imported:
    if ob.name.startswith("火星地形"):
        continue
    for key, mat in NAME_MAT:
        if ob.name.startswith(key):
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            break
    try:
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width = 0.025
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(30)
        wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
print("MATERIALS_OK")

# ── 地形：原地细化（不改变整体轮廓）──
ter = next((o for o in imported if o.name.startswith("火星地形")), None)
if ter is not None:
    def fine(x, y):
        return (noise.noise(Vector((x / 9.0, y / 9.0, 3.1))) * 0.09 +
                noise.noise(Vector((x / 3.0, y / 3.0, 7.7))) * 0.03)

    for v in ter.data.vertices:
        v.co.z += fine(v.co.x, v.co.y)
    bpy.context.view_layer.objects.active = ter
    bpy.ops.object.shade_smooth()

    m = bpy.data.materials.new("S_Terrain")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Z"], inv.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.4
    nz.inputs["Detail"].default_value = 12.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (0.47, 0.23, 0.13, 1)
    mix.inputs["Color2"].default_value = (0.22, 0.11, 0.08, 1)
    nt.links.new(inv.outputs["Value"], mix.inputs["Fac"])
    nz2 = nt.nodes.new("ShaderNodeMixRGB")
    nz2.blend_type = 'OVERLAY'
    nz2.inputs["Fac"].default_value = 0.35
    nt.links.new(mix.outputs["Color"], nz2.inputs["Color1"])
    nt.links.new(nz.outputs["Fac"], nz2.inputs["Color2"])
    nt.links.new(nz2.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.96
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.45
    bp.inputs["Distance"].default_value = 0.06
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    ter.data.materials.clear()
    ter.data.materials.append(m)
print("TERRAIN_OK")

# ── 居住环：按实测几何加"贴合"细节（不移动环体）──
rib = next((o for o in imported if o.name.startswith("穹顶肋")), None)
ring = next((o for o in imported if o.name.startswith("居住穹顶")), None)
src = rib if rib is not None else ring
if src is not None:
    vs = [src.matrix_world @ v.co for v in src.data.vertices]
    cxy = Vector((sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs), 0))
    rxy = sorted(math.hypot(v.x - cxy.x, v.y - cxy.y) for v in vs)
    n = len(rxy)
    R_MAJ = rxy[int(n * 0.5)]
    zs = sorted(v.z for v in vs)
    Z_RING = (zs[int(n * 0.05)] + zs[int(n * 0.95)]) / 2.0
    R_TUBE = max(0.4, (zs[int(n * 0.95)] - zs[int(n * 0.05)]) / 2.0)
    print(f"RING R={R_MAJ:.2f} tube={R_TUBE:.2f} z={Z_RING:.2f}")
    OM = math.sqrt(3.72 / R_MAJ)
    print(f"OMEGA {OM:.3f} rad/s = {OM*60/(2*math.pi):.2f} rpm   HOOP {7850*3.72*R_MAJ/1e6:.2f} MPa")

    # 环肋：原模型 穹顶肋 已有 12 道箍，这里不再重复添加

    # 舷窗：贴在外缘，尺寸按环管半径给
    for k in range(8):
        th = 2 * math.pi * k / 8 + math.pi / 8
        px = cxy.x + (R_MAJ + R_TUBE * 0.62) * math.cos(th)
        py = cxy.y + (R_MAJ + R_TUBE * 0.62) * math.sin(th)
        rr = min(1.4, R_TUBE * 0.5)
        bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=rr * 0.14,
                                         major_segments=28, minor_segments=8,
                                         location=(px, py, Z_RING),
                                         rotation=(0, math.pi / 2, th))
        f = bpy.context.object
        f.name = f"RING_PORT{k}"
        f.data.materials.append(M_STEEL)
        bpy.ops.mesh.primitive_circle_add(radius=rr * 0.95, vertices=28, fill_type='NGON',
                                          location=(px, py, Z_RING),
                                          rotation=(0, math.pi / 2, th))
        g = bpy.context.object
        g.name = f"RING_PORTGLASS{k}"
        g.data.materials.append(M_GLASS)

# ── 校验：原物体是否被移动 ──
moved = 0
worst = 0.0
for o in imported:
    mn0, mx0 = ORIG[o.name]
    mn1, mx1 = bbox(o)
    d = max((mn1 - mn0).length, (mx1 - mx0).length)
    if d > 0.02:
        moved += 1
        worst = max(worst, d)
print("MOVED_OBJECTS", moved, "worst_delta", round(worst, 3))

bpy.ops.wm.save_as_mainfile(filepath=HERE + "/habitat_fixed.blend")
print("FIXED_SAVED")
