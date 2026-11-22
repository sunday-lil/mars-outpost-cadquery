# -*- coding: utf-8 -*-
"""规则复核后的修正：① 恢复被误删的 5 个物体 ② 清除零面积面畸形 ③ 环肋加宽成实体带。"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
GLB = os.path.join(EXPORTS, "mars_outpost.glb")
SCALE = 0.625          # u=3.125 对应的导入比例

RESTORE = ("观察舷窗", "穹顶肋", "顶部信标", "压痕路径", "相机镜片")

# ══ ① 恢复被误删的物体（规则一：不删除任何已存在物体）══
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
dupes = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
ROT = Matrix.Rotation(math.radians(-90), 4, 'X')
keep = []
for ob in dupes:
    if ob.name.startswith(RESTORE):
        ob.data.transform(ROT)
        ob.data.transform(Matrix.Scale(SCALE, 4))
        ob.data.update()
        ob.matrix_world = Matrix.Identity(4)
        base = ob.name.split('.')[0]
        ob.name = base if base not in bpy.data.objects else base + "_r"
        keep.append(ob)
    else:
        bpy.data.objects.remove(ob, do_unlink=True)       # 删除本次导入的重复件
print("RESTORED", [o.name for o in keep])

# 材质交给后续统一处理
M_HULL = bpy.data.materials.get("R2_Hull")
M_STEEL = bpy.data.materials.get("R2_Steel")
M_DARK = bpy.data.materials.get("R2_Dark")
M_GLASS = bpy.data.materials.get("R2_Glass")
for ob in keep:
    if ob.name.startswith(("观察舷窗", "相机镜片")):
        ob.data.materials.clear(); ob.data.materials.append(M_GLASS)
    elif ob.name.startswith(("穹顶肋", "顶部信标")):
        ob.data.materials.clear(); ob.data.materials.append(M_STEEL)
    else:
        ob.data.materials.clear(); ob.data.materials.append(M_HULL)
    bv = ob.modifiers.new("Bevel", 'BEVEL'); bv.width = 0.04; bv.segments = 2
    bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(28)
    wn = ob.modifiers.new("WN", 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()

# ══ ② 清除零面积面 / 退化几何 ══
fixed = []
for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    if zero:
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
        ob.data.update()
        fixed.append((ob.name, zero))
    bm.free()
print("DEGENERATE_FIXED", fixed)

# ══ ③ 环肋：加宽到 3°，方截面 + 端面封盖 ══
for ob in [o for o in bpy.data.objects if o.name.startswith("STR_Rib")]:
    bpy.data.objects.remove(ob, do_unlink=True)

ring = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("居住穹顶"))
vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
cx = (max(v.x for v in vs) + min(v.x for v in vs)) / 2
cy = (max(v.y for v in vs) + min(v.y for v in vs)) / 2
rxy = [math.hypot(v.x - cx, v.y - cy) for v in vs]
R_OUT = max(rxy)
near = [v.z for v, r in zip(vs, rxy) if r > 0.88 * R_OUT]
Z_RING = (max(near) + min(near)) / 2
R_TUBE = max(0.8, (max(near) - min(near)) / 2)
R_MAJ = R_OUT - R_TUBE
print(f"RING R={R_MAJ:.1f} tube={R_TUBE:.2f} z={Z_RING:.1f}")

WIDTH_DEG = 3.0
PUSH = 0.45
NSEG = 48
for k in range(24):
    th0 = 2 * math.pi * k / 24
    bmb = bmesh.new()
    prof = [(R_MAJ + (R_TUBE + PUSH) * math.cos(2 * math.pi * i / NSEG),
             Z_RING + (R_TUBE + PUSH) * math.sin(2 * math.pi * i / NSEG)) for i in range(NSEG)]
    rings = []
    steps = 8
    for s in range(steps + 1):
        th = th0 + math.radians(WIDTH_DEG) * (s / steps - 0.5)
        ca, sa = math.cos(th), math.sin(th)
        rings.append([bmb.verts.new((r * ca, r * sa, z)) for (r, z) in prof])
    for s in range(steps):
        for q in range(NSEG):
            q2 = (q + 1) % NSEG
            bmb.faces.new([rings[s][q], rings[s][q2], rings[s + 1][q2], rings[s + 1][q]])
    bmb.faces.new(list(reversed(rings[0])))      # 端面封盖
    bmb.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bmb, faces=bmb.faces)
    me = bpy.data.meshes.new(f"RIB{k}")
    bmb.to_mesh(me)
    bmb.free()
    ob = bpy.data.objects.new(f"STR_Rib{k}", me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(M_STEEL)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
print("RIBS_REBUILT 24")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "habitat_v3_s4.blend"))
print("S4_DONE")
