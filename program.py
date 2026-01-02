import cv2
import numpy as np
from ultralytics import YOLO
import veritabani 
import time
import os

# Ayarlar
MODEL_PATH = "yolov8n.pt"
OUTPUT_DIR = r"C:\Proje"
TARGET_SIZE = (1280, 720) 
CONFIDENCE_THRESHOLD = 0.30 # Tespit eşiği biraz artırıldı
STABILITY_THRESHOLD = 30 # İnsan kaybolduktan sonra kaç frame beklenecek (gecikme)

def process():
    model = YOLO(MODEL_PATH)
    videolar = veritabani.islenmemis_videolari_getir()
    
    if not videolar:
        print("İşlenecek status=0 olan video bulunamadı.")
        return

    for video_id, path, cam_name in videolar:
        print(f"Başlatıldı: {cam_name} (ID: {video_id})")
        
        cap = cv2.VideoCapture(path)
        if not cap.isOpened(): continue

        output_name = f"{cam_name}_output.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, 30.0, TARGET_SIZE)

        masalar = veritabani.masa_verilerini_cek(video_id)
        
        # SAYAÇLAR VE GECİKME TAKİBİ
        rezerve_counters = {m['table_id']: 10 for m in masalar} # 10 saniyelik rezerve sayacı
        presence_check = {m['table_id']: 0 for m in masalar} # İnsan varlık kontolü
        
        last_sec_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.resize(frame, TARGET_SIZE)
            curr_time = time.time()
            
            # YOLO Tespiti
            results = model.predict(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)[0]
            detections = []
            if results.boxes:
                for box in results.boxes:
                    name = model.names[int(box.cls[0])]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    detections.append({"center": center, "name": name})

            for m in masalar:
                tid = m['table_id']
                poly = np.array(m['coordinates'], np.int32)
                
                # Masadaki tespiti anlık kontrolü
                is_person_now = any(d['name'] == 'person' and cv2.pointPolygonTest(poly, d['center'], False) >= 0 for d in detections)
                has_item = any(d['name'] in ['book', 'laptop', 'backpack', 'mouse', 'keyboard'] 
                               and cv2.pointPolygonTest(poly, d['center'], False) >= 0 for d in detections)

                # --- GECİKME (STABİLİZASYON) MANTIĞI ---
                if is_person_now:
                    presence_check[tid] = STABILITY_THRESHOLD # İnsan varsa sayacı fulle
                else:
                    if presence_check[tid] > 0:
                        presence_check[tid] -= 1 # İnsan yoksa hemen "yok" deme, yavaş yavaş düşür. Delay koy
                
                # Masada insan var mı kabul ediyoruz? (Sayaç 0'dan büyükse evet)
                is_person_stable = presence_check[tid] > 0
                # --------------------------------------

                label = "BOS"
                color = (0, 0, 255) 

                if m['reserved'] == 1:
                    if is_person_stable:
                        # Rezerve + İnsan = DOLU
                        if m['IA'] == 0: veritabani.table_status_guncelle(tid, 1, 1)
                        m['IA'] = 1
                        label, color = "DOLU", (0, 255, 0)
                        rezerve_counters[tid] = 10 # İnsan varken sayacı yenile
                    elif has_item:
                        # Rezerve + Eşya = Sayaçlı REZERVE
                        if curr_time - last_sec_time >= 1.0: rezerve_counters[tid] -= 1
                        if rezerve_counters[tid] <= 0:
                            veritabani.table_status_guncelle(tid, 0, 0)
                            m['reserved'], m['IA'] = 0, 0
                            label, color = "BOS", (0, 0, 255)
                        else:
                            label, color = f"REZERVE ({rezerve_counters[tid]})", (0, 255, 255)
                    else:
                        label, color = "REZERVE", (0, 255, 255)
                
                else: # reserved = 0 ise
                    if is_person_stable:
                        label, color = "DOLU (IZINSIZ)", (0, 165, 255) # Turuncu
                    elif has_item:
                        label = "DIKKAT"
                        color = (0, 255, 255) if int(curr_time * 2) % 2 == 0 else (0, 0, 255)
                    else:
                        label, color = "BOS", (0, 0, 255)

                # Çizim
                cv2.polylines(frame, [poly], True, color, 2)
                cv2.putText(frame, label, (poly[0][0], poly[0][1] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            out.write(frame)
            if curr_time - last_sec_time >= 1.0: last_sec_time = curr_time

        cap.release()
        out.release()
        veritabani.video_status_guncelle(video_id, 1)
        print(f"Kaydedildi: {output_path}")

if __name__ == "__main__":
    process()