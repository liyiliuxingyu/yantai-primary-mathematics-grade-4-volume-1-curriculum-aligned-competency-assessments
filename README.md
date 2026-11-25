# 烟台地区小学数学四年级上册同步素养卷

*Yantai Primary Mathematics, Grade 4, Volume 1 — Curriculum-Aligned Competency Assessments*

本工程收录 27 套学生用卷、参考答案、六册讲解课件，以及对应的 LaTeX、TikZ 和课件构建源码。学生用卷按原书第 1–108 页的顺序拼成 54 个 A3 横向印刷面，每套试卷占一张 A3 纸的正反面。

## 试卷与参考答案

| 文件 | 用途 |
| --- | --- |
| [A3 纯试题版](pdfs/小学同步素养四年级上册数学_A3原生LaTeX纯试题.pdf) | 学生用卷。打印选择 A3、实际大小、双面短边翻转。 |
| [原卷版答案](pdfs/小学同步素养四年级上册数学答案.pdf) | 128 页，依原卷位置查看答案与解析。 |
| [小体积答案](pdfs/小学同步素养四年级上册数学答案（小体积版）.pdf) | 128 页，便于在手机上阅读。 |
| [ctexbook 重排答案](pdfs/小学同步素养四年级上册数学答案_ctexbook重排版.pdf) | 303 页，独立排版的答案册。 |
| [讲解课件](slides/) | 第 1 至第 6 册的可编辑 PowerPoint 文件。 |

可从[题目与课件对应索引](sources/annotated-answers-and-slides/全套题目与课件对应索引答案.csv)或[口算逐式索引](sources/annotated-answers-and-slides/口算逐式与课件对应索引答案.csv)查找讲解位置。

## 源码与编译

| 目录 | 内容与入口 |
| --- | --- |
| [A3 试题](sources/a3-exams/) | `main.tex` 为入口。`panels/` 对应原书各页，`figures/` 为 TikZ 题图。[编译说明与题文校订记录](sources/a3-exams/编译说明.txt) |
| [ctexbook 答案](sources/ctexbook-answers/) | `main.tex` 为入口，正文在 `chapters/`，题图在 `figures/`。[编译说明](sources/ctexbook-answers/编译说明.txt) |
| [原卷答案及课件工程](sources/annotated-answers-and-slides/) | 含答案文字、版面恢复脚本、逐题图形、课件构建脚本、字体资源和历次校订记录。[源码使用说明](sources/annotated-answers-and-slides/源码使用说明答案.txt) |

重编 A3 试题版时，安装含中文支持、Fandol 字体和 TikZ 的 TeX Live，在项目入口所在目录运行两遍 XeLaTeX。

```sh
cd sources/a3-exams
xelatex -halt-on-error -interaction=nonstopmode main.tex
xelatex -halt-on-error -interaction=nonstopmode main.tex
```

[早期答案 PDF](archive/earlier-answer-edition/)保留了原全套交付包中的版本。三个源码包均已展开并保留各自的相对路径，重复收录的课件和索引只存一份。[SHA256SUMS](SHA256SUMS) 列出所收录工程文件与成品的校验值。在仓库根目录运行 `sha256sum -c SHA256SUMS` 可核对文件内容。

公开副本保留了题图样式规范与编译参数。两份相同的样式规范中，指向私人参考文件的标识字段已置空，相应校验值已更新。

[接续说明](接续说明.md)列出了各版本的工程入口和题文校订记录。下载完整工程后，也可使用 Python 3.11 或更高版本运行 `python3 核验.py` 校验文件。
