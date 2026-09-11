# 长读长基因组学常用脚本

[English](README.md) | **简体中文**

收集长读长基因组学日常分析中使用的小型 Python 脚本和 Jupyter Notebook。目前的命令行工具用于批量调用 **fastplong**，对目录中的 FASTQ 文件进行过滤和剪切，并为每个输入文件生成清洗后的序列、质控报告和运行日志。

## 仓库内容

| 文件 | 用途 | 当前功能范围 |
| --- | --- | --- |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | 使用 fastplong 批量过滤和剪切 FASTQ | 命令行脚本，支持并发、过滤参数、质控报告和日志 |
| [Fastplong/clean_v1.ipynb](Fastplong/clean_v1.ipynb) | 早期批量清洗 Notebook | 需要手动修改路径，行为与命令行脚本有所不同 |
| [Seqkit/test.ipynb](Seqkit/test.ipynb) | SeqKit 基础调用示例 | 仅运行 `seqkit -h`，尚未实现序列统计或批量处理 |

## 环境依赖与安装

- **Python 3.8 或更高版本**：`clean_v1.py` 仅使用 Python 标准库。
- **fastplong**：批量清洗时需要安装，并确保可通过 `PATH` 调用。
- **SeqKit**：仅运行 SeqKit Notebook 时需要，同样需能通过 `PATH` 调用。
- **Jupyter Notebook 或 JupyterLab**：仅运行 Notebook 时需要。

克隆仓库并进入根目录：

```bash
git clone https://github.com/complex4died/Common-scripts-of-bio-in-Long-Read-genomics.git
cd Common-scripts-of-bio-in-Long-Read-genomics
```

如果已经安装 Conda，可以参考以下命令创建环境：

```bash
conda create -n longread-tools -c conda-forge -c bioconda python=3.11 fastplong
conda activate longread-tools
```

其他安装方式及平台支持情况见 [fastplong 官方安装说明](https://github.com/OpenGene/fastplong#get-fastplong)。

如需运行 Notebook，可额外安装：

```bash
conda install -c conda-forge -c bioconda seqkit jupyterlab
```

SeqKit 的其他安装方式见 [官方下载安装说明](https://bioinf.shenwei.me/seqkit/download/)。确认清洗工具和脚本能够调用：

```bash
fastplong --help
python Fastplong/clean_v1.py --help
```

脚本目前提供中文命令行帮助。以下示例均在仓库根目录执行。

## 快速开始

将输入 FASTQ 文件直接放在同一个目录下：

```text
input/
├── sample01.fastq.gz
├── sample02.fq.gz
└── sample03.fastq
```

批量清洗，同时运行最多 4 个 fastplong 进程，每个进程使用 3 个线程：

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -p 4 -j 3
```

脚本识别 `.fastq`、`.fq`、`.fastq.gz` 和 `.fq.gz` 后缀，不区分大小写。只扫描输入目录这一层，不递归查找子目录。每个文件单独处理，不会自动合并属于同一生物学样本的多个文件。

指定最短 read 长度、read 平均质量下限，并将输出子目录命名为 `clean`：

```bash
python Fastplong/clean_v1.py \
  -i ./input -o ./results -n clean \
  -p 4 -j 3 -l 1000 -m 10
```

开启 read 首尾两端的质量剪切：

```bash
python Fastplong/clean_v1.py \
  -i ./input -o ./results -n trimmed \
  -p 4 -j 3 -5 -3 -W 4 -M 20
```

这些阈值用于演示参数写法，实际设置需结合数据特点和下游分析要求选择。

## 参数说明

### 输入、输出与并发

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-i`、`--input` | 必填 | 输入目录，不递归扫描 |
| `-o`、`--output` | `.` | 输出根目录，相对路径以当前工作目录为基准 |
| `-n`、`--name` | `fastplong` | 输出根目录下的子目录名，使用单层目录名称 |
| `-p`、`--processes` | `4` | 同时运行的 fastplong 进程数上限 |
| `-j`、`--threads` | `3` | 每个 fastplong 进程使用的线程数 |
| `-h`、`--help` | — | 显示脚本帮助信息 |

配置的线程总数最多为 `min(并发进程数, 输入文件数) × 每进程线程数`。例如，`-p 4 -j 3` 最多同时运行 4 个进程，共配置 12 个线程。请根据分配到的 CPU 资源同时设置这两个参数；`-j` 并不是整个批次的线程总数。

### 过滤与剪切

只有显式指定的过滤参数才会传给 fastplong；未指定时，使用所安装 fastplong 版本的默认行为。脚本帮助中的默认值说明参考 **fastplong 0.7.0**，实际默认值及可用参数请以当前安装版本的帮助信息为准。

| 参数 | 说明 |
| --- | --- |
| `-q`、`--qualified_quality_phred` | 将碱基判定为合格所需的最低质量值 |
| `-u`、`--unqualified_percent_limit` | 单条 read 中不合格碱基的比例上限，范围 0–100% |
| `-m`、`--mean_qual` | read 平均质量下限 |
| `-l`、`--length_required` | read 最短长度，单位 bp |
| `--length_limit` | read 最长长度，单位 bp |
| `--n_percent_limit` | N 碱基比例上限，范围 0–100% |
| `--n_base_limit` | N 碱基数量上限 |
| `-W`、`--cut_window_size` | 首尾质量剪切窗口，范围 1–1000 bp，配合 `-5` 或 `-3` 使用 |
| `-M`、`--cut_mean_quality` | 首尾剪切窗口质量阈值，范围 1–30，配合 `-5` 或 `-3` 使用 |
| `-Q`、`--disable_quality_filtering` | 关闭质量过滤，包括 N 碱基过滤 |
| `-L`、`--disable_length_filtering` | 关闭长度过滤 |
| `-A`、`--disable_adapter_trimming` | 关闭接头剪切 |
| `-5`、`--cut_front` | 开启 read 首端质量剪切 |
| `-3`、`--cut_tail` | 开启 read 尾端质量剪切 |

`-q` 设置的是**单碱基质量阈值**，`-m` 设置的是 **read 平均质量阈值**。在本脚本中，`-n` 用于输出子目录名，`-j` 用于每进程线程数；这些短参数与 fastplong 原生命令中的含义不一定相同。脚本仅封装了上表所列参数，并未开放 fastplong 的全部选项。

## 输出结构

使用 `-o ./results` 并保留默认的 `-n fastplong` 时：

```text
results/
└── fastplong/
    ├── sample01/
    │   ├── sample01_fastplong.fastq.gz
    │   ├── sample01_fastplong.html
    │   ├── sample01_fastplong.json
    │   └── sample01_fastplong.log
    └── sample02/
        └── ...
```

- `.fastq.gz`：清洗后的 reads。
- `.html`：可通过浏览器查看的 fastplong 质控报告。
- `.json`：便于下游解析的 fastplong 报告。
- `.log`：实际执行的命令，以及合并记录的标准输出和标准错误。

样本名由输入文件名去掉已识别的 FASTQ 后缀得到，例如 `sample01.fastq.gz` 对应 `sample01`。不指定 `-o` 和 `-n` 时，结果位于当前工作目录下的 `./fastplong/`。

重复运行时允许覆盖同名结果。同一批次内如果存在重复样本名，例如同时出现 `sample01.fastq` 和 `sample01.fastq.gz`，脚本会在处理前报错。脚本还会检查生成的输出路径是否与本批次输入文件冲突，避免覆盖输入。

## 失败处理与常见问题

脚本会输出成功和失败数量。单个 fastplong 任务失败后会记录错误，其他文件继续处理。批次结束时，全部成功返回退出码 `0`，任一文件失败返回 `1`；初始化检查失败返回 `1`，命令行参数错误由参数解析器返回 `2`。失败任务可能留下不完整的输出文件，使用结果前应先检查日志。

| 问题 | 检查方法 |
| --- | --- |
| 找不到 fastplong | 激活安装了 fastplong 的环境，并在同一终端确认 `fastplong --help` 可运行 |
| 没有找到输入文件 | 检查输入路径和文件后缀；子目录中的文件不会被扫描 |
| 样本名无效或重复 | 确保去掉 FASTQ 后缀后的文件名非空且互不重复 |
| 某个样本处理失败 | 查看对应的 `_fastplong.log`，检查输入完整性、输出权限及 fastplong 参数兼容性 |

## 使用 Notebook

```bash
jupyter lab
```

- **`Fastplong/clean_v1.ipynb`**：包含本地绝对路径，运行前需要修改。其文件筛选列表较宽，不能据此认定 fastplong 支持列表中的全部格式。Notebook 中的 `threads` 变量没有传入 fastplong，且工具输出被丢弃，不会生成逐样本日志。如需使用本文描述的功能，请运行命令行脚本。
- **`Seqkit/test.ipynb`**：仅通过 Python 的 `subprocess` 模块调用 `seqkit -h`，用于初步确认 Notebook 环境能够调用 SeqKit。

仓库目前提供独立工具和示例，尚未包含完整的端到端分析流程或配套验证数据集。正式批量处理前，请先用代表性输入确认所安装工具及参数的实际运行结果。
