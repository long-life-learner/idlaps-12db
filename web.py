from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import inspect

import os
import pandas as pd
from datetime import datetime
import atexit

app = Flask(__name__)
db_path = os.path.expanduser(r'~\\IDLAPS CHECKPOINT\\inventory.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the Excel file
            data = pd.read_excel(filepath)
            for _, row in data.iterrows():
                epc_entry = EPC(bib_number=row['bib'], epc=row['epc'])
                db.session.merge(epc_entry)  # Use merge to avoid duplicates
            db.session.commit()

            return redirect(url_for('upload_excel'))

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
        return jsonify({'message': 'All data has been cleared successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/display', methods=['GET'])
def display_data():
    return render_template('display.html')

if __name__ == '__main__':
    initialize_database()
    app.run(debug=False)
