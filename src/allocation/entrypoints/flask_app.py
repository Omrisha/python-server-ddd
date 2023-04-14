from datetime import datetime

from flask import request, Flask, jsonify
from src.allocation.domain import model, events
from src.allocation.adapters import orm
from src.allocation.service_layer import handlers, unit_of_work, messagebus

orm.start_mappers()
app = Flask(__name__)
app.config["DEBUG"] = True


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        event = events.AllocationRequired(request.json["orderid"], request.json["sku"], request.json["qty"])
        results = messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
        batch_ref = results.pop(0)
    except (model.OutOfStock, handlers.InvalidSku) as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batch_ref": batch_ref}), 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    event = events.BatchCreated(request.json["ref"], request.json["sku"], request.json["qty"], eta)
    messagebus.handle(event, unit_of_work.SqlAlchemyUnitOfWork())
    return "OK", 201
