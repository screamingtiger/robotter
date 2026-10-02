"""Repeatable ONNX Runtime CPU inference latency benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import fmean
from time import perf_counter

import numpy as np
import onnxruntime as ort


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def benchmark(model: Path, *, threads: int, warmup: int, runs: int) -> None:
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    input_info = session.get_inputs()[0]
    shape = [dimension if isinstance(dimension, int) else 1 for dimension in input_info.shape]
    data = np.zeros(shape, dtype=np.float32)
    feed = {input_info.name: data}

    for _ in range(warmup):
        session.run(None, feed)

    latencies_ms: list[float] = []
    for _ in range(runs):
        started = perf_counter()
        session.run(None, feed)
        latencies_ms.append((perf_counter() - started) * 1000)

    average_ms = fmean(latencies_ms)
    print(f"providers={session.get_providers()}")
    print(f"input={input_info.name} shape={shape}")
    print(f"threads={threads} warmup={warmup} runs={runs}")
    print(f"mean_ms={average_ms:.3f}")
    print(f"p50_ms={percentile(latencies_ms, 0.50):.3f}")
    print(f"p95_ms={percentile(latencies_ms, 0.95):.3f}")
    print(f"fps={1000 / average_ms:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark CPU inference with ONNX Runtime")
    parser.add_argument("model", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--runs", type=int, default=20)
    arguments = parser.parse_args()
    if arguments.threads <= 0 or arguments.warmup < 0 or arguments.runs <= 0:
        parser.error("threads and runs must be positive; warmup cannot be negative")
    benchmark(arguments.model, threads=arguments.threads, warmup=arguments.warmup, runs=arguments.runs)


if __name__ == "__main__":
    main()
