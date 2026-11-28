import bpy
ob = bpy.data.objects.get("FAC_Crops")
if ob:
    for m in list(ob.modifiers):
        if m.type == 'SOLIDIFY':
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=m.name)
    before = len(ob.data.polygons)
    dec = ob.modifiers.new("Dec", 'DECIMATE'); dec.ratio = 0.5
    bpy.ops.object.modifier_apply(modifier="Dec")
    print("CROPS_DEC2", before, "->", len(ob.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
