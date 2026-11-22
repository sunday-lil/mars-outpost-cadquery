"""把场平垫半径扩到 420 m：所有设施都在绝对水平的地面上，消除悬空/陷地。"""
import bpy, bmesh, math
from mathutils import Vector, noise
HERE = "/".join(bpy.data.filepath.split("/")[:-1])

ter = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(("火星地形","TERRAIN")))
PAD_R, BLEND_R = 420.0, 560.0
CR = []
import random
rnd = random.Random(2027)
for _ in range(54):
    cr = rnd.uniform(10, 95)
    CR.append((rnd.uniform(-560,560), rnd.uniform(-560,560), cr, cr*rnd.uniform(0.04,0.10)))

def h_raw(x,y):
    z  = noise.noise(Vector((x/320.0, y/320.0, 0.5))) * 10.0
    z += noise.noise(Vector((x/96.0,  y/96.0,  3.3))) * 3.2
    z += noise.noise(Vector((x/24.0,  y/24.0,  8.7))) * 0.8
    z += noise.noise(Vector((x/5.5,   y/5.5,  15.1))) * 0.18
    for (cx,cy,cr,dp) in CR:
        d = math.hypot(x-cx, y-cy)
        if d < cr*2.0:
            t = d/cr
            if t < 1.0: z -= dp*(1-t*t)
            z += dp*0.5*math.exp(-((t-1.05)**2)/0.02)
    return z

def h(x,y):
    r = math.hypot(x,y)
    if r <= PAD_R: w = 0.0
    elif r >= BLEND_R: w = 1.0
    else:
        t = (r-PAD_R)/(BLEND_R-PAD_R); w = t*t*(3-2*t)
    return h_raw(x,y)*w

me = ter.data
n = 0
for v in me.vertices:
    v.co.z = h(v.co.x, v.co.y)
    n += 1
me.update()
print("PAD_FLATTENED verts", n)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("PAD_OK")
