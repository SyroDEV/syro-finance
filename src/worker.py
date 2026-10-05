
from flask import Flask, Response as FlaskResponse, request, jsonify
from workers import wsgi
from pyodide.ffi import run_sync

import hashlib
import secrets
from datetime import datetime, timedelta

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
# AUTHENTICATION
# =========================================================

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


def verify_password(password, stored_password):
    try:
        salt, password_hash = stored_password.split(":", 1)

        calculated_hash = hash_password(
            password,
            salt
        )

        return secrets.compare_digest(
            calculated_hash,
            password_hash
        )

    except Exception:
        return False


def create_session(user_id):
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    expires_at = (
        datetime.utcnow() + timedelta(days=7)
    ).strftime("%Y-%m-%d %H:%M:%S")

    query_db("""
        INSERT INTO sessions
            (user_id, token_hash, expires_at)
        VALUES
            (?, ?, ?)
    """,
        user_id,
        token_hash,
        expires_at
    )

    return token


def get_current_user():
    token = request.cookies.get("syro_session")

    if not token:
        return None

    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    result = query_db("""
        SELECT
            users.id,
            users.nama,
            users.email
        FROM sessions
        JOIN users
            ON users.id = sessions.user_id
        WHERE
            sessions.token_hash = ?
            AND sessions.expires_at > CURRENT_TIMESTAMP
        LIMIT 1
    """, token_hash)

    users = result.get("results", [])

    return users[0] if users else None


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    try:
        data = request.get_json(silent=True) or {}

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({
                "error": "Email dan password wajib diisi"
            }), 400

        result = query_db("""
            SELECT
                id,
                nama,
                email,
                password_hash
            FROM users
            WHERE email = ?
            LIMIT 1
        """, email)

        users = result.get("results", [])

        if not users:
            return jsonify({
                "error": "Email atau password salah"
            }), 401

        user = users[0]

        if not verify_password(
            password,
            user["password_hash"]
        ):
            return jsonify({
                "error": "Email atau password salah"
            }), 401

        token = create_session(user["id"])

        response = jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "nama": user["nama"],
                "email": user["email"]
            }
        })

        response.set_cookie(
            "syro_session",
            token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
            path="/"
        )

        return response

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# CURRENT USER
# =========================================================

@app.route("/api/me", methods=["GET"])
def me():

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Belum login"
            }), 401

        return jsonify({
            "success": True,
            "user": user
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    try:
        token = request.cookies.get("syro_session")

        if token:
            token_hash = hashlib.sha256(
                token.encode()
            ).hexdigest()

            query_db("""
                DELETE FROM sessions
                WHERE token_hash = ?
            """, token_hash)

        response = jsonify({
            "success": True,
            "message": "Logout berhasil"
        })

        response.delete_cookie(
            "syro_session",
            path="/"
        )

        return response

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health", methods=["GET"])
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
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

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
            WHERE user_id = ?
            ORDER BY
                COALESCE(tanggal_transaksi, tanggal) DESC,
                id DESC
        """, user["id"])

        return jsonify(
            result.get("results", [])
        )

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# TAMBAH TRANSAKSI
# =========================================================

@app.route("/api/transaksi", methods=["POST"])
def tambah_transaksi():

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        data = request.get_json(silent=True) or {}

        jenis = data.get("jenis")
        kategori = data.get("kategori")
        nominal = data.get("nominal")
        keterangan = data.get("keterangan", "")
        tanggal_transaksi = data.get(
            "tanggal_transaksi"
        )

        if not jenis or not kategori or nominal is None:
            return jsonify({
                "error": "Data transaksi tidak lengkap"
            }), 400

        result = query_db("""
            INSERT INTO transaksi
                (
                    user_id,
                    jenis,
                    kategori,
                    nominal,
                    keterangan,
                    tanggal_transaksi
                )
            VALUES
                (?, ?, ?, ?, ?, ?)
        """,
            user["id"],
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
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# EDIT TRANSAKSI
# =========================================================

@app.route("/api/transaksi/<int:id>", methods=["PUT"])
def edit_transaksi(id):

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        data = request.get_json(silent=True) or {}

        jenis = data.get("jenis")
        kategori = data.get("kategori")
        nominal = data.get("nominal")
        keterangan = data.get("keterangan", "")
        tanggal_transaksi = data.get(
            "tanggal_transaksi"
        )

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
            WHERE
                id = ?
                AND user_id = ?
        """,
            jenis,
            kategori,
            int(nominal),
            keterangan,
            tanggal_transaksi,
            id,
            user["id"]
        )

        if result.get("meta", {}).get(
            "changes", 0
        ) == 0:

            return jsonify({
                "error": "Transaksi tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "message": "Transaksi berhasil diperbarui"
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# HAPUS SATU TRANSAKSI
# =========================================================

@app.route("/api/transaksi/<int:id>", methods=["DELETE"])
def hapus_transaksi(id):

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        result = query_db("""
            DELETE FROM transaksi
            WHERE
                id = ?
                AND user_id = ?
        """,
            id,
            user["id"]
        )

        if result.get("meta", {}).get(
            "changes", 0
        ) == 0:

            return jsonify({
                "error": "Transaksi tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "message": "Transaksi berhasil dihapus"
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# HAPUS SEMUA TRANSAKSI
# =========================================================

@app.route("/api/transaksi", methods=["DELETE"])
def hapus_semua_transaksi():

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        result = query_db("""
            DELETE FROM transaksi
            WHERE user_id = ?
        """, user["id"])

        return jsonify({
            "success": True,
            "message": "Semua transaksi berhasil dihapus",
            "deleted": result.get(
                "meta", {}
            ).get("changes", 0)
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# STATISTIK
# =========================================================

@app.route("/api/statistik", methods=["GET"])
def statistik():

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        bulan = request.args.get("bulan")

        if not bulan:
            return jsonify({
                "error": "Parameter bulan wajib diisi"
            }), 400

        result = query_db("""
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pemasukan'
                        THEN nominal
                        ELSE 0
                    END
                ), 0) AS pemasukan,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pengeluaran'
                        THEN nominal
                        ELSE 0
                    END
                ), 0) AS pengeluaran,

                COUNT(*) AS jumlah_transaksi

            FROM transaksi

            WHERE
                user_id = ?
                AND tanggal_transaksi LIKE ?
        """,
            user["id"],
            f"{bulan}%"
        )

        data = result.get(
            "results",
            []
        )

        if data:
            pemasukan = data[0].get(
                "pemasukan", 0
            )

            pengeluaran = data[0].get(
                "pengeluaran", 0
            )

            jumlah_transaksi = data[0].get(
                "jumlah_transaksi", 0
            )

        else:
            pemasukan = 0
            pengeluaran = 0
            jumlah_transaksi = 0

        saldo = (
            pemasukan - pengeluaran
        )

        return jsonify({
            "bulan": bulan,
            "pemasukan": pemasukan,
            "pengeluaran": pengeluaran,
            "saldo": saldo,
            "jumlah_transaksi": jumlah_transaksi
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/api/analytics", methods=["GET"])
def analytics():

    try:
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        bulan = request.args.get("bulan")

        if not bulan:
            return jsonify({
                "error": "Parameter bulan wajib diisi"
            }), 400

        arus_result = query_db("""
            SELECT
                tanggal_transaksi AS tanggal,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pemasukan'
                        THEN nominal
                        ELSE 0
                    END
                ), 0) AS pemasukan,

                COALESCE(SUM(
                    CASE
                        WHEN jenis = 'pengeluaran'
                        THEN nominal
                        ELSE 0
                    END
                ), 0) AS pengeluaran

            FROM transaksi

            WHERE
                user_id = ?
                AND tanggal_transaksi LIKE ?

            GROUP BY tanggal_transaksi

            ORDER BY tanggal_transaksi ASC
        """,
            user["id"],
            f"{bulan}%"
        )

        kategori_result = query_db("""
            SELECT
                kategori,
                COALESCE(
                    SUM(nominal),
                    0
                ) AS total

            FROM transaksi

            WHERE
                user_id = ?
                AND jenis = 'pengeluaran'
                AND tanggal_transaksi LIKE ?

            GROUP BY kategori

            ORDER BY total DESC
        """,
            user["id"],
            f"{bulan}%"
        )

        return jsonify({
            "bulan": bulan,
            "arus_kas": arus_result.get(
                "results",
                []
            ),
            "kategori": kategori_result.get(
                "results",
                []
            )
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# WORKERS ENTRYPOINT
# =========================================================



# =========================================================
# STATIC FILES
# =========================================================

@app.route("/", methods=["GET"])
def home():
    assets = request.environ["workers.env"].ASSETS
    response = run_sync(assets.fetch(request.url))

    body = run_sync(response.text())

    headers = {}
    for key, value in response.headers.items():
        headers[key] = value

    return body, response.status, headers


@app.route("/<path:path>", methods=["GET"])
def static_files(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not Found"}), 404

    assets = request.environ["workers.env"].ASSETS
    response = run_sync(assets.fetch(request.url))

    body = run_sync(response.text())

    headers = {}
    for key, value in response.headers.items():
        headers[key] = value

    return body, response.status, headers


Default = wsgi.entrypoint(app)
