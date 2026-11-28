import bpy, os, json
from mathutils import Vector
GLTF = os.path.abspath(os.path.join("..", "董的训练资料（感谢激情赞助）", "新的", "mars_base_alpha_complete.gltf"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLTF)
ms = [o for o in bpy.data.objects if o.type == 'MESH']
print("IMPORTED", len(ms))
def bb(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
info=[]
for ob in ms:
    mn,mx = bb(ob)
    info.append({"name":ob.name,"tris":len(ob.data.polygons),
                 "size":[round(mx.x-mn.x,2),round(mx.y-mn.y,2),round(mx.z-mn.z,2)],
                 "center":[round((mn.x+mx.x)/2,2),round((mn.y+mx.y)/2,2),round((mn.z+mx.z)/2,2)],
                 "zmin":round(mn.z,2)})
info.sort(key=lambda d:-d["tris"])
json.dump(info, open("ref_inventory.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
for d in info[:16]:
    print(f'{d["tris"]:8d}  {d["name"][:26]:26s} size={d["size"]} center={d["center"]}')
# 全局范围
allmn=Vector((1e9,)*3); allmx=Vector((-1e9,)*3)
for ob in ms:
    mn,mx=bb(ob)
    for i in range(3):
        allmn[i]=min(allmn[i],mn[i]); allmx[i]=max(allmx[i],mx[i])
print("SCENE_BOUNDS", [round(v,1) for v in allmn], [round(v,1) for v in allmx])
