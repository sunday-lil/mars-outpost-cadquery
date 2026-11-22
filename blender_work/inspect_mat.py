import bpy
m = bpy.data.materials.get("R2_Hull")
print("MAT", m.name, "use_nodes", m.use_nodes)
for n in m.node_tree.nodes:
    print(" NODE", n.type, n.name, n.bl_idname)
print(" -- links --")
for l in m.node_tree.links:
    print("  ", l.from_node.name, l.from_socket.name, "->", l.to_node.name, l.to_socket.name)
