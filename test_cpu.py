"""test_cpu.py - Unit tests for the CPU simulator.

Run with:  python3 -m unittest -v
"""

import unittest

from memory import Memory
from cache import Cache
from cpu import CPU, CPUError


def make_cpu(program, data=None):
    """Build a CPU with a program (a list of lines) and optional memory values."""
    memory = Memory()
    for address, value in (data or {}).items():
        memory.data[address] = value
    cpu = CPU(memory, Cache(memory))
    cpu.program = program
    return cpu


def run(program, data=None):
    """Build a CPU, run the program, and return the CPU so we can check it."""
    cpu = make_cpu(program, data)
    cpu.run()
    return cpu


class TestMemory(unittest.TestCase):
    def test_starts_empty(self):
        memory = Memory()
        self.assertEqual(memory.read(0), 0)
        self.assertEqual(memory.read(255), 0)

    def test_write_then_read(self):
        memory = Memory()
        memory.write(10, 42)
        self.assertEqual(memory.read(10), 42)
        self.assertEqual(memory.writes, 1)
        self.assertEqual(memory.reads, 1)

    def test_bad_address(self):
        memory = Memory()
        with self.assertRaises(IndexError):
            memory.read(256)
        with self.assertRaises(IndexError):
            memory.write(-1, 5)

    def test_load_from_file(self):
        memory = Memory()
        memory.load_from_file("data_input.txt")
        self.assertEqual(memory.read(0), 5)
        self.assertEqual(memory.read(3), 2)
class TestCache(unittest.TestCase):
    def setUp(self):
        self.memory = Memory()
        for address in range(10):
            self.memory.data[address] = address * 10  # address 3 holds 30, etc.
        self.cache = Cache(self.memory)
        self.cache.enable()

    def test_miss_then_hit(self):
        self.assertEqual(self.cache.read(3), (30, False))  # first time: miss
        self.assertEqual(self.cache.read(3), (30, True))   # second time: hit
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 1)

    def test_fifo_removes_oldest(self):
        for address in [0, 1, 2, 3]:
            self.cache.read(address)  # cache is now full
        self.cache.read(0)  # a hit, but 0 is still the oldest
        self.cache.read(4)  # cache full, so the oldest (0) is removed
        self.assertNotIn(0, self.cache.entries)
        self.assertIn(1, self.cache.entries)
        self.assertIn(4, self.cache.entries)

    def test_write_through(self):
        self.cache.read(5)
        self.cache.write(5, 99)
        self.assertEqual(self.memory.data[5], 99)    # memory updated
        self.assertEqual(self.cache.entries[5], 99)  # cache copy updated too

    def test_flush(self):
        self.cache.read(1)
        self.cache.flush()
        self.assertEqual(self.cache.entries, {})
        self.assertEqual(self.cache.read(1), (10, False))  # miss again

    def test_disabled_cache_counts_nothing(self):
        self.cache.disable()
        self.assertEqual(self.cache.read(2), (20, False))
        self.assertEqual(self.cache.hits + self.cache.misses, 0)

    def test_hit_rate(self):
        self.assertEqual(self.cache.hit_rate(), 0.0)
        self.cache.read(1)  # miss
        self.cache.read(1)  # hit
        self.assertEqual(self.cache.hit_rate(), 50.0)

class TestInstructions(unittest.TestCase):
    def test_add_and_addi(self):
        cpu = run(["ADDI,R1,R0,5", "ADDI,R2,R0,3", "ADD,R3,R1,R2", "HALT,;"])
        self.assertEqual(cpu.registers[3], 8)

    def test_sub(self):
        cpu = run(["ADDI,R1,R0,5", "ADDI,R2,R0,3", "SUB,R3,R1,R2", "HALT,;"])
        self.assertEqual(cpu.registers[3], 2)

    def test_slt(self):
        cpu = run(["ADDI,R1,R0,2", "ADDI,R2,R0,9",
                   "SLT,R3,R1,R2", "SLT,R4,R2,R1", "HALT,;"])
        self.assertEqual(cpu.registers[3], 1)  # 2 < 9, yes
        self.assertEqual(cpu.registers[4], 0)  # 9 < 2, no

    def test_r0_is_always_zero(self):
        cpu = run(["ADDI,R0,R0,7", "HALT,;"])
        self.assertEqual(cpu.registers[0], 0)

    def test_bne_loop(self):
        cpu = run(["ADDI,R2,R0,3", "ADDI,R1,R1,1", "BNE,R1,R2,1", "HALT,;"])
        self.assertEqual(cpu.registers[1], 3)

    def test_j_skips_instructions(self):
        cpu = run(["J,2", "ADDI,R1,R0,99", "HALT,;"])
        self.assertEqual(cpu.registers[1], 0)  # the ADDI was skipped

    def test_jal_and_jr(self):
        cpu = run(["JAL,3", "ADDI,R2,R0,1", "HALT,;", "ADDI,R1,R0,5", "JR,R7"])
        self.assertEqual(cpu.registers[1], 5)  # the function ran
        self.assertEqual(cpu.registers[2], 1)  # and came back
        self.assertEqual(cpu.registers[7], 1)  # the saved return address

    def test_lw_and_sw(self):
        cpu = run(["LW,R1,0(R0)", "ADDI,R1,R1,1", "SW,R1,1(R0)", "HALT,;"],
                  data={0: 41})
        self.assertEqual(cpu.registers[1], 42)
        self.assertEqual(cpu.memory.data[1], 42)

    def test_cache_instruction_modes(self):
        cpu = run(["CACHE,1", "LW,R1,0(R0)", "LW,R1,0(R0)",
                   "CACHE,2", "LW,R1,0(R0)", "CACHE,0", "HALT,;"])
        self.assertEqual(cpu.cache.hits, 1)
        self.assertEqual(cpu.cache.misses, 2)
        self.assertFalse(cpu.cache.enabled)

    def test_cycle_counts(self):
        cpu = run(["CACHE,1", "LW,R1,0(R0)", "LW,R1,0(R0)", "HALT,;"])
        # CACHE 1 + miss (1 + 10) + hit (1 + 1) + HALT 1 = 15
        self.assertEqual(cpu.cycles, 15)
class TestErrors(unittest.TestCase):
    def test_unknown_instruction(self):
        with self.assertRaises(CPUError):
            run(["FLY,R1", "HALT,;"])

    def test_bad_register(self):
        with self.assertRaises(CPUError):
            run(["ADDI,R9,R0,1", "HALT,;"])

    def test_wrong_number_of_arguments(self):
        with self.assertRaises(CPUError):
            run(["ADD,R1,R2", "HALT,;"])

    def test_missing_halt(self):
        with self.assertRaises(CPUError):
            run(["ADDI,R1,R0,1"])

    def test_endless_loop_is_stopped(self):
        with self.assertRaises(CPUError):
            run(["J,0"])


class TestExamplePrograms(unittest.TestCase):
    def run_file(self, filename):
        memory = Memory()
        memory.load_from_file("data_input.txt")
        cpu = CPU(memory, Cache(memory))
        cpu.load_program(filename)
        cpu.run()
        return cpu

    def test_instruction_input(self):
        cpu = self.run_file("instruction_input.txt")
        self.assertEqual(cpu.memory.data[4], 14)

    def test_count_to_10(self):
        cpu = self.run_file("programs/count_to_10.txt")
        self.assertEqual(cpu.registers[1], 10)

    def test_sum_memory(self):
        cpu = self.run_file("programs/sum_memory.txt")
        self.assertEqual(cpu.memory.data[8], 14)

    def test_cache_demo(self):
        cpu = self.run_file("programs/cache_demo.txt")
        self.assertEqual(cpu.cache.hits, 4)
        self.assertEqual(cpu.cache.misses, 5)

    def test_function_call(self):
        cpu = self.run_file("programs/function_call.txt")
        self.assertEqual(cpu.memory.data[8], 10)
        self.assertEqual(cpu.memory.data[9], 14)


if __name__ == "__main__":
    unittest.main()