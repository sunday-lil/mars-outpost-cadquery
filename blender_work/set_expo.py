import bpy
bpy.context.scene.view_settings.exposure = -1.55
bpy.context.scene.eevee.taa_render_samples = 128
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("EXPO_SET")
