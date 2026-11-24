本目录为第3、4册补充简便计算修订的活动补丁、公式源及实际语义覆盖记录。
输入为qa_final和inventory_patch中的上一版PPTX哈希；题干、未改页、原timing及原对象ID/name/order保留。
规则由make_rules.py生成，使用项目已有ppt_simplify/build/patch_simplify.py编译并窄改。
各公式源在formulas中，字体相对路径../../../fonts/从该目录解析。公式实际已以同一包内字体编译；路径便携化不改变公式内容。
原生OMML保留编辑能力，SVG/PNG是实际XeLaTeX编译的兼容分支。
已实际导入及逐张静态渲染检查14张改页，未在PowerPoint/WPS放映。
current_metadata历史formula数组不能用来直接覆盖当前成品；本次语义以post_export_overlay.json及本次规则为准。
