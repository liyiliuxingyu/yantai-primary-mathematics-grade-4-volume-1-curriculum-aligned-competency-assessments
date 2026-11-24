# 第一、二册简便计算更正记录

两册保持426页、479页。改动33张幻灯片：前三单元18题在原主法旁加“学完运算律后”提示；第四单元起7题调整为合适的简算。p008_s03已有完整合并除数方法，课件未重复添加。

- 最终课件：`final/`（与 `../deliverables/讲解课件/`同一SHA256）
- 采用规则：`rules.json`
- 可复现补丁：`build/patch_owned.py`、`build/common_patch.py`
- 逐式LaTeX及真正编译的PDF/SVG/PNG：`formulas/`
- 数学与包结构检查：`qa_checks.json`
- 最终检查：`qa_final.json`、`qa_receipts/`
- 更改页实际渲染与位置：`final_render_v1/`、`final_render_v2/`
- 已同步源目录内第1、2册metadata manifest；共享inventory更新值见`inventory_patch.json`。

复现需原始两册PPTX（SHA256见`qa_checks.json`）、已有源工程的`followup_style/ppt`、`ppt_builder`及`fonts/DroidSansFallback.ttf`，并安装lxml、PyMuPDF、XeLaTeX和Poppler。冻结规则足以复现课件，不必再次生成规则：

```sh
python build/patch_owned.py --source 原始课件目录 --rules rules.json --out 新输出目录
```

补丁以原对象ID作为原生组的动画锚点；新增对象使用新的唯一ID。所有原timing XML字节、原有ID/name顺序和无关ZIP成员均保持。新增提示与对应原对象同次点击显示。本次检查了33张更改页的静态渲染和数学等值；没有实际在PowerPoint或WPS播放，因此不声称这两款软件的播放测试通过。
