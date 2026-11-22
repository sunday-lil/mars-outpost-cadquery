# -*- coding: utf-8 -*-
"""S7：车辙/履带印 + 火星天空重做 + 走姿宇航员。

运行： blender -b habitat_v3_s6.blend -P v3_stage7.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
NEW = []

M_TRACK = None


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def find(pref):
    return next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(pref)), None)


def ground(x, y):
    hit, loc, _, _, _, _ = bpy.context.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), Vector((x, y, 1200)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0


# ══════ 1. 车辙：设施之间的双轨压痕 ══════
mt = bpy.data.materials.new("V3_Track")
mt.use_nodes = True
nt = mt.node_tree
b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
b.inputs["Base Color"].default_value = (0.30, 0.16, 0.10, 1)
b.inputs["Roughness"].default_value = 0.95
tc = nt.nodes.new("ShaderNodeTexCoord")
wv = nt.nodes.new("ShaderNodeTexWave")           # 胎面花纹
wv.bands_direction = 'Y'
wv.inputs["Scale"].default_value = 3.0
wv.inputs["Distortion"].default_value = 0.0
nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
mixc = nt.nodes.new("ShaderNodeMixRGB")
mixc.blend_type = 'MULTIPLY'
mixc.inputs["Fac"].default_value = 0.35
nt.links.new(wv.outputs["Color"], mixc.inputs["Color2"])
nt.links.new(mixc.outputs["Color"], b.inputs["Base Color"])
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.6
bump.inputs["Distance"].default_value = 0.08
nt.links.new(wv.outputs["Color"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
M_TRACK = mt

ring = find("居住穹顶")
targets = {}
for name in ("科研实验舱", "返回火箭", "太阳能板", "火星车体", "气象站"):
    ob = find(name)
    if ob:
        mn, mx = bbox(ob)
        targets[name] = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0))

if ring:
    mn, mx = bbox(ring)
    rc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, 0))
    for name, tgt in targets.items():
        d = (tgt - rc)
        L = d.length
        if L < 1:
            continue
        d.normalize()
        n = max(8, int(L / 25))
        for side in (-1.4, 1.4):                 # 双轨间距 2.8 m
            verts = []
            for i in range(n + 1):
                t = i / n
                p = rc + d * (L * t)
                perp = Vector((-d.y, d.x, 0.0)) * side
                x, y = p.x + perp.x, p.y + perp.y
                verts.append((x, y, ground(x, y) + 0.06))
            # 用 bmesh 生成 60 cm 宽的辙带
            import bmesh
            bmb = bmesh.new()
            left, right = [], []
            for (x, y, z) in verts:
                lx = x + (-d.y) * 0.3
                ly = y + (d.x) * 0.3
                rx = x - (-d.y) * 0.3
                ry = y - (d.x) * 0.3
                left.append(bmb.verts.new((lx, ly, ground(lx, ly) + 0.06)))
                right.append(bmb.verts.new((rx, ry, ground(rx, ry) + 0.06)))
            for i in range(len(left) - 1):
                bmb.faces.new([left[i], left[i + 1], right[i + 1], right[i]])
            me = bpy.data.meshes.new(f"TRACK_{name}")
            bmb.to_mesh(me)
            bmb.free()
            ob = bpy.data.objects.new(f"FAC_Track_{name}_{'L' if side < 0 else 'R'}", me)
            bpy.context.collection.objects.link(ob)
            ob.data.materials.append(mt)
            NEW.append(ob)
    print("TRACKS_OK", len([o for o in NEW if o.name.startswith("FAC_Track")]))

# ══════ 2. 火星天空重做（渐变 + 太阳光晕 + 尘带）══════
scene = bpy.context.scene
w = bpy.data.worlds.new("MarsSky7")
scene.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])

# 竖向渐变：地平线暖尘 → 天顶冷灰紫
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.42
ramp.color_ramp.elements[0].color = (0.42, 0.24, 0.16, 1)
ramp.color_ramp.elements[1].position = 0.85
ramp.color_ramp.elements[1].color = (0.20, 0.19, 0.24, 1)
e = ramp.color_ramp.elements.new(0.55)
e.color = (0.62, 0.40, 0.27, 1)
nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])

# 太阳：核心 + 光晕
sun_dir = Vector((0.45, -0.52, 0.55)).normalized()
dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
dot.inputs[1].default_value = sun_dir
nt.links.new(tc.outputs["Generated"], dot.inputs[0])
core = nt.nodes.new("ShaderNodeMath"); core.operation = 'POWER'
core.inputs[1].default_value = 900.0
nt.links.new(dot.outputs["Value"], core.inputs[0])
halo = nt.nodes.new("ShaderNodeMath"); halo.operation = 'POWER'
halo.inputs[1].default_value = 12.0
nt.links.new(dot.outputs["Value"], halo.inputs[0])
halo_s = nt.nodes.new("ShaderNodeMath"); halo_s.operation = 'MULTIPLY'
halo_s.inputs[1].default_value = 0.45
nt.links.new(halo.outputs["Value"], halo_s.inputs[0])
sum1 = nt.nodes.new("ShaderNodeMath"); sum1.operation = 'ADD'
nt.links.new(core.outputs["Value"], sum1.inputs[0])
nt.links.new(halo_s.outputs["Value"], sum1.inputs[1])
tint = nt.nodes.new("ShaderNodeMixRGB")
tint.blend_type = 'MULTIPLY'
tint.inputs["Fac"].default_value = 1.0
tint.inputs["Color1"].default_value = (1.0, 0.86, 0.66, 1)
nt.links.new(sum1.outputs["Value"], tint.inputs["Color2"])

add = nt.nodes.new("ShaderNodeMixRGB")
add.blend_type = 'ADD'
add.inputs["Fac"].default_value = 1.0
nt.links.new(ramp.outputs["Color"], add.inputs["Color1"])
nt.links.new(tint.outputs["Color"], add.inputs["Color2"])
nt.links.new(add.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.95
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
print("SKY_OK")

# ══════ 3. 走姿宇航员 ×2 ══════
M_SUIT = bpy.data.materials.get("R2_Hull")
M_VISOR = bpy.data.materials.get("R2_Glass")
M_PACK = bpy.data.materials.get("R2_Dark")


def cyl(r, h, loc, rot, mat, name, v=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=v, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    NEW.append(ob)
    return ob


def bx(sx, sy, sz, loc, rot, mat, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat)
    NEW.append(ob)
    return ob


def walker(x, y, yaw, tag):
    gz = ground(x, y)
    ca, sa = math.cos(yaw), math.sin(yaw)
    # 双腿摆动
    for side, ang in ((-0.13, 18), (0.13, -18)):
        ox, oy = -sa * side, ca * side
        cyl(0.09, 0.86, (x + ox - sa * 0.10, y + oy + ca * 0.10, gz + 0.43),
            (math.radians(ang), 0, yaw), M_SUIT, f"REF_WLeg{tag}{side}")
    bx(0.42, 0.26, 0.62, (x, y, gz + 1.18), (0, 0, yaw), M_SUIT, f"REF_WTorso{tag}")
    bx(0.34, 0.20, 0.44, (x - 0.22 * sa, y - 0.22 * ca, gz + 1.20), (0, 0, yaw), M_PACK,
       f"REF_WPack{tag}")
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, segments=20, ring_count=12,
                                         location=(x, y, gz + 1.62))
    h = bpy.context.object
    h.name = f"REF_WHelmet{tag}"
    h.data.materials.append(M_SUIT)
    NEW.append(h)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, segments=16, ring_count=10,
                                         location=(x + 0.10 * sa, y + 0.10 * ca, gz + 1.63))
    v = bpy.context.object
    v.name = f"REF_WVisor{tag}"
    v.data.materials.append(M_VISOR)
    NEW.append(v)
    for side, ang in ((-0.26, -22), (0.26, 22)):
        ox, oy = -sa * side, ca * side
        cyl(0.07, 0.55, (x + ox, y + oy, gz + 1.10), (math.radians(ang), 0, yaw), M_SUIT,
            f"REF_WArm{tag}{side}")


if ring:
    for i, (dx, dy, yaw) in enumerate(((10, -4, 0.6), (-12, 8, 2.4))):
        walker(rc.x + dx * 3, rc.y + dy * 3, yaw, str(i))
print("WALKERS_OK")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s7.blend"))
print("S7_DONE new", len(NEW))
