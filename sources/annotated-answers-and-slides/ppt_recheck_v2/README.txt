本目录是本轮第2册的5题简算修订源。rules.json与post_export_overlay.json记录当前生效内容，公式均为真正OMML并带XeLaTeX生成SVG/PNG兼容分支。
公式源独立编译：进入formulas目录后，xelatex -interaction=nonstopmode -halt-on-error 所选.tex；字体相对路径../../fonts/，已实际逐个编译验证。
一次性定点升级脚本：python ppt_recheck_v2/build/patch_v2.py --source /path/to/上一版第2册.pptx --out /path/to/new-draft
所需上一版PPTX SHA256：06c352e213cf93115face9bc15505d478bb64069136fe879da48dfb6159ba941。当前交付第2册已应用这些修改，不得在其上重复运行升级脚本。上一版大PPTX不在源码包重复装入。
补丁还调用全项目ppt_simplify/build/patch_simplify.py及simplify_update/ppt_1_2/build/patch_owned.py；数学与动画引用保持规则在原脚本内。finalize_v2.mjs、finish_v2.py保留本轮工作路径供追溯，其他工作目录使用时应按实际目录调整；它们不是通用的一键重建器。
已实际渲染并逐张查看5张修改页，未在PowerPoint或WPS中实际放映。
