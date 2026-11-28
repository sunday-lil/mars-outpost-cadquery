import bpy, os
from mathutils import Vector, Matrix
HERE=os.path.dirname(bpy.data.filepath); E=os.path.abspath(os.path.join(HERE,"..","exports"))
sc=bpy.context.scene
sc.render.resolution_x=1920; sc.render.resolution_y=1080; sc.render.resolution_percentage=100
sc.eevee.taa_render_samples=128
cam=bpy.data.objects.get("C"); sc.camera=cam; cam.data.clip_end=20000
def look(pos,tgt,lens):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=M.to_quaternion()
for pos,tgt,lens,name in [((-133.7,60,26),(-133.7,141.7,14),40,"v4_dome"),
                          ((-133.7,110,9),(-133.7,141.7,8),35,"v4_dome_in"),
                          ((-330,-390,210),(-10,-15,45),38,"v4_overview")]:
    look(pos,tgt,lens)
    sc.render.filepath=os.path.join(E,name+".png")
    bpy.ops.render.render(write_still=True)
print("DOME_SHOTS_OK")
