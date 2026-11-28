# -*- coding: utf-8 -*-
"""生成参赛必交文档：Word 版《作品创作说明》。

赛事：河北省中小学「人工智能 +」科学教育实践活动 · 探秘火星逐梦太空（三维设计项目）
要求：可编辑三维模型源文件 + Word 版作品创作说明（设计理念、作品介绍）
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(HERE, "exports")
OUT = os.path.join(EXPORTS, "作品创作说明_探秘火星逐梦太空.docx")

DARK = RGBColor(0x1F, 0x33, 0x46)
ACCENT = RGBColor(0xB4, 0x5F, 0x2A)

doc = Document()

# ── 页面与默认字体 ──
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.4)
sec.top_margin = sec.bottom_margin = Cm(2.2)

style = doc.styles["Normal"]
style.font.name = "宋体"
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
style.paragraph_format.line_spacing = 1.55
style.paragraph_format.space_after = Pt(4)


def H(text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    r.font.size = Pt(16 if level == 1 else 12.5)
    r.font.bold = True
    r.font.color.rgb = ACCENT if level == 1 else DARK
    return p


def P(text, indent=True, size=10.5, bold=False, color=None, align=None):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(21)
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    if color:
        r.font.color.rgb = color
    return p


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.45
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    return p


def table(rows, widths=None, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, val in enumerate(row):
            cells[j].text = ""
            para = cells[j].paragraphs[0]
            para.paragraph_format.line_spacing = 1.25
            para.paragraph_format.space_after = Pt(1)
            r = para.add_run(str(val))
            r.font.size = Pt(9.5)
            if i == 0 and header:
                r.font.bold = True
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


DIMG = os.path.join(EXPORTS, "_docimg")
os.makedirs(DIMG, exist_ok=True)


def _small(path, max_w=1500):
    """插入前压到 1500 px 宽，控制 docx 体积"""
    from PIL import Image
    out = os.path.join(DIMG, os.path.basename(path).replace(".png", ".jpg"))
    if not os.path.exists(out):
        im = Image.open(path).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(out, "JPEG", quality=86, optimize=True)
    return out


def figure(path, caption, width=15.5):
    if not os.path.exists(path):
        return
    doc.add_picture(_small(path), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption)
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x60, 0x60, 0x60)


# ══════════ 封面 ══════════
for _ in range(2):
    doc.add_paragraph()
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("作品创作说明")
r.font.name = "微软雅黑"
r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
r.font.size = Pt(30)
r.font.bold = True
r.font.color.rgb = ACCENT

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("赤星前哨 · 火星科研站")
r.font.name = "微软雅黑"
r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
r.font.size = Pt(20)
r.font.color.rgb = DARK

sub2 = doc.add_paragraph()
sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub2.add_run("—— 探秘火星逐梦太空 · 三维设计项目（初中组）")
r.font.size = Pt(12)
r.font.color.rgb = RGBColor(0x70, 0x70, 0x70)

for _ in range(3):
    doc.add_paragraph()

figure(os.path.join(EXPORTS, "v3_hero.png"), "作品效果图：赤星前哨主视图", 16.0)

for _ in range(2):
    doc.add_paragraph()

info = doc.add_table(rows=0, cols=2)
info.alignment = WD_TABLE_ALIGNMENT.CENTER
for k, v in (("作品名称", "赤星前哨 · 火星科研站"),
             ("参赛组别", "初中组（7–9 年级）"),
             ("参赛赛项", "探秘火星逐梦太空 · 三维设计项目"),
             ("作品类型", "三维模型 + 代码编程综合制作"),
             ("姓名", "＿＿＿＿＿＿＿＿"),
             ("学校", "＿＿＿＿＿＿＿＿"),
             ("指导教师", "＿＿＿＿＿＿＿＿"),
             ("提交日期", "＿＿＿＿年＿＿月＿＿日")):
    cells = info.add_row().cells
    cells[0].text = ""
    cells[1].text = ""
    r0 = cells[0].paragraphs[0].add_run(k)
    r0.font.size = Pt(12)
    r0.font.bold = True
    r1 = cells[1].paragraphs[0].add_run(v)
    r1.font.size = Pt(12)
    cells[0].width = Cm(4.0)
    cells[1].width = Cm(8.5)

doc.add_page_break()

# ══════════ 一、设计理念 ══════════
H("一、设计理念")

P("火星是人类最可能踏上的第二颗行星。载人登陆之后，第一件要解决的问题不是“能不能到”，"
  "而是“怎么活得下去”——低重力会让骨骼与肌肉持续流失，稀薄大气挡不住宇宙射线，"
  "红色尘暴每隔几年就会笼罩全球。因此我把作品的核心命题定为："
  "用一套可自我循环的基地，回答“人在火星上如何长期生存”。")

P("围绕这个命题，我提炼出四条设计原则，它们决定了后面每一个结构和参数：")

bullet("低重力必须被“制造”出来。火星表面重力只有地球的 38%，长期生活会导致骨密度下降。"
       "我采用旋转居住环，用离心加速度补足到 1 g 火星标准（3.72 m/s²），让居住舱内的体感接近地球。")

bullet("能源必须冗余。火星日照强度只有地球的 43%，且尘暴可遮挡阳光数周。"
       "所以能源区采用可调倾角的太阳能阵，倾角随太阳高度角自动调整；阵面分组，单组故障不影响全站。")

bullet("通信必须直达地球。火星与地球单程通信延迟 3–22 分钟，深空天线必须大口径、高增益，"
       "并具备独立的俯仰/方位调节能力，因此单独设置 Ø26 m 抛物面天线与馈源支撑结构。")

bullet("返回能力必须保留。前哨站不是单程票，必须有一座可以返回的运载火箭与配套发射塔架，"
       "这决定了发射区与主基地之间要留出足够的安全距离。")

P("在美学上，我刻意避开“堆满管线的科幻风”，转而追求“工程可信感”："
  "所有结构都能在现实工程手册里找到原型——Stanford Torus 居住环、ISS 式加压舱段、"
  "好奇号式摇臂悬架火星车、Vega 式桁架发射塔。颜色只用火星尘埃的赭红与设备金属的冷灰，"
  "让作品看起来像是真的建在火星上，而不是画出来的。")

# ══════════ 二、作品介绍 ══════════
H("二、作品介绍")

P("《赤星前哨》是一个完整的火星科考前哨站三维模型，按功能划分为六个区，由地表车辙道路串联成一个有机整体。")

figure(os.path.join(EXPORTS, "v3_site.png"), "图 1  全站俯瞰：六个功能分区与连接道路", 16.0)

H("2.1 分区构成", 2)

table([
    ["分区", "主要构成", "设计要点"],
    ["核心科研区", "旋转居住环 + 科研实验舱 + 加压廊道",
     "环体外径 81.2 m，环心半径 33.2 m，环管 Ø14.8 m；12 道管箍、16 扇真挖孔舷窗；中央轮毂 + 6 根辐条"],
    ["能源区", "可调倾角太阳能阵", "倾角 = 90° − 太阳高度角，自动对日；银框 + 蓝片阵列，分组冗余"],
    ["通信区", "深空通信塔 + Ø26 m 抛物面天线", "三柱桁架塔身；抛物面按 z = r²/(4f) 生成；馈源喇叭 + 三腿支撑"],
    ["发射区", "着陆平台 + 返回火箭 + 动力段", "八角平台；火箭含整流罩、24 槽散热格栅、收敛-扩张喷管"],
    ["探测区", "六轮火星车", "摇臂-转向架悬架 + 差速横杆；桅杆双目 + 高增益天线 + 采样机械臂"],
    ["环境监测区", "综合气象站", "主桅杆 + 三杯风速计 + 斯蒂文森百叶箱（温/湿/压探头）"],
    ["连接网络", "车辙道路", "5 条双轨辙带（轨距 2.8 m）+ 5 块 12×8 m 门口铺装"],
    ["生态区（新增）", "测地线穹顶温室", "Ø76 m 测地线桁架 + 透光膜 + 舱内作物（减面后 9.2 万面）"],
    ["原位资源区（新增）", "ISRU 制氧/推进剂站", "Ø80 m 站点：制氧塔 + LOX/LCH4 储罐 + 6 段低温管路接到着陆平台"],
], widths=[2.6, 5.4, 8.0])

H("2.2 尺度与单位", 2)

P("为了让所有设施处在同一个物理尺度下，我设定统一单位 u = 3.125（模型 1 mm 对应实际 0.625 m），"
  "全站尺寸、位置、间距同比放大，结构之间的相对方位保持不变。")

table([
    ["项目", "数值", "项目", "数值"],
    ["居住环外径", "81.2 m", "环心半径 R", "33.2 m"],
    ["环管直径", "14.8 m", "返回火箭高度", "131 m"],
    ["科研实验舱", "115 × 43 m", "火星车", "37 × 30 m"],
    ["场地地形", "1200 × 1200 m", "场平垫半径", "420 m"],
], widths=[4.2, 3.6, 4.2, 3.6])

figure(os.path.join(EXPORTS, "v3_ring.png"), "图 2  旋转居住环：真挖孔舷窗、内筒与舱内灯环、12 道管箍", 15.0)

H("2.3 旋转居住环", 2)

P("居住环是整个作品的技术核心。它是一个 Stanford Torus 式中空环壳，绕中央轮毂自转，"
  "环内壁的向心加速度就是人工重力。为了让舷窗不是“贴上去的贴纸”，"
  "我在环壁上用布尔运算真正挖穿了 16 个圆孔，每个孔配内外法兰与一段 Ø4.4 m × 13 m 的内筒，"
  "筒底加了一圈自发光灯环——从外面看进去能看到筒壁和暖光，像真正的舱窗。")

figure(os.path.join(EXPORTS, "v3_dusk.png"), "图 3  黄昏视角：低角度阳光下拉长的影子与亮起的舷窗灯", 16.0)

H("2.4 桁架体系", 2)

P("为了让“结构”经得起看，我把承力体系全部改成桁架：4 座格构支撑塔（4 肢 + 每节间 X 撑 + 节点球 + 节点板）、"
  "6 根辐条桁架（把原有辐条管包在方形桁架里，与 Stanford Torus 的“tube inside a truss”做法一致）、"
  "发射服务塔（14 节间 + 平台 + 爬梯）、实验舱外挂桁架（环箍 + 纵桁 + 斜撑）、天线背架（径向 + 环向）。")

P("杆件尺寸按 Euler 屈曲反推而不是凭感觉：主肢 Ø1400 钢管、长细比 λ = 167，"
  "σ_cr = π²E/λ² = 74 MPa，工作应力 35 MPa，安全系数 2.1；斜撑 Ø420，节点球 Ø550，"
  "节点板按资料公式 L/50 + L_member/1250 取 1.8 m。", indent=True)

figure(os.path.join(EXPORTS, "v4_dome.png"), "图 4  测地线穹顶温室：桁架骨架 + 透光膜 + 舱内作物", 15.0)

# ══════════ 三、科学性与物理校核 ══════════
H("三、科学性与物理校核")

P("作品的每一个关键尺寸都不是“看着差不多”，而是先算后建。以下计算全部基于实测几何。")

H("3.1 人工重力", 2)
P("环缘向心加速度：a = ω²R。要让环缘达到 1 g 火星标准（3.72 m/s²），"
  "所需角速度为 ω = √(a/R) = √(3.72 / 33.2) = 0.335 rad/s，即 3.20 rpm。", indent=True)

table([
    ["位置", "半径", "向心加速度", "相当于"],
    ["环外壁", "40.6 m", "4.55 m/s²", "1.22 g 火星"],
    ["环中心线", "33.2 m", "3.72 m/s²", "1.00 g 火星"],
    ["环内壁", "25.8 m", "2.90 m/s²", "0.78 g 火星"],
], widths=[4.0, 3.5, 4.0, 3.5])

P("横向重力梯度 1.65 m/s²，说明环管截面相对半径偏粗；若要更均匀，应加大 R 或减小管径。")

H("3.2 结构强度与屈曲", 2)
P("环向应力 σ = ρ·a·R = 7850 × 3.72 × 33.2 = 0.97 MPa。Q355 钢屈服强度 355 MPa，"
  "安全系数 366——强度远不是控制项。")
P("真正的控制项是薄壁屈曲：σ_cr = 0.6·E·t/R。取 60 mm 壁板时 σ_cr = 232 MPa，"
  "仍远大于 0.97 MPa，说明壁厚主要由气密与局部刚度决定，而不是强度。")

H("3.3 地基承载", 2)
P("环体甲板按 3 kPa 恒活载估算，总重约 28 MN。火星壤容许承载力约 80 kPa，"
  "需要 350 m² 承压面积；实际布置 4 座 Ø25 m 垫板，共 1960 m²，安全系数 5.6。")

H("3.4 尘暴风载", 2)
P("火星尘暴动压约 0.4 kPa，环体迎风面积约 1300 m²，水平力 0.52 MN，"
  "对 46 m 高的环面产生 24 MN·m 倾覆力矩；4 座垫板的抗倾覆能力约 700 MN·m，安全系数 29。")

H("3.5 参数汇总", 2)
table([
    ["校核项", "公式", "结果", "判定"],
    ["自转速度", "ω = √(a/R)", "3.20 rpm", "✓ 满足 1 g 火星"],
    ["环向应力", "σ = ρaR", "0.97 MPa", "✓ 安全系数 366"],
    ["屈曲应力", "σ_cr = 0.6Et/R", "232 MPa（t=60 mm）", "✓ 屈曲非控制项"],
    ["甲板拉力", "T = pR", "1.17 MN", "✓"],
    ["地基承载", "A = W/q", "需 350 m²，实给 1960 m²", "✓ 安全系数 5.6"],
    ["抗倾覆", "M = F·h", "24 MN·m vs 700 MN·m", "✓ 安全系数 29"],
], widths=[3.4, 4.4, 4.6, 4.6])

# ══════════ 四、技术实现 ══════════
H("四、技术实现")

P("作品采用“代码建模 + 高模精修”的双阶段流程，两个阶段都保留了可编辑源文件。")

H("4.1 第一阶段：CadQuery 参数化建模", 2)
P("整个基地由 Python 脚本 `mars_outpost.py`（1823 行）参数化生成。所有结构都由参数驱动："
  "环半径、管径、辐条数量、舱段长度、火箭级数、太阳能板倾角……修改参数即可重建模型。"
  "这一阶段输出 STEP（通用可编辑格式）与 GLB（用于渲染）。")

bullet("环壳：圆角矩形截面绕轴旋转 360°，布尔挖出舷窗孔与对接口")
bullet("廊道：样条曲线扫掠圆管，两端做收口")
bullet("抛物面：z = r²/(4f) 曲面 + 法兰圈 + 馈源喇叭")
bullet("火星车：摇臂-转向架悬架用铰点约束求解，12 齿车轮按齿形阵列")

H("4.2 第二阶段：Blender 高模与仿真材质", 2)
P("把 GLB 导入 Blender 后，做四件事：统一单位放大、补结构细节、换仿真材质、布光渲染。")

table([
    ["环节", "做法", "规模"],
    ["单位统一", "全站乘 u = 3.125，尺寸/位置/间距同比缩放", "210 个物体"],
    ["结构细节", "舷窗内筒与灯环、管箍、散热片、舱门、设备箱、管线、桁架、辙带", "新增 184 件"],
    ["材质", "漆色 → 沿 Z 拉伸的污渍流痕 → 菲涅尔边缘磨损，金属度/粗糙度联动", "6 套材质"],
    ["地形", "1200 m 高度场：4 层噪声 + 54 个撞击坑 + 风蚀波纹 + 砾石", "16 万顶点"],
    ["光照", "太阳主光 + 暖色补光 + 冷色轮廓光 + 体积尘，AgX 色彩管理", "白天/黄昏两套"],
], widths=[2.6, 9.8, 3.6])

H("4.3 质量检查", 2)
P("模型做完后我写了 4 个自动化检查脚本，一共 29 项检查，用来抓“人眼容易漏掉”的缺陷。")

table([
    ["轮次", "检查内容", "发现 → 修复"],
    ["第一轮（22 项）", "零面积面、重复顶点、松散几何、法线、陷地、悬空、重叠件、材质槽、命名、相机",
     "379 → 33"],
    ["第二轮（4 项）", "三角级自相交、UV 覆盖、拓扑一致性、渲染一致性", "5 类真实缺陷已修，自相交 92 → 11"],
    ["第三轮（3 项）", "孤岛翻转面、弦高误差、倒角超限、同材质色差", "翻转面 132 → 0，弦高 0 超标，色差 0.00"],
], widths=[3.4, 8.6, 4.0])

P("吸收外部资料后，又对新引入的 13 个模块补做了退化面清理与 UV 重建，缺陷数保持为 0。")

P("第三轮里还做了一次受控实验：同一材质、同朝向的两块平板，渲染色差为 0.00；"
  "换成不同朝向则相差 28.89。这证明材质本身是一致的，之前的色差来自光照角度——"
  "如果没有这个实验，我会误改材质。")

# ══════════ 五、源文件说明 ══════════
H("五、可编辑源文件说明")

P("提交的可编辑源文件包含三层，任选其一即可继续编辑：")

table([
    ["文件", "格式", "用途", "编辑方式"],
    ["mars_outpost.py", "Python 源码", "参数化重建整个基地", "修改参数后运行 CadQuery 即可重新生成"],
    ["mars_outpost.step", "STEP（AP214）", "通用三维交换格式", "SolidWorks / Fusion / Inventor / FreeCAD / Rhino 可直接打开编辑"],
    ["赤星前哨_火星科研站.blend", "Blender 工程", "高模、材质、灯光、相机", "Blender 5.3 打开，按集合分组编辑"],
    ["mars_outpost_v3.glb", "glTF 2.0", "网页/引擎查看", "Three.js / Unity / UE / Windows 3D 查看器"],
], widths=[5.6, 3.2, 5.4, 1.8 + 1.8])

P("模型按集合分为 6 组，方便定位：00_ENV_环境、01_CORE_原始设施、02_STR_结构件、"
  "03_FAC_设施细节、04_REF_人物参照、05_TCK_车辙道路。")

# ══════════ 六、创新点 ══════════
H("六、创新点")

bullet("先算后建：环半径、壁厚、垫板面积都由公式反推，不是凭感觉调尺寸。")
bullet("真挖孔舷窗：用布尔运算真正挖穿环壁并加内筒与灯环，而不是贴一张黑色圆片。")
bullet("程序化地形：4 层噪声叠加 54 个撞击坑，再用坡度遮罩混合尘与岩，1.2 km 地形一次生成。")
bullet("受控实验纠错：用同材质同朝向的对照实验，证明色差来自光照而非材质，避免误改。")
bullet("全流程可复现：从 CAD 参数到渲染，每一步都有脚本，任何人可以重跑出同样的结果。")

# ══════════ 七、演示视频（选交）══════
H("七、演示视频（选交）")

P("如提交演示视频，建议 3 分钟，节奏如下：")
table([
    ["时间", "画面", "解说要点"],
    ["0:00–0:20", "火星地平线推近，基地全貌浮现", "作品名称与命题：人在火星如何长期生存"],
    ["0:20–1:00", "环绕居住环，特写舷窗与管箍", "旋转产生人工重力，3.20 rpm 补足 1 g 火星"],
    ["1:00–1:40", "实验舱、廊道、车辙道路", "模块化加压舱段与地表交通网络"],
    ["1:40–2:20", "火箭、塔架、太阳能阵、天线", "返回能力、能源冗余、深空通信"],
    ["2:20–2:50", "黄昏转夜景，舷窗灯亮起", "昼夜循环下的能源与照明设计"],
    ["2:50–3:00", "字幕：参数与致谢", "关键参数一览"],
], widths=[3.2, 7.4, 5.4])

P("视频文件需 ≤ 50 MB、时长 ≤ 5 分钟，建议 1080p / H.264 编码。")

doc.save(OUT)
print("已生成:", OUT, os.path.getsize(OUT), "字节")
