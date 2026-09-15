# Common Scripts for Long-Read Genomics

**English** | [简体中文](README.cn.md)

Small scripts for batch sequence statistics with **SeqKit**, FASTQ cleaning with **fastplong**, and primer-pair trimming from CSV with **Cutadapt**.

Before running a script, make sure its corresponding tool (`seqkit`, `fastplong`, or `cutadapt`) is available in the local Terminal. The scripts use Python 3 and its standard library. Run the examples below from the repository root.

## Files

| File | Purpose |
| --- | --- |
| [Seqkit/Stats/seqkit_stats.py](Seqkit/Stats/seqkit_stats.py) | Batch FASTA/FASTQ statistics using `seqkit stats -a` |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | Batch FASTQ filtering and trimming, with reports and logs |
| [Cutadpt/cutadapt_trim.py](Cutadpt/cutadapt_trim.py) | Batch primer-pair trimming from CSV, with file-level concurrency and Cutadapt multi-core processing |
| [Cutadpt/primer_hla.csv](Cutadpt/primer_hla.csv) | HLA primer-pair table; both primer sequences are stored in 5′→3′ orientation |
| [Cutadpt/README.md](Cutadpt/README.md) | Detailed Cutadapt usage and matching rules in Chinese |
| [Seqkit/Stats/stats_v1.ipynb](Seqkit/Stats/stats_v1.ipynb) | Notebook used during development of the statistics script |
| [Fastplong/clean_v1.ipynb](Fastplong/clean_v1.ipynb) | Notebook used during development of the cleaning script |

The `.py` files are the main entry points. The notebooks contain local paths and development code; edit them before use. The commands and parameters below describe the `.py` scripts.

## SeqKit: batch sequence statistics

Run statistics for sequence files placed directly in `./input`:

```bash
python Seqkit/Stats/seqkit_stats.py -i ./input -o ./results -n raw -p 4 -j 3
```

The script runs `seqkit stats -a` once per file and writes a separate report for each sample. Reports are not merged into a combined table.

### Input files

The filename filter recognizes these sequence extensions, case-insensitively:

```text
.fa  .fasta  .fas  .fsa  .fna  .ffn  .faa  .frn  .fq  .fastq
```

Each may be uncompressed or followed by `.gz`, `.xz`, `.zst`, `.bz2`, or `.lz4`. These are the wrapper's filename filters; actual decoding support depends on the installed SeqKit version. Subdirectories are not scanned.

### Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `-i`, `--input` | Required | Input directory |
| `-o`, `--output` | Required | Output root directory |
| `-n`, `--name` | `raw` | Single subdirectory name under the output root |
| `-p`, `--processes` | `4` | Maximum concurrent SeqKit processes |
| `-j`, `--threads` | `max(2, (os.cpu_count() or 1) // 3)` | Threads per SeqKit process |
| `-h`, `--help` | — | Show help |

`-a` is always included in the underlying SeqKit command; it is not a separate option for this wrapper.

### Output

For inputs `sample01.fastq.gz` and `sample02.fasta`:

```text
results/
└── raw/
    ├── sample01.stats.txt
    └── sample02.stats.txt
```

Each report contains the statistics produced by the installed `seqkit stats -a`. Tool messages are printed to the Terminal; this script does not create separate log files. A tool failure causes a nonzero script exit; other submitted tasks may still finish, so a failed batch can leave completed or partial reports.

## fastplong: batch FASTQ cleaning

Run cleaning with the installed fastplong version's default filtering settings:

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -p 4 -j 3
```

Set a minimum read length of 1,000 bp and minimum mean read quality of 10:

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -n clean -p 4 -j 3 -l 1000 -m 10
```

Enable quality trimming at both ends:

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -n trimmed -p 4 -j 3 -5 -3 -W 4 -M 20
```

These thresholds are usage examples; choose values appropriate for your data and downstream analysis.

### Input files

The script accepts `.fastq`, `.fq`, `.fastq.gz`, and `.fq.gz`, case-insensitively. It scans only the input directory, without recursion, and processes each file independently.

### Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `-i`, `--input` | Required | Input directory |
| `-o`, `--output` | `.` | Output root directory |
| `-n`, `--name` | `fastplong` | Subdirectory name under the output root |
| `-p`, `--processes` | `4` | Maximum concurrent fastplong processes |
| `-j`, `--threads` | `3` | Threads per fastplong process |
| `-h`, `--help` | — | Show help |

Only explicitly supplied filtering and trimming options are passed to fastplong. Otherwise, defaults come from the installed version. The default-value descriptions in the script's help refer to fastplong 0.7.0.

| Filtering option | Description |
| --- | --- |
| `-q`, `--qualified_quality_phred` | Minimum quality for a base to count as qualified |
| `-u`, `--unqualified_percent_limit` | Maximum percentage of unqualified bases; 0–100 |
| `-m`, `--mean_qual` | Minimum mean read quality |
| `-l`, `--length_required` | Minimum read length in bp |
| `--length_limit` | Maximum read length in bp |
| `--n_percent_limit` | Maximum percentage of N bases; 0–100 |
| `--n_base_limit` | Maximum number of N bases |
| `-5`, `--cut_front` | Enable quality trimming at the read front |
| `-3`, `--cut_tail` | Enable quality trimming at the read tail |
| `-W`, `--cut_window_size` | Trimming window size, 1–1000 bp; use with `-5` or `-3` |
| `-M`, `--cut_mean_quality` | Trimming window quality threshold, 1–30; use with `-5` or `-3` |
| `-Q`, `--disable_quality_filtering` | Disable quality filtering, including N-base filtering |
| `-L`, `--disable_length_filtering` | Disable length filtering |
| `-A`, `--disable_adapter_trimming` | Disable adapter trimming |

`-q` is a per-base threshold; `-m` is a mean read quality threshold. In this wrapper, `-n` names the output subdirectory and `-j` sets threads per process; short options may have different meanings in native fastplong.

### Output

For `-o ./results` with the default `-n fastplong`:

```text
results/
└── fastplong/
    └── sample01/
        ├── sample01_fastplong.fastq.gz
        ├── sample01_fastplong.html
        ├── sample01_fastplong.json
        └── sample01_fastplong.log
```

The files contain cleaned reads, an HTML quality-control report, a JSON report, and a log recording the command and tool output. Each additional sample has its own directory. A sample failure is logged while other samples continue; the script prints success/failure counts and returns a nonzero exit code if any sample fails. Failed tasks may leave partial results.

## Cutadapt: batch primer-pair trimming

Process long amplicon reads that span both primers, using the existing HLA primer table:

```bash
python Cutadpt/cutadapt_trim.py -i ./input -p Cutadpt/primer_hla.csv -o ./results/cutadapt -w 4 -j 2
```

This runs up to four files concurrently, with two cores per Cutadapt process. For one large file, use `-w 1 -j 8`. Omitting both options uses `-w 4 -j 1`.

### Inputs and parameters

The script scans one directory level for `.fastq`, `.fq`, `.fastq.gz`, and `.fq.gz`, case-insensitively. Each file is processed independently; R1/R2 files are not paired automatically.

| Parameter | Default | Description |
| --- | --- | --- |
| `-i`, `--input` | Required | Original FASTQ directory |
| `-p`, `--primers` | Required | Primer CSV file |
| `-o`, `--output` | `.` | Output directory; no tool-name subdirectory is added automatically |
| `-w`, `--workers` | `4` | Maximum concurrent files |
| `-j`, `--threads` | `1` | Cores per Cutadapt process |
| `-h`, `--help` | — | Show help |

`-w` and `-j` must be positive integers; this wrapper does not accept `-j 0`. Unlike the other two wrappers, **`-p` specifies the primer table; use `-w` for file concurrency**.

### Primer CSV

One row defines one primer pair. The four columns `forward_name`, `forward_seq`, `reverse_name`, and `reverse_seq` are required; `target` is optional. Column order does not matter.

```csv
target,forward_name,forward_seq,reverse_name,reverse_seq
HLA-A,HLA-A_F_2,AGTCCCAGCCTTGGGGATTC,HLA-A_R_2,CACAAAGGGAAGGGCAGGAA
```

Enter both primers as ordered, in **5′→3′** orientation. The script computes the reverse complement of R and supports IUPAC DNA codes (`ACGTRYSWKMBDHVN`). Multiple pairs may share a target; pairs are identified by `forward_name__reverse_name`. Missing values, invalid bases, duplicate pair names, or duplicate sequence pairs are rejected.

Use UTF-8 CSV; Excel's UTF-8 BOM is supported. XLSX is not read directly: save the worksheet as CSV UTF-8 first.

### Matching rules

- F must match the start of the read. Remove preceding library adapters before using this rule.
- Both F and the reverse complement of R from the **same pair** must match. The minimum R overlap is set to the full R length; Cutadapt's default error tolerance still applies.
- The script checks both read orientations with `--revcomp`. A better reverse-complement match changes the output orientation and adds Cutadapt's `rc` annotation to the read header.
- A matching linked pair trims both ends; any sequence after the R match is removed too. Valid matches from all primer pairs are written together, without splitting by HLA target.
- Reads that do not meet a pair's requirements are saved separately. This rule is not intended for reads that only reach one primer.

### Output

For `sample01.fastq.gz` with `-o ./results/cutadapt`:

```text
results/
└── cutadapt/
    └── sample01/
        ├── sample01.trimmed.fastq.gz
        ├── sample01.unmatched.fastq.gz
        ├── sample01.cutadapt.json
        └── sample01.cutadapt.log
```

The outputs contain trimmed reads, unmatched reads, a JSON report, and a log with the Cutadapt version, command, report, and run status. Omitting `-o` writes the sample directories directly under the current working directory.

Successful reruns replace previous results. If Cutadapt fails, temporary outputs are removed and any previous successful data/report files remain; the log records the current failure. Check the exit code and log before treating existing output as a result of the latest run. Other files continue processing, and any failure causes a nonzero batch exit code.

See [the detailed guide](Cutadpt/README.md) for matching and validation details. The tests exercise real Cutadapt on synthetic reads; they do not establish real HLA data retention, specificity, or typing accuracy.

## Shared usage notes

- Sample IDs are filenames with the recognized sequence and compression suffixes removed: `sample01.fastq.gz` becomes `sample01`.
- All three scripts reject duplicate sample IDs within a batch and allow existing results to be overwritten on reruns.
- SeqKit and fastplong use `-p` for concurrent processes; Cutadapt uses `-w`. All three use `-j` for per-process threads/cores. The configured total is up to `min(concurrency, number_of_files) × j`, excluding additional I/O/compression overhead. Set both values to fit your CPU allocation, especially for SeqKit's CPU-dependent default.
- If Nextflow or another workflow engine schedules samples, set this wrapper's file concurrency to 1 and let the workflow engine allocate resources.
- All three scripts scan only one directory level. fastplong and Cutadapt write per-sample subdirectories, so passing their output root directly to another wrapper will not discover the reads inside them.
- Cutadapt puts both `*.trimmed.fastq.gz` and `*.unmatched.fastq.gz` in each sample directory. For downstream analysis of matched reads, collect or link only `*.trimmed.fastq.gz` into a flat input directory. Passing the entire sample directory to fastplong or SeqKit would process both sets.
- Relative input and output paths are resolved from the current working directory.

Show the complete command-line help:

```bash
python Seqkit/Stats/seqkit_stats.py --help
python Fastplong/clean_v1.py --help
python Cutadpt/cutadapt_trim.py --help
```
