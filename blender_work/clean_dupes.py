import bpy
# 删掉我自己加的重复环肋与过大的散热片（这些是本次新增件，不属于"已存在物体"）
drop = [o for o in bpy.data.objects if o.name.startswith(("STR_Rib", "FAC_Radiator"))]
for o in drop:
    bpy.data.objects.remove(o, do_unlink=True)
print("DROPPED_MINE", len(drop))
# 恢复件改名去后缀
for o in bpy.data.objects:
    if "_r" == o.name[-2:]:
        o.name = o.name[:-2] + "_restored"
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("CLEAN_OK")
