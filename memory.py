"""memory.py - Main memory for the CPU simulator."""

MEMORY_SIZE = 256  # 8-bit addresses: 0 to 255


class Memory:
    def __init__(self, size=MEMORY_SIZE):
        self.size = size
        self.data = [0] * size  # every box starts at 0
        self.reads = 0
        self.writes = 0

    def _check_address(self, address):
        if not 0 <= address < self.size:
            raise IndexError(
                f"Memory address {address} is out of range (0-{self.size - 1})"
            )
    def read(self, address):
        self._check_address(address)
        self.reads += 1
        return self.data[address]

    def write(self, address, value):
        self._check_address(address)
        self.writes += 1
        self.data[address] = value

    def load_from_file(self, filename):
        with open(filename) as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # skip empty lines and comments
                try:
                    address_text, value_text = line.split(",")
                    address = int(address_text, 2)  # binary -> normal number
                    value = int(value_text)
                except ValueError:
                    raise ValueError(
                        f"{filename}, line {line_number}: can't read '{line}'"
                    ) from None
                self._check_address(address)
                self.data[address] = value
    def non_zero(self):
        return {addr: val for addr, val in enumerate(self.data) if val != 0}

    def dump(self):
        used = self.non_zero()
        if not used:
            print("  (all memory is 0)")
            return
        for address, value in used.items():
            print(f"  {address:08b} ({address:3}): {value}")


if __name__ == "__main__":
    memory = Memory()
    memory.load_from_file("data_input.txt")
    print("Memory after loading data_input.txt:")
    memory.dump()