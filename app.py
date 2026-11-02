import streamlit as st
import subprocess
import os
import tempfile
import json

st.set_page_config(page_title="Pembersih Watermark Video", layout="centered")

st.title("✨ Pembersih Watermark Presisi")
st.markdown("Hapus watermark/logo di pojok kiri atas atau area lain dengan kontrol presisi.")

# Fungsi untuk mendapatkan resolusi video asli via ffprobe
def get_video_info(video_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        info = json.loads(result.stdout)
        width = int(info["streams"][0]["width"])
        height = int(info["streams"][0]["height"])
        return width, height
    except Exception:
        return 1080, 1920  # Standar vertikal Shorts jika gagal baca

# Fungsi untuk mengambil frame pertama sebagai preview
def generate_preview(video_path, x, y, w, h):
    preview_img = "preview.jpg"
    # Menggambar kotak merah di posisi yang dipilih sebagai preview
    draw_box = f"drawbox=x={x}:y={y}:w={w}:h={h}:color=red@0.8:t=4"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"select=eq(n\\,0),{draw_box}",
        "-vframes", "1",
        preview_img
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return preview_img if os.path.exists(preview_img) else None

# Fungsi proses delogo video
def proses_video(video_input_path, x, y, w, h):
    output_path = "video_bersih.mp4"
    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_input_path,
        "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}",
        "-c:a", "copy",
        "-preset", "fast",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        return output_path, "Berhasil! Watermark berhasil dibersihkan."
    except subprocess.CalledProcessError as e:
        return None, f"Terjadi kesalahan FFmpeg: {e}"

# --- UI STREAMLIT ---
uploaded_file = st.file_uploader("Upload Video Anda (MP4, MKV, MOV)", type=["mp4", "mov", "avi", "mkv"])

if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_path = tfile.name

    # Baca dimensi video
    vid_w, vid_h = get_video_info(video_path)
    st.caption(f"📐 Resolusi Video Terdeteksi: **{vid_w} x {vid_h}** piksel")

    st.subheader("🎯 Atur Posisi Area Watermark")
    
    # Preset default untuk pojok kiri atas (seperti @kangbasmedia pada gambar)
    col1, col2 = st.columns(2)
    with col1:
        # Default X & Y diatur sangat dekat ke pojok kiri atas
        x = st.slider("Posisi Horizontal (X)", min_value=0, max_value=vid_w, value=int(vid_w * 0.02), step=2)
        y = st.slider("Posisi Vertikal (Y)", min_value=0, max_value=vid_h, value=int(vid_h * 0.02), step=2)
    with col2:
        # Default W & H mencakup watermark badge kuning secara proporsional
        w = st.slider("Lebar Area (W)", min_value=10, max_value=vid_w, value=int(vid_w * 0.40), step=2)
        h = st.slider("Tinggi Area (H)", min_value=10, max_value=vid_h, value=int(vid_h * 0.06), step=2)

    # Pastikan w & h genap (syarat delogo ffmpeg)
    if w % 2 != 0: w += 1
    if h % 2 != 0: h += 1

    # Tampilkan preview frame
    st.write("🔍 **Pratinjau Posisi (Kotak Merah):**")
    preview_path = generate_preview(video_path, x, y, w, h)
    if preview_path:
        st.image(preview_path, caption="Pastikan kotak merah menutupi tepat tulisan watermark.")

    # Tombol Eksekusi
    if st.button("🚀 Mulai Bersihkan Video Sekarang", type="primary"):
        with st.spinner("Sedang menghapus watermark... Mohon tunggu sebentar..."):
            output_file, msg = proses_video(video_path, x, y, w, h)
            if output_file:
                st.success(msg)
                st.video(output_file)
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="⬇️ Unduh Video Hasil Bersih",
                        data=f,
                        file_name="video_tanpa_watermark.mp4",
                        mime="video/mp4"
                    )
            else:
                st.error(msg)
