"""受控实验：同一材质、同朝向两块平板 → 色差应为 0；
   同一材质、不同朝向 → 色差应由光照造成。
   用于判定之前的 Δ 到底来自材质还是几何。"""
import bpy, os, math
from mathutils import Vector
HERE = "/".join(bpy.data.filepath.split("/")[:-1])
SW = os.path.join(HERE, "sw"); os.makedirs(SW, exist_ok=True)
scene = bpy.context.scene
scene.render.resolution_x = 128; scene.render.resolution_y = 128
scene.eevee.taa_render_samples = 24
cam = scene.camera
mat = bpy.data.materials.get("R2_Hull")

made = []
def plane(loc, rot, name):
    bpy.ops.mesh.primitive_plane_add(size=20, location=loc, rotation=rot)
    ob = bpy.context.object; ob.name = name
    ob.data.materials.append(mat)
    made.append(ob)
    return ob

def shot(ob, tag):
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = (o is not ob)
    c = ob.location
    cam.location = c + Vector((0, -40, 0))
    d = (c - cam.location).normalized()
    cam.rotation_mode='QUATERNION'; cam.rotation_quaternion = d.to_track_quat('-Z','Y')
    cam.data.lens = 50
    p = os.path.join(SW, tag + ".png")
    scene.render.filepath = p
    bpy.ops.render.render()
    bpy.data.images["Render Result"].save_render(p, scene=scene)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = False
    return p

a = plane((-400, -400, 60), (math.radians(90), 0, 0), "PROBE_A")   # 同朝向
b = plane((-360, -400, 60), (math.radians(90), 0, 0), "PROBE_B")
c = plane((-320, -400, 60), (math.radians(35), 0, math.radians(40)), "PROBE_C")  # 不同朝向
shot(a, "ctrl_A"); shot(b, "ctrl_B"); shot(c, "ctrl_C")
print("CTRL_OK")
