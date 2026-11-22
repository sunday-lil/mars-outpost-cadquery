import bpy, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
scene = bpy.context.scene
# 火星天空（新建 world，不删物体）
w = bpy.data.worlds.new("MarsSky"); scene.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type='MULTIPLE_SCATTERING'; sky.sun_elevation=math.radians(15)
sky.sun_rotation=math.radians(205); sky.altitude=1200.0
sky.air_density=0.8; sky.aerosol_density=4.0
mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type='MULTIPLY'
mul.inputs["Fac"].default_value=1.0; mul.inputs["Color2"].default_value=(1.06,0.58,0.38,1)
nt.links.new(sky.outputs["Color"], mul.inputs["Color1"])
mix = nt.nodes.new("ShaderNodeMixRGB"); mix.inputs["Fac"].default_value=0.32
mix.inputs["Color2"].default_value=(0.58,0.33,0.20,1)
nt.links.new(mul.outputs["Color"], mix.inputs["Color1"])
nt.links.new(mix.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value=0.30
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=64
scene.render.resolution_x=1920; scene.render.resolution_y=1080
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Punchy'
scene.view_settings.exposure=0.35

cd = bpy.data.cameras.new("ShotCam"); cd.lens=55; cd.clip_end=6000
cam = bpy.data.objects.new("ShotCam", cd)
bpy.context.collection.objects.link(cam); scene.camera = cam

def look_at(pos, tgt, lens=55):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=M.to_quaternion()

for pos,tgt,lens,name in [
    ((-92,-118,52),(-12,0,26),60,"up_hero"),
    ((-30,-52,30),(-12,0,26),45,"up_ring"),
    ((0,-150,120),(0,0,10),50,"up_top"),
]:
    look_at(pos,tgt,lens)
    scene.render.filepath=os.path.join(EXPORTS,f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("UP_RENDER_OK")
