import bpy, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(bpy.data.filepath)
EXPORTS = os.path.abspath(os.path.join(HERE, "..", "exports"))
scene = bpy.context.scene

# 黄昏天空：太阳压到 5°，天空转红紫
w = bpy.data.worlds.new("MarsDusk"); scene.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.44
ramp.color_ramp.elements[0].color = (0.50, 0.16, 0.07, 1)     # 地平线暗红
e = ramp.color_ramp.elements.new(0.50); e.color = (0.72, 0.30, 0.12, 1)
ramp.color_ramp.elements[1].position = 0.92
ramp.color_ramp.elements[1].color = (0.06, 0.05, 0.10, 1)     # 天顶深紫
madd = nt.nodes.new("ShaderNodeMath"); madd.operation = 'MULTIPLY_ADD'
madd.inputs[1].default_value = 0.5
madd.inputs[2].default_value = 0.5
nt.links.new(sep.outputs["Z"], madd.inputs[0])
nt.links.new(madd.outputs["Value"], ramp.inputs["Fac"])
sun_dir = Vector((0.55, -0.72, 0.09)).normalized()
dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
dot.inputs[1].default_value = sun_dir
nt.links.new(tc.outputs["Generated"], dot.inputs[0])
core = nt.nodes.new("ShaderNodeMath"); core.operation = 'POWER'; core.inputs[1].default_value = 400.0
nt.links.new(dot.outputs["Value"], core.inputs[0])
halo = nt.nodes.new("ShaderNodeMath"); halo.operation = 'POWER'; halo.inputs[1].default_value = 6.0
nt.links.new(dot.outputs["Value"], halo.inputs[0])
hs = nt.nodes.new("ShaderNodeMath"); hs.operation = 'MULTIPLY'; hs.inputs[1].default_value = 0.6
nt.links.new(halo.outputs["Value"], hs.inputs[0])
s1 = nt.nodes.new("ShaderNodeMath"); s1.operation = 'ADD'
nt.links.new(core.outputs["Value"], s1.inputs[0]); nt.links.new(hs.outputs["Value"], s1.inputs[1])
tint = nt.nodes.new("ShaderNodeMixRGB"); tint.blend_type='MULTIPLY'; tint.inputs["Fac"].default_value=1.0
tint.inputs["Color1"].default_value = (1.0, 0.55, 0.25, 1)
nt.links.new(s1.outputs["Value"], tint.inputs["Color2"])
add = nt.nodes.new("ShaderNodeMixRGB"); add.blend_type='ADD'; add.inputs["Fac"].default_value=1.0
nt.links.new(ramp.outputs["Color"], add.inputs["Color1"])
nt.links.new(tint.outputs["Color"], add.inputs["Color2"])
nt.links.new(add.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.55
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

# 太阳：低角度暖光
for ob in bpy.data.objects:
    if ob.type == 'LIGHT' and ob.name in ("KeySun", "DustSun"):
        ob.rotation_euler = (Vector((0,0,0)) - sun_dir).to_track_quat('-Z','Y').to_euler()
        ob.data.energy = 3.2 if ob.name == "KeySun" else 0.8
        ob.data.color = (1.0, 0.62, 0.35)

# 舷窗灯加强
m = bpy.data.materials.get("V3_WinLamp")
if m:
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs["Emission Strength"].default_value = 26.0

scene.view_settings.exposure = -0.35
scene.eevee.taa_render_samples = 128
cd = bpy.data.cameras.new("DuskCam"); cd.lens=45; cd.clip_end=20000
cam = bpy.data.objects.new("DuskCam", cd); bpy.context.collection.objects.link(cam); scene.camera=cam
def look(pos,tgt,lens):
    cam.data.lens=lens
    z=(Vector(pos)-Vector(tgt)).normalized(); up=Vector((0,0,1))
    x=up.cross(z).normalized(); y=z.cross(x).normalized()
    M=Matrix(((x.x,y.x,z.x,pos[0]),(x.y,y.y,z.y,pos[1]),(x.z,y.z,z.z,pos[2]),(0,0,0,1)))
    cam.location=M.to_translation(); cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=M.to_quaternion()

for pos,tgt,lens,name in [
    ((-230,-300,90),(-30,0,55),55,"v3_dusk"),
    ((-70,-150,72), (-30,0,52),50,"v3_dusk_ring"),
]:
    look(pos,tgt,lens)
    scene.render.filepath=os.path.join(EXPORTS,f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("DUSK_OK")
