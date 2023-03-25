from dataclasses import dataclass
from datetime import date
from typing import Optional, List


@dataclass(unsafe_hash=True)
class OrderLine:
    orderId: str
    sku: str
    qty: int


class Batch:
    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set()

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def allocate(self, line: OrderLine):
        print(f"Try allocate {line}")
        if self.can_allocate(line):
            print(f"{line} can be allocated")
            self._allocations.add(line)

    def deallocate(self, line: OrderLine):
        print(f"Try deallocate {line}")
        if line in self._allocations:
            print(f"{line} can be deallocated")
            self._allocations.remove(line)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine):
        return self.sku == line.sku and self.available_quantity >= line.qty


class OutOfStock(Exception):
    pass


def allocate(line: OrderLine, batches: List[Batch]) -> str:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        print(f"Next batch is {batch.reference} with sku {batch.sku}")
        batch.allocate(line)
        print(f"Batch with id {batch.reference} and sku {batch.sku} is successfully allocated")
        return batch.reference
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")


def deallocate(line: OrderLine, batch: Batch):
    try:
        batch.deallocate(line)
    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")

