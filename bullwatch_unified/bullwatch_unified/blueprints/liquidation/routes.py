from flask import render_template

from . import liquidation_bp


@liquidation_bp.get("/")
def index():
    return render_template("liquidation/index.html", title="Liquidation")
