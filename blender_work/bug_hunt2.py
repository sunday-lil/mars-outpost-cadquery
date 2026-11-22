# -*- coding: utf-8 -*-
"""变态级 2.0：四项进阶检查
  A. 自相交检测（BVHTree 三角级 overlap，仅对包围盒已相交的对）
  B. UV 覆盖（缺失 UV / 零面积 UV / 越界 / 翻转）
  C. 拓扑一致性（连通壳数量、碎片化）
  D. 渲染一致性（同材质复用、法线朝向比例、材质图差异）

运行： blender -b habitat_final.blend -P bug_hunt2.py
"""
import json
import os
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = "/".join(bpy.data.filepath.split("/")[:-1]) or "."
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))

MESHES = [o for o in bpy.data.objects if o.type == 'MESH']
R = defaultdict(list)


def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


# ══════ A. 自相交（三角级）══════
def bvh_of(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(ob, dg)


cand = []
for i in range(len(MESHES)):
    a1, b1 = bbox(MESHES[i])
    for j in range(i + 1, len(MESHES)):
        a2, b2 = bbox(MESHES[j])
        if (min(b1.x, b2.x) - max(a1.x, a2.x) > 0.2 and
                min(b1.y, b2.y) - max(a1.y, a2.y) > 0.2 and
                min(b1.z, b2.z) - max(a1.z, a2.z) > 0.2):
            cand.append((MESHES[i], MESHES[j]))
print("CANDIDATE_PAIRS", len(cand))

bvh_cache = {}
tris_hit = 0
for a, b in cand:
    try:
        ta = bvh_cache.setdefault(a.name, bvh_of(a))
        tb = bvh_cache.setdefault(b.name, bvh_of(b))
        ov = ta.overlap(tb)
        if ov:
            tris_hit += 1
            # 装配接口：母子件（车体↔车轮、板↔边框、火箭↔喷管…）
            ASSEMBLY = (("火星车体", "车轮"), ("火星车体", "机械臂"), ("火星车体", "车顶帆板"),
                        ("火星车体", "相机镜片"), ("太阳能板", "能源边框"),
                        ("返回火箭", "推进器机身"), ("返回火箭", "发动机喷管"),
                        ("推力器机身", "发动机喷管"), ("返回火箭", "着陆平台"),
                        ("管道", "科研实验舱"), ("加压廊道", "科研实验舱"),
                        ("加压廊道", "居住穹顶"), ("居住穹顶", "穹顶肋"),
                        ("居住穹顶", "观察舷窗"), ("居住穹顶", "顶部信标"),
                        ("抛物面反射器", "天线馈源臂"), ("塔架", "抛物面反射器"))
            def is_assembly(x, y):
                for p, q in ASSEMBLY:
                    if (p in x and q in y) or (p in y and q in x):
                        return True
                # 后加件（FAC_/STR_/TCK_/FAC_Track）与其宿主：属装配接口
                ADDON = ("FAC_", "STR_", "TCK_", "REF_")
                if x.startswith(ADDON) or y.startswith(ADDON):
                    return True
                # 一方名字是另一方的子串
                return x in y or y in x
            entry = {"a": a.name, "b": b.name, "tri_pairs": len(ov)}
            if is_assembly(a.name, b.name):
                R["A_装配接口"].append(entry)
            else:
                R["A_真自相交"].append(entry)
    except Exception:
        pass
print("SELF_INTERSECT_PAIRS", tris_hit, "of", len(cand))

# ══════ B. UV 检查 ══════
for ob in MESHES:
    me = ob.data
    if not me.uv_layers:
        R["B_缺UV"].append({"obj": ob.name})
        continue
    uv = me.uv_layers.active.data
    zero = 0
    outside = 0
    flipped = 0
    for poly in me.polygons:
        if len(poly.loop_indices) < 3:
            continue
        pts = [uv[li].uv for li in poly.loop_indices]
        area = 0.0
        for k in range(len(pts)):
            x1, y1 = pts[k]
            x2, y2 = pts[(k + 1) % len(pts)]
            area += x1 * y2 - x2 * y1
        area *= 0.5
        if abs(area) < 1e-9:
            zero += 1
        elif area < 0:
            flipped += 1
        for (u, v) in pts:
            if u < -0.01 or u > 1.01 or v < -0.01 or v > 1.01:
                outside += 1
                break
    if zero:
        R["B_零面积UV"].append({"obj": ob.name, "faces": zero})
    total = max(1, len(me.polygons))
    if flipped and flipped > max(3, total * 0.02) and flipped < total * 0.9:
        R["B_UV不一致"].append({"obj": ob.name, "flipped_faces": flipped, "total": total})
    if outside:
        R["B_UV越界"].append({"obj": ob.name, "faces": outside})

# ══════ C. 拓扑一致性 ══════
for ob in MESHES:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen = set()
    islands = 0
    for v in bm.verts:
        if v.index in seen:
            continue
        islands += 1
        stack = [v]
        while stack:
            cur = stack.pop()
            if cur.index in seen:
                continue
            seen.add(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    stack.append(o)
    bm.free()
    if islands > 1:
        R["C_多壳体"].append({"obj": ob.name, "islands": islands})

# ══════ D. 渲染一致性 ══════
mat_users = defaultdict(list)
outward_bad = []
for ob in MESHES:
    for m in ob.data.materials:
        if m:
            mat_users[m.name].append(ob.name)
    # 法线朝外比例（仅闭合体有意义，这里做统计）
    me = ob.data
    n_in = sum(1 for p in me.polygons if p.normal.dot(p.center) < 0)
    if len(me.polygons) > 50 and n_in > len(me.polygons) * 0.5:
        outward_bad.append({"obj": ob.name, "inward_faces": n_in,
                            "total": len(me.polygons)})
for name, users in mat_users.items():
    if len(users) > 30:
        R["D_材质过度共享"].append({"mat": name, "objects": len(users)})
for x in outward_bad:
    R["D_法线朝内偏多"].append(x)

# ══════ 输出 ══════
summary = {k: len(v) for k, v in sorted(R.items())}
print("=== ADVANCED SUMMARY ===")
for k, v in summary.items():
    print(f"{k:16s} {v}")
print("TOTAL", sum(summary.values()))
with open(os.path.join(EXPORTS, "qa_advanced.json"), "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "detail": {k: v[:60] for k, v in R.items()},
               "candidates": len(cand)}, f, ensure_ascii=False, indent=1)
print("WRITTEN qa_advanced.json")
