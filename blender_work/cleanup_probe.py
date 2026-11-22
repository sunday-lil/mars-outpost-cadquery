import bpy
n=0
for ob in [o for o in bpy.data.objects if o.name.startswith("PROBE_")]:
    bpy.data.objects.remove(ob, do_unlink=True); n+=1
print("PROBE_REMOVED", n)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
