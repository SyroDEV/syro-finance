
from flask import Flask, Response, request, jsonify
from workers import wsgi
from pyodide.ffi import run_sync

app = Flask(__name__)


@app.route("/api/health")
def health():

    return jsonify({
        "status": "online",
        "app": "SYRO"
    })


@app.route("/")
@app.route("/<path:path>")
def frontend(path=""):

    if not path:
        path = "index.html"

    assets = request.environ["workers.env"].ASSETS

    asset_response = run_sync(
        assets.fetch(
            f"https://assets.local/{path}"
        )
    )

    body = run_sync(
        asset_response.bytes()
    )

    return Response(
        body,
        status=asset_response.status,
        headers=asset_response.headers
    )


Default = wsgi.entrypoint(app)
