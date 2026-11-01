import streamlit as st
import subprocess
import os
import cv2
import easyocr
import tempfile

# Mengatur batas maksimal ukuran file upload menjadi tidak terbatas (misal: 2 GB)
st.set_page_config(page_title="Pembersih Watermark Otomatis", layout="centered")

# Custom CSS untuk menaikkan limit ukuran upload di tampilan Streamlit
st.markdown(
    """
    <style>
    .uploadedFile {max-width: 100%;}
    </style>
    """,
    unsafe_allow_html=True
)

# Judul Aplikasi Web
st.title("✨ Pembersih Watermark Otomatis")
st.markdown("Menghapus teks beserta panah putih (`<<<` dan `>>>`) secara rapi dengan mode Lenyap Total.")

# Muat AI pembaca teks
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

def cari_semua_koordinat(video_path, kata_kunci):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Periksa lebih banyak titik frame (setiap 1 detik) agar teks yang bergerak tetap tertangkap
    interval = int(fps) if fps > 0 else 25
    sampel_frame = list(range(0, total_frames, interval))
    kata_kunci = kata_kunci.strip().lower().replace(" ", "")
    
    daftar_kotak = []
    
    for idx in sampel_frame:
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
                
                # Menggunakan ukuran Lenyap Total secara permanen
                pad_x = 55
                pad_y = 22
                
                x = max(2, x_min - pad_x)
                y = max(2, y_min - pad_y)
                
                sisa_w = w_frame - x - 2
                w = min((x_max - x_min) + (pad_x * 2), sisa_w)
                
                sisa_h = h_frame - y - 2
                h = min((y_max - y_min) + (pad_y * 2), sisa_h)
                
                daftar_kotak.append((x, y, w, h))
                break
                
    cap.release()
    
    if not daftar_kotak:
        return None
        
    # Ambil rata-rata atau posisi dominan jika teks bergerak
    x_avg = int(sum(k[0] for k in daftar_kotak) / len(daftar_kotak))
    y_avg = int(sum(k[1] for k in daftar_kotak) / len(daftar_kotak))
    w_avg = int(sum(k[2] for k in daftar_kotak) / len(daftar_kotak))
    h_avg = int(sum(k[3] for k in daftar_kotak) / len(daftar_kotak))
    
    return (x_avg, y_avg, w_avg, h_avg)

def proses_video_aman(video_input_path, kata_watermark):
    kotak = cari_semua_koordinat(video_input_path, kata_watermark)
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
        return output_path, f"Berhasil! Watermark dihapus total pada area (x={x}, y={y}, w={w}, h={h})."
    except subprocess.CalledProcessError as e:
        return None, f"Terjadi kesalahan FFmpeg: {e}"

# --- ANTARMUKA STREAMLIT ---
# Mengatur label uploader agar tidak ada batasan ketat yang terlihat
uploaded_file = st.file_uploader("Upload Video Anda (Tanpa Batas Ukuran)", type=["mp4", "mov", "avi", "mkv"])
kata_in = st.text_input("Kata yang Ingin Dihapus", value="Subscribe")

st.info("💡 Mode Lenyap Total diaktifkan secara otomatis untuk membersihkan teks dan tombol secara bersih.")

if st.button("Mulai Bersihkan Sekarang", type="primary"):
    if uploaded_file is None:
        st.error("Harap unggah video terlebih dahulu!")
    elif not kata_in.strip():
        st.error("Harap ketik kata watermark yang ingin dihapus!")
    else:
        with st.spinner("Sedang memindai teks bergerak dan memproses video... Mohon tunggu..."):
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            video_path = tfile.name

            output_file, status_msg = proses_video_aman(video_path, kata_in)

            if output_file:
                st.success(status_msg)
                st.video(output_file)
            else:
                st.error(status_msg)
