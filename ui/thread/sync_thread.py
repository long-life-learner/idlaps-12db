import time
import requests
import json
import sqlite3
import logging
from PySide6.QtCore import QThread, Signal
from ui.utils import get_db_path

logger = logging.getLogger()

class SyncThread(QThread):
    sync_status_signal = Signal(str, str) # level (info/error), message
    unsynced_count_signal = Signal(int) # count of synced=0
    
    def __init__(self, device_sn: str, reader_ip: str, parent=None):
        super().__init__(parent)
        self.device_sn = device_sn
        self.reader_ip = reader_ip
        self.db_path = get_db_path()
        self._is_running = True
        
        # Endpoint server
        self.server_url = "http://time.idlaps.com/api/checkpoint.php"
        
    def run(self):
        logger.info(f"SyncThread() > Started [SN: {self.device_sn}, IP: {self.reader_ip}]")
        
        while self._is_running:
            try:
                self.sync_data()
            except Exception as e:
                logger.error(f"SyncThread() > Crash: {e}")
                
            # Jeda agar tidak makan CPU dan flood network
            time.sleep(2)
            
        logger.info("SyncThread() > Stopped")

    def sync_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"SyncThread() > DB Connect Error: {e}")
            return
            
        try:
            # Emit jumlah data in wait saat ini ke UI
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE synced = 0")
            wait_count = cursor.fetchone()[0]
            self.unsynced_count_signal.emit(wait_count)

            # Batasi 500 records per request agar server tidak timeout/overload
            cursor.execute("SELECT id, epc, timestamp, reader_id FROM inventory WHERE synced = 0 LIMIT 500")
            rows = cursor.fetchall()
            
            if not rows:
                return # Tidak ada data yang antri
                
            reads = []
            ids_to_update = []
            
            for row in rows:
                record_id, epc, ts, r_id = row
                reads.append({
                    "epc": epc,
                    "timestamp": ts,
                    "rssi": -60 # default since we don't store RSSI in offline db currently
                })
                ids_to_update.append(record_id)
                
            payload = {
                "device_sn": self.device_sn,
                "reader_id": self.reader_ip,
                "reads": reads
            }
            
            try:
                # 10 detik cukup untuk upload JSON 500 array
                res = requests.post(self.server_url, json=payload, timeout=10)
                
                if res.status_code == 200:
                    resp_data = res.json()
                    if resp_data.get("success"):
                        # Sukses, update flag synced = 1
                        placeholders = ",".join("?" * len(ids_to_update))
                        update_query = f"UPDATE inventory SET synced = 1 WHERE id IN ({placeholders})"
                        cursor.execute(update_query, ids_to_update)
                        conn.commit()
                        logger.info(f"SyncThread() > Success sent {len(ids_to_update)} records.")
                    else:
                        logger.error(f"SyncThread() > Server error msg: {resp_data.get('message')}")
                        
                elif res.status_code == 422:
                    logger.warning(f"SyncThread() > Device SN '{self.device_sn}' BELUM DI-MAPPING di Web Dashboard!")
                    self.sync_status_signal.emit("warning", f"Device belum di-mapping di server.")
                elif res.status_code == 401:
                    logger.warning(f"SyncThread() > SN '{self.device_sn}' TIDAK DIKENALI Server!")
                    self.sync_status_signal.emit("error", f"Serial Number {self.device_sn} tidak terdaftar.")
                elif res.status_code == 400:
                    logger.error(f"SyncThread() > Server 400 Bad Request: {res.text}")
                else:
                    logger.error(f"SyncThread() > Network Error {res.status_code}: {res.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"SyncThread() > Post Error: {e}")
                
        except sqlite3.Error as e:
            logger.error(f"SyncThread() > DB Query Error: {e}")
        finally:
            cursor.close()
            conn.close()

    def stop(self):
        self._is_running = False
        self.wait(2000)
