import sqlite3
import datetime

# Yeni veritabanı yolu
DB_PATH = r"C:\Proje\Proje.db"

def baglanti_al():
    return sqlite3.connect(DB_PATH)

def islenmemis_videolari_getir():
    """status = 0 olan videoları liste olarak döner."""
    conn = baglanti_al()
    cursor = conn.cursor()
    # Video_source tablosunda status kolonu 0 olan videoları seçiyoruz
    cursor.execute("SELECT video_id, path, camera_name FROM Video_source WHERE status = 0")
    veriler = cursor.fetchall()
    conn.close()
    return veriler

def video_status_guncelle(video_id, status):
    """İşlem bitince status=1 olarak günceller."""
    conn = baglanti_al()
    cursor = conn.cursor()
    cursor.execute("UPDATE Video_source SET status = ? WHERE video_id = ?", (status, video_id))
    conn.commit()
    conn.close()

def masa_verilerini_cek(video_id):
    """Video_id'ye göre masaları ve durumlarını çeker."""
    conn = baglanti_al()
    cursor = conn.cursor()
    # Tables ve Table_status tablolarını table_id üzerinden bağlıyoruz [cite: 182]
    query = """
    SELECT t.table_id, t.coordinate, ts.IA, ts.reserved 
    FROM Tables t
    JOIN Table_status ts ON t.table_id = ts.table_id
    WHERE t.video_id = ?
    """
    cursor.execute(query, (video_id,))
    veriler = cursor.fetchall()
    conn.close()
    
    masalar = []
    for v in veriler:
        try:
            # Koordinat formatı: [(x,y), (x,y), (x,y), (x,y)] [cite: 224]
            noktalar = eval(v[1])
            masalar.append({
                "table_id": v[0],
                "coordinates": noktalar,
                "IA": v[2],
                "reserved": v[3]
            })
        except:
            continue
    return masalar

def table_status_guncelle(table_id, ia, reserved):
    """Masanın durumunu (IA, reserved) ve zamanını günceller[cite: 182]."""
    conn = baglanti_al()
    cursor = conn.cursor()
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE Table_status SET IA = ?, reserved = ?, update_time = ? WHERE table_id = ?",
        (ia, reserved, zaman, table_id)
    )
    conn.commit()
    conn.close()