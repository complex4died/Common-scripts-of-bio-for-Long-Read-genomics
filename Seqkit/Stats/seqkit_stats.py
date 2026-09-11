import os
import argparse
import subprocess

from concurrent.futures import ThreadPoolExecutor


# FASTA / FASTQ 常见文件后缀
sequence_formats = (
    ".fa", ".fasta", ".fas", ".fsa",
    ".fna", ".ffn", ".faa", ".frn",
    ".fq", ".fastq"
)

# 压缩后缀；空字符串表示未压缩
compression_formats = ("", ".gz", ".xz", ".zst", ".bz2", ".lz4")

# 组合所有支持筛选的后缀
file_formats = []

for sequence in sequence_formats:
    for compression in compression_formats:
        file_formats.append(sequence + compression)


# 读取命令行参数
def parse_args():

    parser = argparse.ArgumentParser(
        description="批量运行 SeqKit stats，默认开启完整统计 -a"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="输入文件夹"
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        help="输出根目录"
    )

    parser.add_argument(
        "-n", "--name",
        default="raw",
        help="输出子文件夹名称，默认 raw"
    )

    parser.add_argument(
        "-p", "--processes",
        type=int,
        default=4,
        help="同时运行的 SeqKit 进程数，默认 4"
    )

    parser.add_argument(
        "-j", "--threads",
        type=int,
        default=max(2, (os.cpu_count() or 1) // 3),
        help="每个 SeqKit 的线程数，默认 CPU 数的 1/3，至少 2"
    )

    args = parser.parse_args()

    if args.processes < 1 or args.threads < 1:
        parser.error("进程数和线程数必须大于 0")

    if not os.path.isdir(args.input):
        parser.error(f"输入文件夹不存在：{args.input}")

    if (
        not args.name.strip()
        or args.name in (".", "..")
        or "/" in args.name
        or "\\" in args.name
    ):
        parser.error("-n 必须是一个子文件夹名称，不能包含路径")

    return args


# 从文件名提取样本编号
def get_sample_id(file_name):

    for suffix in file_formats:
        if file_name.lower().endswith(suffix):
            return file_name[:-len(suffix)]

    raise ValueError(f"无法识别文件后缀：{file_name}")


# 主程序
def main():

    args = parse_args()

    input_file = args.input
    output_file = os.path.join(args.output, args.name)

    max_processes = args.processes
    threads = args.threads

    # 筛选输入目录当前层的序列文件
    input_files = sorted([
        f for f in os.listdir(input_file)
        if f.lower().endswith(tuple(file_formats))
        and os.path.isfile(os.path.join(input_file, f))
    ])

    if not input_files:
        raise ValueError("输入文件夹中没有匹配的 FASTA / FASTQ 文件")

    # 提前检查重名，避免多个任务写入同一个结果文件
    sample_ids = set()

    for i in input_files:

        sample_id = get_sample_id(i)

        if sample_id in sample_ids:
            raise ValueError(f"样本编号重复，会导致输出冲突：{sample_id}")

        sample_ids.add(sample_id)

        output_path = os.path.join(
            output_file, f"{sample_id}.stats.txt"
        )

        # if os.path.lexists(output_path):
        #     raise ValueError(f"结果文件已存在，请更换 -n 或 -o：{output_path}")

    os.makedirs(output_file, exist_ok=True)

    # 定义一次函数：每次调用只处理一个文件
    def run_seqkit(i):

        sample_id = get_sample_id(i)

        input_path = os.path.join(input_file, i)

        output_path = os.path.join(
            output_file, f"{sample_id}.stats.txt"
        )

        cmd = [
            "seqkit", "stats",
            input_path,
            "-o", output_path,
            "-a",
            "-j", str(threads)
        ]

        subprocess.run(cmd, check=True)

        return sample_id

    print(f"输入文件数量：{len(input_files)}")
    print(f"最大并发进程数：{max_processes}")
    print(f"每个 SeqKit 的线程数：{threads}")
    print(f"输出文件夹：{output_file}")

    # 自动分配任务，最多同时运行 max_processes 个 SeqKit
    with ThreadPoolExecutor(max_workers=max_processes) as executor:

        for sample_id in executor.map(run_seqkit, input_files):
            print(f"{sample_id} 统计完成")

    print("全部统计完成")


# 直接运行本脚本时，从这里开始
if __name__ == "__main__":

    try:
        main()

    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"运行失败：{error}")