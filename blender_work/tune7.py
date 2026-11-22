import bpy
# 地形风蚀波纹：尺度调细、对比降低，避免"木纹"
ter = next((o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN"))), None)
if ter and ter.data.materials:
    for n in ter.data.materials[0].node_tree.nodes:
        if n.type == 'TEX_WAVE':
            n.inputs["Scale"].default_value = 0.45
            n.inputs["Distortion"].default_value = 12.0
        if n.type == 'MIX_RGB' and n.blend_type == 'OVERLAY':
            n.inputs["Fac"].default_value = 0.16
        if n.type == 'BUMP':
            n.inputs["Strength"].default_value = 0.45
            n.inputs["Distance"].default_value = 0.12
bpy.context.scene.view_settings.exposure = -1.15
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("TUNE7_OK")
