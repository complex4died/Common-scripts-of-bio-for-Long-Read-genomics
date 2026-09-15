#!/usr/bin/env python3
"""从 CSV 读取引物对，批量调用 Cutadapt 处理完整扩增子长读段。

用法：python cutadapt_trim.py -i raw_dir -p primer_hla.csv -o results
输出：<output>/<sample>/<sample>.trimmed.fastq.gz、unmatched.fastq.gz、报告和日志。
只使用 Python 标准库；运行环境须能调用 cutadapt。
"""

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


FASTQ_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
REQUIRED_COLUMNS = ("forward_name", "forward_seq", "reverse_name", "reverse_seq")
DNA_ALPHABET = set("ACGTRYSWKMBDHVN")
COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")


@dataclass(frozen=True)
class PrimerPair:
    name: str
    forward: str
    reverse: str

    def adapter(self):
        """保留配对关系；要求完整 R 长度参与匹配，避免默认短重叠误匹配。"""
        reverse_complement = self.reverse.translate(COMPLEMENT)[::-1]
        return f"{self.name}=^{self.forward}...{reverse_complement};min_overlap={len(self.reverse)}"


def read_primers(path):
    """读取 UTF-8 CSV（兼容 Excel BOM）；target 可选且允许重复。"""
    if path.suffix.lower() != ".csv":
        raise ValueError("-p 当前接受 CSV；Excel 表请另存为 CSV UTF-8")
    pairs = []
    names = set()
    sequences = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("引物表为空")
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV 有重复列名")
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise ValueError("CSV 缺少列：" + ", ".join(sorted(missing)))
        for row in reader:
            line = reader.line_num
            if None in row:
                raise ValueError(f"CSV 第 {line} 行列数超过表头")
            if not any(value and value.strip() for value in row.values()):
                continue
            values = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            if not all(values.values()):
                raise ValueError(f"CSV 第 {line} 行缺少引物名称或序列")
            for key in ("forward_name", "reverse_name"):
                name = values[key]
                if any(char.isspace() or char in "=;" for char in name):
                    raise ValueError(f"CSV 第 {line} 行的 {key} 不能包含空白、= 或 ;")
            for key in ("forward_seq", "reverse_seq"):
                seq = values[key].upper()
                invalid = set(seq) - DNA_ALPHABET
                if invalid or set(seq) == {"N"}:
                    raise ValueError(f"CSV 第 {line} 行的 {key} 不是有效 DNA/IUPAC 引物序列：{seq}")
                values[key] = seq
            pair = PrimerPair(values["forward_name"] + "__" + values["reverse_name"],
                              values["forward_seq"], values["reverse_seq"])
            if pair.name in names or (pair.forward, pair.reverse) in sequences:
                raise ValueError(f"CSV 第 {line} 行存在重复引物对名称或序列：{pair.name}")
            names.add(pair.name)
            sequences.add((pair.forward, pair.reverse))
            pairs.append(pair)
    if not pairs:
        raise ValueError("CSV 中没有引物对")
    return pairs


def find_inputs(folder):
    """仅扫描一层，每个 FASTQ 独立处理，不自动拼接或配对 R1/R2。"""
    if not folder.is_dir():
        raise ValueError(f"输入目录不存在：{folder}")
    inputs = []
    samples = set()
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        suffix = next((ext for ext in FASTQ_SUFFIXES if path.name.lower().endswith(ext)), None)
        if suffix is None:
            continue
        sample = path.name[:-len(suffix)]
        if not sample or sample in (".", "..") or sample.casefold() in samples:
            raise ValueError(f"样本名为空、无效或重复：{path.name}")
        samples.add(sample.casefold())
        inputs.append((path, sample))
    if not inputs:
        raise ValueError("输入目录中没有 .fastq / .fq / .fastq.gz / .fq.gz 文件（不递归）")
    return inputs


def output_paths(folder, sample):
    return [folder / (sample + suffix) for suffix in (
        ".trimmed.fastq.gz", ".unmatched.fastq.gz", ".cutadapt.json", ".cutadapt.log")]


def run_sample(executable, version, path, sample, output, pairs, threads):
    folder = output / sample
    folder.mkdir(parents=True, exist_ok=True)
    final_paths = output_paths(folder, sample)
    log_path = final_paths[-1]
    # 在临时目录完成剪切；Cutadapt 失败时不以半成品替换上次成功的结果。
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"Cutadapt version: {version}\nInput: {path}\n")
        with tempfile.TemporaryDirectory(prefix=".cutadapt-", dir=folder) as temp:
            staged = output_paths(Path(temp), sample)
            cmd = [executable, "--revcomp", "-j", str(threads)]
            for pair in pairs:
                cmd.extend(["-g", pair.adapter()])
            cmd.extend(["--untrimmed-output", str(staged[1]), "--json", str(staged[2]),
                        "-o", str(staged[0]), str(path)])
            log.write("Command: " + shlex.join(cmd) + "\n\n")
            log.flush()
            try:
                subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
                for temporary, final in zip(staged[:3], final_paths[:3]):
                    temporary.replace(final)
            except (OSError, subprocess.CalledProcessError) as error:
                log.write(f"\n状态：失败；{error}\n")
                raise
        log.write("\n状态：成功\n")


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("必须是大于 0 的整数") from None
    if number < 1:
        raise argparse.ArgumentTypeError("必须是大于 0 的整数")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="按 CSV 引物对批量剪切完整扩增子长读段，两端必须匹配，未匹配 reads 另存。",
        allow_abbrev=False,
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="原始 FASTQ 文件夹（不递归）")
    parser.add_argument("-p", "--primers", required=True, type=Path, help="引物 CSV，例如 primer_hla.csv")
    parser.add_argument("-o", "--output", default=Path("."), type=Path, help="输出文件夹，默认 ./（当前工作目录）")
    parser.add_argument("-w", "--workers", type=positive_int, default=4,
                        help="同时处理的文件数，默认 4")
    parser.add_argument("-j", "--threads", type=positive_int, default=1,
                        help="每个 Cutadapt 进程的核数，默认 1；总计算核数配置为 workers × threads")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        input_dir = args.input.expanduser().resolve()
        primer_path = args.primers.expanduser().resolve()
        output = args.output.expanduser().resolve()
        pairs = read_primers(primer_path)
        inputs = find_inputs(input_dir)
        # 允许覆盖旧结果，但禁止覆盖本批次原始输入或引物表。
        protected = {path.resolve() for path, _ in inputs} | {primer_path}
        for _, sample in inputs:
            for path in output_paths(output / sample, sample):
                if path.resolve() in protected or any(
                    path.exists() and path.samefile(source) for source in protected
                ):
                    raise ValueError(f"输出路径与输入文件冲突：{path}")
        executable = shutil.which("cutadapt")
        if executable is None:
            raise ValueError("未找到 cutadapt；请在能运行 cutadapt 的终端环境中执行脚本")
        version = subprocess.run([executable, "--version"], check=True,
                                 capture_output=True, text=True).stdout.strip()
        output.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, csv.Error, subprocess.CalledProcessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    workers = min(args.workers, len(inputs))
    print(f"Cutadapt {version}；{len(pairs)} 对引物；{len(inputs)} 个 FASTQ；"
          f"同时处理 {workers} 个文件，每进程 {args.threads} 核，"
          f"计算核数配置合计最多 {workers * args.threads}。", flush=True)
    print(f"输出目录：{output}", flush=True)
    failed = 0
    # Python 线程仅调度/等待外部进程，实际剪切由各 Cutadapt 进程执行。
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_sample, executable, version, path, sample,
                            output, pairs, args.threads): sample
            for path, sample in inputs
        }
        for future in as_completed(futures):
            sample = futures[future]
            try:
                future.result()
                print(f"完成：{sample}", flush=True)
            except (OSError, subprocess.CalledProcessError) as error:
                failed += 1
                print(f"失败：{sample}；{error}；日志：{output / sample / (sample + '.cutadapt.log')}",
                      file=sys.stderr, flush=True)
    print(f"处理结束：成功 {len(inputs) - failed}，失败 {failed}。", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
