import bpy, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 128
scene.render.image_settings.file_format = 'PNG'
cd = bpy.data.cameras.new("C"); cd.lens=50; cd.clip_end=20000
cam = bpy.data.objects.new("C", cd); bpy.context.collection.objects.link(cam); scene.camera=cam
def look(pos,tgt,lens):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=M.to_quaternion()
for pos,tgt,lens,name in [
    ((-250,-320,150),(-30,0,60),58,"v3_hero"),
    ((-78,-155,88), (-30,0,58),52,"v3_ring"),
    ((160,-330,190),(0,0,40), 42,"v3_site"),
]:
    look(pos,tgt,lens)
    scene.render.filepath=os.path.join(EXPORTS,f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("V3C_OK")
