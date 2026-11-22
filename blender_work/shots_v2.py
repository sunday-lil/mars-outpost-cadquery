import bpy, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
scene = bpy.context.scene
w = bpy.data.worlds.new("MarsSky"); scene.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
sk = nt.nodes.new("ShaderNodeTexSky")
sk.sky_type='MULTIPLE_SCATTERING'; sk.sun_elevation=math.radians(20)
sk.sun_rotation=math.radians(205); sk.altitude=1200.0
sk.air_density=0.9; sk.aerosol_density=4.5
mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type='MULTIPLY'
mul.inputs["Fac"].default_value=1.0; mul.inputs["Color2"].default_value=(1.06,0.60,0.40,1)
nt.links.new(sk.outputs["Color"], mul.inputs["Color1"])
mx = nt.nodes.new("ShaderNodeMixRGB"); mx.inputs["Fac"].default_value=0.30
mx.inputs["Color2"].default_value=(0.60,0.34,0.20,1)
nt.links.new(mul.outputs["Color"], mx.inputs["Color1"])
nt.links.new(mx.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value=0.45
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
sd = bpy.data.lights.new("SunV2",'SUN'); sd.energy=4.2; sd.angle=math.radians(1.0)
sd.color=(1.0,0.93,0.82)
sun = bpy.data.objects.new("SunV2", sd); bpy.context.collection.objects.link(sun)
sun.rotation_euler=(Vector((0,0,0))-Vector((0.42,-0.55,0.58)).normalized()).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=64
scene.render.resolution_x=1920; scene.render.resolution_y=1080
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Punchy'
scene.view_settings.exposure=0.35
cd = bpy.data.cameras.new("C"); cd.lens=50; cd.clip_end=9000
cam = bpy.data.objects.new("C", cd); bpy.context.collection.objects.link(cam); scene.camera=cam
def look(pos,tgt,lens):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=M.to_quaternion()
for pos,tgt,lens,name in [
    ((-150,-210,95),(-12,0,30),42,"v2_hero"),
    ((-40,-120,42), (-12,0,30),38,"v2_ring"),
    ((60,-150,70),  (0,0,25),  40,"v2_site"),
]:
    look(pos,tgt,lens)
    scene.render.filepath=os.path.join(EXPORTS,f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("V2_SHOTS_OK")
