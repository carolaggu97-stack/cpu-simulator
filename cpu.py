"""cpu.py - The CPU: registers, program counter, and the fetch-decode-execute loop."""

NUM_REGISTERS = 8
MAX_INSTRUCTIONS = 10_000  # safety limit, stops endless loops

# Cycle costs
BASE_CYCLES = 1     # every instruction takes at least 1 cycle
HIT_CYCLES = 1      # extra cycles when a value is found in the cache
MEMORY_CYCLES = 10  # extra cycles when we have to go to main memory

# What each instruction expects after its name:
# R = register, I = number, M = memory reference like 0(R1)
FORMATS = {
    "ADD": "RRR",
    "SUB": "RRR",
    "SLT": "RRR",
    "ADDI": "RRI",
    "BNE": "RRI",
    "J": "I",
    "JAL": "I",
    "JR": "R",
    "LW": "RM",
    "SW": "RM",
    "CACHE": "I",
    "HALT": "",
}


class CPUError(Exception):
    """An error in the program the CPU is running."""


def parse_register(text):
    text = text.strip().upper()
    if not text.startswith("R") or not text[1:].isdigit():
        raise ValueError(f"'{text}' is not a register (use R0-R7)")
    number = int(text[1:])
    if not 0 <= number < NUM_REGISTERS:
        raise ValueError(f"'{text}' is not a register (use R0-R7)")
    return number


def parse_memory_ref(text):
    """Turn '4(R1)' into (4, 1): an offset and a register number."""
    text = text.strip()
    if "(" not in text or not text.endswith(")"):
        raise ValueError(f"'{text}' should look like offset(register), e.g. 0(R1)")
    offset_text, register_text = text[:-1].split("(")
    return int(offset_text), parse_register(register_text)


def read_program_file(filename):
    program = []
    with open(filename) as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # skip empty lines and comments
            program.append(line)
    return program

class CPU:
    def __init__(self, memory, cache):
        self.memory = memory
        self.cache = cache
        self.registers = [0] * NUM_REGISTERS
        self.pc = 0  # program counter: the number of the next instruction
        self.program = []
        self.cycles = 0
        self.instructions_run = 0
        self.halted = False

    def load_program(self, filename):
        self.program = read_program_file(filename)
        self.pc = 0
        self.halted = False

    def get_register(self, number):
        return self.registers[number]

    def set_register(self, number, value):
        if number != 0:  # R0 is always 0, so writes to it are ignored
            self.registers[number] = value

    def fetch(self):
        if not 0 <= self.pc < len(self.program):
            raise CPUError(
                f"PC is {self.pc}, but the program only has instructions "
                f"0-{len(self.program) - 1}. Did you forget HALT?"
            )
        return self.program[self.pc]

    def decode(self, line):
        parts = [part.strip() for part in line.split(",")]
        op = parts[0].upper()
        args = parts[1:]

        if op not in FORMATS:
            raise ValueError(f"unknown instruction '{op}'")
        if op == "HALT":
            return op, []  # HALT ignores anything after it, like ';'

        expected = FORMATS[op]
        if len(args) != len(expected):
            raise ValueError(
                f"{op} needs {len(expected)} argument(s), but got {len(args)}"
            )

        operands = []
        for kind, arg in zip(expected, args):
            if kind == "R":
                operands.append(parse_register(arg))
            elif kind == "I":
                operands.append(int(arg))
            elif kind == "M":
                operands.append(parse_memory_ref(arg))
        return op, operands
    def execute(self, op, operands):
        """Do the instruction. Return a plain-English explanation of what happened."""
        next_pc = self.pc + 1  # normally we go on to the next instruction
        self.cycles += BASE_CYCLES

        if op == "ADD":
            rd, rs, rt = operands
            a, b = self.get_register(rs), self.get_register(rt)
            self.set_register(rd, a + b)
            message = f"Add R{rs} ({a}) and R{rt} ({b}), put {a + b} in R{rd}"

        elif op == "ADDI":
            rt, rs, number = operands
            a = self.get_register(rs)
            self.set_register(rt, a + number)
            message = f"Add {number} to R{rs} ({a}), put {a + number} in R{rt}"

        elif op == "SUB":
            rd, rs, rt = operands
            a, b = self.get_register(rs), self.get_register(rt)
            self.set_register(rd, a - b)
            message = f"Subtract R{rt} ({b}) from R{rs} ({a}), put {a - b} in R{rd}"

        elif op == "SLT":
            rd, rs, rt = operands
            a, b = self.get_register(rs), self.get_register(rt)
            result = 1 if a < b else 0
            answer = "yes" if result else "no"
            self.set_register(rd, result)
            message = f"Is R{rs} ({a}) less than R{rt} ({b})? {answer}, so R{rd} = {result}"

        elif op == "BNE":
            rs, rt, target = operands
            a, b = self.get_register(rs), self.get_register(rt)
            if a != b:
                next_pc = target
                message = f"R{rs} ({a}) is not equal to R{rt} ({b}), so jump to instruction {target}"
            else:
                message = f"R{rs} ({a}) equals R{rt} ({b}), so don't jump"
        elif op == "J":
            target = operands[0]
            next_pc = target
            message = f"Jump to instruction {target}"

        elif op == "JAL":
            target = operands[0]
            self.set_register(7, self.pc + 1)
            next_pc = target
            message = f"Save return address {self.pc + 1} in R7, then jump to instruction {target}"

        elif op == "JR":
            rs = operands[0]
            next_pc = self.get_register(rs)
            message = f"Jump to instruction {next_pc} (the address in R{rs})"

        elif op == "LW":
            rt, memory_ref = operands
            offset, rs = memory_ref
            address = self.get_register(rs) + offset
            value, hit = self.cache.read(address)
            self.set_register(rt, value)
            if hit:
                self.cycles += HIT_CYCLES
                where = "cache hit, fast"
            else:
                self.cycles += MEMORY_CYCLES
                where = "cache miss, slow" if self.cache.enabled else "from memory, slow"
            message = f"Load memory[{address}] ({value}) into R{rt} ({where})"

        elif op == "SW":
            rt, memory_ref = operands
            offset, rs = memory_ref
            address = self.get_register(rs) + offset
            value = self.get_register(rt)
            self.cache.write(address, value)
            self.cycles += MEMORY_CYCLES
            message = f"Store R{rt} ({value}) in memory[{address}] (write-through, slow)"

        elif op == "CACHE":
            mode = operands[0]
            if mode == 0:
                self.cache.disable()
                message = "Turn the cache off"
            elif mode == 1:
                self.cache.enable()
                message = "Turn the cache on"
            elif mode == 2:
                self.cache.flush()
                message = "Flush the cache (empty it)"
            else:
                raise ValueError(f"CACHE needs 0, 1 or 2, but got {mode}")

        elif op == "HALT":
            self.halted = True
            next_pc = self.pc  # stay where we are
            message = "Stop the program"

        self.pc = next_pc
        self.instructions_run += 1
        return message
    def step(self):
        """Run one instruction: fetch, decode, execute."""
        number = self.pc
        line = self.fetch()
        try:
            op, operands = self.decode(line)
            message = self.execute(op, operands)
        except (ValueError, IndexError) as error:
            raise CPUError(f"Instruction {number} ({line}): {error}") from None
        return number, line, message

    def run(self, explain=False, step_mode=False):
        while not self.halted:
            if self.instructions_run >= MAX_INSTRUCTIONS:
                raise CPUError(
                    f"Stopped after {MAX_INSTRUCTIONS} instructions. Is there an endless loop?"
                )
            number, line, message = self.step()
            if explain or step_mode:
                print(f"[{number:2}] {line:<16} {message}")
            if step_mode and not self.halted:
                self.print_registers()
                input("     Press Enter for the next instruction...")

    def print_registers(self):
        values = "  ".join(f"R{i}={v}" for i, v in enumerate(self.registers))
        print(f"     {values}")

    def print_report(self):
        print()
        print("========== Final report ==========")
        print("Registers:")
        self.print_registers()
        print("Memory (non-zero values):")
        self.memory.dump()
        print("Cache:")
        print(f"  Hits: {self.cache.hits}  Misses: {self.cache.misses}  "
              f"Hit rate: {self.cache.hit_rate():.1f}%")
        print(f"Instructions run: {self.instructions_run}")
        print(f"Cycles: {self.cycles}")


if __name__ == "__main__":
    from memory import Memory
    from cache import Cache

    memory = Memory()
    memory.load_from_file("data_input.txt")
    cache = Cache(memory)
    cpu = CPU(memory, cache)
    cpu.load_program("instruction_input.txt")
    cpu.run(explain=True)
    cpu.print_report()