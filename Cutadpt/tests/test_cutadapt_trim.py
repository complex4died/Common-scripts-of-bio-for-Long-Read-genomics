"""使用真实 Cutadapt 验证剪切结果；运行前确保 cutadapt 在 PATH。"""
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "cutadapt_trim.py"
HEADER = "target,forward_name,forward_seq,reverse_name,reverse_seq\n"
ROWS = (
    "HLA-A,A_F,AGTCCCAGCCTTGGGGATTC,A_R,CACAAAGGGAAGGGCAGGAA\n"
    "HLA-A,B_F,GCTCCCGGTTGCAATAGACAGTAACAAA,B_R,TCTAGACTATGGACCCAATTTTACAAACAAATA\n"
)
INSERT = "GATCTACGATCGTACCTAGCTAGCATGCATCGATCG"
F1 = "AGTCCCAGCCTTGGGGATTC"
RC_R1 = "TTCCTGCCCTTCCCTTTGTG"
F2 = "GCTCCCGGTTGCAATAGACAGTAACAAA"
RC_R2 = "TATTTGTTTGTAAAATTGGGTCCATAGTCTAGA"


class TrimmingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "raw reads"
        self.inputs.mkdir()
        self.primers = self.root / "primer hla.csv"
        self.primers.write_text(HEADER + ROWS, encoding="utf-8-sig")

    def run_cli(self, output=True, extra=()):
        cmd = [sys.executable, str(SCRIPT), "-i", str(self.inputs), "-p", str(self.primers)]
        if output:
            cmd.extend(["-o", str(self.root / "results")])
        cmd.extend(extra)
        return subprocess.run(cmd, cwd=self.root, text=True, capture_output=True)

    def write_reads(self, name, reads):
        path = self.inputs / name
        opener = gzip.open if name.endswith(".gz") else open
        with opener(path, "wt") as handle:
            for key, seq in reads:
                handle.write(f"@{key}\n{seq}\n+\n{'I' * len(seq)}\n")

    def read_sequences(self, path):
        with gzip.open(path, "rt") as handle:
            return handle.read().splitlines()[1::4]

    def test_two_pairs_orientation_and_unmatched(self):
        # Catches wrong R reverse-complement, cross-pair mixing, missing required ends.
        first = F1 + INSERT + RC_R1
        reverse = first.translate(str.maketrans("ACGT", "TGCA"))[::-1]
        self.write_reads("sample 01.fastq", [
            ("pair1", first), ("reverse", reverse),
            ("pair2", F2 + INSERT + RC_R2),
            ("cross", F1 + INSERT + RC_R2),
            ("only_left", F1 + INSERT), ("neither", INSERT),
        ])
        self.write_reads("sample02.fq.gz", [("pair2", F2 + INSERT + RC_R2)])
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        folder = self.root / "results" / "sample 01"
        self.assertEqual(self.read_sequences(folder / "sample 01.trimmed.fastq.gz"), [INSERT] * 3)
        self.assertEqual(len(self.read_sequences(folder / "sample 01.unmatched.fastq.gz")), 3)
        report = json.loads((folder / "sample 01.cutadapt.json").read_text())
        self.assertEqual(report["read_counts"]["input"], 6)
        self.assertEqual(len(report["adapters_read1"]), 2)
        self.assertEqual(self.read_sequences(self.root / "results/sample02/sample02.trimmed.fastq.gz"), [INSERT])

    def test_default_output_and_iupac_reverse_complement(self):
        # V in R becomes B in RC(R); concrete G must match it.
        self.primers.write_text(
            "forward_name,forward_seq,reverse_name,reverse_seq\n"
            "F,AGTCCCAGCCTTGGGGATTC,R,CACAAAGGGAAGGGCAGGAV\n"
        )
        self.write_reads("iupac.fq", [("degenerate", F1 + INSERT + "GTCCTGCCCTTCCCTTTGTG")])
        result = self.run_cli(output=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(self.read_sequences(self.root / "iupac/iupac.trimmed.fastq.gz"), [INSERT])

    def test_invalid_table_stops_before_outputs(self):
        self.write_reads("a.fq", [("r", INSERT)])
        for content in (HEADER, HEADER + ROWS.replace("AGTCCC", "AGZCCC"),
                        HEADER + ROWS + ROWS.splitlines()[0] + "\n",
                        "forward_name,forward_seq\nF,ACGT\n"):
            with self.subTest(content=content):
                self.primers.write_text(content)
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("错误", result.stderr)
                self.assertFalse((self.root / "results").exists())

    def test_duplicate_sample_stems_rejected(self):
        self.write_reads("a.fq", [("r", INSERT)])
        self.write_reads("a.fastq.gz", [("r", INSERT)])
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("重复", result.stderr)
        self.assertFalse((self.root / "results").exists())

    def test_failed_fastq_keeps_previous_successful_outputs(self):
        self.write_reads("a.fq", [("r", F1 + INSERT + RC_R1)])
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "results/a/a.trimmed.fastq.gz"
        previous = output.read_bytes()
        (self.inputs / "a.fq").write_text("@broken\nACGT\n+\nI\n")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), previous)
        self.assertIn("失败", (self.root / "results/a/a.cutadapt.log").read_text())

    def test_parallel_files_and_real_cutadapt_cores(self):
        # Missing -j forwarding must fail even if trimming still succeeds.
        for name in ("a", "b", "c"):
            self.write_reads(name + ".fq", [("r", F1 + INSERT + RC_R1)])
        result = self.run_cli(extra=("-w", "2", "-j", "2"))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        for name in ("a", "b", "c"):
            folder = self.root / "results" / name
            self.assertEqual(self.read_sequences(folder / (name + ".trimmed.fastq.gz")), [INSERT])
            report = json.loads((folder / (name + ".cutadapt.json")).read_text())
            self.assertEqual(report["cores"], 2)

    def test_parallel_failure_does_not_stop_other_files(self):
        (self.inputs / "a_bad.fq").write_text("@broken\nACGT\n+\nI\n")
        self.write_reads("b_good.fq", [("r", F1 + INSERT + RC_R1)])
        result = self.run_cli(extra=("-w", "2", "-j", "2"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read_sequences(self.root / "results/b_good/b_good.trimmed.fastq.gz"), [INSERT])
        self.assertFalse((self.root / "results/a_bad/a_bad.trimmed.fastq.gz").exists())

    def test_invalid_parallel_settings(self):
        self.write_reads("a.fq", [("r", INSERT)])
        for flag in ("-w", "-j"):
            for value in ("0", "-1", "1.5"):
                with self.subTest(flag=flag, value=value):
                    result = self.run_cli(extra=(flag, value))
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("大于 0 的整数", result.stderr)
                    self.assertFalse((self.root / "results").exists())

    def test_scheduler_runs_exactly_two_jobs_at_once(self):
        # Replace only the external job boundary; exercise real main/scheduler.
        # A serial scheduler breaks the barrier; >2 workers exceeds the peak.
        spec = importlib.util.spec_from_file_location("cutadapt_test_module", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        for name in ("a", "b", "c", "d"):
            self.write_reads(name + ".fq", [("r", INSERT)])
        barrier = threading.Barrier(2, timeout=5)
        lock = threading.Lock()
        active = 0
        peak = 0
        completed = []

        def job(executable, version, path, sample, output, pairs, threads):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                barrier.wait()
            finally:
                with lock:
                    active -= 1
                    completed.append(sample)

        with patch.object(module, "run_sample", side_effect=job):
            status = module.main(["-i", str(self.inputs), "-p", str(self.primers),
                                  "-o", str(self.root / "results"), "-w", "2", "-j", "1"])
        self.assertEqual(status, 0)
        self.assertEqual(peak, 2)
        self.assertCountEqual(completed, ["a", "b", "c", "d"])


if __name__ == "__main__":
    unittest.main()
