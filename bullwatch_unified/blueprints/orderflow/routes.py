from flask import render_template

from . import orderflow_bp


@orderflow_bp.get("/")
def index():
    return render_template("orderflow/index.html", title="Orderflow")
