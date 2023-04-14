import uuid


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name=""):
    return f"sku-{name}-{random_suffix()}"


def random_batch_ref(name=""):
    return f"batch-{name}-{random_suffix()}"


def random_order_id(name=""):
    return f"order-{name}-{random_suffix()}"
