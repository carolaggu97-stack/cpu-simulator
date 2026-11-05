"""main.py - Start the CPU simulator from the terminal."""

import argparse
import sys

from memory import Memory
from cache import Cache
from cpu import CPU, CPUError


def parse_arguments():
    parser = argparse.ArgumentParser(description="A simple CPU simulator.")
    parser.add_argument(
        "program",
        nargs="?",
        default="instruction_input.txt",
        help="instruction file to run (default: instruction_input.txt)",
    )
    parser.add_argument(
        "--data",
        default="data_input.txt",
        help="file with the starting memory (default: data_input.txt)",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="explain each instruction in plain English",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="run one instruction at a time (press Enter to continue)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    memory = Memory()
    cache = Cache(memory)
    cpu = CPU(memory, cache)

    try:
        memory.load_from_file(args.data)
        cpu.load_program(args.program)
        print(f"Running {args.program} ({len(cpu.program)} instructions)")
        cpu.run(explain=args.explain, step_mode=args.step)
    except FileNotFoundError as error:
        print(f"Error: can't find the file '{error.filename}'")
        sys.exit(1)
    except (CPUError, ValueError, IndexError) as error:
        print(f"Error: {error}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped by user.")

    cpu.print_report()


if __name__ == "__main__":
    main()
    