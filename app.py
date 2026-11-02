import streamlit as st
import cv2
from PIL import Image
from streamlit_cropper import st_cropper
import subprocess
import os
import tempfile

st.set_page_config(page_title="Pembersih Watermark Geser Jari", layout="centered")

st.title("👆 Pembersih Watermark Geser Jari")
st.markdown("Geser dan sesuaikan kotak merah langsung di atas watermark dengan jari Anda!")

# Fungsi mengambil frame pertama dari video
def ambil_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    return None

# Fungsi FFmpeg untuk membersihkan watermark
def proses_hapus_watermark(video_input, x, y, w, h):
    output_path = "video_bersih.mp4"
    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_input,
        "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}",
        "-c:a", "copy",
        "-preset", "veryfast",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        return output_path
    except subprocess.CalledProcessError:
        return None

# --- UPLOAD VIDEO ---
uploaded_file = st.file_uploader("Unggah Video Anda (MP4, MOV, MKV)", type=["mp4", "mov", "avi", "mkv"])

if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_path = tfile.name

    gambar_frame = ambil_frame(video_path)

    if gambar_frame:
        st.info("👇 **Sentuh dan geser kotak merah di bawah tepat ke atas tulisan watermark:**")

        # FITUR GESER JARI (TOUCHSCREEN)
        kotak = st_cropper(
            gambar_frame,
            realtime_update=True,
            box_color="#FF0000",
            aspect_ratio=None,       # Ukuran bebas (bisa memanjang)
            return_type="box"        # Mengambil posisi koordinat piksel
        )

        if kotak:
            x = int(kotak['left'])
            y = int(kotak['top'])
            w = int(kotak['width'])
            h = int(kotak['height'])

            # Delogo FFmpeg mewajibkan ukuran angka genap
            if w % 2 != 0: w += 1
            if h % 2 != 0: h += 1

            # Mencegah kotak melebihi batas resolusi video
            if x + w > gambar_frame.width:
                w = gambar_frame.width - x
                if w % 2 != 0: w -= 1
            if y + h > gambar_frame.height:
                h = gambar_frame.height - y
                if h % 2 != 0: h -= 1

            st.caption(f"📍 Posisi terpilih: X={x}, Y={y}, Lebar={w}, Tinggi={h}")

            # Tombol Eksekusi
            if st.button("🚀 Bersihkan Watermark Sekarang", type="primary"):
                with st.spinner("Sedang memproses video... Mohon tunggu sebentar..."):
                    hasil_video = proses_hapus_watermark(video_path, x, y, w, h)
                    
                    if hasil_video:
                        st.success("✅ Watermark berhasil dibersihkan!")
                        st.video(hasil_video)
                        with open(hasil_video, "rb") as f:
                            st.download_button(
                                label="⬇️ Unduh Video Hasil Bersih",
                                data=f,
                                file_name="video_bersih.mp4",
                                mime="video/mp4"
                            )
                    else:
                        st.error("Terjadi kesalahan saat memproses video.")
