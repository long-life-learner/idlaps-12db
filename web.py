from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import inspect, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
import sqlite3
import os
import pandas as pd
from datetime import datetime, date, time, timedelta
import re

import atexit
import webbrowser

def pyinstaller_resource_path(relative_path):
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            template_folder=pyinstaller_resource_path("templates"),
            static_folder=pyinstaller_resource_path("static"))
app.secret_key = "IDLAPS-CHECKPOINT"  # Gantilah dengan secret key yang aman

# ─────────────────────────────────────────────────────────────────────────────
# SQLite — database file di sebelah .exe (atau direktori root saat development)
# ─────────────────────────────────────────────────────────────────────────────
from ui.utils import get_db_path  # noqa: E402  (import di sini agar path tersedia)
_DB_PATH = get_db_path()
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"check_same_thread": False},  # Flask berjalan di thread terpisah
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

# ─────────────────────────────────────────────────────────────────────────────
# Aktifkan WAL mode + synchronous=NORMAL pada setiap koneksi SQLite baru.
# WAL (Write-Ahead Logging) mengizinkan 1 writer + banyak reader BERSAMAAN
# tanpa menimbulkan error "database is locked".
# ─────────────────────────────────────────────────────────────────────────────
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")  # tunggu 30 detik sebelum error
        cursor.close()


# Define models
class EPC(db.Model):
    __tablename__ = "epc"
    id = db.Column(db.Integer, primary_key=True)
    bib_number = db.Column(db.String(50), nullable=False)
    epc = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=True)
    team = db.Column(db.String(100), nullable=True)
    category_id = db.Column(db.Integer, nullable=True)


class Inventory(db.Model):
    __tablename__ = "inventory"
    id = db.Column(db.Integer, primary_key=True)
    epc = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(
        db.String(50), nullable=False
    )  # Changed to String to handle non-ISO format
    reader_id = db.Column(db.String(50), nullable=True)  # Identitas antenna yang merekam


class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lap = db.Column(db.Integer, nullable=True)


# Initialize database
def initialize_database():
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            if not inspector.has_table("epc") or not inspector.has_table("inventory") or not inspector.has_table("category"):
                db.create_all()
            
            # Migrasi: Tambah kolom reader_id jika belum ada (untuk DB lama)
            if inspector.has_table("inventory"):
                columns = [col['name'] for col in inspector.get_columns("inventory")]
                if "reader_id" not in columns:
                    from sqlalchemy import text
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE inventory ADD COLUMN reader_id TEXT"))
                        conn.commit()
                        print("[DB] Kolom 'reader_id' berhasil ditambahkan ke tabel inventory.")

            print(f"[DB] SQLite database siap: {_DB_PATH}")
            return True, "Database initialized successfully"
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False, str(e)


# Function to close database connection
def close_database_connection():
    try:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
            print("Database connection closed.")
    except Exception as e:
        print(f"Error closing database connection: {e}")


# Register the cleanup function to run when the server shuts down
atexit.register(close_database_connection)


@app.route("/upload", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        file = request.files["file"]

        if file and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                # Gunakan sheet_name=None untuk membaca semua sheet jadi Dictionary
                data_dict = pd.read_excel(filepath, sheet_name=None)
                
                if not data_dict:
                    flash("File Excel kosong atau format tidak sesuai.", "error")
                    return redirect(url_for("upload_excel"))

                cat_count = 0
                epc_count = 0

                # 1. Proses sheet Kategori Terlebih Dahulu
                if "category" in data_dict:
                    cat_data = data_dict["category"]
                    for _, row in cat_data.iterrows():
                        try:
                            # Gunakan parameter dari header row: id, name, lap
                            cat_id = int(row["id"]) if pd.notna(row.get("id")) else None
                            if cat_id is not None:
                                cat_entry = Category(
                                    id=cat_id, 
                                    name=str(row["name"]), 
                                    lap=int(row["lap"]) if pd.notna(row.get("lap")) else 99
                                )
                                db.session.merge(cat_entry)
                                cat_count += 1
                        except Exception as e:
                            db.session.rollback()
                            flash(f"Gagal memproses kategori baris {row.to_dict()}: {e}", "error")
                            return redirect(url_for("upload_excel"))
                    db.session.commit()

                # 2. Proses sheet EPC (Pembalap)
                epc_sheet_name = None
                if "epc" in data_dict:
                    epc_sheet_name = "epc"
                elif "Sheet1" in data_dict and not "category" in data_dict:
                    # Fallback compatibility ke template lama
                    epc_sheet_name = list(data_dict.keys())[0]

                if epc_sheet_name:
                    epc_data = data_dict[epc_sheet_name]
                    for _, row in epc_data.iterrows():
                        try:
                            epc_entry = EPC(
                                bib_number=str(row["bib"]),
                                epc=str(row["epc"]),
                                name=str(row.get("name", "")),
                                team=str(row.get("team", "")),
                                category_id=int(row.get("category_id", 0)) if pd.notna(row.get("category_id")) else None,
                            )
                            db.session.merge(epc_entry)
                            epc_count += 1
                        except IntegrityError:
                            db.session.rollback()
                            flash(f'Gagal: Duplicate EPC Tag ({row.get("epc")}). Tag ini sudah ada di database.', "error")
                            return redirect(url_for("upload_excel"))
                        except Exception as e:
                            db.session.rollback()
                            flash(f"Gagal memproses pembalap baris {row.to_dict()}: {e}", "error")
                            return redirect(url_for("upload_excel"))
                    db.session.commit()

                flash(f"Berhasil Sinkronisasi: {cat_count} Kategori dan {epc_count} Data EPC/Pembalap diperbarui.", "success")
            except Exception as e:
                flash(f"Kesalahan Fatal saat membaca file: {e}", "error")

            return redirect(url_for("upload_excel"))
        else:
            flash("Format file tidak didukung. Harap unggah file Excel (.xlsx / .xls).", "error")

    return render_template("upload.html")

# ==========================================
# CATEGORY CRUD API
# ==========================================
@app.route("/category_page", methods=["GET"])
def category_page():
    return render_template("category.html")

@app.route("/api/category", methods=["POST"])
def create_category():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Nama kategori wajib diisi"}), 400
    try:
        new_cat = Category(
            name=data["name"], 
            lap=int(data.get("lap", 10))
        )
        db.session.add(new_cat)
        db.session.commit()
        return jsonify({"message": "Kategori berhasil ditambahkan"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/category/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"error": "Kategori tidak ditemukan"}), 404
    data = request.get_json()
    try:
        if "name" in data:
            cat.name = data["name"]
        if "lap" in data:
            cat.lap = int(data["lap"])
        db.session.commit()
        return jsonify({"message": "Kategori berhasil diperbarui"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/category/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    # Proteksi: Jangan hapus jika ada EPC (Pembalap) berlaga di kategori ini
    linked_epc = EPC.query.filter_by(category_id=cat_id).first()
    if linked_epc:
        return jsonify({"error": "Gagal: Kategori ini sedang tertaut dengan satu/lebih pembalap. Hapus data pembalap terkait terlebih dahulu."}), 400
    
    try:
        cat = Category.query.get(cat_id)
        if cat:
            db.session.delete(cat)
            db.session.commit()
            return jsonify({"message": "Kategori berhasil dihapus permanen"}), 200
        return jsonify({"error": "Kategori tidak ditemukan"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


    return render_template("upload.html")


@app.route("/data", methods=["GET"])
def fetch_data():
    results = (
        db.session.query(Inventory.id, EPC.bib_number, Inventory.timestamp)
        .join(Inventory, EPC.epc == Inventory.epc)
        .order_by(Inventory.timestamp.desc())
        .all()
    )
    data = []
    for r in results:
        try:
            formatted_timestamp = datetime.fromisoformat(r[2]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            formatted_timestamp = r[2]  # Use raw value if not ISO format
        data.append({"id": r[0], "bib_number": r[1], "timestamp": formatted_timestamp})

    total_bib = len({d["bib_number"] for d in data})
    return jsonify({"data": data, "total_bib": total_bib})


# endpoint hapus data per ID
@app.route("/delete/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = Inventory.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": f"Data dengan ID {item_id} berhasil dihapus"})
    else:
        return jsonify({"error": "Data tidak ditemukan"}), 404


TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\.\d{3}$")


@app.route("/update/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json(silent=True) or {}
    new_timestamp = (data.get("timestamp") or "").strip()

    if not new_timestamp:
        return jsonify({"error": "timestamp tidak boleh kosong"}), 400

    # Validasi format HH:MM:SS.mmm
    if not TIME_REGEX.match(new_timestamp):
        return (
            jsonify({"error": "Format waktu harus HH:MM:SS.mmm, contoh 22:51:52.968"}),
            400,
        )

    item = Inventory.query.get(item_id)
    if not item:
        return jsonify({"error": f"Data dengan ID {item_id} tidak ditemukan"}), 404

    try:
        # Jika kolom Inventory.timestamp adalah String/Text, langsung simpan string:
        item.timestamp = new_timestamp

        # Jika kolomnya bertipe DateTime dan kamu ingin tetap menyimpan:
        # - Simpan sebagai string di kolom terpisah, ATAU
        # - Gabungkan dengan tanggal (mis. tanggal hari ini) sebelum set ke DateTime.
        # Contoh gabung (opsional):
        # from datetime import datetime, date
        # t = datetime.strptime(new_timestamp, '%H:%M:%S.%f').time()
        # item.timestamp = datetime.combine(date.today(), t)

        db.session.commit()
        return jsonify({"message": f"Waktu untuk ID {item_id} berhasil diperbarui"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/clear_data", methods=["GET"])
def clear_data():
    try:
        with app.app_context():
            # Hapus semua data dari tabel `epc` dan `inventory`
            db.session.query(EPC).delete()
            db.session.query(Inventory).delete()
            db.session.query(Category).delete()
            db.session.commit()
        return (
            jsonify(
                {"message": "Data EPC dan Inventory dan Category berhasil dihapus dari database."}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/clear_inv", methods=["GET"])
def clear_inv():
    try:
        with app.app_context():
            # Hapus semua data dari tabel `inventory`
            db.session.query(Inventory).delete()
            db.session.commit()
        return (
            jsonify({"message": "Data Inventory berhasil dihapus dari database."}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/display", methods=["GET"])
def display_data():
    return render_template("display.html")


@app.route("/", methods=["GET"])
def home():
    return render_template("menu.html")


def format_time(seconds):
    """Format detik (float) ke HH:mm:ss.mmm. Menangani nilai negatif juga."""
    if seconds is None:
        return "00:00:00.000"
    sign = "-" if seconds < 0 else ""
    s = abs(seconds)
    sec_int = int(s)
    ms = int(round((s - sec_int) * 1000))
    # handle rounding carry
    if ms == 1000:
        sec_int += 1
        ms = 0
    hours = sec_int // 3600
    minutes = (sec_int % 3600) // 60
    secs = sec_int % 60
    return f"{sign}{hours:02}:{minutes:02}:{secs:02}.{ms:03}"


def parse_timestamp(ts, start_time_dt=None, ref_date=None):
    """
    Parse berbagai format:
      - full ISO datetime -> datetime.fromisoformat
      - time-only "HH:MM:SS" or "HH:MM:SS.fff" -> combine with ref_date or start_time_dt.date() or today
    Jika start_time_dt diberikan, dan hasil < start_time_dt, tambahkan 1 hari sampai >= start_time_dt
    """
    if ts is None:
        raise ValueError("Empty timestamp")
    if isinstance(ts, datetime):
        dt = ts
    else:
        ts_str = str(ts).strip()
        # coba ISO full
        try:
            dt = datetime.fromisoformat(ts_str)
        except Exception:
            # coba time only
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
                try:
                    t = datetime.strptime(ts_str, fmt).time()
                    break
                except Exception:
                    t = None
            if t is None:
                raise ValueError(f"Unsupported timestamp format: {ts_str}")
            if start_time_dt:
                base_date = start_time_dt.date()
            elif ref_date:
                base_date = ref_date
            else:
                base_date = date.today()
            dt = datetime.combine(base_date, t)

    # jika start_time_dt ada, pastikan dt >= start_time_dt (jika tidak, anggap lewat tengah malam -> tambah hari)
    if start_time_dt:
        while dt < start_time_dt:
            dt += timedelta(days=1)
    return dt


@app.route("/race_data", methods=["GET"])
def race_data():
    try:
        # parse start_time param: format HH:MM:SS (time-only)
        start_time_str = request.args.get("start_time", "").strip()
        category = request.args.get("category", "").strip()
        start_time_dt = None
        ref_date = date.today()
        if start_time_str:
            # terima "HH:MM:SS" atau "HH:MM"
            try:
                t = datetime.strptime(start_time_str, "%H:%M:%S").time()
            except ValueError:
                try:
                    t = datetime.strptime(start_time_str, "%H:%M").time()
                except ValueError:
                    # invalid -> fallback ke midnight
                    t = time(0, 0, 0)
            start_time_dt = datetime.combine(ref_date, t)
        else:
            # default: midnight hari ini (atau Anda bisa ubah ke earliest read)
            start_time_dt = datetime.combine(ref_date, time(0, 0, 0))

        # ambil data (Batasi columns supaya tidak menyebabkan unpack error)
        rows = (
            db.session.query(EPC.bib_number, EPC.name, EPC.team, Inventory.timestamp)
            .join(Inventory, EPC.epc == Inventory.epc)
            .filter(EPC.category_id == category)
            .order_by(Inventory.timestamp.asc())
            .all()
        )

        # group per bib dengan parsing timestamp
        bib_grouped = {}
        for bib_number, name, team, ts in rows:
            try:
                parsed_ts = parse_timestamp(ts, start_time_dt, ref_date)
            except Exception:
                # lewati timestamp yg tidak bisa di-parse
                continue
            if bib_number not in bib_grouped:
                bib_grouped[bib_number] = {"name": name, "team": team, "timestamps": []}
            bib_grouped[bib_number]["timestamps"].append(parsed_ts)

        # hitung lap times (angka), total_seconds, last_lap_seconds, lap_count
        riders = []
        # Tambahan Jaring Pengaman (Software Debounce) 
        # Cukup ubah angka ini 
        MIN_LAP_SECONDS = 15.0

        for bib, info in bib_grouped.items():
            # hanya ambil timestamps yang >= start_time_dt
            stamps = sorted([t for t in info["timestamps"] if t >= start_time_dt])
            if not stamps:
                continue
                
            # Filter ganda (Software Level) untuk membuang Tag B yang tak sengaja lolos karena masalah antrian alat
            valid_stamps = [stamps[0]]
            for i in range(1, len(stamps)):
                if (stamps[i] - valid_stamps[-1]).total_seconds() >= MIN_LAP_SECONDS:
                    valid_stamps.append(stamps[i])
            
            lap_times = []
            # lap pertama = first_timestamp - start_time
            lap_times.append((valid_stamps[0] - start_time_dt).total_seconds())
            for i in range(1, len(valid_stamps)):
                lap_times.append((valid_stamps[i] - valid_stamps[i - 1]).total_seconds())
                
            total_seconds = sum(lap_times)
            last_lap_seconds = lap_times[-1] if lap_times else 0.0
            lap_count = len(lap_times)
            riders.append(
                {
                    "bib_number": bib,
                    "name": info["name"],
                    "team": info["team"],
                    "lap_count": lap_count,
                    "total_seconds": total_seconds,
                    "last_lap_seconds": last_lap_seconds,
                }
            )

        # sort: lap_count desc, total_seconds asc
        riders.sort(key=lambda r: (-r["lap_count"], r["total_seconds"]))

        # hitung posisi dan gap (numeric), lalu format untuk dikirim
        final = []
        for i, r in enumerate(riders):
            pos = i + 1
            total_s = r["total_seconds"]
            last_s = r["last_lap_seconds"]

            if i == 0:
                gap_str = "-"
            else:
                prev = riders[i - 1]
                if r["lap_count"] == prev["lap_count"]:
                    diff = r["total_seconds"] - prev["total_seconds"]
                    gap_str = "+" + format_time(abs(diff))
                else:
                    lap_diff = prev["lap_count"] - r["lap_count"]
                    time_diff = abs(prev["total_seconds"] - r["total_seconds"])
                    gap_str = f"+{lap_diff}L {format_time(time_diff)}"

            final.append(
                {
                    "position": pos,
                    "bib_number": r["bib_number"],
                    "name": r["name"],
                    "team": r["team"],
                    "lap_count": r["lap_count"],
                    "last_lap": format_time(last_s),
                    "total_time": format_time(total_s),
                    "gap": gap_str,
                }
            )

        return jsonify({"data": final, "start_time": start_time_dt.isoformat()})
    except Exception as e:
        # untuk debugging Anda bisa print(e) atau log
        return jsonify({"error": str(e)}), 500


@app.route("/race")
def race_view():
    return render_template("race.html")


@app.route("/categories", methods=["GET"])
def get_categories():
    categories = db.session.query(Category.id, Category.name, Category.lap).order_by(Category.id.asc()).all()
    categories = [{"id": c[0], "name": c[1], "lap": c[2] if c[2] else 0} for c in categories if c[0] is not None]
    return jsonify({"categories": categories})


def start_web_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    success, msg = initialize_database()
    if success:
        start_web_server()
    else:
        print(f"Failed to start server: {msg}")
