import streamlit as st
import subprocess
import os
import cv2
import easyocr
import tempfile

# Judul Aplikasi Web
st.title("✨ Pembersih Watermark Otomatis")
st.markdown("Menghapus teks beserta panah putih (`<<<` dan `>>>`) secara rapi.")

# Muat AI pembaca teks (cache agar tidak load ulang terus)
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

def cari_koordinat_aman(video_path, kata_kunci, mode_bersih):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    sampel_frame = [0, int(fps), int(fps * 2), total_frames // 2]
    kata_kunci = kata_kunci.strip().lower().replace(" ", "")
    kotak = None
    
    for idx in sampel_frame:
        if idx >= total_frames:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        
        h_frame, w_frame = frame.shape[:2]
        hasil_ocr = reader.readtext(frame)
        
        for (bbox, teks, prob) in hasil_ocr:
            teks_bersih = teks.strip().lower().replace(" ", "")
            if kata_kunci in teks_bersih or teks_bersih in kata_kunci:
                pts = [(int(p[0]), int(p[1])) for p in bbox]
                x_min = min(p[0] for p in pts)
                x_max = max(p[0] for p in pts)
                y_min = min(p[1] for p in pts)
                y_max = max(p[1] for p in pts)
                
                if "Lenyap Total" in mode_bersih:
                    pad_x = 55
                    pad_y = 22
                else:
                    pad_x = 35
                    pad_y = 8
                
                x = max(2, x_min - pad_x)
                y = max(2, y_min - pad_y)
                
                sisa_w = w_frame - x - 2
                w = min((x_max - x_min) + (pad_x * 2), sisa_w)
                
                sisa_h = h_frame - y - 2
                h = min((y_max - y_min) + (pad_y * 2), sisa_h)
                
                kotak = (x, y, w, h)
                break
        if kotak:
            break
            
    cap.release()
    return kotak

def proses_video_aman(video_input_path, kata_watermark, mode_bersih):
    kotak = cari_koordinat_aman(video_input_path, kata_watermark, mode_bersih)
    if not kotak:
        return None, f"Kata '{kata_watermark}' tidak terdeteksi di dalam video."

    x, y, w, h = kotak
    output_path = "video_super_bersih.mp4"
    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_input_path,
        "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}",
        "-c:a", "copy",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        return output_path, f"Berhasil! Watermark dihapus pada area (x={x}, y={y}, w={w}, h={h})."
    except subprocess.CalledProcessError as e:
        return None, f"Terjadi kesalahan FFmpeg: {e}"

# --- ANTARMUKA STREAMLIT ---
uploaded_file = st.file_uploader("Upload Video Anda", type=["mp4", "mov", "avi"])
kata_in = st.text_input("Kata yang Ingin Dihapus", value="Subscribe")

mode_pilihan = st.radio(
    "Pilih Hasil Akhir",
    ["Lenyap Total (Tombol Merah & Panah Hilang Bersih)", "Merah Polos (Teks & Panah Putih Hilang)"]
)

if st.button("Mulai Bersihkan Sekarang", type="primary"):
    if uploaded_file is None:
        st.error("Harap unggah video terlebih dahulu!")
    elif not kata_in.strip():
        st.error("Harap ketik kata watermark yang ingin dihapus!")
    else:
        with st.spinner("Sedang memproses video... Mohon tunggu..."):
            # Simpan file yang di-upload ke file sementara agar bisa dibaca OpenCV & FFmpeg
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            video_path = tfile.name

            output_file, status_msg = proses_video_aman(video_path, kata_in, mode_pilihan)

            if output_file:
                st.success(status_msg)
                st.video(output_file)
            else:
                st.error(status_msg)
