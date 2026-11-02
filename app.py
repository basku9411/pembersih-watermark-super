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
st.markdown("Hapus watermark secara otomatis atau tentukan area secara manual jika teks sulit terbaca.")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

def cari_koordinat_fleksibel(video_path, kata_kunci):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Periksa lebih banyak frame di awal video
    sampel_frame = [0, int(fps*0.5), int(fps), int(fps*1.5), int(fps*2)]
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
            
            # Jika keyword sangat pendek atau cocok sebagian
            if keyword_bersih and (keyword_bersih in teks_bersih or teks_bersih in keyword_bersih or any(sub in teks_bersih for sub in keyword_bersih.split() if len(sub) > 2)):
                pts = [(int(p[0]), int(p[1])) for p in bbox]
                x_min = min(p[0] for p in pts)
                x_max = max(p[0] for p in pts)
                y_min = min(p[1] for p in pts)
                y_max = max(p[1] for p in pts)
                
                # Perlebar kotak agar area watermark tertutup aman
                pad_x = 35
                pad_y = 20
                
                x = max(0, x_min - pad_x)
                y = max(0, y_min - pad_y)
                w = min((x_max - x_min) + (pad_x * 2), w_frame - x)
                h = min((y_max - y_min) + (pad_y * 2), h_frame - y)
                
                kotak_ditemukan = (x, y, w, h)
                break
        if kotak_ditemukan:
            break
            
    cap.release()
    
    # CADANGAN JIKA OCR GAGAL: Jika teks tidak terbaca AI, gunakan koordinat default pojok kiri atas (tempat biasa watermark @kangbasmedia berada)
    if not kotak_ditemukan:
        # Perkiraan area pojok kiri atas (x=0, y=0 dengan lebar 300 dan tinggi 100)
        kotak_ditemukan = (0, 0, 320, 120)
        
    return kotak_ditemukan

def proses_video_aman(video_input_path, kata_watermark):
    x, y, w, h = cari_koordinat_fleksibel(video_input_path, kata_watermark)
    
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
        return output_path, f"Berhasil! Area watermark di pojok kiri atas berhasil dibersihkan (x={x}, y={y}, w={w}, h={h})."
    except subprocess.CalledProcessError as e:
        return None, f"Terjadi kesalahan FFmpeg: {e}"

# --- ANTARMUKA STREAMLIT ---
uploaded_file = st.file_uploader("Upload Video Anda (Tanpa Batas Ukuran)", type=["mp4", "mov", "avi", "mkv"])
kata_in = st.text_input("Teks/Watermark yang Ingin Dihapus", value="kangbasmedia")

st.info("💡 Jika teks gagal terbaca AI, sistem otomatis membersihkan area pojok kiri atas tempat watermark biasanya berada.")

if st.button("Mulai Bersihkan Sekarang", type="primary"):
    if uploaded_file is None:
        st.error("Harap unggah video terlebih dahulu!")
    else:
        with st.spinner("Sedang memproses video... Mohon tunggu..."):
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            video_path = tfile.name

            output_file, status_msg = proses_video_aman(video_path, kata_in)

            if output_file:
                st.success(status_msg)
                st.video(output_file)
            else:
                st.error(status_msg)
