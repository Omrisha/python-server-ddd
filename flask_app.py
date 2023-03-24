from flask import request, Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
import model
import repository
import orm

orm.start_mappers()
uri = config.get_postgres_uri()
engine = create_engine(uri)
get_session = sessionmaker(bind=engine)
app = Flask(__name__)
app.config["DEBUG"] = True


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = get_session()
    batches = repository.SqlAlchemyRepository(session).list()
    line = model.OrderLine(
        request.json["orderid"], request.json["sku"], request.json["qty"],
    )

    batch_ref = model.allocate(line, batches)

    return {"batchref": batch_ref}, 201
