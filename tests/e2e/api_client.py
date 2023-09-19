import requests

from allocation import config


def post_to_add_batch(ref, sku, qty, eta):
    url = config.get_api_url()
    r = requests.post(
        f"{url}/add_batch", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


def post_to_allocate(order_id, sku, qty, expect_success=True):
    url = config.get_api_url()
    r = requests.post(
        f"{url}/allocate",
        json={
            "orderid": order_id,
            "sku": sku,
            "qty": qty
        },
    )
    if expect_success:
        assert r.status_code == 201
    return r
