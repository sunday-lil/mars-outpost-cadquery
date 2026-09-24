# 赤星前哨 · 火星科研站 (Mars Research Outpost)

基于 **CadQuery** 的参数化三维建模作品（探秘火星逐梦太空 · 智能算法编程类 · 三维设计项目）。

以 2030 年代火星科考前哨站为蓝图，构建"一站多器"综合场景：主居住穹顶、科研实验舱、加压廊道、太阳能翼阵、深空通讯塔、六轮火星车、返回火箭着陆平台、气象观测站。

## 核心算法

- 极坐标放置、三角函数定向斜杆、海伦公式求弧半径
- 抛物线 `y = x²/(4f)` 旋转成抛物面天线
- 随机数撒布岩石（固定种子可复现）+ 禁布区防穿模
- 太阳能板倾角 = 90° − 太阳高度角（自动对日）

## 运行

```bash
python mars_outpost.py
```

输出（`exports/` 目录）：

| 文件 | 说明 |
|---|---|
| `mars_outpost.step` | 带彩色分层的工程交换文件 |
| `mars_outpost.glb` | Blender 即开即用，含 PBR 材质（自研 glTF 2.0 导出器，仅用标准库） |
| `mars_outpost.stl` | 整体网格 |
| `view_iso/top/front.svg` | 三视角工程线框图 |

全站参数化：修改脚本顶部【参数区】常数（如 `SUN_ELEV` 太阳高度角），模型自动重建，太阳能板与天线指向随之自动更新。

## 依赖

- Python 3.10+
- [CadQuery](https://cadquery.readthedocs.io/)（`pip install cadquery`）

## License

[MIT](LICENSE)
