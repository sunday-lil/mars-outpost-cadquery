"""删除历次导入残留的参考模型散件（不属于本作品的对象）。"""
import bpy
OURS = ("居住穹顶","科研实验舱","加压廊道","返回火箭","推进器机身","发动机喷管","加速器喷管",
        "塔架","抛物面反射器","天线馈源臂","着陆平台","火星车体","车轮","机械臂","太阳能板",
        "能源边框","火星岩石","散热格栅","气象站","车顶帆板","观察舷窗","穹顶肋","顶部信标",
        "压痕路径","相机镜片","火星地形","TERRAIN","FX_","FAC_","STR_","TCK_","REF_")
dead = [o for o in bpy.data.objects
        if o.type in {'MESH','EMPTY'} and not o.name.startswith(OURS)]
print("PURGE", len(dead))
for o in dead:
    bpy.data.objects.remove(o, do_unlink=True)
left = [o for o in bpy.data.objects if o.type=='MESH']
print("REMAIN_MESH", len(left))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("PURGE_DONE")
