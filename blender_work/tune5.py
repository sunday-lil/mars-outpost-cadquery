import bpy
fog = bpy.data.objects.get("FX_Dust")
if fog:
    for n in fog.data.materials[0].node_tree.nodes:
        if n.type == 'PRINCIPLED_VOLUME':
            n.inputs["Density"].default_value = 0.00022
            n.inputs["Anisotropy"].default_value = 0.66
for ob in bpy.data.objects:
    if ob.type == 'LIGHT' and ob.name == "DustSun":
        ob.data.energy = 1.2
bpy.context.scene.view_settings.exposure = 0.05
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("TUNE5_OK")
