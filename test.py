from datetime import datetime
from rfid.tag import Tag
from ui.inventory_widget import DatabasePooler
from ui.inventory_widget import InventoryTagItemModel
from datetime import timedelta

def main():
    # Inisialisasi model
    model = InventoryTagItemModel(None)

    # Buat beberapa Tag dummy
    base_time = datetime.now()
    tags = [
        Tag(
            rssi=b'\x01',
            antenna=1,
            channel=1,
            data=b'\xDE\xAD\xBE\xEF',
            count=1,
            timestamp=base_time
        ),
        Tag(
            rssi=b'\x02',
            antenna=2,
            channel=2,
            data=b'\xCA\xFE\xBA\xBE',
            count=1,
            timestamp=base_time + timedelta(seconds=30)
        ),
        Tag(
            rssi=b'\x03',
            antenna=3,
            channel=3,
            data=b'\xAA\xBB\xCC\xDD',
            count=1,
            timestamp=base_time + timedelta(seconds=61)
        ),
    ]

    # Tambahkan tag dummy ke model
    for tag in tags:
        model.tags.append(tag)

    # Inisialisasi DatabasePooler
    pooler = DatabasePooler(model)

    # Jalankan fungsi send_data untuk simulasi insert ke database
    pooler.send_data()

if __name__ == "__main__":
    main()