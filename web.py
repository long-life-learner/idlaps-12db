from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
import os
import pandas as pd
from datetime import datetime
import atexit

app = Flask(__name__)
app.secret_key = 'IDLAPS-CHECKPOINT'  # Gantilah dengan secret key yang aman
# db_path = os.path.expanduser(r'~\\IDLAPS CHECKPOINT\\inventory.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Bismillah74@localhost:5432/inventory'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
# app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
#     'pool_pre_ping': True,  # Ping koneksi sebelum digunakan
#     'pool_recycle': 280,    # Mendaur ulang koneksi setiap 280 detik
#     'pool_timeout': 30,     # Timeout jika koneksi pool penuh
#     'max_overflow': 10,     # Maksimal koneksi tambahan
# }
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Define models
class EPC(db.Model):
    __tablename__ = 'epc'
    id = db.Column(db.Integer, primary_key=True)
    bib_number = db.Column(db.String(50), nullable=False)
    epc = db.Column(db.String(50), nullable=False, unique=True)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    epc = db.Column(db.String(50), nullable=False, unique=True)
    timestamp = db.Column(db.String(50), nullable=False)  # Changed to String to handle non-ISO format
    
# Initialize database
def initialize_database():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('epc'):
            db.create_all()

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

@app.route('/', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        file = request.files['file']
        
        if file and file.filename.endswith('.xlsx'):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                data = pd.read_excel(filepath)
                if data.empty:
                    flash('File Excel kosong atau tidak terbaca.', 'error')
                    return redirect(url_for('upload_excel'))

                count = 0
                first_row = None
                last_row = None

                for _, row in data.iterrows():
                    try :
                        epc_entry = EPC(bib_number=row['bib'], epc=row['epc'])
                        db.session.merge(epc_entry)  # Use merge to avoid duplicates
                        count += 1
                        if first_row is None:
                            first_row = row
                        last_row = row

                    except IntegrityError:
                        db.session.rollback()  # rollback transaksi yang error
                        flash(f'Data lama masih ada. Hapus terlebih dahulu jika ingin mengganti, kunjungi halaman "lihat data yang terbaca" untuk menghapus data', 'error')
                        
                        return redirect(url_for('upload_excel'))
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Gagal memproses baris: {row}. Error: {e}', 'error')
                        
                        return redirect(url_for('upload_excel'))

                db.session.commit()
                if count > 0:
                    flash(f'Berhasil memproses {count} data. '
                          f'Data pertama: bib={first_row["bib"]}, epc={first_row["epc"]}. '
                          f'Data terakhir: bib={last_row["bib"]}, epc={last_row["epc"]}.', 'success')
                else:
                    flash('Tidak ada data yang diproses.', 'warning')

            except Exception as e:
                flash(f'Gagal memproses file: {e}', 'error')

            return redirect(url_for('upload_excel'))
        else:
            flash('Format file tidak didukung. Harap unggah file Excel (.xlsx).', 'error')

    return render_template('upload.html')

@app.route('/data', methods=['GET'])
def fetch_data():
    results = db.session.query(EPC.bib_number, Inventory.timestamp).join(Inventory, EPC.epc == Inventory.epc).order_by(Inventory.timestamp.desc()).all()
    data = []
    for r in results:
        try:
            formatted_timestamp = datetime.fromisoformat(r[1]).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            formatted_timestamp = r[1]  # Use raw value if not ISO format
        data.append({'bib_number': r[0], 'timestamp': formatted_timestamp})
    
    total_bib = len({d['bib_number'] for d in data})
    return jsonify({'data': data, 'total_bib': total_bib})

@app.route('/clear_data', methods=['GET'])
def clear_data():
    try:
        with app.app_context():
            # Hapus semua data dari tabel `epc` dan `inventory`
            db.session.query(EPC).delete()
            db.session.query(Inventory).delete()
            db.session.commit()
        return jsonify({'message': 'Data EPC dan Inventory berhasil dihapus dari database.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/clear_inv', methods=['GET'])
def clear_inv():
    try:
        with app.app_context():
            # Hapus semua data dari tabel `inventory`
            db.session.query(Inventory).delete()
            db.session.commit()
        return jsonify({'message': 'Data Inventory berhasil dihapus dari database.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/display', methods=['GET'])
def display_data():
    return render_template('display.html')

@app.route('/race_data', methods=['GET'])
def race_data():
    try:
        data = []

        # Ambil semua bib yang pernah muncul di inventory
        bib_list = (
            # db.session.query(EPC.bib_number, EPC.nama, EPC.tim, Inventory.timestamp)
            db.session.query(EPC.bib_number, Inventory.timestamp)
            .join(Inventory, EPC.epc == Inventory.epc)
            .order_by(Inventory.timestamp.asc())
            .all()
        )

        bib_grouped = {}
        for bib_number, ts in bib_list:
            if bib_number not in bib_grouped:
                bib_grouped[bib_number] = {
                    # 'nama': nama,
                    # 'tim': tim,
                    'timestamps': []
                }
            bib_grouped[bib_number]['timestamps'].append(datetime.fromisoformat(ts))

        # Hitung total waktu dan waktu lap terakhir
        for bib, info in bib_grouped.items():
            timestamps = sorted(info['timestamps'])

            # Hitung waktu antar lap
            lap_times = [(timestamps[i] - timestamps[i - 1]).total_seconds()
                         for i in range(1, len(timestamps))]

            total_time = sum(lap_times) if lap_times else 0
            last_lap = lap_times[-1] if lap_times else 0

            data.append({
                'bib_number': bib,
                # 'nama': info['nama'],
                # 'tim': info['tim'],
                'last_lap': last_lap,
                'total_time': total_time
            })

        # Urutkan berdasarkan total_time (tercepat di atas)
        data = sorted(data, key=lambda x: x['total_time'])
        
        # Hitung posisi dan gap
        for i, row in enumerate(data):
            row['position'] = i + 1
            if i < len(data) - 1:
                gap = data[i + 1]['total_time'] - row['total_time']
                row['gap'] = round(gap, 2)
            else:
                row['gap'] = '-'

        return jsonify({'data': data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    initialize_database()
    app.run(debug=False)
