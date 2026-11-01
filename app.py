import streamlit as st
import subprocess
import os
import cv2
import easyocr
import tempfile

st.set_page_config(page_title="Pembersih Watermark Otomatis", layout="centered")

st.markdown(
    """
    <style>
    .uploadedFile {max-width: 100%;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("✨ Pembersih Watermark Otomatis")
st.markdown("Menghapus teks atau watermark secara presisi di mana pun posisinya.")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

def cari_koordinat_presisi(video_path, kata_kunci):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Periksa beberapa frame pertama (0, 1 detik, 2 detik) tempat watermark biasanya muncul
    sampel_frame = [0, int(fps), int(fps * 2), int(fps * 3)]
    
    # Bersihkan kata kunci dari spasi dan simbol khusus agar mudah dicocokkan
    keyword_bersih = "".join(ch for ch in kata_kunci if ch.isalnum()).lower()
    
    kotak_ditemukan = None
    
    for idx in sampel_frame:
        if idx >= total_frames:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        
        h_frame, w_frame = frame.shape[:2]
        hasil_ocr = reader.readtext(frame)
        
        for (bbox, teks, prob) in hasil_ocr:
            teks_bersih = "".join(ch for ch in teks if ch.isalnum()).lower()
            
            # Cocokkan teks (mendukung pencocokan sebagian atau keseluruhan)
            if keyword_bersih in teks_bersih or teks_bersih in keyword_bersih:
                pts = [(int(p[0]), int(p[1])) for p in bbox]
                x_min = min(p[0] for p in pts)
                x_max = max(p[0] for p in pts)
                y_min = min(p[1] for p in pts)
                y_max = max(p[1] for p in pts)
                
                # Padding atau perlebar kotak agar menutupi seluruh teks dengan bersih
                pad_x = 25
                pad_y = 15
                
                x = max(0, x_min - pad_x)
                y = max(0, y_min - pad_y)
                
                w = min((x_max - x_min) + (pad_x * 2), w_frame - x)
                h = min((y_max - y_min) + (pad_y * 2), h_frame - y)
                
                kotak_ditemukan = (x, y, w, h)
                break
        if kotak_ditemukan:
            break
            
    cap.release()
    return kotak_ditemukan

def proses_video_aman(video_input_path, kata_watermark):
    kotak = cari_koordinat_presisi(video_input_path, kata_watermark)
    if not kotak:
        return None, f"Teks '{kata_watermark}' tidak ditemukan di dalam video. Coba pastikan ejaannya benar."

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
        return output_path, f"Berhasil! Watermark '{kata_watermark}' dihapus pada area (x={x}, y={y}, w={w}, h={h})."
    except subprocess.CalledProcessError as e:
        return None, f"Terjadi kesalahan FFmpeg: {e}"

# --- ANTARMUKA STREAMLIT ---
uploaded_file = st.file_uploader("Upload Video Anda (Tanpa Batas Ukuran)", type=["mp4", "mov", "avi", "mkv"])
kata_in = st.text_input("Teks/Watermark yang Ingin Dihapus", value="kangbasmedia")

st.info("💡 Masukkan tulisan persis seperti yang muncul di video (misal: @kangbasmedia atau nama akun lainnya).")

if st.button("Mulai Bersihkan Sekarang", type="primary"):
    if uploaded_file is None:
        st.error("Harap unggah video terlebih dahulu!")
    elif not kata_in.strip():
        st.error("Harap ketik teks yang ingin dihapus!")
    else:
        with st.spinner("Sedang memindai dan membersihkan video... Mohon tunggu..."):
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            video_path = tfile.name

            output_file, status_msg = proses_video_aman(video_path, kata_in)

            if output_file:
                st.success(status_msg)
                st.video(output_file)
            else:
                st.error(status_msg)
