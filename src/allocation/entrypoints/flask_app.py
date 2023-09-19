from datetime import datetime

from flask import request, Flask, jsonify
from allocation import bootstrap
from allocation.domain import commands
from allocation.service_layer import views
from allocation.domain import model
from allocation.service_layer import handlers

app = Flask(__name__)
bus = bootstrap.bootstarp()


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        cmd = commands.Allocate(request.json["orderid"], request.json["sku"], request.json["qty"])
        results = bus.handle(cmd)
        batch_ref = results.pop(0)
    except (model.OutOfStock, handlers.InvalidSku) as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batch_ref": batch_ref}), 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(request.json["ref"], request.json["sku"], request.json["qty"], eta)
    bus.handle(cmd)
    return "OK", 201


@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid):
    result  = views.allocations(orderid, bus.uow)
    if not result:
        return "not found", 404
    return jsonify(result), 200