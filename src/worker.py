
from flask import Flask, Response, request, jsonify
from workers import wsgi
from pyodide.ffi import run_sync

app = Flask(__name__)


# =========================================================
# D1 DATABASE
# =========================================================

def get_db():
    env = request.environ["workers.env"]
    return env.DB


def query_db(sql, *params):
    db = get_db()

    statement = db.prepare(sql)

    if params:
        statement = statement.bind(*params)

    result = run_sync(statement.run())

    return {
        "results": result.results,
        "meta": result.meta
    }


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "app": "SYRO"
    })


# =========================================================
# GET TRANSAKSI
# =========================================================

@app.route("/api/transaksi", methods=["GET"])
def get_transaksi():

    try:
        result = query_db("""
            SELECT
                id,
                jenis,
                kategori,
                nominal,
                keterangan,
                tanggal,
                tanggal_transaksi
            FROM transaksi
            ORDER BY
                COALESCE(tanggal_transaksi, tanggal) DESC,
                id DESC
        """)

        return jsonify(result.get("results", []))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# TAMBAH TRANSAKSI
# =========================================================

@app.route("/api/transaksi", methods=["POST"])
def tambah_transaksi():

    try:
        data = request.get_json(silent=True) or {}

        jenis = data.get("jenis")
        kategori = data.get("kategori")
        nominal = data.get("nominal")
        keterangan = data.get("keterangan", "")
        tanggal_transaksi = data.get("tanggal_transaksi")

        if not jenis or not kategori or nominal is None:
            return jsonify({
                "error": "Data transaksi tidak lengkap"
            }), 400

        result = query_db("""
            INSERT INTO transaksi
                (jenis, kategori, nominal, keterangan, tanggal_transaksi)
            VALUES
                (?, ?, ?, ?, ?)
        """,
            jenis,
            kategori,
            int(nominal),
            keterangan,
            tanggal_transaksi
        )

        return jsonify({
            "success": True,
            "message": "Transaksi berhasil ditambahkan",
            "result": result
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# EDIT TRANSAKSI
# =========================================================

@app.route("/api/transaksi/<int:id>", methods=["PUT"])
def edit_transaksi(id):

    try:
        data = request.get_json(silent=True) or {}

        jenis = data.get("jenis")
        kategori = data.get("kategori")
        nominal = data.get("nominal")
        keterangan = data.get("keterangan", "")
        tanggal_transaksi = data.get("tanggal_transaksi")

        if not jenis or not kategori or nominal is None:
            return jsonify({
                "error": "Data transaksi tidak lengkap"
            }), 400

        result = query_db("""
            UPDATE transaksi
            SET
                jenis = ?,
                kategori = ?,
                nominal = ?,
                keterangan = ?,
                tanggal_transaksi = ?
            WHERE id = ?
        """,
            jenis,
            kategori,
            int(nominal),
            keterangan,
            tanggal_transaksi,
            id
        )

        if result.get("meta", {}).get("changes", 0) == 0:
            return jsonify({
                "error": "Transaksi tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "message": "Transaksi berhasil diperbarui"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# HAPUS SATU TRANSAKSI
# =========================================================

@app.route("/api/transaksi/<int:id>", methods=["DELETE"])
def hapus_transaksi(id):

    try:
        result = query_db("""
            DELETE FROM transaksi
            WHERE id = ?
        """, id)

        if result.get("meta", {}).get("changes", 0) == 0:
            return jsonify({
                "error": "Transaksi tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "message": "Transaksi berhasil dihapus"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# HAPUS SEMUA
# =========================================================

@app.route("/api/transaksi", methods=["DELETE"])
def hapus_semua_transaksi():

    try:
        result = query_db("""
            DELETE FROM transaksi
        """)

        return jsonify({
            "success": True,
            "message": "Semua transaksi berhasil dihapus",
            "deleted": result.get("meta", {}).get("changes", 0)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# STATISTIK
# =========================================================

@app.route("/api/statistik", methods=["GET"])
def statistik():

    try:
        bulan = request.args.get("bulan")

        if not bulan:
            return jsonify({
                "error": "Parameter bulan wajib diisi"
            }), 400

        result = query_db("""
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pemasukan' THEN nominal
                        ELSE 0
                    END
                ), 0) AS pemasukan,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pengeluaran' THEN nominal
                        ELSE 0
                    END
                ), 0) AS pengeluaran

            FROM transaksi
            WHERE tanggal_transaksi LIKE ?
        """, f"{bulan}%")

        data = result.get("results", [])

        pemasukan = data[0]["pemasukan"] if data else 0
        pengeluaran = data[0]["pengeluaran"] if data else 0

        return jsonify({
            "bulan": bulan,
            "pemasukan": pemasukan,
            "pengeluaran": pengeluaran,
            "saldo": pemasukan - pengeluaran
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/api/analytics", methods=["GET"])
def analytics():

    try:
        bulan = request.args.get("bulan")

        if not bulan:
            return jsonify({
                "error": "Parameter bulan wajib diisi"
            }), 400

        arus_kas = query_db("""
            SELECT
                tanggal_transaksi AS tanggal,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pemasukan' THEN nominal
                        ELSE 0
                    END
                ), 0) AS pemasukan,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pengeluaran' THEN nominal
                        ELSE 0
                    END
                ), 0) AS pengeluaran

            FROM transaksi
            WHERE tanggal_transaksi LIKE ?
            GROUP BY tanggal_transaksi
            ORDER BY tanggal_transaksi ASC
        """, f"{bulan}%")

        kategori = query_db("""
            SELECT
                kategori,
                SUM(nominal) AS total

            FROM transaksi
            WHERE
                jenis = 'pengeluaran'
                AND tanggal_transaksi LIKE ?

            GROUP BY kategori
            ORDER BY total DESC
        """, f"{bulan}%")

        return jsonify({
            "arus_kas": arus_kas.get("results", []),
            "kategori": kategori.get("results", [])
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# FRONTEND
# =========================================================

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


# =========================================================
# CLOUDFLARE WORKER
# =========================================================

Default = wsgi.entrypoint(app)
