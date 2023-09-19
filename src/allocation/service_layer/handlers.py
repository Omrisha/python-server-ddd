from typing import TYPE_CHECKING
from allocation.adapters import notifications

from allocation.adapters import redis_eventpublisher
from allocation.domain import model, events, commands
from allocation.domain.model import OrderLine
from allocation.service_layer import unit_of_work

if TYPE_CHECKING:
    from . import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
        command: commands.CreateBatch,
        uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get(sku=command.sku)
        if product is None:
            product = model.Product(command.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(command.ref, command.sku, command.qty, command.eta))
        uow.commit()


def allocate(
        command: commands.Allocate,
        uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = OrderLine(command.order_id, command.sku, command.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_ref = product.allocate(line)
        uow.commit()
        return batch_ref
    

def reallocate(
        cmd: commands.Allocate,
        uow: unit_of_work.AbstractUnitOfWork,
):
    line = OrderLine(cmd.order_id, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        product.allocate(line)
        uow.commit()


def change_batch_quantity(
        command: commands.ChangeBatchQuantity,
        uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get_by_batch_ref(batch_ref=command.ref)
        product.change_batch_quantity(ref=command.ref, qty=command.qty)
        uow.commit()


def send_out_of_stock_notification(
        event: events.OutOfStock
):
    notifications.send_email(
        "stock@make.com",
        f"Out of stock for {event.sku}",
    )


def deallocate(
        command: commands.Deallocate,
        uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        product = uow.products.get(sku=command.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {command.sku}")
        product.deallocate(command.ref, OrderLine(command.order_id, command.sku, command.qty))
        uow.commit()
        

def publish_allocated_event(
        event: events.Allocated,
        uow: unit_of_work.AbstractUnitOfWork,
):
    redis_eventpublisher.publish("line_allocated", event)


def add_allocations_to_read_model(
    event: events.Allocated,
    uow: unit_of_work.SqlAlchemyUnitOfWork
):
    with uow:
        uow.session.execute(
            """
            INSERT INTO allocations_view (orderid, sku, batchref)
            values (:orderid, :sku, :batchref)
            """,
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref)
        )
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated,
    uow: unit_of_work.SqlAlchemyUnitOfWork
):
    with uow:
        uow.session.execute(
            """
            DELETE FROM allocations_view
            WHERE orderid = :orderid AND sku = :sku
            """,
            dict(orderid=event.orderid, sku=event.sku)
        )
        uow.commit()


COMMAND_HANDLERS = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.Deallocate: deallocate,
    commands.ChangeBatchQuantity: change_batch_quantity,
}

EVENT_HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
    events.Allocated: [
        publish_allocated_event,
        add_allocations_to_read_model
    ],
    events.Deallocated: [
        remove_allocation_from_read_model
    ]
}