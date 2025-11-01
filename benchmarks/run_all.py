#!/usr/bin/env python3
"""Run all benchmarks and generate summary report."""

import platform
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bench_builder import run_benchmarks as run_builder_benchmarks
from bench_parser import run_benchmarks as run_parser_benchmarks
from bench_roundtrip import run_benchmarks as run_roundtrip_benchmarks


def print_system_info():
    """Print system information."""
    print("=" * 60)
    print("System Information")
    print("=" * 60)
    print(f"Date:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python:   {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print(f"CPU:      {platform.processor() or 'Unknown'}")
    print()


def main():
    """Run all benchmarks."""
    print_system_info()

    print("\n")
    run_parser_benchmarks()

    print("\n")
    run_builder_benchmarks()

    print("\n")
    run_roundtrip_benchmarks()

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
