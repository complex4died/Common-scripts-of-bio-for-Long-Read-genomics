# CSV 引物对批量剪切

`cutadapt_trim.py` 从 CSV 读取多对引物，并行处理输入目录中的 FASTQ。
适用于一条 read 能覆盖两端引物的扩增子长读段，例如 ONT HLA 扩增子。
运行脚本的终端需要能调用 `python3` 和 `cutadapt`；脚本本身仅使用 Python 标准库。

## 使用

在本文件夹下运行：

```bash
python3 cutadapt_trim.py -i /path/to/raw_fastq -p primer_hla.csv -o /path/to/results -w 4 -j 2
```

省略 `-o` 时，输出到启动命令时的当前工作目录 `./`：

```bash
python3 cutadapt_trim.py -i /path/to/raw_fastq -p primer_hla.csv
```

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `-i` / `--input` | 原始 FASTQ 文件夹 | 必填 |
| `-p` / `--primers` | 引物 CSV 文件 | 必填 |
| `-o` / `--output` | 输出文件夹 | `./` |
| `-w` / `--workers` | 同时处理的文件数 | `4` |
| `-j` / `--threads` | 每个 Cutadapt 进程的计算核数 | `1` |

扫描输入目录第一层的 `.fastq`、`.fq`、`.fastq.gz`、`.fq.gz`，不扫描子目录。
每个文件独立处理；不合并测序分块、不自动配对 R1/R2。
错误率等未显式设置的参数沿用所安装版本的默认值。

## 并行

有两层并行：脚本使用线程池调度多个外部 Cutadapt 进程，Cutadapt 通过 `-j` 使用多个核。
Python 线程只负责等待外部进程，实际序列处理由 Cutadapt 执行。

- `-w 4 -j 2`：最多同时处理 4 个文件，每个进程使用 2 核，计算核数配置合计最多 8。
- `-w 1 -j 8`：一次处理一个文件，每个进程使用 8 核，适合单个大文件。
- `-w 1 -j 1`：串行、单核运行。
- 省略两项：默认 `-w 4 -j 1`；实际文件并发数为 `min(w, 文件数)`。

`-w`、`-j` 都必须是正整数。这一封装不接受 `-j 0` 自动占用所有核，避免多个文件进程各自申请整机核数。
脚本启动时打印实际文件并发数、每进程核数和两者乘积；日志和 JSON 记录每次 Cutadapt 使用的核数。
`w × j` 表示计算核数配置，不是操作系统总线程数的硬上限，读写和压缩可能有额外开销；也不会自动将用户显式配置缩减到机器核数。
如果由 Nextflow 等外层流程并行调度样本，将本脚本设为 `-w 1`，避免叠加样本级调度。

## 引物表

CSV 必须有以下四列，列顺序不限；`target` 可选，其他列忽略。

```csv
target,forward_name,forward_seq,reverse_name,reverse_seq
HLA-A,HLA-A_F_2,AGTCCCAGCCTTGGGGATTC,HLA-A_R_2,CACAAAGGGAAGGGCAGGAA
HLA-B,HLA-B_F3,AGGTGAATGGCTCTGAAAATTTGTCTC,HLA-B_R3,AGAGTTTAATTGTAATGCTGTTTTGACACA
```

- 每行是一对引物，F 和 R 都填写订购时的 **5′→3′** 序列。
- 脚本自动计算 R 的反向互补，支持 `ACGTRYSWKMBDHVN`，小写自动转大写。
- 同一 `target` 可以有多对引物，使用 `forward_name__reverse_name` 标识每一对。
- 缺失名称/序列、非法碱基、重复引物对名称或重复序列对会报错。
- 使用 UTF-8 CSV，兼容 Excel 导出的 UTF-8 BOM。这一版只接受 CSV；XLSX 请另存为 CSV UTF-8。

## 匹配规则

每对引物构建为 `-g '名称=^F...RC(R);min_overlap=R长度'`：

1. F 从 read 开头匹配；前面若仍有建库接头等序列，应先去除。
2. **同一对**的 F、RC(R) 都必须找到，才归入匹配结果。
3. R 的最小重叠设为完整 R 长度，避免仅凭末端几个碱基就认定匹配；仍按 Cutadapt 错误率规则允许测序错误。
4. R 后方可以有残余序列；匹配后剪去 R 及其后方序列，保留两引物之间的部分。
5. 启用 `--revcomp`，检查原始方向和反向互补方向。反向匹配更好时，输出会改变方向，并由 Cutadapt 在 read 标题后标记 `rc`。
6. 存在多个有效候选时由 Cutadapt 选择最佳匹配，不向多个引物对重复分发同一 read。

同一个输入文件中所有匹配成功的 reads 合并输出，不按 HLA 靶标拆分；JSON/日志包含各引物对的匹配统计。
未匹配 reads 另存，包括缺少任意一端或两端不属于同一指定引物对的 reads。
这版规则不适用于只能读到一端引物的短 reads。

## 输出

例如输入 `sample01.fastq.gz`：

```text
results/
└── sample01/
    ├── sample01.trimmed.fastq.gz
    ├── sample01.unmatched.fastq.gz
    ├── sample01.cutadapt.json
    └── sample01.cutadapt.log
```

- `trimmed`：满足配对规则、已去引物的 reads。
- `unmatched`：没有满足配对规则的 reads。
- `json`：Cutadapt 结构化报告。
- `log`：Cutadapt 版本、实际命令、文本报告及本次状态。命令中的临时输出路径在完成后被移动到上述最终文件名。

同名成功结果允许覆盖；原始输入和引物 CSV 不允许被输出覆盖。
Cutadapt 失败时，临时产物清理，旧的成功结果保留；日志记录本次失败，因此请同时检查退出码和日志，避免把旧结果误认为本次结果。
单文件失败不停止其他文件；按各文件实际完成顺序报告进度，只要有失败，脚本以非零退出码结束。
同目录中 `sample01.fq` 和 `sample01.fastq.gz` 会因样本名重复而报错。

## 验证

在能调用 Cutadapt 的环境中：

```bash
python3 -m unittest discover -s tests -v
```

测试使用真实 Cutadapt 和合成 FASTQ，覆盖多对引物、正反方向、简并碱基、缺端/错配对分流、默认输出、压缩输入、CSV 校验、失败时保留旧结果、多核参数和并行失败隔离。
文件调度另用同步屏障测试，验证任务确实同时运行且不超过设定的文件并发数；它不代表真实数据上的加速比。
合成数据验证不代表已验证真实 HLA 测序数据的保留率、特异性或分型准确性。

参考：[Cutadapt linked adapters](https://cutadapt.readthedocs.io/en/stable/guide.html#linked-adapters-combined-5-and-3-adapter)。
并行参数：[Cutadapt multi-core support](https://cutadapt.readthedocs.io/en/stable/reference.html#multi-core-support)。
