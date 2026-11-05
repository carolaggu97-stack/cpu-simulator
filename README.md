# CPU Simulator

A simple CPU simulator written in Python, built for the Codecademy CS104
Computer Architecture portfolio project. It reads a small assembly-style
program, runs it through a **fetch → decode → execute** loop, and shows
how registers, memory and a cache work together.

## Features

- 8 registers (R0–R7). R0 is always 0, and JAL saves the return address in R7
- A program counter (PC) that points to the next instruction
- 256 memory addresses, loaded from a file
- A 4-entry cache with **FIFO** replacement and **write-through** writes
- Cache hit/miss stats and a cycle count (hits are cheaper than misses)
- Three ways to run: normal, `--explain` and `--step`
- Example programs and 30 unit tests

## How it works

**Fetch → Decode → Execute.** The CPU repeats three steps until it reaches HALT:

1. **Fetch:** get the instruction the PC points to.
2. **Decode:** work out what it means, for example `ADDI,R1,R0,5` means
   "add 5 to R0 and put the answer in R1".
3. **Execute:** do it, then move the PC to the next instruction
   (or somewhere else, if it's a jump or branch).

**Memory** is big but slow. **The cache** is small but fast: it keeps
copies of recently used values. Reading a value that's in the cache is a
**hit** (fast); otherwise it's a **miss** (slow), and a copy is saved
in the cache for next time.

- **FIFO (First In, First Out):** when the cache is full, the value that
  came in first is removed, even if it was just used.
- **Write-through:** every write goes straight to memory, and the cache
  copy is updated too, so they never disagree.

### Cycle costs

| Action | Cycles |
|---|---|
| Any instruction | 1 |
| LW, cache hit | +1 |
| LW, cache miss or cache off | +10 |
| SW (always goes to memory) | +10 |

## Instruction set

| Instruction | Example | Meaning |
|---|---|---|
| ADD | `ADD,R3,R1,R2` | R3 = R1 + R2 |
| ADDI | `ADDI,R1,R0,5` | R1 = R0 + 5 |
| SUB | `SUB,R3,R1,R2` | R3 = R1 - R2 |
| SLT | `SLT,R3,R1,R2` | R3 = 1 if R1 < R2, else 0 |
| BNE | `BNE,R1,R2,4` | If R1 ≠ R2, jump to instruction 4 |
| J | `J,8` | Jump to instruction 8 |
| JAL | `JAL,7` | Save the next instruction number in R7, jump to 7 |
| JR | `JR,R7` | Jump to the instruction number in R7 (return) |
| LW | `LW,R4,0(R1)` | R4 = memory[R1 + 0] |
| SW | `SW,R3,8(R0)` | memory[R0 + 8] = R3 |
| CACHE | `CACHE,1` | 0 = cache off, 1 = on, 2 = flush (empty it) |
| HALT | `HALT,;` | Stop the program |

JR is an extra instruction I added. Without it, a function can't return
to where it was called from.

## File formats

**Program files** (like `instruction_input.txt`): one instruction per line,
in the form `INSTRUCTION,ARG1,...,ARGn`. Instructions are numbered from 0.
Lines starting with `#` are comments and are skipped (they don't count
when numbering instructions).

**Data file** (`data_input.txt`): one value per line, in the form
`binary address,value`. For example, `00000011,2` puts 2 at address 3.

## How to run

You need Python 3. No extra packages are needed.

```bash
# Run instruction_input.txt with data_input.txt
python3 main.py

# Explain each instruction in plain English
python3 main.py --explain

# Run one instruction at a time (press Enter to continue, Ctrl + C to stop)
python3 main.py --step

# Run your own program file
python3 main.py programs/cache_demo.txt --explain

# Use a different data file
python3 main.py my_program.txt --data my_data.txt

# Show all options
python3 main.py --help
```

At the end, the simulator prints a report with the registers, the memory
values that aren't 0, the cache hits, misses and hit rate, the number of
instructions run, and the total cycles.

## Example programs

| File | What it shows | Result |
|---|---|---|
| `instruction_input.txt` | A loop that adds memory 0–3, with the cache on | memory[4] = 14 |
| `programs/count_to_10.txt` | A simple loop with BNE | R1 = 10 |
| `programs/sum_memory.txt` | Loading and storing with the cache off | memory[8] = 14 |
| `programs/cache_demo.txt` | Hits, misses, flush and turning the cache off | 4 hits, 5 misses (44.4%) |
| `programs/function_call.txt` | Calling a function twice with JAL and JR | memory[8] = 10, memory[9] = 14 |

## Tests

```bash
python3 -m unittest -v
```

The 30 tests check memory, the cache (FIFO, write-through, flush, hit rate),
every instruction, cycle counts, error messages for broken programs, and
the results of all the example programs.

## Project structure

```
cpu-simulator/
├── main.py                 # starts the simulator, reads the options
├── cpu.py                  # registers, PC, fetch-decode-execute, report
├── cache.py                # FIFO write-through cache with stats
├── memory.py               # main memory, loaded from a file
├── test_cpu.py             # unit tests
├── instruction_input.txt   # default program
├── data_input.txt          # default starting memory
└── programs/               # example programs
```

## What I learned

- **How a CPU really runs a program.** Every instruction goes through the
  same three steps: fetch, decode, execute. Building this loop myself made
  it clear that a "program" is just a list of simple steps, and the program
  counter decides which one comes next.
- **Jumps and loops are just changes to the program counter.** BNE and J
  don't do anything magic. They only set the PC to a different number.
  That's how a few lines of code can repeat many times.
- **A cache only helps if you reuse data.** My first program read each
  memory address only once, so the hit rate was 0%. In `cache_demo`, the
  second pass over the same addresses was all hits, and those loads cost
  2 cycles instead of 11.
- **FIFO has a weakness.** When the cache was full, FIFO removed the oldest
  value, even though I had just used it. That showed me why some CPUs use
  LRU (least recently used) instead.
- **Write-through is simple but slow for writes.** Every store goes all the
  way to memory, so SW always costs the full 10 cycles. The upside is that
  memory and the cache never disagree.
- **Functions need a way to come back.** JAL saves the return address, but
  I had to add JR to jump back to it. I also learned to put HALT before the
  function code, or the CPU runs straight into it by accident.
- **Small details matter.** R0 is always 0, so `8(R0)` is an easy way to
  write "address 8". And one missing bracket stopped all my tests from
  running, until I learned to look at the line *above* the error.
- **Tests save time.** With 30 unit tests, I can change the code and know
  in one second if I broke something, instead of checking the output by eye.
- **Git works best in small steps.** I committed after every file, so my
  history shows how the project was built, one piece at a time.

## Ideas for the future

- An LRU cache (remove the least recently used value instead of the oldest)
  to compare with FIFO
- Labels in programs (like `loop:`) instead of instruction numbers
- A write-back cache to compare with write-through