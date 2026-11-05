"""cache.py - A small, fast cache between the CPU and memory."""

CACHE_SIZE = 4  # how many values the cache can hold


class Cache:
    def __init__(self, memory, size=CACHE_SIZE):
        self.memory = memory
        self.size = size
        self.entries = {}  # address -> value, oldest first
        self.enabled = False
        self.hits = 0
        self.misses = 0

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
        self.flush()

    def flush(self):
        self.entries.clear()

    def read(self, address):
        """Return (value, hit). hit is True if the value came from the cache."""
        if not self.enabled:
            return self.memory.read(address), False

        if address in self.entries:
            self.hits += 1
            return self.entries[address], True

        self.misses += 1
        value = self.memory.read(address)
        self._add(address, value)
        return value, False

    def _add(self, address, value):
        if len(self.entries) >= self.size:
            oldest = next(iter(self.entries))
            del self.entries[oldest]
        self.entries[address] = value

    def write(self, address, value):
        self.memory.write(address, value)  # write-through: memory always updated
        if self.enabled and address in self.entries:
            self.entries[address] = value

    def hit_rate(self):
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total * 100


if __name__ == "__main__":
    from memory import Memory

    memory = Memory()
    memory.load_from_file("data_input.txt")
    cache = Cache(memory)
    cache.enable()

    for address in [0, 1, 0, 2, 3, 4, 0]:
        value, hit = cache.read(address)
        result = "HIT" if hit else "MISS"
        print(f"Read address {address}: value {value} -> {result}")

    print(f"Hits: {cache.hits}, Misses: {cache.misses}, "
          f"Hit rate: {cache.hit_rate():.1f}%")