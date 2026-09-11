#!/usr/bin/env python3
"""批量调用 fastplong；仅使用 Python 标准库，需要环境中已安装 fastplong。

示例：
    python clean_v1.py -i input_dir -o results -p 4 -j 3
    python clean_v1.py -i input_dir -o results -n clean -q 15 -l 1000

输出：<输出根目录>/<name>/<样本名>/<样本名>_fastplong.*
默认输出到 ./fastplong/；-o 修改根目录，-n 修改 fastplong 这一层目录名。
同名结果允许覆盖。-p 是并发进程数，-j 是每个进程的线程数。
过滤参数不指定时，不传给 fastplong，沿用所安装版本的默认行为。
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


FILE_FORMATS = (".fastq.gz", ".fq.gz", ".fastq", ".fq")

# 参数名、短参数、fastplong 0.7.0 默认值说明。
FILTER_OPTIONS = (
    ("qualified_quality_phred", "-q", "合格碱基的最低质量，默认 15"),
    ("unqualified_percent_limit", "-u", "不合格碱基比例上限（百分比），默认 40"),
    ("mean_qual", "-m", "read 平均质量下限，默认 0（不限制）"),
    ("length_required", "-l", "read 最短长度 (bp)，默认 20"),
    ("length_limit", None, "read 最长长度 (bp)，默认 0（不限制）"),
    ("n_percent_limit", None, "N 碱基比例上限（百分比），默认 10；-n 已用于输出子目录"),
    ("n_base_limit", None, "N 碱基数量上限，默认 1000000（不限制）"),
    ("cut_window_size", "-W", "首尾质量剪切窗口 (bp)，默认 4；需开启 -5 或 -3"),
    ("cut_mean_quality", "-M", "首尾质量剪切窗口质量下限，默认 20；需开启 -5 或 -3"),
)

SWITCH_OPTIONS = (
    ("disable_quality_filtering", "-Q", "关闭质量过滤（包括 N 碱基过滤）"),
    ("disable_length_filtering", "-L", "关闭长度过滤"),
    ("disable_adapter_trimming", "-A", "关闭接头剪切"),
    ("cut_front", "-5", "开启 read 首端质量剪切，默认关闭"),
    ("cut_tail", "-3", "开启 read 尾端质量剪切，默认关闭"),
)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("必须是大于 0 的整数")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("必须是大于或等于 0 的整数")
    return number


def parse_args():
    parser = argparse.ArgumentParser(
        description="批量过滤 FASTQ，保持 fastplong 默认行为，支持按需调整过滤参数。",
        epilog="默认值说明基于 fastplong 0.7.0；实际默认行为取决于安装版本。",
        allow_abbrev=False,
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="输入目录（不递归）")
    parser.add_argument("-o", "--output", default=Path("."), type=Path, help="输出根目录，默认当前目录 ./")
    parser.add_argument("-n", "--name", default="fastplong", help="输出子目录名，默认 fastplong；最终目录为 <output>/<name>/")
    parser.add_argument("-p", "--processes", type=positive_int, default=4, help="同时运行的进程数，默认 4")
    parser.add_argument("-j", "--threads", type=positive_int, default=3, help="每个 fastplong 进程的线程数，默认 3")
    filters = parser.add_argument_group("过滤与剪切：仅显式指定时才传给 fastplong")
    for name, short, description in FILTER_OPTIONS:
        flags = ([short] if short else []) + ["--" + name]
        filters.add_argument(*flags, type=nonnegative_int, default=None, help=description)
    for name, short, description in SWITCH_OPTIONS:
        filters.add_argument(short, "--" + name, action="store_true", help=description)
    args = parser.parse_args()
    if args.name and (args.name in (".", "..") or "/" in args.name or "\\" in args.name):
        parser.error("-n 只能是一个子目录名，不能包含路径分隔符或使用 . / ..")
    for name in ("unqualified_percent_limit", "n_percent_limit"):
        value = getattr(args, name)
        if value is not None and value > 100:
            parser.error("--" + name + " 必须在 0 到 100 之间")
    if args.cut_window_size is not None and not 1 <= args.cut_window_size <= 1000:
        parser.error("--cut_window_size 必须在 1 到 1000 之间")
    if args.cut_mean_quality is not None and not 1 <= args.cut_mean_quality <= 30:
        parser.error("--cut_mean_quality 必须在 1 到 30 之间")
    return args


def get_sample_id(filename):
    for suffix in FILE_FORMATS:
        if filename.lower().endswith(suffix):
            return filename[:-len(suffix)]
    raise ValueError("不支持的输入格式：" + filename)


def run_fastplong(input_path, output_dir, threads, filter_args, executable):
    """每次处理一个文件；Python 线程等待对应的 fastplong 进程结束。"""
    sample_id = get_sample_id(input_path.name)
    sample_dir = output_dir / sample_id
    log_path = sample_dir / (sample_id + "_fastplong.log")
    try:
        sample_dir.mkdir(parents=True, exist_ok=True)
        prefix = sample_dir / (sample_id + "_fastplong")
        cmd = [
            executable, "-i", str(input_path),
            "-o", str(prefix) + ".fastq.gz",
            "--html", str(prefix) + ".html",
            "--json", str(prefix) + ".json",
            "--thread", str(threads),
        ] + filter_args
        with log_path.open("w", encoding="utf-8") as log:
            log.write(shlex.join(cmd) + "\n\n")
            log.flush()
            subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"{sample_id} 失败：{error}；日志：{log_path}", file=sys.stderr, flush=True)
        return False
    print(f"{sample_id} 过滤完成", flush=True)
    return True


def main():
    args = parse_args()
    try:
        input_dir = args.input.expanduser().resolve()
        if not input_dir.is_dir():
            raise ValueError(f"输入目录不存在：{input_dir}")
        input_files = sorted(
            path for path in input_dir.iterdir()
            if path.is_file() and path.name.lower().endswith(FILE_FORMATS)
        )
        if not input_files:
            raise ValueError("没有找到 .fq / .fastq / .fq.gz / .fastq.gz 文件")
        sample_ids = set()
        for path in input_files:
            sample_id = get_sample_id(path.name)
            if not sample_id or sample_id in (".", "..") or sample_id in sample_ids:
                raise ValueError(f"样本名为空、无效或重复：{path.name}")
            sample_ids.add(sample_id)
        executable = shutil.which("fastplong")
        if executable is None:
            raise ValueError("未找到 fastplong，请先安装或激活对应环境")
        output_dir = (args.output.expanduser() / args.name).resolve()
        # 允许覆盖旧结果，但不能覆盖本批次输入文件。
        input_paths = {path.resolve() for path in input_files}
        for sample_id in sample_ids:
            prefix = output_dir / sample_id / (sample_id + "_fastplong")
            for suffix in (".fastq.gz", ".html", ".json", ".log"):
                if Path(str(prefix) + suffix).resolve() in input_paths:
                    raise ValueError(f"输出路径与输入文件冲突：{prefix}{suffix}")
        filter_args = []
        for name, _, _ in FILTER_OPTIONS:
            value = getattr(args, name)
            if value is not None:
                filter_args.extend(["--" + name, str(value)])
        for name, _, _ in SWITCH_OPTIONS:
            if getattr(args, name):
                filter_args.append("--" + name)
        output_dir.mkdir(parents=True, exist_ok=True)
        processes = min(args.processes, len(input_files))
        print(f"共 {len(input_files)} 个文件；并发 {processes}；每进程 {args.threads} 线程；"
              f"线程配置合计最多 {processes * args.threads}。", flush=True)
        print(f"输出目录：{output_dir}", flush=True)
        worker = partial(run_fastplong, output_dir=output_dir, threads=args.threads,
                         filter_args=filter_args, executable=executable)
        with ThreadPoolExecutor(max_workers=processes) as executor:
            results = list(executor.map(worker, input_files))
        failed = results.count(False)
        print(f"处理结束：成功 {len(results) - failed}，失败 {failed}。", flush=True)
        return 1 if failed else 0
    except (OSError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
