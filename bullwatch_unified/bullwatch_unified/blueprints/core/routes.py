from flask import render_template

from . import core_bp


@core_bp.get("/")
def dashboard():
    return render_template("core/dashboard.html", title="Dashboard")
