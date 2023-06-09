# pylint: disable=no-self-use
from datetime import date
from unittest import mock

import pytest

from src.allocation.domain import model, events, commands
from src.allocation.service_layer import handlers, unit_of_work, messagebus

from src.allocation.adapters.repository import AbstractRepository


class FakeRepository(AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((b for b in self._products if b.sku == sku), None)

    def list(self):
        return list(self._products)

    def _get_by_batch_ref(self, batch_ref) -> model.Product:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batch_ref),
            None,
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class TestAddBatch:
    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(
            commands.CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None), uow
        )
        assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_for_existing_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("b1", "GARISH-RUG", 100, None), uow)
        messagebus.handle(commands.CreateBatch("b2", "GARISH-RUG", 99, None), uow)
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


@pytest.fixture(autouse=True)
def fake_redis_publish():
    with mock.patch("src.allocation.adapters.redis_eventpublisher.publish"):
        yield


class TestAllocation:
    def test_returns_allocation(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("batch1", "COMPLICATED-LAMP", 100, None), uow)
        result = messagebus.handle(commands.Allocate("o1", "COMPLICATED-LAMP", 10), uow)

        assert result.pop(0) == "batch1"
        [batch] = uow.products.get("COMPLICATED-LAMP").batches
        assert batch.available_quantity == 90

    def test_error_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("b1", "AREALSKU", 100, None), uow)

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            messagebus.handle(commands.Allocate("o1", "NONEXISTENTSKU", 10), uow)

    def test_commits(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("b1", "OMINOUS-MIRROR", 100, None), uow)
        messagebus.handle(commands.Allocate("o1", "OMINOUS-MIRROR", 10), uow)
        assert uow.committed

    def test_sends_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("b1", "POPULAR-CURTAINS", 9, None), uow)

        with mock.patch("src.allocation.adapters.email.send") as mock_send_email:
            messagebus.handle(commands.Allocate("o1", "POPULAR-CURTAINS", 10), uow)
            assert mock_send_email.call_args == mock.call(
                "stock@made.com", f"Out of stock for POPULAR-CURTAINS"
            )

    def test_deallocate_decrements_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("b1", "BLUE-PLINTH", 100, None), uow)
        messagebus.handle(commands.Allocate("o1", "BLUE-PLINTH", 10), uow)
        batch = next(b for b in uow.products.get("BLUE-PLINTH").batches if b.reference == "b1")
        assert batch.available_quantity == 90
        messagebus.handle(commands.Deallocate("b1", "o1", "BLUE-PLINTH", 10), uow)
        assert batch.available_quantity == 100


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(commands.CreateBatch("batch1", "ADORABLE-SETTEE", 100, None), uow)

        [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        messagebus.handle(commands.ChangeBatchQuantity("batch1", 50), uow)

        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            commands.CreateBatch("batch1", "INDIFFERENT-TABLE", 50, None),
            commands.CreateBatch("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            commands.Allocate("order1", "INDIFFERENT-TABLE", 20),
            commands.Allocate("order2", "INDIFFERENT-TABLE", 20)
        ]
        for e in event_history:
            messagebus.handle(e, uow)

        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(commands.ChangeBatchQuantity("batch1", 25), uow)

        # order1 or order2 will be deallocated, so we'll have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
