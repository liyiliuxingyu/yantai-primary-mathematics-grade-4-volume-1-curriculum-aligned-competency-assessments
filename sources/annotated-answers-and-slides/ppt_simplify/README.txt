本目录保存第3—6册本次简便计算修订的公式源与定点补丁。
权威数学内容为全项目accepted_changes.json及本目录post_export_overlay_3_6.json。
current_metadata只作题号、原位置、原点击组的结构索引；其历史formula数组不用于重打新课件。
所有原生动画timing原字节保留；新步骤在原简析点击组内同时显示，原有逐行点击组仍保留。
未在PowerPoint或WPS中实际放映；本次检查为ArtifactTool导入、静态渲染、包结构、几何与字体策略检查。
补丁输入须为上一版当前课件，SHA见qa/qa_package.json。
运行：python build/patch_simplify.py --rules rules_all.json --source 输入PPTX目录 --out 新输出目录 --assets formulas
运行时依赖全项目ppt_builder、followup_style/ppt辅助代码、fonts/DroidSansFallback.ttf及XeLaTeX/Poppler。
