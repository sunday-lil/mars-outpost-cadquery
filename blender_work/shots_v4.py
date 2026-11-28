import bpy, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
scene = bpy.context.scene
scene.render.resolution_x = 1920; scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 128
cd = bpy.data.objects.get("C")
if cd is None:
    cdat = bpy.data.cameras.new("C"); cd = bpy.data.objects.new("C", cdat)
    bpy.context.collection.objects.link(cd)
scene.camera = cd
cd.data.clip_end = 20000
def look(pos, tgt, lens):
    cd.data.lens = lens
    z = (Vector(pos) - Vector(tgt)).normalized(); up = Vector((0,0,1))
    x = up.cross(z).normalized(); y = z.cross(x).normalized()
    M = Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cd.location = M.to_translation(); cd.rotation_mode='QUATERNION'
    cd.rotation_quaternion = M.to_quaternion()
shots = [
    ((-330,-390,210), (-10,-15,45), 38, "v4_overview"),
    ((-205,55,52),    (-122,122,14), 45, "v4_dome"),
    ((10,-250,58),    (64,-138,22), 45, "v4_isru"),
    ((-215,-160,70),  (-146,-62,55), 42, "v4_comms"),
]
for pos,tgt,lens,name in shots:
    look(pos,tgt,lens)
    scene.render.filepath = os.path.join(EXPORTS, f"{name}.png")
    bpy.ops.render.render(write_still=True)
print("V4_OK")
