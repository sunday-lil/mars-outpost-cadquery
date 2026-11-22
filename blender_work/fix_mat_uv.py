"""把漆面材质的纹理坐标从 Object 改为 UV，并降低 dirt/wear 强度（统一多物体外观）。"""
import bpy

MATS = ("R2_Hull", "R2_Steel", "R2_Dark", "R2_Solar")
report = []
for name in MATS:
    m = bpy.data.materials.get(name)
    if not m or not m.use_nodes:
        continue
    nt = m.node_tree
    tc = next((n for n in nt.nodes if n.type == 'TEX_COORD'), None)
    if tc is None:
        # 没有 TexCoord 就新建一个 UV 坐标，接到所有 Vector 型输入
        tc = nt.nodes.new("ShaderNodeTexCoord")
        for n in nt.nodes:
            for inp in n.inputs:
                if inp.type == 'VECTOR' and not inp.is_linked:
                    nt.links.new(tc.outputs["UV"], inp)
        report.append((name, "created_uv_coord"))
        continue
    switched = 0
    for link in list(nt.links):
        if link.from_node is tc and link.from_socket.name == "Object":
            nt.links.remove(link)
            nt.links.new(tc.outputs["UV"], link.to_socket)
            switched += 1
    # 降低污渍 / 磨损强度
    tuned = 0
    for n in nt.nodes:
        if n.type == 'MIX_RGB':
            f = n.inputs["Fac"]
            if not f.is_linked and f.default_value in (0.40, 0.55, 0.25, 0.30):
                if f.default_value >= 0.5:
                    f.default_value = 0.22
                else:
                    f.default_value = min(f.default_value, 0.18)
                tuned += 1
    report.append((name, f"uv_links={switched} tuned={tuned}"))

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("MAT_UV_DONE", report)
