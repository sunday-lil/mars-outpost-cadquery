import bpy
for name in ("R2_Hull", "R2_Steel", "R2_Dark", "R2_Solar"):
    m = bpy.data.materials.get(name)
    if not m or not m.use_nodes:
        continue
    nt = m.node_tree
    tc = next((n for n in nt.nodes if n.type == 'TEX_COORD'), None)
    if tc is None:
        continue
    uv_sock = tc.outputs.get("UV")
    sw = 0
    for link in list(nt.links):
        if link.from_node is tc and link.from_socket is not uv_sock:
            to = link.to_socket
            nt.links.remove(link)
            nt.links.new(uv_sock, to)
            sw += 1
    tn = 0
    for n in nt.nodes:
        if n.type in {'MIX_RGB', 'MIX'}:
            f = n.inputs.get("Fac")
            if f and not f.is_linked:
                f.default_value = min(f.default_value, 0.18)
                tn += 1
    print("FIXED", name, "uv_links", sw, "fac_tuned", tn)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("MAT_UV2_DONE")
