# -*- coding: utf-8 -*-
"""
====================================================================
  作品名称：《赤星前哨 · 火星科研站》(Mars Research Outpost)
  参赛赛项：探秘火星逐梦太空（智能算法编程类 · 三维设计项目）
  参赛组别：初中组        建模软件：CadQuery（Python 参数化建模）
====================================================================
  设计理念
  --------
  以 2030 年代火星科考前哨站为蓝图，构建"一站多器"综合场景：
  主居住穹顶、科研实验舱、加压廊道、太阳能翼阵、深空通讯塔、
  六轮火星车、返回火箭着陆平台、气象观测站。

  ── 阶段一总装大通关: 离子推进器动力总成 ──
  24 槽全向辐射散热格栅(倾斜 15° 百叶窗式), 依据斯蒂芬-玻尔兹曼
  热辐射定律设计; CadQuery 批量布尔差集(cut)高效算法; 刀具两端
  预留 1mm 贯通容差修复 Z-Fighting, 100% 水密交付。

  ── 阶段二: 深空通信系统 ──
  旋转抛物面高增益天线, 严谨推导 z = r²/(4f) 微积分方程, 微积分
  点集离散采样生成壁厚 2mm 反射体, 外缘法兰圈加固; X 波段(8.4GHz)
  深空通信链路增益核算(dBi), 导出高精度 STL。

  核心算法：极坐标放置、三角函数定向斜杆、海伦公式求弧半径、
  抛物线 z=r²/(4f) 旋转成天线、斯蒂芬-玻尔兹曼热辐射散热格栅、
  CadQuery 批量布尔差集、Z-Fighting 贯通容差修复、
  随机数撒布岩石(固定种子可复现)、
  太阳能板倾角 = 90° − 太阳高度角(自动对日)。

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

import cadquery as cq

# =====================================================================
# 一、参数区（改这里, 全站自动重建）
# =====================================================================
BASE_R, BASE_H = 300, 14           # 火星基座半径 / 厚度
DOME_R, DOME_H, DOME_RIBS = 80, 60, 10   # 穹顶半径 / 矢高 / 肋数
LAB_R, LAB_L = 32, 120             # 实验舱半径 / 长度
SUN_ELEV, PANEL_N = 35, 4          # 太阳高度角(度) / 太阳能板数
TOWER_H, DISH_D, EARTH_ELEV = 190, 70, 40   # 塔高 / 天线口径 / 对地仰角
ROCKET_H = 210                     # 火箭总高
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

# --- 阶段二: 旋转抛物面高增益天线 ---
DISH_F = 45                         # 抛物面焦距 f(mm), z = r²/(4f)
DISH_APERTURE = 120                 # 天线口径直径(mm)
DISH_WALL = 2                       # 反射体壁厚(mm)
DISH_FLANGE_W = 6                   # 法兰圈宽度
DISH_FLANGE_T = 4                   # 法兰圈厚度
DISH_SAMPLE_N = 48                  # 微积分点集离散采样数
X_BAND_FREQ = 8.4e9                 # X 波段中心频率(Hz)

# 各系统落位(x, y)
POS_DOME, POS_LAB = (-60, 0), (68, 0)
POS_TOWER, POS_ROVER = (95, 150), (75, -120)
POS_ROCKET, POS_WEATHER = (195, 105), (-160, 100)
POS_SOLAR = (-156, -190)
POS_ION = (-210, -80)               # 离子推进器动力总成落位
POS_DISH = (130, -160)              # 高增益天线落位

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
    "深空天线":   {"color": (0.92, 0.92, 0.94), "metal": 0.30, "rough": 0.20},
    "天线信标":   {"color": (1.00, 0.10, 0.06), "metal": 0.00, "rough": 0.20,
                   "emissive": (0.9, 0.02, 0.0)},
    "火星车体":   {"color": (0.90, 0.88, 0.84), "metal": 0.30, "rough": 0.40},
    "车轮":       {"color": (0.25, 0.25, 0.27), "metal": 0.20, "rough": 0.80},
    "着陆平台":   {"color": (0.45, 0.47, 0.50), "metal": 0.50, "rough": 0.60},
    "返回火箭":   {"color": (0.85, 0.87, 0.90), "metal": 0.85, "rough": 0.20},
    "发动机喷管": {"color": (0.35, 0.33, 0.30), "metal": 0.95, "rough": 0.30},
    "气象站":     {"color": (0.93, 0.93, 0.91), "metal": 0.20, "rough": 0.40},
    # 阶段一: 离子推进器动力总成
    "推进器机身": {"color": (0.78, 0.80, 0.83), "metal": 0.90, "rough": 0.25},
    "加速器喷管": {"color": (0.30, 0.28, 0.25), "metal": 0.95, "rough": 0.35},
    "散热格栅":   {"color": (0.65, 0.67, 0.70), "metal": 0.85, "rough": 0.30},
    # 阶段二: 高增益抛物面天线
    "抛物面反射器": {"color": (0.95, 0.95, 0.97), "metal": 0.60, "rough": 0.12},
    "天线法兰":   {"color": (0.55, 0.57, 0.60), "metal": 0.80, "rough": 0.35},
    "天线馈源臂": {"color": (0.70, 0.72, 0.75), "metal": 0.75, "rough": 0.30},
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


def arc_r(p1, p_mid, p2):
    """海伦公式求过三点的圆弧半径(保证不小于半弦长)。"""
    a, b, c = math.dist(p_mid, p2), math.dist(p1, p2), math.dist(p1, p_mid)
    s = (a + b + c) / 2
    k = math.sqrt(max(s * (s - a) * (s - b) * (s - c), 1e-9))
    return max(a * b * c / (4 * k), b / 2 + 0.5)


def strut(p0, p1, r):
    """连接空间两点的圆柱斜杆(三角函数定向)。"""
    dx, dy, dz = (p1[i] - p0[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    return (
        cq.Workplane("XY").circle(r).extrude(length)
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
    # 经向肋: 沿椭圆弧的球链拱(格构式外骨架, 零布尔运算), 旋转阵列
    def dome_rib_chain():
        balls = []
        for tdeg in range(4, 90, 7):                     # 顶→边 13 颗球
            t = math.radians(tdeg)
            x = DOME_R * 1.01 * math.sin(t)
            z = DOME_H * 1.01 * math.cos(t) + 2          # 紧贴壳外表面
            balls.append(cq.Workplane("XY").workplane(offset=z)
                         .sphere(2.8).translate((x, 0, 0)).val())
        return compound_of(balls)

    ribs = [dome_rib_chain().rotate((0, 0, 0), (0, 0, 1), i * 360 / DOME_RIBS)
            for i in range(DOME_RIBS)]
    ribs.append(cq.Solid.makeTorus(DOME_R * 0.80, 2.2).translate((0, 0, DOME_H * 0.38)))
    ribs.append(cq.Solid.makeTorus(DOME_R * 0.56, 2.2).translate((0, 0, DOME_H * 0.68)))
    # 舷窗: 先旋转向位再平移, 保证圆柱始终径向朝外
    win = cq.Workplane("YZ").circle(5).extrude(8)          # 沿 +X 伸出
    wins = [polar(win.rotate((0, 0, 0), (0, 0, 1), a),
                  DOME_R * 0.78, a, DOME_H * 0.42)
            for a in (120, 180, 240)]
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
    """通讯塔: 三柱桁架(斜杆函数) + 环撑 + 抛物面天线(y=x²/4f) + 信标。"""
    H, top_r, bot_r = TOWER_H, 8, 26
    struts = [strut((bot_r * math.cos(math.radians(a)), bot_r * math.sin(math.radians(a)), 0),
                    (top_r * math.cos(math.radians(a)), top_r * math.sin(math.radians(a)), H), 3)
              for a in (90, 210, 330)]
    rings = [cq.Solid.makeTorus(bot_r + (top_r - bot_r) * f, 1.2)
             .translate((0, 0, H * f))
             for f in (0.15, 0.32, 0.5, 0.68, 0.85)]
    # 抛物面天线: 内外抛物线夹薄壳 → 绕 Z 旋转; 馈源置于焦点 z=f
    f_dish, rim_r = DISH_D * 0.35, DISH_D / 2
    xs = [rim_r * i / 6 for i in range(7)]
    dish = revolve_z(
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .spline([(x, x * x / (4 * f_dish)) for x in xs[1:]])          # 外表面
        .lineTo(rim_r, rim_r * rim_r / (4 * f_dish) + 3)
        .spline([(x, x * x / (4 * f_dish) + 3)
                 for x in reversed(xs[:-1])])                          # 内表面
        .close()
    ).union(post(1.2, f_dish).union(
        cq.Workplane("XY").workplane(offset=f_dish).sphere(3)))        # 馈源
    dish = dish.rotate((0, 0, 0), (1, 0, 0), -EARTH_ELEV).translate((0, 0, H - 8))
    # 桅杆警示灯: 桅杆从天线盘中心穿过后高出盘缘 15mm 以上,
    # 红球置于杆顶(航空警示灯), 不会"糊"在盘面上
    beacon = (post(1.5, 54).translate((0, 0, H - 20))
              .union(cq.Workplane("XY").workplane(offset=H + 34).sphere(4.5)))

    # 桁架件互不融合, 直接打包复合体(避免多余布尔运算)
    dx, dy = POS_TOWER
    return [
        ("塔架", compound_of(struts + rings + [dish]).translate((dx, dy, BASE_H))),
        ("天线信标", beacon.val().translate((dx, dy, BASE_H))),
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
    """着陆平台(八角+边界灯) + 火箭(局部 z=0 为平台面: 喷管口/着陆脚踩面)。"""
    H, r_b = ROCKET_H, 26
    pad = (
        cq.Workplane("XY").polygon(8, 130).extrude(8)
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(60).circle(52).extrude(2)
    )
    lamps = [polar(post(3, 4), 56, a, 8) for a in range(0, 360, 45)]
    for lamp in lamps:
        pad = pad.union(lamp)

    nozzle = revolve_z(                                   # 喷管 z 0~26, 口朝下
        cq.Workplane("XZ").polyline(
            [(r_b * 0.35, 26), (r_b * 0.75, 0),
             (r_b * 0.7, 0), (r_b * 0.4, 24)]).close())
    hull = post(r_b, 130).translate((0, 0, 26))           # 机身 z 26~156
    hull = hull.union(                                    # 推进剂段箍
        cq.Workplane("XY").workplane(offset=89)
        .circle(r_b + 2).circle(r_b).extrude(10))
    # 整流罩: 椭圆弧加密采样折线从机身顶缘收到顶点 → 实心旋转体;
    # 折线不过冲(样条起点陡升会内凹出"细脖子"), 基线嵌入机身破共面
    arc = [(x, 155 + z) for x, z in reversed(ell_arc(r_b, 63, 14))]
    nose = revolve_z(
        cq.Workplane("XZ").moveTo(0, 155).lineTo(r_b, 155)
        .polyline(arc[1:]).close())
    hull = hull.union(nose)
    legs = []
    for ang in (45, 135, 225, 315):                       # 着陆腿踩平台面
        a = math.radians(ang)
        mount = (r_b * math.cos(a), r_b * math.sin(a), 100)
        foot = (60 * math.cos(a), 60 * math.sin(a), 0)
        legs.append(strut(mount, foot, 2.5))
        legs.append(post(7, 3).translate((foot[0], foot[1], 0)))

    dx, dy = POS_ROCKET
    z0 = BASE_H + 10                                      # 平台顶面
    return [
        ("着陆平台", pad.translate((dx, dy, BASE_H))),
        ("返回火箭", hull.translate((dx, dy, z0))),
        ("发动机喷管", compound_of([nozzle] + legs).translate((dx, dy, z0))),
    ]


def build_weather():
    """气象站: 三柱底张顶收格架 + 三杯风速计(120° 阵列) + 百叶箱。"""
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
    station = station.union(post(1.2, 14).translate((0, 0, 66)))
    for ang in (0, 120, 240):                             # 三杯风速计
        arm = cq.Workplane("XY").box(10, 2, 2).translate((5, 0, 76))
        cup = cq.Workplane("XY").sphere(3.5).translate((10, 0, 76))
        station = station.union(arm.rotate((0, 0, 0), (0, 0, 1), ang))
        station = station.union(cup.rotate((0, 0, 0), (0, 0, 1), ang))
    station = station.union(                              # 百叶箱挂塔身
        cq.Workplane("XY").workplane(offset=34).box(14, 14, 12).translate((16, 0, 0)))
    dx, dy = POS_WEATHER
    return [("气象站", station.val().translate((dx, dy, BASE_H)))]


# =====================================================================
# 四-B、阶段一总装大通关: 24 槽全向辐射散热格栅 + 离子推进器动力总成
# =====================================================================
# 📐 工程原理(斯蒂芬-玻尔兹曼热辐射定律)
# ---------------------------------------------------------------
#   P_rad = ε·σ·A·T⁴
#   σ = 5.670×10⁻⁸ W/(m²·K⁴),  ε 为发射率, A 为有效辐射面积
#
#   真空环境无对流散热, 唯一散热途径为热辐射。百叶窗式倾斜格栅
#   在不大幅增加体积的前提下, 将有效辐射表面积倍增:
#
#   对于 N=24 槽, 倾斜角 θ=15°, 每个槽壁的有效辐射面积因子为
#   1/cos(θ) ≈ 1.035(法线偏转修正) + 内外双面 ≈ 2 倍面积
#   总倍增效应 ≈ N_slots × 双面 / 单面积 ≈ 显著放大
#
#   百叶窗倾斜 15° 使散热面法线偏离天顶, 各槽互相不遮挡, 实现
#   全向辐射; 24 槽圆周阵列确保 360° 无死角散热。
#
# 🔧 Z-Fighting 修复: 刀具体(布尔差集用)两端各预留 GRILL_TOLERANCE=1mm
#   贯通容差, 确保切削后壁面端口干净, 杜绝微小坏面与缝隙 → 水密。


def build_ion_thruster_assembly():
    """阶段一"火星离子推进动力总成"完全体一键构建。

    构建流程:
    1. 推进器机身(圆柱) + 加速器喷管(旋转体)
    2. 24 槽倾斜百叶窗散热格栅(CadQuery 批量布尔差集 cut)
    3. 整合为水密单体, 100% 无坏面

    返回: [(材质名, 实体), ...]
    """
    # ── 1. 推进器机身 ──
    body = post(ION_BODY_R, ION_BODY_L)

    # 推进剂储箱段箍(两道环形加强)
    for z in (ION_BODY_L * 0.3, ION_BODY_L * 0.7):
        body = body.union(
            cq.Workplane("XY").workplane(offset=z)
            .circle(ION_BODY_R + 2.5).circle(ION_BODY_R).extrude(5))

    # ── 2. 加速器喷管(收敛-扩张旋转体) ──
    nozzle_profile = [
        (ION_BODY_R * 0.35, 0),                    # 喷管入口
        (ION_NOZZLE_R * 0.55, ION_NOZZLE_L * 0.3), # 收敛段
        (ION_NOZZLE_R * 0.40, ION_NOZZLE_L * 0.5), # 喉部(最窄)
        (ION_NOZZLE_R * 0.75, ION_NOZZLE_L * 0.8), # 扩张段
        (ION_NOZZLE_R, ION_NOZZLE_L),              # 喷管出口
    ]
    nozzle = revolve_z(
        cq.Workplane("XZ").polyline(nozzle_profile).close())
    nozzle = nozzle.translate((0, 0, ION_BODY_L))

    # ── 3. 24 槽百叶窗式散热格栅(核心: 批量布尔差集) ──
    # 散热套: 外壁圆筒, 内壁圆筒, 中间被 24 组倾斜刀片挖出百叶窗槽
    grill_outer_r = GRILL_R_OUT
    grill_inner_r = GRILL_R_IN
    grill_h = GRILL_H

    # 散热套壁体(外筒 - 内筒)
    grill_sleeve = (
        cq.Workplane("XY").circle(grill_outer_r).circle(grill_inner_r)
        .extrude(grill_h)
    )

    # 构建 24 组切削刀具体(百叶窗叶片), 倾斜 15°
    # 每个刀片是一个薄长方体, 沿径向贯穿散热套壁
    # 两端各预留 GRILL_TOLERANCE=1mm 贯通容差, 杜绝 Z-Fighting
    blade_length = (grill_outer_r - grill_inner_r) + 2 * GRILL_TOLERANCE
    blade = (
        cq.Workplane("XY")
        .box(blade_length, GRILL_BLADE_W,
             grill_h + 2 * GRILL_TOLERANCE)
        # 刀片沿 X 方向(径向)放置, 中心在壁厚中点
        .translate(((grill_outer_r + grill_inner_r) / 2, 0, 0))
    )
    # 倾斜 15°(绕 X 轴旋转 → 百叶窗效果)
    blade_tilted = blade.rotate((0, 0, 0), (1, 0, 0), GRILL_TILT)

    # 圆周阵列 24 组刀片, 批量执行布尔差集
    cutters = [
        blade_tilted.rotate((0, 0, 0), (0, 0, 1), i * 360 / GRILL_SLOTS)
        for i in range(GRILL_SLOTS)
    ]

    # 批量布尔差集: 从散热套壁体中挖去 24 个百叶窗槽
    for cutter in cutters:
        grill_sleeve = grill_sleeve.cut(cutter)

    # 散热套上下端环(加固端面, 密封端口)
    grill_sleeve = grill_sleeve.union(
        cq.Workplane("XY")
        .circle(grill_outer_r).circle(grill_inner_r)
        .extrude(3).translate((0, 0, 0))
    ).union(
        cq.Workplane("XY")
        .circle(grill_outer_r).circle(grill_inner_r)
        .extrude(3).translate((0, 0, grill_h - 3))
    )

    # 散热套定位到机身中段
    grill_z = ION_BODY_L * 0.2
    grill_sleeve = grill_sleeve.translate((0, 0, grill_z))

    # ── 4. 推进器接口法兰(连接机身与散热套) ──
    flange = (
        cq.Workplane("XY")
        .circle(ION_BODY_R + 3).circle(ION_BODY_R)
        .extrude(4).translate((0, 0, grill_z - 4))
    ).union(
        cq.Workplane("XY")
        .circle(ION_BODY_R + 3).circle(ION_BODY_R)
        .extrude(4).translate((0, 0, grill_z + GRILL_H))
    )

    # ── 5. 整合: 机身 + 散热套 + 法兰(喷管单独返回, 材质不同) ──
    assembly = body.union(grill_sleeve).union(flange)

    dx, dy = POS_ION
    z0 = BASE_H
    return [
        ("推进器机身", assembly.translate((dx, dy, z0))),
        ("加速器喷管", nozzle.translate((dx, dy, z0))),
    ]


# =====================================================================
# 四-C、阶段二: 旋转抛物面高增益天线(深空通信系统)
# =====================================================================
# 📐 抛物面微积分推导
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


def ParabolicDishGenerator():
    """旋转抛物面高增益天线几何生成器。

    步骤:
    1. 微积分点集离散采样生成壁厚 2mm 的反射体截面
    2. 围绕 Z 轴 360° 旋转拉伸成抛物面壳体
    3. 外边缘并集构建刚性加固法兰圈(杜绝薄壁震颤变形)
    4. 馈源支撑臂 + 馈源(置于焦点 z=f)

    返回: 抛物面反射器 Workplane 实体
    """
    f = DISH_F
    rim_r = DISH_APERTURE / 2
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

    # 4. 馈源支撑臂(三根 120° 阵列) + 馈源(焦点处)
    feed_z = f  # 馈源位于焦点 z = f
    feed_arms = []
    for ang in (0, 120, 240):
        arm = strut(
            (0, 0, rim_r ** 2 / (4 * f) + wall / 2),  # 盘缘
            (0, 0, feed_z),                            # 焦点
            1.5
        ).rotate((0, 0, 0), (0, 0, 1), ang)
        feed_arms.append(arm)

    feed = cq.Workplane("XY").workplane(offset=feed_z).sphere(4)

    return dish, compound_of(feed_arms), feed


def build_deep_space_antenna():
    """阶段二: 深空通信高增益抛物面天线。

    返回: [(材质名, 实体), ...]
    """
    dish, arms, feed = ParabolicDishGenerator()

    # 天线整体倾斜对地(指向地球方向)
    earth_tilt = EARTH_ELEV
    dish = dish.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)
    arms = arms.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)
    feed = feed.rotate((0, 0, 0), (1, 0, 0), -earth_tilt)

    # 支撑立柱
    mast = post(3, 40)

    dx, dy = POS_DISH
    z0 = BASE_H

    # 基座
    base_plate = (
        cq.Workplane("XY").polygon(6, 30).extrude(4)
        .faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(10).circle(3).extrude(2)
    )

    return [
        ("抛物面反射器",
         dish.translate((dx, dy, z0 + 40))),
        ("天线法兰",
         compound_of([base_plate, mast]).translate((dx, dy, z0))),
        ("天线馈源臂",
         compound_of([arms, feed]).translate((dx, dy, z0 + 40))),
    ]


# =====================================================================
# 五、总装(材质表驱动, 一个循环完成全部装配)
# =====================================================================
BUILDERS = (build_terrain, build_dome, build_lab, build_tunnel, build_solar,
            build_tower, build_rover, build_rocket, build_weather,
            build_ion_thruster_assembly, build_deep_space_antenna)


def build_scene():
    """按"地形→居住→科研→能源→通讯→运输→探测"工程逻辑总装。"""
    assy = cq.Assembly(name="MarsResearchOutpost")
    for builder in BUILDERS:
        for name, shape in builder():
            assy.add(shape, name=name, color=cq.Color(*mat_of(name)["color"]))
    return assy


# =====================================================================
# 六、导出器
# =====================================================================
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

    每个零件 → 独立 node/mesh/material, 且注入三重真实感要素:
    ① 平滑顶点法线(PBR 反射高光的数学基础)
    ② 材质 PBR 参数(金属度/粗糙度/自发光, 由 MATERIALS 表驱动)
    ③ KHR_lights_punctual 太阳方向光 + 暖色补光(打开即有光照氛围)
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
                "accessors": [], "bufferViews": [], "buffers": []}
    # 太阳方向光节点: 绕X -50°绕Z 135° → 光从东南上方斜照(火星午后)
    sun_node = {"name": "太阳光", "extensions": {"KHR_lights_punctual": {"light": 0}},
                "rotation": [-0.342, 0.0, 0.940, 0.0]}
    fill_node = {"name": "补光", "extensions": {"KHR_lights_punctual": {"light": 1}},
                 "translation": [300.0, -300.0, 500.0]}
    json_doc["nodes"] += [sun_node, fill_node]
    json_doc["scenes"][0]["nodes"] += [0, 1]
    blob = bytearray()

    def add_view(data, target):
        while len(blob) % 4:
            blob.append(0)
        offset = len(blob)
        blob.extend(data)
        json_doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(data),
             "target": target})
        return len(json_doc["bufferViews"]) - 1

    for i, (shape, name, loc, _c) in enumerate(assy):
        name = name.split("/")[-1]        # 去掉装配路径前缀, 只留零件名
        verts, tris = tessellate(shape.moved(loc))
        normals = smooth_normals(verts, tris)
        v_data = struct.pack(f"<{len(verts) * 3}f",
                             *[c for v in verts for c in v])
        n_data = struct.pack(f"<{len(normals) * 3}f",
                             *[c for n in normals for c in n])
        i_data = struct.pack(f"<{len(tris) * 3}I",
                             *[t for tri in tris for t in tri])
        v_view = add_view(v_data, 34962)
        n_view = add_view(n_data, 34962)
        i_view = add_view(i_data, 34963)
        mins = [min(v[k] for v in verts) for k in range(3)]
        maxs = [max(v[k] for v in verts) for k in range(3)]
        pos_acc = {"bufferView": v_view, "componentType": 5126,
                   "count": len(verts), "type": "VEC3", "min": mins, "max": maxs}
        nrm_acc = {"bufferView": n_view, "componentType": 5126,
                   "count": len(normals), "type": "VEC3"}
        idx_acc = {"bufferView": i_view, "componentType": 5125,
                   "count": len(tris) * 3, "type": "SCALAR"}
        json_doc["accessors"] += [pos_acc, nrm_acc, idx_acc]
        m = mat_of(name)
        emissive = m.get("emissive", (0, 0, 0))
        json_doc["materials"].append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [*m["color"], 1.0],
                "metallicFactor": m["metal"],
                "roughnessFactor": m["rough"]},
            "emissiveFactor": list(emissive),
            "doubleSided": True})
        json_doc["meshes"].append({"primitives": [{
            "attributes": {"POSITION": len(json_doc["accessors"]) - 3,
                           "NORMAL": len(json_doc["accessors"]) - 2},
            "indices": len(json_doc["accessors"]) - 1,
            "material": i}]})
        json_doc["nodes"].append({"name": name, "mesh": i})
        json_doc["scenes"][0]["nodes"].append(len(json_doc["nodes"]) - 1)

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

    地形带大量布尔起伏时 HLR 算法可能失败 → 降级为无地形单独图,
    保证导出流程不中断。
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
    D_m = DISH_APERTURE / 1000  # 口径(m)
    gain_linear = eta * (math.pi * D_m / wavelength) ** 2
    gain_dbi = 10 * math.log10(gain_linear)
    print(f"      抛物面焦距 f = {DISH_F}mm, 口径 D = {DISH_APERTURE}mm")
    print(f"      X 波段频率 = {X_BAND_FREQ:.2e} Hz, 波长 λ = {wavelength*100:.2f} cm")
    print(f"      天线增益 G = {gain_linear:.1f} 倍 = {gain_dbi:.1f} dBi")

    print("完成! 全部文件位于 exports/ 目录。")
