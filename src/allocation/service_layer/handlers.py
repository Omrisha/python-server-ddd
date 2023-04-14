from src.allocation.adapters import email
from src.allocation.domain import model, events
from src.allocation.domain.model import OrderLine
from src.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
        event: events.BatchCreated,
        uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(event.ref, event.sku, event.qty, event.eta))
        uow.commit()


def allocate(
        event: events.AllocationRequired,
        uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = OrderLine(event.order_id, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_ref = product.allocate(line)
        uow.commit()
        return batch_ref


def send_out_of_stock_notification(
        event: events.OutOfStock
):
    email.send_email(
        "stock@make.com",
        f"Out of stock for {event.sku}",
    )


def deallocate(
        event: events.DeallocationRequired,
        uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {event.sku}")
        product.deallocate(event.ref, OrderLine(event.order_id, event.sku, event.qty))
        uow.commit()


def change_batch_quantity(
        event: events.BatchQuantityChanged,
        uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get_by_batch_ref(batch_ref=event.ref)
        product.change_batch_quantity(ref=event.ref, qty=event.qty)
        uow.commit()
