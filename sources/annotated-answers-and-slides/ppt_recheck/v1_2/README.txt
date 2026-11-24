本目录为本轮第1册7题、8张幻灯片的当前窄改源。数学规则在rules_v1.json；实际最终对象在post_export_overlay_v1.json；改页的current_metadata/volume01已据最终OMML同步。
新增公式是真正原生OMML，兼有实际XeLaTeX生成的SVG/PNG；formulas目录的TeX字体为相对路径../../../fonts/，在本目录formulas内逐个运行xelatex 文件名.tex可编译。全部38份已实际编译通过。
apply_v1.py用于从本轮输入的上一版第1册PPTX升级；需保留其bundle/讲解课件目录结构或自行改输入位置。本包不重复装入大PPTX，勿对已经应用补丁的最终PPTX再次运行。finalize_v1.mjs为实际结构、几何、字体及ArtifactTool导入检查程序。
原动画timing、原ID/name顺序保留；新增提示复用原点击组。静态修改页已逐张实看，未在PowerPoint/WPS实际放映。
