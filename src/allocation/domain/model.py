from dataclasses import dataclass
from datetime import date
from typing import Optional, List

from src.allocation.domain import events, commands


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

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine):
        return self.sku == line.sku and self.available_quantity >= line.qty


class Product:
    def __init__(self, sku: str, batches: [Batch], version_number: int = 0):
        self.sku = sku
        self.batches = batches
        self.version_number = version_number
        self.events = []

    def allocate(self, line: OrderLine) -> str:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            print(f"Next batch is {batch.reference} with sku {batch.sku}")
            batch.allocate(line)
            self.version_number += 1
            self.events.append(
                events.Allocated(
                    orderid=line.orderId,
                    sku=line.sku,
                    qty=line.qty,
                    batchref=batch.reference,
                )
            )
            print(f"Batch with id {batch.reference} and sku {batch.sku} is successfully allocated")
            return batch.reference
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))

    def deallocate(self, batch_ref: str, line: OrderLine):
        try:
            batch = next(b for b in sorted(self.batches) if b.reference == batch_ref)
            batch.deallocate(line)
            self.version_number += 1
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))

    def change_batch_quantity(self, ref: str, qty: int):
        batch = next(b for b in self.batches if b.reference == ref)
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(
                commands.Allocate(line.orderId, line.sku, line.qty)
            )
