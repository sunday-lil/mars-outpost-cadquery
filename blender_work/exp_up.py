import bpy, os
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
bpy.ops.object.select_all(action='DESELECT')
ms = [o for o in bpy.data.objects if o.type == 'MESH']
for o in ms: o.select_set(True)
print("MESHES", len(ms))
bpy.ops.export_scene.gltf(filepath=os.path.join(EXPORTS, "mars_outpost_upgraded.glb"),
                          export_format='GLB', use_selection=True, export_apply=True,
                          export_yup=True, export_materials='EXPORT')
p = os.path.join(EXPORTS, "mars_outpost_upgraded.glb")
print("WROTE", round(os.path.getsize(p)/1e6, 1), "MB")
