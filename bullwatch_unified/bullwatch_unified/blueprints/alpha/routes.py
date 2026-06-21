from flask import render_template

from . import alpha_bp


@alpha_bp.get("/")
def index():
    return render_template("alpha/index.html", title="Alpha")
