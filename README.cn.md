# 长读长基因组学常用脚本

[English](README.md) | **简体中文**

用于日常序列处理的小型脚本，目前包含 **SeqKit 批量序列统计**、**fastplong 批量 FASTQ 清洗**和 **Cutadapt 按 CSV 引物对批量剪切**。

使用前，请确保本地 Terminal 中可以直接调用相应脚本需要的工具：`seqkit`、`fastplong` 或 `cutadapt`。脚本使用 Python 3 及其标准库。以下命令均在仓库根目录执行。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [Seqkit/Stats/seqkit_stats.py](Seqkit/Stats/seqkit_stats.py) | 使用 `seqkit stats -a` 批量统计 FASTA/FASTQ |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | 批量过滤和剪切 FASTQ，生成报告与日志 |
| [Cutadpt/cutadapt_trim.py](Cutadpt/cutadapt_trim.py) | 按 CSV 引物对批量剪切，支持文件并发和 Cutadapt 多核处理 |
| [Cutadpt/primer_hla.csv](Cutadpt/primer_hla.csv) | HLA 引物对表，正反向引物均以 5′→3′ 方向填写 |
| [Cutadpt/README.md](Cutadpt/README.md) | Cutadapt 的详细用法与匹配规则 |
| [Seqkit/Stats/stats_v1.ipynb](Seqkit/Stats/stats_v1.ipynb) | 序列统计脚本开发时使用的 Notebook |
| [Fastplong/clean_v1.ipynb](Fastplong/clean_v1.ipynb) | 清洗脚本开发时使用的 Notebook |

日常使用以 `.py` 脚本为入口。Notebook 包含本地路径和开发过程代码，使用前需要自行调整。本文的命令和参数均对应 `.py` 脚本。

## SeqKit：批量序列统计

统计直接放在 `./input` 目录下的序列文件：

```bash
python Seqkit/Stats/seqkit_stats.py -i ./input -o ./results -n raw -p 4 -j 3
```

脚本对每个文件执行一次 `seqkit stats -a`，每个样本单独生成统计报告，不会自动合并成一张汇总表。

### 输入文件

文件名筛选识别以下序列后缀，不区分大小写：

```text
.fa  .fasta  .fas  .fsa  .fna  .ffn  .faa  .frn  .fq  .fastq
```

各格式可以不压缩，也可以后接 `.gz`、`.xz`、`.zst`、`.bz2` 或 `.lz4`。这些是脚本的文件名筛选规则，实际解压和读取能力取决于安装的 SeqKit 版本。脚本不扫描子目录。

### 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-i`、`--input` | 必填 | 输入目录 |
| `-o`、`--output` | 必填 | 输出根目录 |
| `-n`、`--name` | `raw` | 输出根目录下的单层子目录名 |
| `-p`、`--processes` | `4` | 同时运行的 SeqKit 进程数上限 |
| `-j`、`--threads` | `max(2, (os.cpu_count() or 1) // 3)` | 每个 SeqKit 进程的线程数 |
| `-h`、`--help` | — | 显示帮助 |

底层 SeqKit 命令固定带有 `-a`，无需也不能向本脚本另外传入 `-a`。

### 输出

输入为 `sample01.fastq.gz` 和 `sample02.fasta` 时：

```text
results/
└── raw/
    ├── sample01.stats.txt
    └── sample02.stats.txt
```

每份报告包含当前安装的 `seqkit stats -a` 所输出的统计内容。工具信息直接显示在 Terminal 中，脚本不另存日志文件。工具执行失败时，脚本返回非零退出码；其他已提交的任务仍可能完成，因此失败批次可能留下已完成或不完整的报告。

## fastplong：批量 FASTQ 清洗

使用当前安装 fastplong 版本的默认过滤设置进行清洗：

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -p 4 -j 3
```

设置最短 read 长度为 1,000 bp，read 平均质量下限为 10：

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -n clean -p 4 -j 3 -l 1000 -m 10
```

开启 read 首尾两端质量剪切：

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -n trimmed -p 4 -j 3 -5 -3 -W 4 -M 20
```

以上阈值用于演示参数写法，实际设置请结合数据特点和下游分析要求选择。

### 输入文件

识别 `.fastq`、`.fq`、`.fastq.gz` 和 `.fq.gz`，不区分大小写。只扫描输入目录当前层，不递归查找子目录，每个文件独立处理。

### 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-i`、`--input` | 必填 | 输入目录 |
| `-o`、`--output` | `.` | 输出根目录 |
| `-n`、`--name` | `fastplong` | 输出根目录下的子目录名 |
| `-p`、`--processes` | `4` | 同时运行的 fastplong 进程数上限 |
| `-j`、`--threads` | `3` | 每个 fastplong 进程的线程数 |
| `-h`、`--help` | — | 显示帮助 |

只有显式指定的过滤和剪切参数才会传给 fastplong；未指定时沿用安装版本的默认行为。脚本帮助中的默认值说明参考 fastplong 0.7.0。

| 过滤参数 | 说明 |
| --- | --- |
| `-q`、`--qualified_quality_phred` | 将碱基判定为合格所需的最低质量值 |
| `-u`、`--unqualified_percent_limit` | 不合格碱基比例上限，范围 0–100% |
| `-m`、`--mean_qual` | read 平均质量下限 |
| `-l`、`--length_required` | read 最短长度，单位 bp |
| `--length_limit` | read 最长长度，单位 bp |
| `--n_percent_limit` | N 碱基比例上限，范围 0–100% |
| `--n_base_limit` | N 碱基数量上限 |
| `-5`、`--cut_front` | 开启 read 首端质量剪切 |
| `-3`、`--cut_tail` | 开启 read 尾端质量剪切 |
| `-W`、`--cut_window_size` | 剪切窗口大小，范围 1–1000 bp，配合 `-5` 或 `-3` 使用 |
| `-M`、`--cut_mean_quality` | 剪切窗口质量阈值，范围 1–30，配合 `-5` 或 `-3` 使用 |
| `-Q`、`--disable_quality_filtering` | 关闭质量过滤，包括 N 碱基过滤 |
| `-L`、`--disable_length_filtering` | 关闭长度过滤 |
| `-A`、`--disable_adapter_trimming` | 关闭接头剪切 |

`-q` 是单碱基质量阈值，`-m` 是 read 平均质量阈值。本脚本中的 `-n` 用于输出子目录名，`-j` 用于每进程线程数；短参数含义可能与 fastplong 原生命令不同。

### 输出

指定 `-o ./results`，保留默认的 `-n fastplong` 时：

```text
results/
└── fastplong/
    └── sample01/
        ├── sample01_fastplong.fastq.gz
        ├── sample01_fastplong.html
        ├── sample01_fastplong.json
        └── sample01_fastplong.log
```

四个文件分别保存清洗后的 reads、HTML 质控报告、JSON 报告，以及包含执行命令和工具输出的日志。每个样本使用独立目录。单个样本失败后会记录错误，其他样本继续处理；脚本最终输出成功和失败数量，任一样本失败时返回非零退出码。失败任务可能留下不完整的结果。

## Cutadapt：按引物对批量剪切

使用已有 HLA 引物表，处理能覆盖两端引物的扩增子长读段：

```bash
python Cutadpt/cutadapt_trim.py -i ./input -p Cutadpt/primer_hla.csv -o ./results/cutadapt -w 4 -j 2
```

该命令最多同时处理 4 个文件，每个 Cutadapt 进程使用 2 核。只有一个大文件时，可以使用 `-w 1 -j 8`。不指定这两项时，默认 `-w 4 -j 1`。

### 输入与参数

识别 `.fastq`、`.fq`、`.fastq.gz` 和 `.fq.gz`，不区分大小写；只扫描输入目录当前层。每个文件独立处理，不会自动将 R1/R2 配成双端数据。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-i`、`--input` | 必填 | 原始 FASTQ 文件夹 |
| `-p`、`--primers` | 必填 | 引物 CSV 文件 |
| `-o`、`--output` | `.` | 输出目录，不会自动增加工具名子目录 |
| `-w`、`--workers` | `4` | 同时处理的文件数上限 |
| `-j`、`--threads` | `1` | 每个 Cutadapt 进程使用的核数 |
| `-h`、`--help` | — | 显示帮助 |

`-w`、`-j` 都必须是正整数，本脚本不接受 `-j 0`。与另外两个脚本不同，**这里的 `-p` 是引物表，文件并发数使用 `-w`**。

### 引物 CSV

每行定义一对引物。必须有 `forward_name`、`forward_seq`、`reverse_name`、`reverse_seq` 四列；`target` 可选，列顺序不限。

```csv
target,forward_name,forward_seq,reverse_name,reverse_seq
HLA-A,HLA-A_F_2,AGTCCCAGCCTTGGGGATTC,HLA-A_R_2,CACAAAGGGAAGGGCAGGAA
```

正反向引物都填写订购时的 **5′→3′** 序列。脚本自动计算 R 的反向互补，支持 IUPAC DNA 简并碱基（`ACGTRYSWKMBDHVN`）。同一靶标可以有多对引物，每对使用 `forward_name__reverse_name` 标识。缺失值、非法碱基、重复引物对名称或重复序列对会报错。

使用 UTF-8 CSV，兼容 Excel 导出的 UTF-8 BOM。当前不直接读取 XLSX；请先另存为 CSV UTF-8。

### 匹配规则

- F 从 read 开头匹配；前面若仍有建库接头，应先去除。
- **同一对**的 F 和 R 的反向互补序列都必须匹配。R 的最小重叠设为完整 R 长度，仍沿用 Cutadapt 默认错误容忍规则。
- 启用 `--revcomp` 检查 read 的两个方向。反向互补匹配更好时，输出会改变方向，并由 Cutadapt 在 read 标题后添加 `rc` 标记。
- 匹配成功后剪掉两端引物，R 匹配位置后面的残余序列也会去除。所有引物对的匹配 reads 合并输出，不按 HLA 靶标拆分。
- 未满足配对规则的 reads 单独保存。这版规则不适用于只能读到一端引物的 reads。

### 输出

输入 `sample01.fastq.gz`，指定 `-o ./results/cutadapt` 时：

```text
results/
└── cutadapt/
    └── sample01/
        ├── sample01.trimmed.fastq.gz
        ├── sample01.unmatched.fastq.gz
        ├── sample01.cutadapt.json
        └── sample01.cutadapt.log
```

四个文件分别保存剪切后的 reads、未匹配 reads、JSON 报告，以及包含 Cutadapt 版本、命令、报告和本次状态的日志。省略 `-o` 时，各样本目录直接生成在当前工作目录下。

重复运行成功后会覆盖旧结果。Cutadapt 失败时清理临时产物，保留已有的成功数据和报告，日志记录本次失败；应检查退出码和日志，避免把旧结果当作本次结果。某个文件失败不停止其他文件，任一文件失败时批次返回非零退出码。

完整匹配与验证说明见 [Cutadapt 详细文档](Cutadpt/README.md)。测试使用真实 Cutadapt 处理合成 reads，不代表已验证真实 HLA 数据的保留率、特异性或分型准确性。

## 通用使用说明

- 样本名由文件名去掉已识别的序列及压缩后缀得到，例如 `sample01.fastq.gz` 对应 `sample01`。
- 三个脚本都会检查同一批次内的重复样本名；重复运行时允许覆盖同名结果。
- SeqKit、fastplong 使用 `-p` 控制进程并发数，Cutadapt 使用 `-w`；三个脚本均使用 `-j` 控制每进程线程或核数。计算资源配置最多为 `min(并发数, 文件数) × j`，不含读写、压缩等额外开销。应按分配到的 CPU 资源设置两者，尤其是默认线程数随 CPU 数量变化的 SeqKit 脚本。
- 如果由 Nextflow 等外层流程并行调度样本，将脚本内的文件并发数设为 1，由外层流程分配资源。
- 三个脚本都只扫描一层目录。fastplong 和 Cutadapt 将结果放在逐样本子目录中，直接将输出根目录传给另一个脚本，无法发现子目录里的 reads。
- Cutadapt 每个样本目录同时有 `*.trimmed.fastq.gz` 和 `*.unmatched.fastq.gz`。下游只分析匹配 reads 时，应仅将 `*.trimmed.fastq.gz` 收集或链接到平铺输入目录；把整个样本目录传给 fastplong 或 SeqKit 会同时处理这两类文件。
- 相对输入、输出路径均以当前工作目录为基准。

查看完整命令行帮助：

```bash
python Seqkit/Stats/seqkit_stats.py --help
python Fastplong/clean_v1.py --help
python Cutadpt/cutadapt_trim.py --help
```
