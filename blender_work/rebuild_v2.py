# -*- coding: utf-8 -*-
"""v2 重建：放大居住环到 R=40 m，清掉旧环遗留装饰，其他设施保持原位且不穿模。

物理：
  ω = sqrt(3.72/40) = 0.305 rad/s = 2.91 rpm      （< 3 rpm，舒适区间）
  σ = ρ·a·R = 7850×3.72×40 = 1.17 MPa             （Q355 SF 303）
  环管 6 m，壁板 100 mm；24 道环肋，肋间无支撑弧长 10.5 m
  环体离地 30 m，4 座支撑塔落在地形上；中央毂 + 6 辐条 + 电梯井

运行： blender -b -P rebuild_v2.py
"""
import math
import random

import bpy
from mathutils import Matrix, Vector, noise

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
GLB = HERE + "/../exports/mars_outpost.glb"
SCALE = 0.2
G = 3.72

# ── 环参数 ──
R_RING = 40.0
R_TUBE = 6.0
R_Z = 30.0
CENTER = Vector((-12.0, 0.0, R_Z))
HUB_R = 8.0

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
imported = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
ROT = Matrix.Rotation(math.radians(-90), 4, 'X')
for ob in imported:
    ob.data.transform(ROT)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    ob.data.update()
    ob.matrix_world = Matrix.Identity(4)

# ── 删除旧环遗留装饰（这些是"原来环位置上的鬼畜装饰件"）──
DROP = ("居住穹顶", "穹顶肋", "观察舷窗", "顶部信标", "压痕路径", "加压廊道")
dropped = []
for ob in list(imported):
    if ob.name.startswith(DROP):
        dropped.append(ob.name)
        bpy.data.objects.remove(ob, do_unlink=True)
print("DROPPED", dropped)
live = [o for o in bpy.data.objects if o.type == 'MESH']

# ── 材质 ──
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
        bp.inputs["Distance"].default_value = 0.05
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (rough * 0.62,) * 3 + (1,)
    rr.color_ramp.elements[1].color = (min(1.0, rough * 1.45),) * 3 + (1,)
    nt.links.new(nz.outputs["Fac"], rr.inputs["Fac"])
    nt.links.new(rr.outputs["Color"], b.inputs["Roughness"])
    return m


M_HULL = pbr("V2_Hull", (0.80, 0.80, 0.77), 0.2, 0.40, 0.25, 3.0, dust=0.10)
M_STEEL = pbr("V2_Steel", (0.57, 0.59, 0.62), 0.92, 0.26, 0.2, 12.0)
M_DARK = pbr("V2_Dark", (0.09, 0.09, 0.10), 0.7, 0.45, 0.25, 16.0)
M_GLASS = pbr("V2_Glass", (0.02, 0.06, 0.12), 0.6, 0.05, 0.0)
M_SOLAR = pbr("V2_Solar", (0.03, 0.06, 0.14), 0.65, 0.15, 0.1, 20.0)
M_PAD = pbr("V2_Pad", (0.55, 0.52, 0.48), 0.05, 0.85, 0.3, 2.0)

NAME_MAT = [("科研实验舱", M_STEEL), ("返回火箭", M_HULL), ("推进器机身", M_STEEL),
            ("发动机喷管", M_DARK), ("加速器喷管", M_STEEL), ("塔架", M_STEEL),
            ("抛物面反射器", M_HULL), ("天线馈源臂", M_STEEL), ("着陆平台", M_STEEL),
            ("火星车体", M_HULL), ("车轮", M_DARK), ("机械臂", M_STEEL),
            ("太阳能板", M_SOLAR), ("能源边框", M_STEEL), ("火星岩石", M_HULL),
            ("散热格栅", M_STEEL), ("气象站", M_STEEL), ("相机镜片", M_GLASS),
            ("车顶帆板", M_SOLAR), ("加压廊道", M_STEEL)]
for ob in live:
    if ob.name.startswith("火星地形"):
        continue
    for key, mat in NAME_MAT:
        if ob.name.startswith(key):
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            break
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

# ── 地形：原地重建 2.4 km 高度场 ──
import bmesh as bmesh_mod
ter = next((o for o in live if o.name.startswith("火星地形")), None)
rnd = random.Random(2027)
CRATERS = [(rnd.uniform(-1100, 1100), rnd.uniform(-1100, 1100),
            (cr := rnd.uniform(14, 120)), cr * rnd.uniform(0.05, 0.11)) for _ in range(48)]


def h(x, y):
    z = noise.noise(Vector((x / 600.0, y / 600.0, 0.4))) * 16.0
    z += noise.noise(Vector((x / 185.0, y / 185.0, 3.7))) * 5.0
    z += noise.noise(Vector((x / 46.0, y / 46.0, 8.1))) * 1.3
    z += noise.noise(Vector((x / 8.5, y / 8.5, 15.3))) * 0.26
    for (cx, cy, cr, dp) in CRATERS:
        d = math.hypot(x - cx, y - cy)
        if d < cr * 2.1:
            t = d / cr
            if t < 1.0:
                z -= dp * (1 - t * t)
            z += dp * 0.5 * math.exp(-((t - 1.05) ** 2) / 0.015)
    return z


if ter is not None:
    SIZE, SEG = 2400.0, 400
    bm = bmesh_mod.new()
    step = SIZE / SEG
    grid = []
    for j in range(SEG + 1):
        y = -SIZE / 2 + j * step
        grid.append([bm.verts.new((-SIZE / 2 + i * step, y,
                                   h(-SIZE / 2 + i * step, y))) for i in range(SEG + 1)])
    for j in range(SEG):
        for i in range(SEG):
            bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    bmesh_mod.ops.recalc_face_normals(bm, faces=bm.faces)
    m2 = bpy.data.meshes.new("TERRAIN_2KM")
    bm.to_mesh(m2)
    bm.free()
    ter.data = m2
    ter.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = ter
    bpy.ops.object.shade_smooth()

    mt = bpy.data.materials.new("V2_Terrain")
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
print("TERRAIN_OK")

# ── 新环体（bmesh 旋转圆角矩形截面）──
RC = 1.5


def prof():
    ro, ri = R_RING + R_TUBE, R_RING - R_TUBE
    zc = R_TUBE
    pts = [(ri, -zc), (ro - RC, -zc)]
    for i in range(5):
        a = -math.pi / 2 + (math.pi / 2) * i / 4
        pts.append((ro - RC + RC * math.cos(a), -zc + RC + RC * math.sin(a)))
    for i in range(5):
        a = (math.pi / 2) * i / 4
        pts.append((ro - RC + RC * math.cos(a), zc - RC + RC * math.sin(a)))
    pts += [(ro - RC, zc), (ri, zc)]
    return pts


bm = bmesh_mod.new()
N = 384
rings = []
for i in range(N):
    a = 2 * math.pi * i / N
    ca, sa = math.cos(a), math.sin(a)
    rings.append([bm.verts.new((r * ca, r * sa, z + R_Z)) for (r, z) in prof()])
for i in range(N):
    j = (i + 1) % N
    for k in range(len(prof())):
        k2 = (k + 1) % len(prof())
        bm.faces.new([rings[i][k], rings[i][k2], rings[j][k2], rings[j][k]])
bmesh_mod.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("RING_HULL")
bm.to_mesh(me)
bm.free()
hull = bpy.data.objects.new("RING_HULL", me)
bpy.context.collection.objects.link(hull)
hull.data.materials.append(M_HULL)
bpy.context.view_layer.objects.active = hull
bpy.ops.object.shade_smooth()

# 环肋：贴合截面的窄带（沿轮廓扫掠 1.4°），不再是悬空的圆环
for k in range(24):
    th0 = 2 * math.pi * k / 24
    bmb = bmesh_mod.new()
    segs = 6
    prev = []
    for i in range(segs + 1):
        a = th0 + math.radians(1.4) * i / segs
        ca, sa = math.cos(a), math.sin(a)
        cur = [bmb.verts.new(((r + 0.12) * ca, (r + 0.12) * sa, z + R_Z))
               for (r, z) in prof()]
        if prev:
            for q in range(len(cur)):
                q2 = (q + 1) % len(cur)
                bmb.faces.new([prev[q], prev[q2], cur[q2], cur[q]])
        prev = cur
    bmesh_mod.ops.recalc_face_normals(bmb, faces=bmb.faces)
    mrb = bpy.data.meshes.new(f"RIB{k}")
    bmb.to_mesh(mrb)
    bmb.free()
    rob = bpy.data.objects.new(f"RingRib{k}", mrb)
    bpy.context.collection.objects.link(rob)
    rob.data.materials.append(M_STEEL)
    bpy.context.view_layer.objects.active = rob
    bpy.ops.object.shade_smooth()

for k in range(24):
    th = 2 * math.pi * k / 24 + math.pi / 24
    px = (R_RING + R_TUBE - 0.3) * math.cos(th) + CENTER.x
    py = (R_RING + R_TUBE - 0.3) * math.sin(th) + CENTER.y
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.18,
                                     major_segments=32, minor_segments=8,
                                     location=(px, py, R_Z),
                                     rotation=(0, math.pi / 2, th))
    f = bpy.context.object
    f.name = f"RingPort{k}"
    f.data.materials.append(M_STEEL)
    bpy.ops.mesh.primitive_circle_add(radius=1.55, vertices=32, fill_type='NGON',
                                      location=(px, py, R_Z), rotation=(0, math.pi / 2, th))
    gl = bpy.context.object
    gl.name = f"RingPortGlass{k}"
    gl.data.materials.append(M_GLASS)

# 辐条 + 毂 + 电梯井
for k in range(6):
    th = 2 * math.pi * k / 6 + math.pi / 6
    L = (R_RING - R_TUBE) - HUB_R
    mid = (CENTER.x + (HUB_R + L / 2) * math.cos(th),
           CENTER.y + (HUB_R + L / 2) * math.sin(th), R_Z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=mid, rotation=(0, 0, th))
    sp = bpy.context.object
    sp.name = f"Spoke{k}"
    sp.scale = (L, 1.4, 1.8)
    bpy.ops.object.transform_apply(scale=True)
    sp.data.materials.append(M_STEEL)
    bpy.ops.object.shade_smooth()

bpy.ops.mesh.primitive_cylinder_add(radius=HUB_R, depth=20.0,
                                    location=(CENTER.x, CENTER.y, R_Z), vertices=48)
hub = bpy.context.object
hub.name = "HUB"
hub.data.materials.append(M_HULL)
bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_cylinder_add(radius=4.5, depth=R_Z - 10.0,
                                    location=(CENTER.x, CENTER.y, (R_Z - 10.0) / 2), vertices=32)
sh = bpy.context.object
sh.name = "HUB_Shaft"
sh.data.materials.append(M_DARK)

# 4 座支撑塔 + 垫板（落在地形上）
def terrain_at(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 500)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


for k in range(4):
    th = 2 * math.pi * k / 4 + math.pi / 4
    px = CENTER.x + R_RING * math.cos(th)
    py = CENTER.y + R_RING * math.sin(th)
    gz = terrain_at(px, py)
    top = R_Z - R_TUBE
    hgt = top - gz
    bpy.ops.mesh.primitive_cylinder_add(radius=1.6, depth=max(hgt, 1.0),
                                        location=(px, py, gz + hgt / 2), vertices=24)
    t1 = bpy.context.object
    t1.name = f"Tower{k}"
    t1.data.materials.append(M_STEEL)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(radius=5.0, depth=1.2,
                                        location=(px, py, gz + 0.6), vertices=40)
    p1 = bpy.context.object
    p1.name = f"Pad{k}"
    p1.data.materials.append(M_PAD)
    bpy.ops.object.shade_smooth()
    for i in range(1, max(2, int(hgt / 6))):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.75, minor_radius=0.14,
                                         major_segments=24, minor_segments=6,
                                         location=(px, py, gz + i * 6))
        c = bpy.context.object
        c.name = f"Tower{k}_band{i}"
        c.data.materials.append(M_DARK)

print("RING_BUILT")
bpy.ops.wm.save_as_mainfile(filepath=HERE + "/habitat_v2.blend")
print("V2_SAVED")
