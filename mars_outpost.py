# -*- coding: utf-8 -*-
"""
====================================================================
  作品名称：《赤星前哨 · 火星科研站》(Mars Research Outpost)
  参赛赛项：探秘火星逐梦太空（智能算法编程类 · 三维设计项目）
  参赛组别：初中组        建模软件：CadQuery（Python 参数化建模）
====================================================================
  设计理念
  --------
  以 2030 年代火星科考前哨站为蓝图，按功能分区构建有机连通的综合基地：
  核心科研区(穹顶+实验舱+廊道)、能源区(太阳能翼阵)、
  通信区(深空通信塔+大口径抛物面天线)、发射区(着陆平台+火箭+离子推进器)、
  探测区(六轮火星车)、环境监测区(综合气象站)。
  连接道路贯穿各区域, 形成完整的基地运维生态。

  ── 阶段一: 离子推进器动力总成(集成于火箭动力段) ──
  24 槽全向辐射散热格栅(倾斜 15° 百叶窗式), 依据斯蒂芬-玻尔兹曼
  热辐射定律设计; CadQuery 批量布尔差集(cut)高效算法; 刀具两端
  预留 1mm 贯通容差修复 Z-Fighting, 100% 水密交付。

  ── 阶段二: 深空通信系统(集成于通信塔顶) ──
  旋转抛物面高增益天线, 严谨推导 z = r²/(4f) 微积分方程, 微积分
  点集离散采样生成壁厚 2mm 反射体, 外缘法兰圈加固; 焦点馈源为
  两圆截面 loft 放样的锥台喇叭(内置 Ø8×12mm 微波谐振腔), 三根
  锥形支撑臂按 120° 极坐标阵列悬固; X 波段(8.4GHz)深空通信链路
  增益核算(dBi), 导出高精度 STL。

  核心算法：极坐标放置、三角函数定向斜杆、椭圆参数方程旋转成穹顶、
  抛物线 z=r²/(4f) 微积分推导 + 旋转成抛物面天线、
  多截面放样 loft(馈源喇叭锥台 / 根粗端细的锥形支撑臂)、
  斯蒂芬-玻尔兹曼热辐射定律 → 百叶窗散热格栅、
  CadQuery 批量布尔差集 + Z-Fighting 贯通容差修复、
  随机数撒布岩石(固定种子可复现)、
  太阳能板倾角 = 90° − 太阳高度角(自动对日)。

  ── 程序化纹理贴图(纯标准库) ──
  6 种程序化纹理: 火星地表(fBm噪声)、金属面板(拉丝+铆钉)、
  太阳能板(网格)、火箭壳体(条纹)、抛物面反射器(同心圆)、
  压痕路径(车辙)。fBm 值噪声 + PNG 编码(zlib), 嵌入 GLB
  作为 baseColorTexture, 平面投影 UV 自动生成。

  使用说明
  --------
  1. 运行:  python mars_outpost.py
  2. 输出(exports/ 目录):
     - mars_outpost.step   带彩色分层的工程交换文件
     - mars_outpost.glb    Blender 即开即用, 含 PBR 材质
                           (金属度/粗糙度/自发光, 由 MATERIALS 表驱动)
     - mars_outpost.stl    整体网格
     - parabolic_dish_reflector.stl  高精度抛物面反射器
     - view_iso/top/front.svg  三视角工程线框图
  3. 全站参数化: 修改【参数区】常数(如 SUN_ELEV 太阳高度角)
     模型自动重建, 太阳能板与天线指向随之自动更新。
====================================================================
"""
import json
import math
import random
import re
import struct
import zlib

import cadquery as cq

# =====================================================================
# 一、参数区（改这里, 全站自动重建）
# =====================================================================
BASE_R, BASE_H = 300, 14           # 火星基座半径 / 厚度
DOME_R, DOME_H, DOME_RIBS = 80, 60, 10   # 穹顶半径 / 矢高 / 肋数
LAB_R, LAB_L = 32, 120             # 实验舱半径 / 长度
SUN_ELEV, PANEL_N = 35, 4          # 太阳高度角(度) / 太阳能板数
TOWER_H, DISH_D, EARTH_ELEV = 190, 120, 40   # 塔高 / 大天线口径 / 对地仰角
ROCKET_H = 210                     # 返回火箭主体(机身段+整流罩)总高
ROCK_SEED, ROCK_N = 2026, 20       # 岩石随机种子 / 数量

# --- 阶段一: 离子推进器动力总成 + 24 槽散热格栅 ---
ION_BODY_R, ION_BODY_L = 28, 85     # 推进器机身半径 / 长度
ION_NOZZLE_R, ION_NOZZLE_L = 18, 40 # 加速器喷管半径 / 长度
GRILL_SLOTS = 24                    # 散热格栅槽数(24 组刀具体圆周阵列)
GRILL_TILT = 15                     # 百叶窗倾斜角(度)——斯蒂芬-玻尔兹曼热辐射优化
GRILL_R_OUT, GRILL_R_IN = 42, 30   # 散热套外/内半径
GRILL_H = 60                        # 散热套高度
GRILL_BLADE_W = 3                   # 单个切削刀片宽度
GRILL_TOLERANCE = 1                 # Z-Fighting 容差: 刀片两端贯通预留(mm)

# --- 阶段二: 旋转抛物面高增益天线(集成于深空通信塔) ---
DISH_F = 45                         # 抛物面焦距 f(mm), z = r²/(4f)
DISH_WALL = 2                       # 反射体壁厚(mm)
DISH_FLANGE_W = 6                   # 法兰圈宽度
DISH_FLANGE_T = 4                   # 法兰圈厚度
DISH_SAMPLE_N = 48                  # 微积分点集离散采样数
X_BAND_FREQ = 8.4e9                 # X 波段中心频率(Hz)

# --- 焦点馈源喇叭(多截面放样 loft + 微波谐振腔) ---
FEED_R_BACK, FEED_R_APERTURE = 6.0, 12.0   # 喉部(焦点处)半径 / 喇叭口半径
FEED_H = 16.0                              # 喇叭轴向高度
FEED_HOLE_D, FEED_HOLE_DEPTH = 8.0, 12.0   # 谐振腔直径 / 深度(留 4mm 金属封底)
FEED_ARM_R0, FEED_ARM_R1 = 1.8, 1.2        # 支撑臂根部 / 端部半径(锥形杆)

# 各系统落位(x, y) —— 按功能分区:
#   核心科研区(穹顶+实验舱+廊道): 中央
#   能源区(太阳能翼阵): 南侧
#   通信区(深空通信塔+大天线): 东北
#   发射区(着陆平台+火箭+离子推进器): 东南
#   探测区(火星车): 西南
#   环境监测区(气象站): 西北
POS_DOME, POS_LAB = (-60, 0), (68, 0)
POS_TOWER, POS_ROVER = (95, 150), (75, -120)
POS_ROCKET, POS_WEATHER = (195, 105), (-160, 100)
POS_SOLAR = (-156, -190)

# =====================================================================
# 二、材质表（glTF 2.0 PBR 参数, Blender 原生识别）
#   color: 基色RGB   metal: 金属度   rough: 粗糙度   emissive: 自发光
# =====================================================================
MATERIALS = {
    "火星地形":   {"color": (0.72, 0.35, 0.22), "metal": 0.00, "rough": 0.95},
    "火星岩石":   {"color": (0.32, 0.17, 0.11), "metal": 0.00, "rough": 0.90},
    "居住穹顶":   {"color": (0.95, 0.95, 0.93), "metal": 0.05, "rough": 0.25},
    "穹顶肋":     {"color": (0.75, 0.77, 0.80), "metal": 0.60, "rough": 0.40},
    "观察舷窗":   {"color": (0.15, 0.35, 0.55), "metal": 0.30, "rough": 0.08},
    "顶部信标":   {"color": (1.00, 0.08, 0.05), "metal": 0.00, "rough": 0.20,
                   "emissive": (1.0, 0.05, 0.02)},
    "科研实验舱": {"color": (0.82, 0.84, 0.87), "metal": 0.80, "rough": 0.30},
    "加压廊道":   {"color": (0.60, 0.62, 0.65), "metal": 0.50, "rough": 0.45},
    "太阳能板":   {"color": (0.07, 0.14, 0.45), "metal": 0.40, "rough": 0.15},
    "能源边框":   {"color": (0.85, 0.62, 0.18), "metal": 0.90, "rough": 0.35},
    "塔架":       {"color": (0.55, 0.57, 0.60), "metal": 0.70, "rough": 0.50},
    "火星车体":   {"color": (0.90, 0.88, 0.84), "metal": 0.30, "rough": 0.40},
    "车轮":       {"color": (0.25, 0.25, 0.27), "metal": 0.20, "rough": 0.80},
    "着陆平台":   {"color": (0.45, 0.47, 0.50), "metal": 0.50, "rough": 0.60},
    "返回火箭":   {"color": (0.85, 0.87, 0.90), "metal": 0.85, "rough": 0.20},
    "发动机喷管": {"color": (0.35, 0.33, 0.30), "metal": 0.95, "rough": 0.30},
    "气象站":     {"color": (0.93, 0.93, 0.91), "metal": 0.20, "rough": 0.40},
    # 离子推进器(集成于火箭动力段)
    "推进器机身": {"color": (0.78, 0.80, 0.83), "metal": 0.90, "rough": 0.25},
    "加速器喷管": {"color": (0.30, 0.28, 0.25), "metal": 0.95, "rough": 0.35},
    "散热格栅":   {"color": (0.65, 0.67, 0.70), "metal": 0.85, "rough": 0.30},
    # 深空通信(集成于通信塔)
    "抛物面反射器": {"color": (0.95, 0.95, 0.97), "metal": 0.60, "rough": 0.12},
    "天线馈源臂": {"color": (0.70, 0.72, 0.75), "metal": 0.75, "rough": 0.30},
    # 连接道路
    "压痕路径":   {"color": (0.55, 0.28, 0.18), "metal": 0.00, "rough": 0.98},
}
M_DEFAULT = {"color": (0.7, 0.7, 0.7), "metal": 0.1, "rough": 0.5}


def mat_of(name):
    """按零件名取材质参数。"""
    return MATERIALS.get(name, M_DEFAULT)


# =====================================================================
# 三、工具函数（复用核心）
# =====================================================================
def polar(part, radius, angle_deg, z=0.0):
    """极坐标放置: 把零件摆到 (半径, 方位角) 处。"""
    a = math.radians(angle_deg)
    return part.translate((radius * math.cos(a), radius * math.sin(a), z))


def strut(p0, p1, r, r_end=None):
    """连接空间两点的斜杆(三角函数定向)。

    只给 r: 等径圆柱杆(塔柱/悬架/着陆腿);
    再给 r_end: 两端各画一个圆截面做 loft 放样, 得到根粗端细的锥形杆件
    (馈源支撑臂用这种桁架杆更贴近真实受力结构)。
    """
    dx, dy, dz = (p1[i] - p0[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if r_end is None:
        body = cq.Workplane("XY").circle(r).extrude(length)
    else:
        body = (cq.Workplane("XY").circle(r)
                .workplane(offset=length).circle(r_end).loft())
    return (
        body
        .rotate((0, 0, 0), (0, 1, 0), math.degrees(math.atan2(math.hypot(dx, dy), dz)))
        .rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(dy, dx)))
        .translate(p0)
    )


def post(r, h):
    """竖直圆柱快捷方式。"""
    return cq.Workplane("XY").circle(r).extrude(h)


def revolve_z(builder):
    """XZ 轮廓(x=半径, z=高度)绕 Z 轴转 → 竖直旋转体(穹顶/天线/喷管)。

    注意: Workplane.revolve 的轴参数是"工作平面局部坐标"——
    Workplane("XZ") 的局部 y 方向恰好映射为全局 Z, 故传 (0,±1,0)。
    """
    return builder.revolve(360, (0, -1, 0), (0, 1, 0))


def ell_arc(ra, h, n=7):
    """椭圆参数方程采样: 从顶点(0,h)到边缘(ra,0)的弧线点列。

    x = ra·sin(t), z = h·cos(t),  t: 0°→90°
    """
    return [(ra * math.sin(math.radians(t)), h * math.cos(math.radians(t)))
            for t in (i * 90 / n for i in range(n + 1))]


def compound_of(shapes):
    """零件列表 → 复合体(自动把 Workplane 转成 Shape)。"""
    solids = [s.val() if isinstance(s, cq.Workplane) else s for s in shapes]
    return cq.Compound.makeCompound(solids)


# =====================================================================
# 四、各子系统建模(每个函数返回 [(材质名, 实体), ...])
# =====================================================================
def build_terrain():
    """火星地表: 两层圆台 + 环形山 + 随机坑洼鼓包(起伏) + 岩石碎石层。

    起伏算法: 随机撒浅球鼓包(半埋露出 2.5~6mm) + 微型环形山坑,
    固定种子可复现; 全部零布尔叠加, 稳定不翻车。
    """
    base = (
        cq.Workplane("XY").circle(BASE_R).extrude(BASE_H * 0.55)
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(BASE_R * 0.93).extrude(BASE_H * 0.45)
        .edges(">Z").fillet(6)
    )
    for cx, cy, cr in [(-195, 165, 46), (205, -175, 38), (-70, -235, 30)]:
        rim = cq.Solid.makeTorus(cr * 0.8, cr * 0.22).translate((cx, cy, BASE_H))
        pit = post(cr * 0.55, 1.5).translate((cx, cy, BASE_H + 1))
        base = base.union(rim).union(pit)

    rng = random.Random(ROCK_SEED)
    # 岩石禁布区: 各系统落位附近(避免穿模)
    keep_out = [
        (*POS_DOME, 130), (*POS_LAB, 130), (*POS_TOWER, 60),
        (*POS_ROVER, 80), (*POS_ROCKET, 140), (*POS_WEATHER, 50),
        (*POS_SOLAR, 150),
    ]
    rocks = []
    while len(rocks) < ROCK_N:
        ang, dist = rng.uniform(0, 360), rng.uniform(120, BASE_R - 30)
        x = dist * math.cos(math.radians(ang))
        y = dist * math.sin(math.radians(ang))
        if all(math.hypot(x - kx, y - ky) > kr for kx, ky, kr in keep_out):
            size = rng.uniform(6, 16)
            rock = (
                cq.Workplane("XY").box(size, size * 0.8, size * 0.6)
                .edges("|Z").fillet(size * 0.3)
                .edges(">Z").fillet(size * 0.2)
            )
            rocks.append(rock.val().translate((x, y, BASE_H)))

    # 碎石层: 40 颗细小砾石, 增强地表颗粒粗糙感
    chips = []
    while len(chips) < 40:
        ang, dist = rng.uniform(0, 360), rng.uniform(100, BASE_R - 15)
        x = dist * math.cos(math.radians(ang))
        y = dist * math.sin(math.radians(ang))
        if all(math.hypot(x - kx, y - ky) > kr * 0.9
               for kx, ky, kr in keep_out):
            size = rng.uniform(2.5, 4.5)
            chips.append(cq.Solid.makeBox(
                size, size * 0.8, size * 0.5,
                cq.Vector(x - size / 2, y - size * 0.4, BASE_H)))

    # 地表起伏: 36 处零布尔叠加——鼓包(浅球贴地) + 坑洼(微型环形山环+坑底)
    # (批量 fuse/cut 会产生畸形体, 叠加方案稳定且视觉效果相同)
    rng2 = random.Random(ROCK_SEED + 1)
    relief = []
    attempts = 0
    while len(relief) < 36 and attempts < 600:
        attempts += 1
        ang, dist = rng2.uniform(0, 360), rng2.uniform(55, BASE_R - 25)
        x = dist * math.cos(math.radians(ang))
        y = dist * math.sin(math.radians(ang))
        # 起伏很浅, 禁布区按 0.7 倍收缩(允许贴近建筑)
        if not all(math.hypot(x - kx, y - ky) > kr * 0.7
                   for kx, ky, kr in keep_out):
            continue
        r = rng2.uniform(9, 22)
        if rng2.random() < 0.5:                     # 鼓包: 半埋浅球
            h = rng2.uniform(2.5, 6)                # 露出高度
            relief.append(cq.Solid.makeSphere(
                r, cq.Vector(x, y, BASE_H - r + h)))
        else:                                        # 坑: 微型环形山
            relief.append(cq.Solid.makeTorus(
                r * 0.75, r * 0.16).translate((x, y, BASE_H)))
            relief.append(cq.Solid.makeCylinder(
                r * 0.5, 1.2).translate((x, y, BASE_H)))   # 坑底
    return [("火星地形", compound_of([base] + relief)),
            ("火星岩石", compound_of(rocks + chips))]


def build_dome():
    """穹顶壳(椭圆参数方程+旋转) + 极向肋 + 环带 + 舷窗 + 信标 + 气闸。"""
    # 壳体: 椭圆弧 x=R·sin(t), z=H·cos(t) 采样 → 样条 → 绕 Z 旋转
    shell = revolve_z(
        cq.Workplane("XZ").moveTo(0, DOME_H)
        .spline(ell_arc(DOME_R, DOME_H)[1:])       # 椭圆弧: 顶→(R,0)
        .lineTo(DOME_R, -4).lineTo(0, -4).close()
    )
    # ── 舷窗几何(先算出来: 肋上的球链要避开窗口, 否则球会扣在窗里) ──
    WIN_AZ = (120, 180, 240)
    win_z = DOME_H * 0.42
    win_rho = DOME_R * math.sin(math.acos(win_z / DOME_H))
    nx, nz = win_rho / DOME_R ** 2, win_z / DOME_H ** 2   # 椭球法线的水平/竖直分量
    nl = math.hypot(nx, nz)
    nx, nz = nx / nl, nz / nl
    win_bases = [(win_rho * math.cos(math.radians(a)),
                  win_rho * math.sin(math.radians(a)), win_z) for a in WIN_AZ]

    # 经向肋: 沿椭圆弧的球链拱(格构式外骨架, 零布尔运算), 旋转阵列
    def dome_rib_chain(alpha_deg):
        a = math.radians(alpha_deg)
        balls = []
        for tdeg in range(4, 90, 7):                     # 顶→边 13 颗球
            t = math.radians(tdeg)
            x = DOME_R * 1.01 * math.sin(t)
            z = DOME_H * 1.01 * math.cos(t) + 2          # 紧贴壳外表面
            px, py = x * math.cos(a), x * math.sin(a)
            if any((px - wx) ** 2 + (py - wy) ** 2 + (z - wz) ** 2 < 8.5 ** 2
                   for wx, wy, wz in win_bases):
                continue                                  # 避让舷窗开孔
            balls.append(cq.Workplane("XY").workplane(offset=z)
                         .sphere(2.8).translate((px, py, 0)).val())
        return compound_of(balls)

    ribs = [dome_rib_chain(i * 360 / DOME_RIBS) for i in range(DOME_RIBS)]
    ribs.append(cq.Solid.makeTorus(DOME_R * 0.80, 2.2).translate((0, 0, DOME_H * 0.38)))
    ribs.append(cq.Solid.makeTorus(DOME_R * 0.56, 2.2).translate((0, 0, DOME_H * 0.68)))
    # 舷窗: 窗筒必须沿"椭球面法线"方向插入——该处法线并非水平, 而是向外上翘
    # 约 32°; 用水平圆柱会一半埋进壳体、一半翘成楔形块
    wins = []
    for base in win_bases:
        ca, sa = base[0] / win_rho, base[1] / win_rho
        n = (nx * ca, nx * sa, nz)                         # 外法线方向
        p0 = tuple(base[i] - n[i] * 2 for i in range(3))   # 埋入壳体 2mm
        p1 = tuple(base[i] + n[i] * 0.8 for i in range(3))  # 只外凸 0.8mm, 做"平嵌窗"
        wins.append(strut(p0, p1, 5))                      # Ø10 舷窗
        # 金属窗框(并入"穹顶肋"材质): 让舷窗有圈口, 而不是贴在壳上的蓝点
        ty = math.degrees(math.atan2(math.hypot(n[0], n[1]), n[2]))
        tz = math.degrees(math.atan2(n[1], n[0]))
        rings = (cq.Solid.makeTorus(5.6, 0.6)
                 .rotate((0, 0, 0), (0, 1, 0), ty)
                 .rotate((0, 0, 0), (0, 0, 1), tz)
                 .translate(base))
        ribs.append(rings)
    # 信标: 杆 + 红灯
    beacon = post(2, 35).translate((0, 0, 50))
    beacon = beacon.union(
        cq.Workplane("XY").workplane(offset=85).sphere(5))
    # 气闸门舱: 竖直圆鼓对接舱, 贴在穹顶侧面
    airlock = (
        post(16, 24).faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(12).extrude(2)
    ).translate((DOME_R - 4, 0, 0))

    shell = shell.union(airlock)
    dx, dy = POS_DOME
    return [
        ("居住穹顶", shell.translate((dx, dy, BASE_H))),
        ("穹顶肋", compound_of([r.translate((dx, dy, BASE_H)) for r in ribs])),
        ("观察舷窗", compound_of([w.translate((dx, dy, BASE_H)) for w in wins])),
        ("顶部信标", beacon.val().translate((dx, dy, BASE_H))),
    ]


def build_lab():
    """实验舱: 圆柱机身 + 两端半球封头 + 加强箍 + 散热鳍 + 支腿。"""
    r, L = LAB_R, LAB_L
    body = (cq.Workplane("YZ").circle(r).extrude(L)      # 机身沿 X
            .union(cq.Workplane("XY").sphere(r))         # 左半球封头
            .union(cq.Workplane("XY").sphere(r).translate((L, 0, 0))))
    hoops = [cq.Workplane("YZ").circle(r + 2.5).circle(r).extrude(5)
             .translate((x, 0, 0)) for x in (L * 0.25, L * 0.5, L * 0.75)]
    fins = (cq.Workplane("XY").workplane(offset=r * 0.92)
            .center(L * 0.5, 0).rarray(14, 1, 5, 1).box(3, 26, 10))
    # 支腿: 从舱底(局部 z=-r-3)伸到地面
    legs = [polar(post(4, 31), r * 0.8, a).translate((0, 0, -r - 3))
            for a in (90, 210, 330)]

    part = body
    for extra in hoops + [fins] + legs:
        part = part.union(extra)
    dx, dy = POS_LAB
    return [("科研实验舱", part.translate((dx, dy, BASE_H + 35)))]


def build_tunnel():
    """加压廊道: 圆环截面沿样条曲线扫掠(截面圆心与路径起点重合)。"""
    # 路径 z 从 0 缓升到 10 再回落(局部坐标), 后面统一抬升
    path = cq.Workplane("XZ").moveTo(20, 0).spline([(55, 10), (95, 10), (128, 0)])
    tube = (cq.Workplane("YZ").workplane(offset=20)
            .circle(14).circle(11).sweep(path))
    ring = (cq.Workplane("YZ").workplane(offset=95)
            .circle(16).circle(11).extrude(6).translate((0, 0, 10)))
    tube = tube.union(ring)
    dx, dy = POS_DOME        # 廊道起点挂在穹顶一侧
    return [("加压廊道", tube.translate((dx, dy, BASE_H + 30)))]


def build_solar():
    """太阳能翼阵: 银色基板框 + 蓝色电池片阵列(5×8), 绕下边缘倾斜。

    倾角 = 90° − 太阳高度角(阳光垂直入射); 电池片间缝隙露出银框,
    远看整片深蓝, 近看是银框分割的电池格——真实光伏板构造。
    """
    tilt = 90 - SUN_ELEV
    w, l = 46, 70
    panels, frames = [], []
    for i in range(PANEL_N):
        x = i * (w + 12)
        # 银色基板(框): 下边缘对齐局部原点(旋转轴), 板向 +Y 铺开
        board = cq.Workplane("XY").box(w, l, 3).translate((0, l / 2, 1.5))
        # 蓝色电池片阵列: 5 列 × 8 行坐在基板上, 缝隙露银框
        cells = (cq.Workplane("XY").workplane(offset=3)
                 .center(0, l / 2).rarray(8.0, 8.4, 5, 8)
                 .box(6.4, 7.2, 1.2))
        panels.append(cells.rotate((0, 0, 0), (1, 0, 0), tilt)
                      .translate((x, 0, 26)))          # 电池片 → 板材质
        frames.append(board.rotate((0, 0, 0), (1, 0, 0), tilt)
                      .translate((x, 0, 26)))          # 基板 → 银框材质
        frames.append(post(3, 26).translate((x, 0, 0)))  # 立柱在板根正下方
    dx, dy = POS_SOLAR
    return [
        ("太阳能板", compound_of([p.translate((dx, dy, BASE_H)) for p in panels])),
        ("能源边框", compound_of([f.translate((dx, dy, BASE_H)) for f in frames])),
    ]


def build_tower():
    """深空通信塔: 三柱桁架 + 环撑 + 大口径抛物面高增益天线(阶段二集成)。

    将阶段二的 ParabolicDishGenerator 大抛物面天线直接集成到塔顶,
    替代原来小口径天线——一座塔, 一套天线, 通信逻辑清晰。
    """
    H, top_r, bot_r = TOWER_H, 8, 26
    # 桁架顶端收在 H-12: 天线盘装在 H-8, 若桁架做到 H, 三根柱顶会从
    # 反射面正中捅出来(在盘面上留下三个小凸柱)
    struts = [strut((bot_r * math.cos(math.radians(a)), bot_r * math.sin(math.radians(a)), 0),
                    (top_r * math.cos(math.radians(a)), top_r * math.sin(math.radians(a)), H - 12), 3)
              for a in (90, 210, 330)]
    rings = [cq.Solid.makeTorus(bot_r + (top_r - bot_r) * f, 1.2)
             .translate((0, 0, H * f))
             for f in (0.15, 0.32, 0.5, 0.68, 0.85)]

    # ── 大口径抛物面天线(阶段二 ParabolicDishGenerator 集成) ──
    # 微积分点集离散采样: z = r²/(4f), 壁厚 2mm, 外缘法兰圈加固
    dish_reflector, feed_arms, feed = ParabolicDishGenerator()

    # 天线整体倾斜对地(指向地球方向), 置于塔顶
    earth_tilt = EARTH_ELEV
    dish_reflector = dish_reflector.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)
    feed_arms = feed_arms.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)
    feed = feed.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)

    dish_group = compound_of([dish_reflector]).translate((0, 0, H - 8))
    feed_group = compound_of([feed_arms, feed]).translate((0, 0, H - 8))

    # 天线盘上不再挂任何警示灯: 桅杆会穿过反射面, 球灯挂在法兰上又会
    # 挡住口径边缘——塔顶警示统一交给穹顶信标, 天线保持"盘+馈源"的干净结构

    dx, dy = POS_TOWER
    return [
        ("塔架", compound_of(struts + rings).translate((dx, dy, BASE_H))),
        ("抛物面反射器", dish_group.translate((dx, dy, BASE_H))),
        ("天线馈源臂", feed_group.translate((dx, dy, BASE_H))),
    ]


def build_rover():
    """火星车: 车身+双目桅杆+机械臂 + 摇臂悬架 + 每侧三轮(轮心共面)。"""
    # 局部坐标: 轮心所在平面 z=0(轮半径 9 → 整体抬高 BASE_H+9 后贴地)
    body = (
        cq.Workplane("XY").box(46, 62, 14).edges("|Z").fillet(6)
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .box(40, 56, 3).translate((0, 0, 2))            # 太阳能甲板 z~-3..11
    )
    mast = post(1.8, 26).translate((0, -22, 11))        # 桅杆 z 11~37
    cam = cq.Workplane("XY").workplane(offset=37).center(0, -22).box(10, 6, 7)
    arm = (cq.Workplane("XZ").center(20, 0).circle(1.5).extrude(16)
           .rotate((0, 0, 0), (0, 0, 1), 40).translate((12, 18, 6)))
    chassis = body.union(mast).union(cam.val()).union(arm)

    def wheel_unit():
        """单轮: 轮心在原点, 轴线沿 Y(转动 90° 后)。"""
        w = (cq.Workplane("XY").circle(9).extrude(3.5, both=True)
             .union(cq.Workplane("XY").circle(3.5).extrude(5, both=True))
             .union(cq.Workplane("XY").circle(9.5).circle(8).extrude(1, both=True)))
        for k in range(12):                              # 12 条抓地齿
            w = w.union(cq.Workplane("XY").box(3.5, 2.5, 15)
                        .translate((8.2, 0, 0))
                        .rotate((0, 0, 0), (0, 0, 1), k * 30))
        return w.rotate((0, 0, 0), (1, 0, 0), 90)

    wheels, rods = [], []
    for side in (-1, 1):                                 # 左右对称
        for wx in (-21, 0, 21):                          # 前中后三轮
            wy = side * 38
            wheels.append(wheel_unit().translate((wx, wy, 0)))
            rods.append(strut((0, side * 28, 8), (wx, wy, 5), 1.6))
    dx, dy = POS_ROVER
    pos = (dx, dy, BASE_H + 9)
    return [
        ("火星车体", compound_of([chassis] + rods).translate(pos)),
        ("车轮", compound_of(wheels).translate(pos)),
    ]


def build_rocket():
    """发射区: 着陆平台(八角+边界灯) + 返回火箭 + 离子推进器动力段(阶段一集成)。

    将阶段一的 24 槽散热格栅 + 收敛-扩张喷管直接作为火箭下方的动力段,
    替代原来重复的化学火箭喷管——一套推进系统, 动力逻辑清晰。
    """
    r_b = 26
    pad = (
        cq.Workplane("XY").polygon(8, 130).extrude(8)
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(60).circle(52).extrude(2)
    )
    lamps = [polar(post(3, 4), 56, a, 8) for a in range(0, 360, 45)]
    for lamp in lamps:
        pad = pad.union(lamp)

    # ── 离子推进器动力段(阶段一集成) ──
    # 24 槽散热格栅: 批量布尔差集, 倾斜 15° 百叶窗, Z-Fighting 1mm 容差
    grill_outer_r, grill_inner_r, grill_h = GRILL_R_OUT, GRILL_R_IN, GRILL_H
    grill_sleeve = (
        cq.Workplane("XY").circle(grill_outer_r).circle(grill_inner_r)
        .extrude(grill_h)
    )
    blade_length = (grill_outer_r - grill_inner_r) + 2 * GRILL_TOLERANCE
    blade = (
        cq.Workplane("XY")
        .box(blade_length, GRILL_BLADE_W, grill_h + 2 * GRILL_TOLERANCE)
        .translate(((grill_outer_r + grill_inner_r) / 2, 0, 0))
    )
    blade_tilted = blade.rotate((0, 0, 0), (1, 0, 0), GRILL_TILT)
    cutters = [blade_tilted.rotate((0, 0, 0), (0, 0, 1), i * 360 / GRILL_SLOTS)
               for i in range(GRILL_SLOTS)]
    for cutter in cutters:
        grill_sleeve = grill_sleeve.cut(cutter)
    # 上下端环密封端口
    grill_sleeve = grill_sleeve.union(
        cq.Workplane("XY").circle(grill_outer_r).circle(grill_inner_r)
        .extrude(3)).union(
        cq.Workplane("XY").circle(grill_outer_r).circle(grill_inner_r)
        .extrude(3).translate((0, 0, grill_h - 3)))
    # 散热格栅环绕火箭下段
    grill_sleeve = grill_sleeve.translate((0, 0, 20))

    # 收敛-扩张离子加速器喷管(旋转体)
    nozzle_profile = [
        (ION_BODY_R * 0.35, 0),
        (ION_NOZZLE_R * 0.55, ION_NOZZLE_L * 0.3),
        (ION_NOZZLE_R * 0.40, ION_NOZZLE_L * 0.5),
        (ION_NOZZLE_R * 0.75, ION_NOZZLE_L * 0.8),
        (ION_NOZZLE_R, ION_NOZZLE_L),
    ]
    ion_nozzle = revolve_z(
        cq.Workplane("XZ").polyline(nozzle_profile).close())
    ion_nozzle = ion_nozzle.translate((0, 0, grill_h + 20))

    # 推进器机身段(连接散热套与火箭主体)
    ion_body = post(ION_BODY_R, ION_BODY_L).translate((0, 0, grill_h + 20 + ION_NOZZLE_L))

    # 火箭主体(机身+段箍+整流罩), 直接叠在推进器顶面上, 总高 = ROCKET_H
    z_ion_top = grill_h + 20 + ION_NOZZLE_L + ION_BODY_L
    nose_h = 63                                # 整流罩高度
    hull_h = ROCKET_H - nose_h                 # 机身段高度
    # 机身与整流罩"一次旋转成型"(分两个实体再 union, 接缝处会留下着色箍痕):
    # 母线 = 底面 → 侧壁 → 椭圆弧顶(按等高度采样, 根部才不会出现直筒段)
    nose_pts = [(r_b * math.sqrt(max(1.0 - (i / 24) ** 2, 0.0)), nose_h * i / 24)
                for i in range(1, 25)]
    body_profile = [(0, 0), (r_b, 0), (r_b, hull_h)] + \
                   [(x, hull_h + z) for x, z in nose_pts]
    hull = revolve_z(
        cq.Workplane("XZ").polyline(body_profile).close()).translate((0, 0, z_ion_top))
    hull = hull.union(                          # 推进剂段箍(机身 68% 高度处)
        cq.Workplane("XY").workplane(offset=z_ion_top + hull_h * 0.68)
        .circle(r_b + 2).circle(r_b).extrude(10))

    # 着陆腿: 从机身侧壁斜撑到平台面
    leg_mount_z = z_ion_top + hull_h * 0.68
    legs = []
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        mount = (r_b * math.cos(a), r_b * math.sin(a), leg_mount_z)
        foot = (60 * math.cos(a), 60 * math.sin(a), 0)
        legs.append(strut(mount, foot, 2.5))
        legs.append(post(7, 3).translate((foot[0], foot[1], 0)))

    dx, dy = POS_ROCKET
    z0 = BASE_H + 10
    return [
        ("着陆平台", pad.translate((dx, dy, BASE_H))),
        ("散热格栅", grill_sleeve.translate((dx, dy, z0))),
        ("加速器喷管", ion_nozzle.translate((dx, dy, z0))),
        ("推进器机身", ion_body.translate((dx, dy, z0))),
        ("返回火箭", hull.translate((dx, dy, z0))),
        ("发动机喷管", compound_of(legs).translate((dx, dy, z0))),
    ]


def build_weather():
    """环境监测站: 三柱格架 + 中心主桅杆 + 三杯风速计 + 百叶箱 + 温湿压探头。

    所有设备都挂在一根中心桅杆上(百叶箱在右侧、三层探头在左侧), 避免
    小方块散落在细细的三脚架周围; 百叶箱做成斯蒂文森屏(多层百叶板+顶盖)。
    """
    legs = []
    for ang in (90, 210, 330):                            # 柱底张开, 顶部收拢
        leg = (post(1.5, 66).translate((9, 0, 0))
               .rotate((0, 0, 0), (0, 1, 0), -8)
               .rotate((0, 0, 0), (0, 0, 1), ang))
        legs.append(leg)
    station = compound_of(legs)
    braces = [cq.Workplane("XY").workplane(offset=z).polygon(3, 14 - z * 0.1).extrude(2)
              for z in (22, 44)]
    station = cq.Workplane("XY").union(station)
    for b in braces:
        station = station.union(b)
    # 中心主桅杆: 三柱收拢后一直通到顶部, 所有仪器都有"主心骨"
    station = station.union(post(1.6, 78))
    for ang in (0, 120, 240):                             # 三杯风速计
        arm = cq.Workplane("XY").box(10, 2, 2).translate((5, 0, 76))
        cup = cq.Workplane("XY").sphere(3.5).translate((10, 0, 76))
        station = station.union(arm.rotate((0, 0, 0), (0, 0, 1), ang))
        station = station.union(cup.rotate((0, 0, 0), (0, 0, 1), ang))
    # 百叶箱 = 斯蒂文森屏: 5 层水平百叶板 + 顶盖, 挂在主桅杆右侧
    for i in range(5):
        station = station.union(
            cq.Workplane("XY").workplane(offset=26 + i * 3.2)
            .box(14, 14, 1.2).translate((8, 0, 0)))
    station = station.union(
        cq.Workplane("XY").workplane(offset=26 + 5 * 3.2)
        .box(15.5, 15.5, 1.5).translate((8, 0, 0)))

    # 温湿压探头收在百叶箱内部(斯蒂文森屏本来就是干球/湿球温度表的防辐射罩),
    # 不再单独摆小方块——小灰块在渲染里会被当成破面/多余几何
    dx, dy = POS_WEATHER
    return [("气象站", station.val().translate((dx, dy, BASE_H)))]


# =====================================================================
# 四-B、高级几何生成器(工具函数, 供 build_tower / build_rocket 调用)
# =====================================================================
# 📐 抛物面微积分推导(阶段二: 深空通信)
# ---------------------------------------------------------------
#   抛物面标准方程: z = r² / (4f),  其中 f 为焦距
#
#   证明平行光 100% 汇聚于焦点:
#   设平行光沿 -z 方向入射, 打在抛物面 z = r²/(4f) 上点 P(r, θ, z)。
#   反射定律: 入射角 = 反射角(均以法线为基准)
#
#   抛物面 F(r,θ,z) = z - r²/(4f) = 0
#   梯度(法线方向): ∇F = (-r/(2f), 0, 1)
#   法线单位向量 n = (-r/(2f), 0, 1) / √(1 + r²/(4f²))
#
#   入射光方向 d_in = (0, 0, -1)
#   反射光方向 d_out = d_in - 2(d_in·n)n
#   d_in·n = -1/√(1 + r²/(4f²))
#   d_out = (0,0,-1) + 2n/√(...) → 方向为 (r/(2f), 0, -1+1) / √(...)
#         = (r/(2f), 0, 0) → 径向方向
#
#   即: 反射光沿径向指向焦点 (0,0,f), 因为:
#   从点 (r,θ,r²/(4f)) 指向 (0,0,f) 的向量 = (-r, 0, f - r²/(4f))
#   = (-r, 0, f(1 - r²/(4f²))) 与径向反射方向平行 ✓
#
#   ∴ 平行入射的电磁波经抛物面反射后 100% 汇聚于焦点(0,0,f)。
#
# 📡 X 波段深空通信链路核算
# ---------------------------------------------------------------
#   天线增益 G = η·(π·D/λ)²,  η≈0.55(效率),  λ=c/freq
#   D = 口径,  freq = 8.4 GHz (X 波段深空通信标准频率)
#
# 📐 斯蒂芬-玻尔兹曼热辐射定律(阶段一: 散热格栅)
# ---------------------------------------------------------------
#   P_rad = ε·σ·A·T⁴
#   σ = 5.670×10⁻⁸ W/(m²·K⁴),  ε 为发射率, A 为有效辐射面积
#
#   真空环境无对流散热, 唯一散热途径为热辐射。百叶窗式倾斜格栅
#   在不大幅增加体积的前提下, 将有效辐射表面积倍增:
#   对于 N=24 槽, 倾斜角 θ=15°, 总倍增效应 ≈ N × 双面 / 单面积
#   百叶窗倾斜 15° 使散热面法线偏离天顶, 各槽互相不遮挡, 全向辐射。
#
# 🔧 Z-Fighting 修复: 刀具体两端预留 GRILL_TOLERANCE=1mm
#   贯通容差, 确保切削后壁面端口干净, 杜绝微小坏面与缝隙 → 水密。


def parabolic_profile(f, rim_r, wall, n=DISH_SAMPLE_N):
    """微积分点集离散采样: 生成抛物面壁厚截面轮廓点列。

    外表面: z = r²/(4f)
    内表面: z = r²/(4f) + wall(向 +z 偏移壁厚)
    采样: r 从 0 到 rim_r 均匀取 n+1 个点

    返回: [(x_outer, z_outer), ..., (x_inner, z_inner), ...] 闭合轮廓
    """
    outer = [(rim_r * i / n, (rim_r * i / n) ** 2 / (4 * f))
             for i in range(n + 1)]
    inner = [(rim_r * i / n, (rim_r * i / n) ** 2 / (4 * f) + wall)
             for i in range(n, -1, -1)]
    return outer + inner


def feed_horn(feed_z):
    """焦点馈源喇叭: 两圆截面 loft 放样成锥台, 小端在焦点、大口向上张开。

    与课程 1.py / 5 精简.py 的构造方向一致: 焦点 z=f 处画小圆(喉部 r=6),
    向上 16mm 画大圆(喇叭口 r=12) 放样; 再从喇叭口向下掏 Ø8×12mm 盲孔,
    底部保留 4mm 金属封底——"多截面放样 + faces().hole()"的组合用法。
    """
    return (
        cq.Workplane("XY")
        .workplane(offset=feed_z)
        .circle(FEED_R_BACK)                                # 焦点处: 喉部小端
        .workplane(offset=FEED_H)
        .circle(FEED_R_APERTURE)                            # 向上张开: 喇叭口
        .loft()                                             # 锥台放样
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .hole(FEED_HOLE_D, depth=FEED_HOLE_DEPTH)           # 谐振腔(留 4mm 底)
    )


def ParabolicDishGenerator():
    """旋转抛物面高增益天线几何生成器(集成于深空通信塔顶)。

    步骤:
    1. 微积分点集离散采样生成壁厚 2mm 的反射体截面
    2. 围绕 Z 轴 360° 旋转拉伸成抛物面壳体
    3. 外边缘并集构建刚性加固法兰圈(杜绝薄壁震颤变形)
    4. 焦点馈源喇叭(loft 锥台 + 谐振腔) + 三根 120° 锥形支撑臂

    返回: (dish, feed_arms, feed) 三元组
    """
    f = DISH_F
    rim_r = DISH_D / 2
    wall = DISH_WALL

    # 1. 微积分离散采样 → 闭合截面轮廓
    profile_pts = parabolic_profile(f, rim_r, wall)

    # 2. 绕 Z 轴 360° 旋转拉伸(使用 revolve_z 工具函数)
    dish = revolve_z(
        cq.Workplane("XZ")
        .moveTo(*profile_pts[0])
        .spline(profile_pts[1:])
        .close()
    )

    # 3. 外边缘法兰圈(刚性加固, 杜绝薄壁震颤)
    flange = (
        cq.Workplane("XY")
        .circle(rim_r + DISH_FLANGE_W)
        .circle(rim_r)
        .extrude(DISH_FLANGE_T)
        .translate((0, 0, rim_r ** 2 / (4 * f) - DISH_FLANGE_T / 2))
    )
    dish = dish.union(flange)

    # 4. 三根支撑臂(120° 阵列): 下端扎在盘缘法兰, 上端收拢托住喇叭喉部,
    #    杆件用锥形放样(根部粗、端部细), 端点埋进喉部底端 1mm 处熔合
    feed_z = f
    rim_z = rim_r ** 2 / (4 * f) + wall            # 盘缘上表面高度
    tip_r = FEED_R_BACK - 1                        # 端点落在喉部壁内
    feed_arms = []
    for ang in (0, 120, 240):
        a = math.radians(ang)
        mount = (rim_r * math.cos(a), rim_r * math.sin(a), rim_z)          # 盘缘
        tip = (tip_r * math.cos(a), tip_r * math.sin(a), feed_z + 1)       # 喉部
        feed_arms.append(strut(mount, tip, FEED_ARM_R0, FEED_ARM_R1))

    # 5. 焦点馈源喇叭
    feed = feed_horn(feed_z)

    return dish, compound_of(feed_arms), feed


def build_paths():
    """连接道路: 地表压痕路径连接各功能分区。

    用扁平带状体(宽 8mm, 厚 1mm)在各建筑间铺设火星车辙印路径,
    使场景从"散点布局"升级为"有机连通的整体基地"。
    路径连接: 穹顶→实验舱, 穹顶→通信塔, 实验舱→发射区, 穹顶→气象站,
    穹顶→太阳能区, 穹顶→火星车停放点。
    """
    paths = []
    # 路径定义: (起点, 终点)
    route_defs = [
        (POS_DOME, POS_LAB),        # 穹顶→实验舱
        (POS_DOME, POS_TOWER),      # 穹顶→通信塔
        (POS_LAB, POS_ROCKET),      # 实验舱→发射区
        (POS_DOME, POS_WEATHER),    # 穹顶→气象站
        (POS_DOME, POS_SOLAR),      # 穹顶→能源区
        (POS_DOME, POS_ROVER),      # 穹顶→火星车停放点
    ]
    for (x0, y0), (x1, y1) in route_defs:
        dx_seg, dy_seg = x1 - x0, y1 - y0
        seg_len = math.hypot(dx_seg, dy_seg)
        if seg_len < 1:
            continue
        # 扁平带状路径: 宽 8, 厚 1, 沿 XY 方向铺设
        path = (
            cq.Workplane("XY").box(seg_len, 8, 1)
            .translate((seg_len / 2, 0, 0))        # 原点对齐起点
        )
        # 旋转到方向
        angle = math.degrees(math.atan2(dy_seg, dx_seg))
        path = path.rotate((0, 0, 0), (0, 0, 1), angle)
        path = path.translate((x0, y0, BASE_H + 0.5))
        paths.append(path.val())

    return [("压痕路径", compound_of(paths))]


# =====================================================================
# 五、总装(材质表驱动, 一个循环完成全部装配)
# =====================================================================
BUILDERS = (build_terrain, build_paths, build_dome, build_lab, build_tunnel,
            build_solar, build_tower, build_rover, build_rocket, build_weather)


def build_scene():
    """总装: 地形→道路→居住→科研→能源→通信→探测→发射→环境监测。

    按功能分区逻辑总装, 连接道路贯穿各区域, 形成有机整体基地。
    """
    assy = cq.Assembly(name="MarsResearchOutpost")
    for builder in BUILDERS:
        for name, shape in builder():
            assy.add(shape, name=name, color=cq.Color(*mat_of(name)["color"]))
    return assy


# =====================================================================
# 六、导出器
# =====================================================================

# ── 程序化纹理生成器(纯标准库 zlib+struct, 无第三方依赖) ──
# 为关键材质生成 64×64 PNG 纹理, 嵌入 GLB 作为 baseColorTexture

def _png_encode(pixels, w, h):
    """将 RGBA 像素列表编码为 PNG 字节流(纯标准库)。

    pixels: [(r,g,b,a), ...] 长度 w*h, 每通道 0-255
    返回: bytes (完整 PNG 文件)
    """
    def chunk(tag, data):
        c = tag + data
        return (struct.pack(">I", len(data)) + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))

    raw = bytearray()
    for y in range(h):
        raw.append(0)                          # filter type 0 (None)
        for x in range(w):
            r, g, b, a = pixels[y * w + x]
            raw += bytes([r, g, b, a])
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (sig + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def _hash_noise(x, y, seed=0):
    """简易值噪声(基于整数哈希), 返回 0.0~1.0。"""
    h = (x * 374761393 + y * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0


def _smooth_noise(x, y, seed=0):
    """双线性插值平滑噪声。"""
    ix, iy = int(x), int(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash_noise(ix, iy, seed)
    b = _hash_noise(ix + 1, iy, seed)
    c = _hash_noise(ix, iy + 1, seed)
    d = _hash_noise(ix + 1, iy + 1, seed)
    return a * (1 - ux) * (1 - uy) + b * ux * (1 - uy) + c * (1 - ux) * uy + d * ux * uy


def _fbm(x, y, octaves=4, seed=0):
    """分形布朗运动(fBm): 多倍频噪声叠加, 生成自然纹理。"""
    val, amp, freq = 0.0, 1.0, 1.0
    for _ in range(octaves):
        val += _smooth_noise(x * freq, y * freq, seed) * amp
        amp *= 0.5
        freq *= 2.0
    return val / 1.875


def gen_texture_mars_ground(size=64):
    """火星地表纹理: 橙红基底 + 暗斑噪纹 + 细微颗粒。"""
    px = []
    for y in range(size):
        for x in range(size):
            n = _fbm(x / size * 8, y / size * 8, 4, seed=42)
            n2 = _fbm(x / size * 16, y / size * 16, 3, seed=99)
            r = int(180 + n * 50 - n2 * 30)
            g = int(85 + n * 35 - n2 * 20)
            b = int(50 + n * 20 - n2 * 15)
            a = 255
            px.append((max(0, min(255, r)), max(0, min(255, g)),
                       max(0, min(255, b)), a))
    return _png_encode(px, size, size)


def gen_texture_metal_panel(size=64):
    """金属面板纹理: 灰色基底 + 拉丝纹路 + 铆钉点阵。"""
    px = []
    for y in range(size):
        for x in range(size):
            base = 120 + _hash_noise(x // 4, y // 4, 7) * 40
            # 拉丝纹(水平方向周期性明暗)
            brush = math.sin(x * 0.8) * 8 + _hash_noise(x, y // 8, 3) * 10
            # 铆钉(每 16 像素一个)
            rx, ry = x % 16, y % 16
            if 6 <= rx <= 9 and 6 <= ry <= 9:
                rivet = 30
            else:
                rivet = 0
            v = int(base + brush - rivet)
            v = max(60, min(200, v))
            px.append((v, min(255, v + 2), min(255, v + 4), 255))
    return _png_encode(px, size, size)


def gen_texture_solar_panel(size=64):
    """太阳能板纹理: 深蓝基底 + 网格线 + 高光反光。"""
    px = []
    for y in range(size):
        for x in range(size):
            # 网格线(每 16 像素分隔)
            if x % 16 < 2 or y % 16 < 2:
                r, g, b = 40, 50, 60
            else:
                n = _hash_noise(x, y, 5)
                r = int(10 + n * 15)
                g = int(25 + n * 20)
                b = int(70 + n * 40)
            px.append((r, g, b, 255))
    return _png_encode(px, size, size)


def gen_texture_rocket_hull(size=64):
    """火箭壳体纹理: 白色基底 + 红色条纹 + 标识区。"""
    px = []
    for y in range(size):
        for x in range(size):
            n = _hash_noise(x, y, 11) * 20
            if 20 <= y <= 24:                     # 红色条纹
                r, g, b = int(200 + n), 40, 30
            elif 40 <= y <= 44:
                r, g, b = int(200 + n), 40, 30
            else:
                r = int(230 + n - 10)
                g = int(228 + n - 10)
                b = int(225 + n - 10)
            px.append((max(0, min(255, r)), max(0, min(255, g)),
                       max(0, min(255, b)), 255))
    return _png_encode(px, size, size)


def gen_texture_dish_reflector(size=64):
    """抛物面反射器纹理: 银白基底 + 同心圆纹路。"""
    px = []
    cx = cy = size / 2
    for y in range(size):
        for x in range(size):
            r_dist = math.hypot(x - cx, y - cy)
            ring = math.sin(r_dist * 0.6) * 15
            n = _hash_noise(x // 2, y // 2, 13) * 10
            v = int(235 + ring + n - 5)
            v = max(180, min(252, v))
            px.append((v, v, min(255, v + 3), 255))
    return _png_encode(px, size, size)


def gen_texture_dirt_path(size=64):
    """压痕路径纹理: 深红泥土 + 车辙痕迹。"""
    px = []
    for y in range(size):
        for x in range(size):
            n = _fbm(x / size * 6, y / size * 6, 3, seed=77)
            # 两条平行车辙
            if 18 <= x <= 22 or 42 <= x <= 46:
                dark = 40
            else:
                dark = 0
            r = int(120 + n * 40 - dark)
            g = int(55 + n * 20 - dark)
            b = int(30 + n * 15 - dark)
            px.append((max(0, min(255, r)), max(0, min(255, g)),
                       max(0, min(255, b)), 255))
    return _png_encode(px, size, size)


# 材质名 → 纹理生成函数 映射(无映射的材质用纯色)
TEXTURE_MAP = {
    "火星地形": gen_texture_mars_ground,
    "火星岩石": gen_texture_mars_ground,
    "压痕路径": gen_texture_dirt_path,
    "科研实验舱": gen_texture_metal_panel,
    "加压廊道": gen_texture_metal_panel,
    "着陆平台": gen_texture_metal_panel,
    "推进器机身": gen_texture_metal_panel,
    "散热格栅": gen_texture_metal_panel,
    "塔架": gen_texture_metal_panel,
    "太阳能板": gen_texture_solar_panel,
    "返回火箭": gen_texture_rocket_hull,
    "抛物面反射器": gen_texture_dish_reflector,
}


def gen_uv(verts, tris):
    """生成 UV 坐标: 包围盒归一化投影。

    计算整个网格的包围盒, 取最大跨度方向的两个轴作为 UV 投影面,
    将坐标归一化到 [0,1] 区间。简单稳定, 保证所有顶点都有有效 UV。
    """
    if not verts:
        return []
    # 包围盒
    min_x = min(v[0] for v in verts)
    max_x = max(v[0] for v in verts)
    min_y = min(v[1] for v in verts)
    max_y = max(v[1] for v in verts)
    min_z = min(v[2] for v in verts)
    max_z = max(v[2] for v in verts)
    # 找最大跨度方向, 选另外两个轴做 UV
    sx = max_x - min_x or 1e-6
    sy = max_y - min_y or 1e-6
    sz = max_z - min_z or 1e-6
    if sx >= sy and sx >= sz:
        # X 最大 → 用 YZ 投影
        uvs = [[(v[1] - min_y) / sy, (v[2] - min_z) / sz] for v in verts]
    elif sy >= sz:
        # Y 最大 → 用 XZ 投影
        uvs = [[(v[0] - min_x) / sx, (v[2] - min_z) / sz] for v in verts]
    else:
        # Z 最大 → 用 XY 投影
        uvs = [[(v[0] - min_x) / sx, (v[1] - min_y) / sy] for v in verts]
    return uvs


def tessellate(shape, tol=0.3):
    """实体 → (顶点表, 三角索引表), 多实体自动合并。"""
    verts, tris = [], []
    for solid in (shape.Solids() or [shape]):
        vs, ts = solid.tessellate(tol)
        base = len(verts)
        verts += [tuple(v.toTuple()) for v in vs]
        tris += [(base + a, base + b, base + c) for a, b, c in ts]
    return verts, tris


def smooth_normals(verts, tris):
    """平滑顶点法线(纯数学, 无第三方库): 面法线叉积累加到顶点后归一化。

    glTF 光照(PBR 金属度/粗糙度)依赖 NORMAL 属性计算反射高光,
    缺失则金属材质无光泽。
    """
    acc = [[0.0, 0.0, 0.0] for _ in verts]
    for a, b, c in tris:
        va, vb, vc = verts[a], verts[b], verts[c]
        ux, uy, uz = vb[0] - va[0], vb[1] - va[1], vb[2] - va[2]
        vx, vy, vz = vc[0] - va[0], vc[1] - va[1], vc[2] - va[2]
        fx, fy, fz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        for idx in (a, b, c):
            acc[idx][0] += fx
            acc[idx][1] += fy
            acc[idx][2] += fz
    normals = []
    for nx, ny, nz in acc:
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        normals.append((nx / length, ny / length, nz / length))
    return normals


def write_glb(assy, path):
    """原生 glTF 2.0 GLB 导出器(仅用 json+struct 标准库)。

    每个零件 → 独立 node/mesh/material, 且注入四重真实感要素:
    ① 平滑顶点法线(PBR 反射高光的数学基础)
    ② 材质 PBR 参数(金属度/粗糙度/自发光, 由 MATERIALS 表驱动)
    ③ KHR_lights_punctual 太阳方向光 + 暖色补光(打开即有光照氛围)
    ④ 程序化纹理贴图(baseColorTexture): 火星地表/金属面板/太阳能板等
       纹理由纯标准库生成(fBm 噪声 + PNG 编码), 嵌入 GLB 二进制块
    """
    json_doc = {"asset": {"version": "2.0",
                          "generator": "MarsOutpost parametric builder"},
                "scene": 0, "scenes": [{"nodes": []}],
                "extensionsUsed": ["KHR_lights_punctual"],
                "extensions": {"KHR_lights_punctual": {"lights": [
                    {"type": "directional", "name": "太阳",
                     "color": [1.0, 0.96, 0.88], "intensity": 2.8},
                    {"type": "point", "name": "补光",
                     "color": [0.55, 0.65, 0.85], "intensity": 5e5}]}},
                "nodes": [], "meshes": [], "materials": [],
                "accessors": [], "bufferViews": [], "buffers": [],
                "images": [], "textures": [], "samplers": []}
    # 太阳方向光节点: 绕X -50°绕Z 135° → 光从东南上方斜照(火星午后)
    sun_node = {"name": "太阳光", "extensions": {"KHR_lights_punctual": {"light": 0}},
                "rotation": [-0.342, 0.0, 0.940, 0.0]}
    fill_node = {"name": "补光", "extensions": {"KHR_lights_punctual": {"light": 1}},
                 "translation": [300.0, -300.0, 500.0]}
    json_doc["nodes"] += [sun_node, fill_node]
    json_doc["scenes"][0]["nodes"] += [0, 1]
    blob = bytearray()

    def add_view(data, target=0):
        while len(blob) % 4:
            blob.append(0)
        offset = len(blob)
        blob.extend(data)
        json_doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(data),
             "target": target} if target else
            {"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        return len(json_doc["bufferViews"]) - 1

    # ── 纹理缓存: 同名材质只生成一次 PNG ──
    # 先在循环中收集材质名, 循环结束后统一生成 PNG 追加到 blob 末尾
    # (避免图片 bufferView 与几何 bufferView 交错导致渲染器解析异常)
    tex_pending = {}   # 材质名 → texture_index (循环中分配, 循环后填充数据)

    def get_texture(name):
        """获取(或生成并缓存)材质对应的纹理索引。无纹理返回 None。"""
        if name in tex_pending:
            return tex_pending[name][0]
        gen_fn = TEXTURE_MAP.get(name)
        if gen_fn is None:
            return None
        # 预分配 texture/sampler/image 索引, PNG 数据循环后统一追加
        sampler_idx = len(json_doc["samplers"])
        json_doc["samplers"].append(
            {"wrapS": 10497, "wrapT": 10497,           # REPEAT
             "magFilter": 9729, "minFilter": 9987})     # LINEAR_MIPMAP_LINEAR
        img_idx = len(json_doc["images"])
        # image 的 bufferView 循环后填充, 先占位
        json_doc["images"].append(
            {"bufferView": -1, "mimeType": "image/png"})
        tex_idx = len(json_doc["textures"])
        json_doc["textures"].append(
            {"source": img_idx, "sampler": sampler_idx})
        tex_pending[name] = (tex_idx, img_idx, gen_fn)
        return tex_idx

    for i, (shape, name, loc, _c) in enumerate(assy):
        name = name.split("/")[-1]        # 去掉装配路径前缀, 只留零件名
        verts, tris = tessellate(shape.moved(loc))
        normals = smooth_normals(verts, tris)
        uvs = gen_uv(verts, tris)                           # ★ 生成 UV 坐标
        v_data = struct.pack(f"<{len(verts) * 3}f",
                             *[c for v in verts for c in v])
        n_data = struct.pack(f"<{len(normals) * 3}f",
                             *[c for n in normals for c in n])
        uv_data = struct.pack(f"<{len(uvs) * 2}f",           # ★ UV 二进制
                              *[c for uv in uvs for c in uv])
        i_data = struct.pack(f"<{len(tris) * 3}I",
                             *[t for tri in tris for t in tri])
        v_view = add_view(v_data, 34962)
        n_view = add_view(n_data, 34962)
        uv_view = add_view(uv_data, 34962)                   # ★ UV bufferView
        i_view = add_view(i_data, 34963)
        mins = [min(v[k] for v in verts) for k in range(3)]
        maxs = [max(v[k] for v in verts) for k in range(3)]
        pos_acc = {"bufferView": v_view, "componentType": 5126,
                   "count": len(verts), "type": "VEC3", "min": mins, "max": maxs}
        nrm_acc = {"bufferView": n_view, "componentType": 5126,
                   "count": len(normals), "type": "VEC3"}
        uv_acc = {"bufferView": uv_view, "componentType": 5126,  # ★ UV accessor
                  "count": len(uvs), "type": "VEC2"}
        idx_acc = {"bufferView": i_view, "componentType": 5125,
                   "count": len(tris) * 3, "type": "SCALAR"}
        json_doc["accessors"] += [pos_acc, nrm_acc, uv_acc, idx_acc]
        m = mat_of(name)
        emissive = m.get("emissive", (0, 0, 0))
        # ★ 有纹理时 baseColorFactor=白(1,1,1), 让纹理原色完整显示;
        #   无纹理时用材质表基色(glTF 中 baseColorTexture × baseColorFactor 相乘)
        tex_idx = get_texture(name)
        base_color = (1.0, 1.0, 1.0) if tex_idx is not None else m["color"]
        pbr = {
            "baseColorFactor": [*base_color, 1.0],
            "metallicFactor": m["metal"],
            "roughnessFactor": m["rough"]}
        if tex_idx is not None:
            pbr["baseColorTexture"] = {"index": tex_idx, "texCoord": 0}
        json_doc["materials"].append({
            "name": name,
            "pbrMetallicRoughness": pbr,
            "emissiveFactor": list(emissive),
            "doubleSided": True})
        json_doc["meshes"].append({"primitives": [{
            "attributes": {"POSITION": len(json_doc["accessors"]) - 4,
                           "NORMAL": len(json_doc["accessors"]) - 3,
                           "TEXCOORD_0": len(json_doc["accessors"]) - 2},  # ★
            "indices": len(json_doc["accessors"]) - 1,
            "material": i}]})
        json_doc["nodes"].append({"name": name, "mesh": i})
        json_doc["scenes"][0]["nodes"].append(len(json_doc["nodes"]) - 1)

    # ── 所有几何数据写完后, 统一生成 PNG 纹理 ──
    # 使用 base64 data URI 内联(兼容性最佳, 所有 glTF 渲染器都支持)
    import base64
    for _mat_name, (tex_idx, img_idx, gen_fn) in tex_pending.items():
        png_bytes = gen_fn()
        b64 = base64.b64encode(png_bytes).decode('ascii')
        json_doc["images"][img_idx] = {
            "uri": f"data:image/png;base64,{b64}",
            "mimeType": "image/png"}

    json_doc["buffers"].append({"byteLength": len(blob)})
    while len(blob) % 4:
        blob.append(0)
    j_bytes = json.dumps(json_doc, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    j_bytes += b" " * (-len(j_bytes) % 4)          # JSON 用空格补齐 4 字节
    glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j_bytes) + 8 + len(blob))
           + struct.pack("<II", len(j_bytes), 0x4E4F534A) + j_bytes
           + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob))
    with open(path, "wb") as fp:
        fp.write(glb)
    return len(json_doc["nodes"])


def export_svg(compound, path, proj_dir, stroke="rgb(255,122,60)", bg="#0d1526"):
    """SVG 线框三视图(深空蓝底 + 火星橙线, 工程蓝图风)。

    地形带大量布尔起伏时 HLR 算法个别视角可能失败 → 打印提示并跳过
    该视角, 保证整体导出流程不中断。
    """
    try:
        cq.exporters.export(
            compound, path,
            opt={"projectionDir": proj_dir, "width": 1600, "height": 1100,
                 "showAxes": False, "showHidden": False, "strokeWidth": 0.8,
                 "marginLeft": 20, "marginTop": 20})
        text = open(path, encoding="utf-8").read()
        text = text.replace('stroke="rgb(0,0,0)"', f'stroke="{stroke}"')
        text = re.sub(r'(<svg[^>]*>)',
                      r'\1<rect x="0" y="0" width="100%" height="100%" '
                      r'fill="' + bg + '"/>', text, count=1)
        open(path, "w", encoding="utf-8").write(text)
        return True
    except Exception as e:
        print(f"  [SVG 降级] {path} 失败({type(e).__name__}), 跳过该视角")
        return False


# =====================================================================
# 七、程序入口: 建模 → STEP/GLB/STL/SVG 一键导出
# =====================================================================
if __name__ == "__main__":
    import os
    os.makedirs("exports", exist_ok=True)

    print("[1/5] 构建模型……")
    scene = build_scene()
    solids = [s.moved(loc) for s, _, loc, _ in scene]

    print("[2/5] 导出 STEP(彩色分层) / STL ……")
    try:
        scene.export("exports/mars_outpost.step")
    except AttributeError:
        scene.save("exports/mars_outpost.step")
    cq.exporters.export(compound_of(solids), "exports/mars_outpost.stl",
                        tolerance=0.2)

    print("[3/5] 导出 GLB(Blender PBR 材质, 原生 json+struct 打包)……")
    n_parts = write_glb(scene, "exports/mars_outpost.glb")
    print(f"      GLB 零件材质数: {n_parts}")

    print("[4/5] 导出 SVG 三视图(等轴/俯视/正视)……")
    whole = compound_of(solids)
    export_svg(whole, "exports/view_iso.svg", (1, -1, 0.75))
    export_svg(whole, "exports/view_top.svg", (0, 0, 1))
    export_svg(whole, "exports/view_front.svg", (0, -1, 0))

    # ── 阶段二: 高精度抛物面反射器单独导出 STL ──
    print("[5/5] 导出高精度抛物面反射器 STL + X 波段链路核算……")
    dish_reflector, _feed_arms, _feed = ParabolicDishGenerator()
    cq.exporters.export(dish_reflector, "exports/parabolic_dish_reflector.stl",
                        tolerance=0.1)

    # X 波段深空通信链路核算
    c_light = 3e8  # 光速(m/s)
    wavelength = c_light / X_BAND_FREQ  # 波长(m)
    eta = 0.55  # 天线效率
    D_m = DISH_D / 1000  # 口径(m)
    gain_linear = eta * (math.pi * D_m / wavelength) ** 2
    gain_dbi = 10 * math.log10(gain_linear)
    print(f"      抛物面焦距 f = {DISH_F}mm, 口径 D = {DISH_D}mm")
    print(f"      X 波段频率 = {X_BAND_FREQ:.2e} Hz, 波长 λ = {wavelength*100:.2f} cm")
    print(f"      天线增益 G = {gain_linear:.1f} 倍 = {gain_dbi:.1f} dBi")

    print("完成! 全部文件位于 exports/ 目录。")
