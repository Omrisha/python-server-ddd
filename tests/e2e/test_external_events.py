import json

from tenacity import Retrying, stop_after_delay

from tests.e2e import redis_client, api_client
from tests.random_refs import random_order_id, random_sku, random_batch_ref


def test_change_batch_quantity_leading_to_reallocation():
    order_id, sku = random_order_id(), random_sku()
    earlier_batch, later_batch = random_batch_ref("old"), random_batch_ref("newer")
    api_client.post_to_add_batch(earlier_batch, sku, qty=10, eta="2011-01-01")
    api_client.post_to_add_batch(later_batch, sku, qty=10, eta="2011-01-02")
    response = api_client.post_to_allocate(order_id, sku, 10)
    assert response.json()["batchref"] == earlier_batch

    subscription = redis_client.subscribe_to("line_allocated")

    redis_client.publish_message(
        "change_batch_quantity",
        {"batchref": earlier_batch, "qty": 5},
    )

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
            data = json.loads(messages[-1]["data"])
            assert data["orderid"] == order_id
            assert data["batchref"] == later_batch
