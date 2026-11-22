import bpy
for name in ("R2_Hull","R2_Steel","R2_Dark","R2_Solar"):
    m = bpy.data.materials.get(name)
    if not m or not m.use_nodes: continue
    nt = m.node_tree
    sw = 0
    for link in list(nt.links):
        fn = link.from_node
        if fn.type == 'TEX_COORD' and link.from_socket.name != 'UV':
            tc = fn
            uv = tc.outputs.get("UV") or tc.outputs["UV"]
            to = link.to_socket
            nt.links.remove(link)
            nt.links.new(uv, to)
            sw += 1
    print("FIXED", name, sw)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("MAT_UV3_DONE")
