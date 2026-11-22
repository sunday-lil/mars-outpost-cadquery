import bpy, math
from mathutils import Vector
ring = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith("居住穹顶"))
vs = [ring.matrix_world @ v.co for v in ring.data.vertices]
# 环平面：先看主轴跨度，找出"环所在的两个轴"
xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
print("SPAN x=%.1f y=%.1f z=%.1f" % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)))
cx = (max(xs)+min(xs))/2; cz = (max(zs)+min(zs))/2
r = [math.hypot(v.x-cx, v.z-cz) for v in vs]   # 假定环在 XZ 平面
r.sort()
print("ROUTER %.1f  RMEDIAN %.1f" % (r[-1], r[len(r)//2]))
tube = (max(ys)-min(ys))/2
print("TUBE %.2f" % tube)
R = r[-1] - tube
om = math.sqrt(3.72/R)
print("R=%.1f  omega=%.4f rad/s  rpm=%.2f  hoop=%.2f MPa  g_at_R=%.2f" % (R, om, om*60/(2*math.pi), 7850*3.72*R/1e6, om*om*R))
