# Common Scripts for Long-Read Genomics

**English** | [简体中文](README.cn.md)

Small scripts for batch sequence statistics with **SeqKit** and batch FASTQ cleaning with **fastplong**.

Before running, make sure `seqkit` and `fastplong` are available in the local Terminal used to launch the scripts. Run the examples below from the repository root.

## Files

| File | Purpose |
| --- | --- |
| [Seqkit/Stats/seqkit_stats.py](Seqkit/Stats/seqkit_stats.py) | Batch FASTA/FASTQ statistics using `seqkit stats -a` |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | Batch FASTQ filtering and trimming, with reports and logs |
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

## Shared usage notes

- Sample IDs are filenames with the recognized sequence and compression suffixes removed: `sample01.fastq.gz` becomes `sample01`.
- Both scripts reject duplicate sample IDs within a batch and allow existing results to be overwritten on reruns.
- `-p` controls concurrent external processes; `-j` controls threads per process. Up to `min(p, number_of_files) × j` threads are configured. For example, `-p 4 -j 3` configures up to 12 threads. Set both values explicitly to fit your CPU allocation, especially for SeqKit's CPU-dependent default.
- Both scripts scan only one directory level. fastplong outputs use per-sample subdirectories, so passing `./results/fastplong` directly to the SeqKit wrapper will not discover the cleaned reads inside them. Point SeqKit at an individual sample directory or collect the intended files in a flat input directory.
- Relative input and output paths are resolved from the current working directory.

Show the complete command-line help:

```bash
python Seqkit/Stats/seqkit_stats.py --help
python Fastplong/clean_v1.py --help
```
