from src.allocation.domain import events
from src.allocation.service_layer import unit_of_work
from . import handlers


def handle(
        event: events.Event,
        uow: unit_of_work.AbstractUnitOfWork
):
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow=uow))
            queue.extend(uow.collect_new_events())

    return results


HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.AllocationRequired: [handlers.allocate],
    events.BatchCreated: [handlers.add_batch],
    events.DeallocationRequired: [handlers.deallocate],
    events.BatchQuantityChanged: [handlers.change_batch_quantity],
}
