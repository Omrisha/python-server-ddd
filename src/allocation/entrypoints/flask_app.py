from datetime import datetime

from flask import request, Flask, jsonify
from src.allocation.domain import model
from src.allocation.adapters import orm
from src.allocation.service_layer import services, unit_of_work

orm.start_mappers()
app = Flask(__name__)
app.config["DEBUG"] = True


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        batch_ref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            unit_of_work.SqlAlchemyUnitOfWork()
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batchref": batch_ref}), 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork(),
    )
    return "OK", 201