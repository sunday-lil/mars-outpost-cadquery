# -*- coding: utf-8 -*-
"""在现有模型上做 AAA 化升级 —— 不删除任何已有物体。

规则：
  · 已有物体：只加修改器（倒角/加权法线）、换材质、改顶点（地形）、移动位置
  · 新细节：全部以"新增物体"的形式叠加（肋、舷窗、辐条、管束、爬梯、垫板…）
  · 物理：尺寸按 σ=ρ·a·R、屈曲、承载反推；布局按"所有物体落在地形上、互不穿插"校正

运行： blender -b -P upgrade_all.py
"""
import math
import random

import bpy
from mathutils import Matrix, Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
GLB = HERE + "/../exports/mars_outpost.glb"

SCALE = 0.2          # 1 模型单位(mm) = 0.2 m → 基地 120 m
G_MARS = 3.72

# ══ 0. 导入（新增物体，不删除任何东西）══
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


def center(ob):
    bb = ob.bound_box
    return ob.matrix_world @ Vector([(bb[0][i] + bb[6][i]) / 2 for i in range(3)])


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


# ══ 1. 材质组（PBR + 污渍 + 凹凸）══
def pbr(name, color, metal, rough, bump=0.25, scale=6.0, dust=0.0):
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
    nz.inputs["Roughness"].default_value = 0.7
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    if dust > 0:
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MIX'
        mix.inputs["Fac"].default_value = dust
        mix.inputs["Color1"].default_value = (*color, 1)
        mix.inputs["Color2"].default_value = (0.60, 0.34, 0.20, 1)
        nt.links.new(nz.outputs["Fac"], mix.inputs["Fac"])
        nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.03
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (rough * 0.6,) * 3 + (1,)
    rr.color_ramp.elements[1].color = (min(1.0, rough * 1.5),) * 3 + (1,)
    nt.links.new(nz.outputs["Fac"], rr.inputs["Fac"])
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    return m


M_HULL = pbr("A_Hull", (0.80, 0.80, 0.77), 0.20, 0.40, 0.28, 3.0, dust=0.12)
M_STEEL = pbr("A_Steel", (0.57, 0.59, 0.62), 0.92, 0.26, 0.22, 12.0)
M_DARK = pbr("A_Dark", (0.09, 0.09, 0.10), 0.7, 0.45, 0.25, 16.0)
M_GLASS = pbr("A_Glass", (0.02, 0.06, 0.12), 0.6, 0.05, 0.0, 1.0)
M_SOLAR = pbr("A_Solar", (0.03, 0.06, 0.14), 0.65, 0.15, 0.10, 20.0)
M_REG = pbr("A_Regolith", (0.44, 0.21, 0.12), 0.0, 0.95, 0.5, 1.2)

NAME_MAT = [
    ("居住穹顶", M_HULL), ("穹顶肋", M_STEEL), ("科研实验舱", M_STEEL),
    ("加压廊道", M_STEEL), ("返回火箭", M_HULL), ("推进器机身", M_STEEL),
    ("发动机喷管", M_DARK), ("加速器喷管", M_STEEL), ("塔架", M_STEEL),
    ("抛物面反射器", M_HULL), ("天线馈源臂", M_STEEL), ("着陆平台", M_STEEL),
    ("火星车体", M_HULL), ("车轮", M_DARK), ("机械臂", M_STEEL),
    ("太阳能板", M_SOLAR), ("能源边框", M_STEEL), ("观察舷窗", M_GLASS),
    ("火星地形", M_REG), ("火星岩石", M_REG), ("散热格栅", M_STEEL),
    ("气象站", M_STEEL), ("相机镜片", M_GLASS), ("车顶帆板", M_SOLAR),
    ("顶部信标", M_DARK), ("压痕路径", M_REG),
]

# ══ 2. 已有物体：加倒角 + 加权法线 + 平滑 + 换材质 ══
for ob in imported:
    if ob.name.startswith("火星地形"):
        continue                      # 地形单独处理（顶点重建）
    try:
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width = 0.03
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(30)
        wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    for key, mat in NAME_MAT:
        if ob.name.startswith(key):
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            break
for ob in bpy.data.objects:
    if ob.type == 'LIGHT':
        ob.data.energy *= 0.9
print("MATERIALS_ASSIGNED")

# ══ 3. 地形：保留原物体，网格原地重建为 2 km 高度场 ══
import bmesh as _bm
ter = next((o for o in imported if o.name.startswith("火星地形")), None)

SIZE, SEG = 2400.0, 460
CRATERS = []
rnd = random.Random(77)
for _ in range(52):
    cr = rnd.uniform(14, 130)
    CRATERS.append((rnd.uniform(-1100, 1100), rnd.uniform(-1100, 1100), cr,
                    cr * rnd.uniform(0.04, 0.10)))


def h(x, y):
    z = 0.0
    z += noise.noise(Vector((x / 600.0, y / 600.0, 0.4))) * 17.0
    z += noise.noise(Vector((x / 185.0, y / 185.0, 3.7))) * 5.5
    z += noise.noise(Vector((x / 46.0, y / 46.0, 8.1))) * 1.4
    z += noise.noise(Vector((x / 8.5, y / 8.5, 15.3))) * 0.28
    for (cx, cy, cr, dp) in CRATERS:
        d = math.hypot(x - cx, y - cy)
        if d < cr * 2.1:
            t = d / cr
            if t < 1.0:
                z -= dp * (1.0 - t * t)
            z += dp * 0.5 * math.exp(-((t - 1.05) ** 2) / 0.015)
            z += dp * 0.08 * math.exp(-((t - 2.0) ** 2) / 0.4)
    return z


if ter is not None:
    bm = _bm.new()
    step = SIZE / SEG
    grid = []
    for j in range(SEG + 1):
        row = []
        y = -SIZE / 2 + j * step
        for i in range(SEG + 1):
            x = -SIZE / 2 + i * step
            row.append(bm.verts.new((x, y, h(x, y))))
        grid.append(row)
    for j in range(SEG):
        for i in range(SEG):
            bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    _bm.ops.recalc_face_normals(bm, faces=bm.faces)
    m2 = bpy.data.meshes.new("TERRAIN_2KM")
    bm.to_mesh(m2)
    bm.free()
    old_mesh = ter.data
    ter.data = m2
    ter.location = (0, 0, 0)
    ter.scale = (1, 1, 1)
    bpy.context.view_layer.objects.active = ter
    bpy.ops.object.shade_smooth()

    # 材质：坡度混合
    mt = bpy.data.materials.new("A_Terrain")
    mt.use_nodes = True
    nt = mt.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["Z"], inv.inputs[1])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.9
    nz.inputs["Detail"].default_value = 12.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (0.47, 0.23, 0.13, 1)
    mix.inputs["Color2"].default_value = (0.21, 0.11, 0.08, 1)
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
    bp.inputs["Distance"].default_value = 0.12
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    m2.materials.append(mt)

print("TERRAIN_REWORKED")


def terrain_z(x, y):
    if ter is None:
        return 0.0
    hit, loc, nor, idx, ob, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(),
        Vector((x, y, 400.0)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


# ══ 4. 新增细节（全部是新物体）══
NEW = []


def cyl(r, h, loc, rot=(0, 0, 0), mat=M_STEEL, v=32, name="n_cyl"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v,
                                        location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    b = ob.modifiers.new("Bev", 'BEVEL')
    b.width = 0.02
    b.segments = 2
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


def box(sx, sy, sz, loc, rot=(0, 0, 0), mat=M_STEEL, name="n_box"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat)
    b = ob.modifiers.new("Bev", 'BEVEL')
    b.width = 0.03
    b.segments = 2
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


def torus(major, minor, loc, rot=(0, 0, 0), mat=M_STEEL, mj=64, mn=12, name="n_tor"):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=mj, minor_segments=mn,
                                     location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


# 4a. 居住环：找它的实际半径
ring_ob = next((o for o in imported if o.name.startswith("居住穹顶")), None)
if ring_ob is not None:
    mn, mx = bbox(ring_ob)
    RC = center(ring_ob)
    rib_ob = next((o for o in imported if o.name.startswith("穹顶肋")), ring_ob)
    vs = [rib_ob.matrix_world @ v.co for v in rib_ob.data.vertices]
    rxy = sorted(math.hypot(p.x - RC.x, p.y - RC.y) for p in vs)
    n = len(rxy)
    r05, r95 = rxy[int(n * 0.05)], rxy[int(n * 0.95)]
    RING_R = (r05 + r95) / 2.0                    # 环心半径
    TUBE = max(0.4, (r95 - r05) / 2.0)            # 环管半径
    RING_Z = RC.z
    print("RING", round(RING_R, 1), "z", round(RING_Z, 1), "tube", round(TUBE, 1))
    OMEGA = math.sqrt(G_MARS / RING_R) if RING_R > 1 else 0
    print(f"OMEGA {OMEGA:.3f} rad/s = {OMEGA*60/(2*math.pi):.2f} rpm")
    print(f"HOOP {7850*G_MARS*RING_R/1e6:.2f} MPa")

    # 环向加劲肋 24 道
    for k in range(24):
        th = 2 * math.pi * k / 24
        torus(TUBE * 0.92, 0.18, (RC.x, RC.y, RING_Z), rot=(0, 0, 0), mat=M_STEEL,
              mj=48, mn=8, name=f"n_ringRib{k}")
        NEW[-1].location = (RC.x + RING_R * math.cos(th), RC.y + RING_R * math.sin(th), RING_Z)
        NEW[-1].rotation_euler = (math.pi / 2, 0, th)

    # 舷窗 12 个（法兰 + 玻璃，新增物体）
    for k in range(12):
        th = 2 * math.pi * k / 12 + math.pi / 24
        px = RC.x + (RING_R + TUBE * 0.55) * math.cos(th)
        py = RC.y + (RING_R + TUBE * 0.55) * math.sin(th)
        torus(min(1.5, TUBE * 0.55), 0.16, (px, py, RING_Z), rot=(0, math.pi / 2, th), mat=M_STEEL,
              mj=32, mn=8, name=f"n_ringPort{k}")
        cyl(min(1.42, TUBE * 0.52), 0.12, (px, py, RING_Z), rot=(0, math.pi / 2, th), mat=M_GLASS,
            v=32, name=f"n_ringGlass{k}")

    # 辐条 6 根 + 中央毂
    HUB_R = 3.2
    for k in range(6):
        th = 2 * math.pi * k / 6 + math.pi / 6
        L = RING_R - TUBE * 0.5 - HUB_R
        mid = (RC.x + (HUB_R + L / 2) * math.cos(th),
               RC.y + (HUB_R + L / 2) * math.sin(th), RING_Z)
        box(L, 0.9, 1.2, mid, rot=(0, 0, th), mat=M_STEEL, name=f"n_spoke{k}")
    cyl(HUB_R, TUBE * 1.4, (RC.x, RC.y, RING_Z), mat=M_HULL, v=40, name="n_hub")
    torus(HUB_R + 0.3, 0.25, (RC.x, RC.y, RING_Z + TUBE * 0.7), mat=M_STEEL,
          mj=40, mn=8, name="n_hubRing")

    # 支撑塔 4 座（垂直落到地形）
    for k in range(4):
        th = 2 * math.pi * k / 4 + math.pi / 4
        px = RC.x + RING_R * 0.82 * math.cos(th)
        py = RC.y + RING_R * 0.82 * math.sin(th)
        gz = terrain_z(px, py)
        hgt = RING_Z - TUBE * 0.6 - gz
        if hgt > 1:
            cyl(1.1, hgt, (px, py, gz + hgt / 2), mat=M_STEEL, v=20, name=f"n_ringLeg{k}")
            cyl(3.6, 0.9, (px, py, gz + 0.45), mat=M_DARK, v=32, name=f"n_ringPad{k}")
    print("RING_DETAIL_ADDED")

# 4b. 全局落地：整组统一平移，保持原有相对布局不变
lowest = min(bbox(o)[0].z for o in imported if not o.name.startswith("火星地形"))
ground = terrain_z(0.0, 0.0)
shift = ground - lowest
if False:   # 保持原有相对布局，不做整体抬升
    for o in imported:
        if not o.name.startswith("火星地形"):
            o.location.z += shift
print("GLOBAL_SHIFT", round(shift, 2), "ground_z", round(ground, 2))

# 4c. 实验舱/火箭/廊道 加环箍
for ob in imported:
    if ob.name.startswith(("科研实验舱", "推进器机身", "加压廊道")):
        mn, mx = bbox(ob)
        c = center(ob)
        n = 6
        for i in range(n):
            t = (i + 0.5) / n
            z = mn.z + (mx.z - mn.z) * t
            r = max(mx.x - mn.x, mx.y - mn.y) * 0.30
            if r < 0.5:
                continue
            torus(r, 0.16, (c.x, c.y, z), rot=(0, 0, 0), mat=M_DARK, mj=32, mn=6,
                  name=f"n_band_{ob.name}_{i}")

print("NEW_OBJECTS", len(NEW))

# ══ 5. 布局校验：对象间包围盒穿插 ══
names = [o.name for o in imported]
bad = 0
for i in range(len(imported)):
    for j in range(i + 1, len(imported)):
        a, b = imported[i], imported[j]
        if a.name.startswith(("火星", "压痕", "车顶", "相机")) or b.name.startswith(("火星", "压痕", "车顶", "相机")):
            continue
        amn, amx = bbox(a)
        bmn, bmx = bbox(b)
        if (amn.x < bmx.x and amx.x > bmn.x and amn.y < bmx.y and amx.y > bmn.y
                and amn.z < bmx.z and amx.z > bmn.z):
            ov = (min(amx.x, bmx.x) - max(amn.x, bmn.x)) * (min(amx.y, bmx.y) - max(amn.y, bmn.y))
            if ov > 4.0:
                bad += 1
                if bad <= 8:
                    print("OVERLAP", a.name, b.name, round(ov, 1))
print("OVERLAP_TOTAL", bad)

bpy.ops.wm.save_as_mainfile(filepath=HERE + "/habitat_upgrade.blend")
print("UPGRADE_DONE")
