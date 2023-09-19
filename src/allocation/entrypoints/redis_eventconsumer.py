import json
import logging

import redis
from allocation.bootstrap import bootstarp

from allocation import config
from allocation.domain import commands

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())


def main():
    bus = bootstarp.bootstarp()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        hand_change_batch_quantity(m, bus)


def hand_change_batch_quantity(m, bus):
    logger.debug("handling %s", m)
    data = json.load(m["data"])
    cmd = commands.ChangeBatchQuantity(ref=data["batchref"], qty=data["qty"])
    bus.handle(cmd)
    