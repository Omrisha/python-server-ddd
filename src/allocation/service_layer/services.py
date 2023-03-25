from datetime import date
from typing import Optional

from src.allocation.domain import model
from src.allocation.domain.model import OrderLine
from src.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def allocate(
        orderid: str, sku: str, qty: int,
        uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = OrderLine(orderid, sku, qty)
    with uow:
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_ref = model.allocate(line, batches)
        uow.commit()
    return batch_ref


def add_batch(
        orderid, sku, qty, eta,
        uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        uow.batches.add(model.Batch(orderid, sku, qty, eta))
        uow.commit()


def deallocate(
        batch_ref, orderid: str, sku: str, qty: int,
        uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        batch = uow.batches.get(batch_ref)
        model.deallocate(OrderLine(orderid, sku, qty), batch)
        uow.commit()
