import bpy, json, os, bmesh
from mathutils import Vector
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
def bbox(ob):
    pts=[ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
qa={"objects":0,"deformed":[],"overlaps":[]}
ms=[o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith(("TERRAIN","FX_"))]
qa["objects"]=len(ms)
for ob in ms:
    bm=bmesh.new(); bm.from_mesh(ob.data)
    z=sum(1 for f in bm.faces if f.calc_area()<1e-8)
    bm.free()
    if z: qa["deformed"].append({"name":ob.name,"zero_area":z})
for i in range(len(ms)):
    for j in range(i+1,len(ms)):
        a,b=ms[i],ms[j]
        amn,amx=bbox(a); bmn,bmx=bbox(b)
        ox=min(amx.x,bmx.x)-max(amn.x,bmn.x); oy=min(amx.y,bmx.y)-max(amn.y,bmn.y); oz=min(amx.z,bmx.z)-max(amn.z,bmn.z)
        if ox>0 and oy>0 and oz>0 and ox*oy*oz>200:
            qa["overlaps"].append({"a":a.name,"b":b.name,"m3":round(ox*oy*oz,1)})
json.dump(qa, open(os.path.join(EXPORTS,"qa_report.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("QA objects=%d deformed=%d overlaps=%d" % (qa["objects"], len(qa["deformed"]), len(qa["overlaps"])))
bpy.ops.object.select_all(action='DESELECT')
for o in ms: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(EXPORTS,"mars_outpost_v3.glb"),
                          export_format='GLB', use_selection=True, export_apply=True,
                          export_yup=True, export_materials='EXPORT')
p=os.path.join(EXPORTS,"mars_outpost_v3.glb")
print("GLB %.1f MB" % (os.path.getsize(p)/1e6))
