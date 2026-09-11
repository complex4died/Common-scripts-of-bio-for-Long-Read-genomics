# Common Scripts for Long-Read Genomics

**English** | [简体中文](README.cn.md)

A collection of small Python scripts and Jupyter notebooks for common tasks in long-read genomics. The current command-line tool runs **fastplong** across a directory of FASTQ files, producing cleaned reads, quality-control reports, and a log for each input file.

## Repository contents

| File | Purpose | Current scope |
| --- | --- | --- |
| [Fastplong/clean_v1.py](Fastplong/clean_v1.py) | Batch FASTQ filtering and trimming with fastplong | Command-line script with configurable concurrency, filtering, reports, and logs |
| [Fastplong/clean_v1.ipynb](Fastplong/clean_v1.ipynb) | Earlier notebook implementation of batch cleaning | Requires manual path edits; behavior differs from the command-line script |
| [Seqkit/test.ipynb](Seqkit/test.ipynb) | Basic SeqKit invocation example | Runs `seqkit -h`; does not yet implement sequence statistics or batch processing |

## Requirements and setup

- **Python 3.8 or later** for `clean_v1.py`, which uses only the Python standard library.
- **fastplong**, available on `PATH`, for batch cleaning.
- **SeqKit**, available on `PATH`, only for the SeqKit notebook.
- **Jupyter Notebook or JupyterLab**, only if you want to run the notebooks.

Clone the repository and enter its root directory:

```bash
git clone https://github.com/complex4died/Common-scripts-of-bio-in-Long-Read-genomics.git
cd Common-scripts-of-bio-in-Long-Read-genomics
```

For an existing Conda installation, an example environment is:

```bash
conda create -n longread-tools -c conda-forge -c bioconda python=3.11 fastplong
conda activate longread-tools
```

For other installation methods and platform availability, see the [official fastplong installation instructions](https://github.com/OpenGene/fastplong#get-fastplong).

Optional dependencies for the notebooks:

```bash
conda install -c conda-forge -c bioconda seqkit jupyterlab
```

See the [official SeqKit download instructions](https://bioinf.shenwei.me/seqkit/download/) for alternative installations. Confirm the cleaning tool and script are accessible:

```bash
fastplong --help
python Fastplong/clean_v1.py --help
```

The script's help text is currently in Chinese. All examples below run from the repository root.

## Quick start

Place input FASTQ files directly in one directory:

```text
input/
├── sample01.fastq.gz
├── sample02.fq.gz
└── sample03.fastq
```

Run batch cleaning with four concurrent fastplong processes and three threads per process:

```bash
python Fastplong/clean_v1.py -i ./input -o ./results -p 4 -j 3
```

The script accepts `.fastq`, `.fq`, `.fastq.gz`, and `.fq.gz` extensions, case-insensitively. It scans only the input directory, without recursion. Each file is processed independently; files belonging to the same biological sample are not merged automatically.

To set a minimum read length and mean read quality, and name the output subdirectory `clean`:

```bash
python Fastplong/clean_v1.py \
  -i ./input -o ./results -n clean \
  -p 4 -j 3 -l 1000 -m 10
```

To also enable quality trimming at both ends:

```bash
python Fastplong/clean_v1.py \
  -i ./input -o ./results -n trimmed \
  -p 4 -j 3 -5 -3 -W 4 -M 20
```

These thresholds illustrate usage; select filtering settings for your data and downstream analysis.

## Parameters

### Input, output, and concurrency

| Parameter | Default | Description |
| --- | --- | --- |
| `-i`, `--input` | Required | Input directory; not searched recursively |
| `-o`, `--output` | `.` | Output root directory, relative to the current working directory |
| `-n`, `--name` | `fastplong` | Subdirectory under the output root; use a single directory name |
| `-p`, `--processes` | `4` | Maximum number of fastplong processes running concurrently |
| `-j`, `--threads` | `3` | Threads passed to each fastplong process |
| `-h`, `--help` | — | Show the script's help message |

The configured thread total is at most `min(processes, input_file_count) × threads`. For example, `-p 4 -j 3` configures up to 12 threads across four processes. Choose both values to fit your allocated CPU resources; `-j` is not the total batch thread budget.

### Filtering and trimming

Only explicitly supplied filtering options are passed to fastplong. Otherwise, the installed fastplong version controls the defaults. The script's help descriptions refer to **fastplong 0.7.0**; check your installed version's help for actual defaults and supported options.

| Parameter | Description |
| --- | --- |
| `-q`, `--qualified_quality_phred` | Minimum quality for a base to be considered qualified |
| `-u`, `--unqualified_percent_limit` | Maximum percentage of unqualified bases in a read; 0–100 |
| `-m`, `--mean_qual` | Minimum mean read quality |
| `-l`, `--length_required` | Minimum read length in bases |
| `--length_limit` | Maximum read length in bases |
| `--n_percent_limit` | Maximum percentage of N bases; 0–100 |
| `--n_base_limit` | Maximum number of N bases |
| `-W`, `--cut_window_size` | End-trimming window size; 1–1000 bases; used with `-5` or `-3` |
| `-M`, `--cut_mean_quality` | End-trimming window quality threshold; 1–30; used with `-5` or `-3` |
| `-Q`, `--disable_quality_filtering` | Disable quality filtering, including N-base filtering |
| `-L`, `--disable_length_filtering` | Disable length filtering |
| `-A`, `--disable_adapter_trimming` | Disable adapter trimming |
| `-5`, `--cut_front` | Enable quality trimming at the front of each read |
| `-3`, `--cut_tail` | Enable quality trimming at the tail of each read |

`-q` sets a **per-base** threshold; `-m` sets a **mean read quality** threshold. In this wrapper, `-n` names the output subdirectory and `-j` sets threads per process. These short options do not necessarily have the same meanings in the native fastplong command. The wrapper exposes only the options listed above, not every fastplong option.

## Output structure

For `-o ./results` with the default `-n fastplong`:

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

- `.fastq.gz`: cleaned reads.
- `.html`: fastplong quality-control report for viewing in a browser.
- `.json`: fastplong report for downstream parsing.
- `.log`: executed command, followed by combined standard output and standard error.

The sample ID is the filename with its recognized FASTQ extension removed: `sample01.fastq.gz` becomes `sample01`. With no `-o` or `-n`, output goes to `./fastplong/` under the current working directory.

Existing results with the same names may be overwritten on reruns. Duplicate sample IDs in a batch, such as `sample01.fastq` and `sample01.fastq.gz`, are rejected before processing. The script also checks that generated output paths do not overwrite input files in the current batch.

## Failures and troubleshooting

The script prints a success/failure summary. An individual fastplong failure is logged, while other files continue processing. A completed batch exits with `0` if every file succeeds and `1` if any file fails. Setup failures return `1`; invalid command-line arguments are rejected by the argument parser with exit code `2`. Failed runs can leave partial output files, so check the log before using their results.

| Problem | What to check |
| --- | --- |
| fastplong cannot be found | Activate the environment containing fastplong and confirm `fastplong --help` works in the same terminal |
| No input files found | Check the input path and supported extensions; files in subdirectories are not discovered |
| Invalid or duplicate sample ID | Use nonempty, distinct filenames after removing FASTQ extensions |
| A sample fails | Read its `_fastplong.log` and check input integrity, output permissions, and fastplong option compatibility |

## Working with the notebooks

```bash
jupyter lab
```

- **`Fastplong/clean_v1.ipynb`** contains local absolute paths that must be changed before running. Its broad filename filter does not establish fastplong support for all listed formats. Its `threads` variable is not passed to fastplong, and it suppresses tool output instead of saving per-sample logs. Use the command-line script for the behavior documented above.
- **`Seqkit/test.ipynb`** only calls `seqkit -h` through Python's `subprocess` module. It is a starting example for checking that SeqKit can be invoked from the notebook environment.

This repository currently provides individual utilities and examples; it does not yet include an end-to-end analysis pipeline or bundled validation datasets. Validate your installed tools and parameters on representative inputs before processing a full dataset.
