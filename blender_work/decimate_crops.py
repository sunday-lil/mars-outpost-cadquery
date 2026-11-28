import bpy
ob = bpy.data.objects.get("FAC_Crops")
if ob:
    before = len(ob.data.polygons)
    dec = ob.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = 0.55
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="Dec")
    print("CROPS_DECIMATED", before, "->", len(ob.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
