import bpy, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
scene = bpy.context.scene
scene.render.resolution_x = 480; scene.render.resolution_y = 270
scene.eevee.taa_render_samples = 8
cam = bpy.data.objects["C"]
def look(pos,tgt,lens):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=M.to_quaternion()
look((-250,-320,150),(-30,0,60),58)
out = os.path.join(HERE, "_calib.png")
for expo in (-0.4, -1.0, -1.6):
    scene.view_settings.exposure = expo
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("EXPO", expo, "->", out)
