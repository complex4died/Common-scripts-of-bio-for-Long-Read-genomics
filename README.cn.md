# 长读长基因组学常用脚本

[English](README.md) | **简体中文**

用于日常序列处理的小型脚本，目前包含 **SeqKit 批量序列统计**和 **fastplong 批量 FASTQ 清洗**。

使用前，请确保运行脚本的本地 Terminal 中可以直接调用 `seqkit` 和 `fastplong`。以下命令均在仓库根目录执行。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [Seqkit/Stats/seqkit_stats.py](Seqkit/Stats/seqkit_stats.py) | 使用 `seqkit stats -a` 批量统计 FASTA/FASTQ |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | 批量过滤和剪切 FASTQ，生成报告与日志 |
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

## 通用使用说明

- 样本名由文件名去掉已识别的序列及压缩后缀得到，例如 `sample01.fastq.gz` 对应 `sample01`。
- 两个脚本都会检查同一批次内的重复样本名；重复运行时允许覆盖同名结果。
- `-p` 控制同时运行的外部进程数，`-j` 控制每个进程的线程数。线程配置总数最多为 `min(p, 文件数) × j`，例如 `-p 4 -j 3` 最多配置 12 个线程。建议根据分配到的 CPU 资源显式设置两者，尤其是默认线程数随 CPU 数量变化的 SeqKit 脚本。
- 两个脚本都只扫描一层目录。fastplong 将结果放在逐样本子目录内，因此直接把 `./results/fastplong` 传给 SeqKit 脚本，无法找到子目录中的清洗结果。应指向某个样本目录，或将待统计文件整理到同一个平铺目录。
- 相对输入、输出路径均以当前工作目录为基准。

查看完整命令行帮助：

```bash
python Seqkit/Stats/seqkit_stats.py --help
python Fastplong/clean_v1.py --help
```
