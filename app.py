import streamlit as st
import os
import requests
import numpy as np
import moviepy.editor as mp
from gtts import gTTS
import tempfile
from PIL import Image, ImageDraw, ImageFont
from proglog import ProgressBarLogger

# --- CONFIGURATION ---
st.set_page_config(page_title="JIGGYMAX Studio", page_icon="⚡", layout="wide")

# --- FONT MANAGEMENT ---
# We define where fonts live. If they aren't there, we download them.
FONT_MAP = {
    "Anatoleum": {
        "file": "Anatoleum.ttf",
        # No URL for this one, expects you to upload it.
        # If missing, it falls back to Arial.
    },
    "Google Sans": {
        "file": "Roboto-Bold.ttf",  # Roboto is the open-source Google Sans
        "url": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    },
    "Arial": {
        "file": "Arimo-Bold.ttf",  # Arimo is the open-source Arial
        "url": "https://github.com/googlefonts/arimo/raw/main/fonts/ttf/Arimo-Bold.ttf",
    },
}


def get_font_path(font_choice):
    """
    Returns a valid file path for the selected font.
    Downloads the file if it's missing and a URL is available.
    """
    data = FONT_MAP.get(font_choice, FONT_MAP["Arial"])
    filename = data["file"]

    # 1. Check if file exists locally
    if os.path.exists(filename):
        return filename

    # 2. If not, try to download it
    if "url" in data:
        with st.spinner(f"Downloading {font_choice} font..."):
            try:
                response = requests.get(data["url"], timeout=10)
                if response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    return filename
            except Exception as e:
                print(f"Font download failed: {e}")

    # 3. Fallback to system default if all else fails
    return "arial.ttf"  # This usually maps to a generic font in PIL


def get_font_object(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()


# --- CUSTOM LOGGER FOR PROGRESS BAR ---
class StreamlitLogger(ProgressBarLogger):
    def __init__(self, st_progress_bar, status_text):
        super().__init__(
            init_state=None,
            bars=None,
            ignored_bars=None,
            logged_bars="all",
            min_time_interval=0,
            ignore_bars_under=0,
        )
        self.st_progress_bar = st_progress_bar
        self.status_text = status_text

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == "t":  # 't' tracks time/frames in MoviePy
            total = self.bars[bar]["total"]
            if total > 0:
                percentage = value / total
                # We map 0-100% of rendering to 20-100% of the UI bar
                # (First 20% is reserved for audio/layout calc)
                ui_prog = 0.20 + (percentage * 0.80)
                self.st_progress_bar.progress(min(ui_prog, 1.0))
                self.status_text.text(f"Rendering Video: {int(percentage * 100)}%")


# --- VIDEO GENERATOR ENGINE ---
def measure_text_width(text, font):
    img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left


def create_pil_text_clip(text, font_path, font_size, color):
    font = get_font_object(font_path, font_size)
    img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = right - left, bottom - top
    final_h = int(text_h * 1.5)
    final_w = int(text_w * 1.1)
    txt_img = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(txt_img)
    y_pos = (final_h - text_h) // 2
    draw_txt.text((0, y_pos), text, font=font, fill=color)
    return mp.ImageClip(np.array(txt_img)), final_w, final_h


def generate_video(text_input, font_path, use_voice):
    # UI Elements for progress
    progress_bar = st.progress(0)
    status_text = st.empty()

    clean_text = text_input.replace("\n", " ").strip()
    words = clean_text.split()
    if not words:
        return None

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "output_video.mp4")

    # --- STEP 1: AUDIO ---
    if use_voice:
        status_text.text("Synthesizing Voiceover...")
        progress_bar.progress(0.05)

        audio_path = os.path.join(temp_dir, "temp_audio.mp3")
        tts = gTTS(clean_text, lang="en")
        tts.save(audio_path)

        audio_clip = mp.AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        SECONDS_PER_WORD = audio_duration / len(words)
    else:
        status_text.text("Calculating Silent Timing...")
        progress_bar.progress(0.05)
        audio_clip = None
        # Viral speed for silent reading
        SECONDS_PER_WORD = 0.4

    progress_bar.progress(0.10)

    # --- STEP 2: LAYOUT ---
    status_text.text("Calculating Layout & Scaling...")

    VIDEO_W, VIDEO_H = 1920, 1200
    BASE_FONT_SIZE = 130
    LEFT_MARGIN = 150
    RIGHT_MARGIN = 150
    MAX_TEXT_WIDTH = VIDEO_W - (LEFT_MARGIN + RIGHT_MARGIN)
    WORD_GAP = 35
    LINE_GAP = 40
    WORDS_PER_LINE = 3
    LINES_PER_SCREEN = 4
    WORDS_PER_SCREEN = WORDS_PER_LINE * LINES_PER_SCREEN

    final_clips = []
    chunks = list(range(0, len(words), WORDS_PER_SCREEN))

    for chunk_index in chunks:
        batch_words = words[chunk_index : chunk_index + WORDS_PER_SCREEN]
        batch_duration = len(batch_words) * SECONDS_PER_WORD

        screen_clips = []
        bg_clip = mp.ColorClip(size=(VIDEO_W, VIDEO_H), color=(0, 0, 0)).set_duration(
            batch_duration
        )
        screen_clips.append(bg_clip)

        lines_data = []
        total_block_height = 0

        for line_idx in range(0, len(batch_words), WORDS_PER_LINE):
            line_words = batch_words[line_idx : line_idx + WORDS_PER_LINE]

            # Auto-Scaling Logic
            current_font_size = BASE_FONT_SIZE
            line_fits = False
            while not line_fits and current_font_size > 40:
                temp_font = get_font_object(font_path, current_font_size)
                total_w = 0
                for w in line_words:
                    total_w += measure_text_width(w, temp_font)
                total_w += (len(line_words) - 1) * WORD_GAP
                if total_w < MAX_TEXT_WIDTH:
                    line_fits = True
                else:
                    current_font_size -= 10

            line_clips = []
            max_h = 0
            for w in line_words:
                clip, w_w, w_h = create_pil_text_clip(
                    w, font_path, current_font_size, "white"
                )
                line_clips.append((w, clip, w_w, w_h))
                if w_h > max_h:
                    max_h = w_h
            lines_data.append({"clips": line_clips, "height": max_h})
            total_block_height += max_h

        if len(lines_data) > 1:
            total_block_height += (len(lines_data) - 1) * LINE_GAP

        start_y = (VIDEO_H - total_block_height) / 2
        current_y = start_y
        global_word_idx = 0

        for line_data in lines_data:
            current_x = LEFT_MARGIN
            for w_text, clip, w_w, w_h in line_data["clips"]:
                light_up_time = global_word_idx * SECONDS_PER_WORD

                dim_clip = (
                    clip.set_position((current_x, current_y))
                    .set_duration(batch_duration)
                    .set_opacity(0.25)
                )

                bright_duration = batch_duration - light_up_time
                if bright_duration > 0:
                    bright_clip = (
                        clip.set_position((current_x, current_y))
                        .set_start(light_up_time)
                        .set_duration(bright_duration)
                    )
                    screen_clips.append(dim_clip)
                    screen_clips.append(bright_clip)
                else:
                    screen_clips.append(dim_clip)
                current_x += w_w + WORD_GAP
                global_word_idx += 1
            current_y += line_data["height"] + LINE_GAP

        screen_composite = mp.CompositeVideoClip(
            screen_clips, size=(VIDEO_W, VIDEO_H)
        ).set_duration(batch_duration)
        final_clips.append(screen_composite)

    # --- STEP 3: RENDERING ---
    if final_clips:
        status_text.text("Starting Rendering Engine...")
        final_video = mp.concatenate_videoclips(final_clips)
        if audio_clip:
            final_video = final_video.set_audio(audio_clip)

        logger = StreamlitLogger(progress_bar, status_text)
        final_video.write_videofile(
            output_path, fps=24, audio_codec="aac", logger=logger
        )

        status_text.success("Done!")
        progress_bar.progress(1.0)
        return output_path
    return None


# --- UI LAYOUT ---
st.title("⚡ JIGGYMAX Studio")

# CSS to hide the hamburger menu and footer for a cleaner look
st.markdown(
    """
<style>
    .stApp { background-color: #0e0e0e; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

col1, col2 = st.columns([2, 1])

# LEFT COLUMN: Text Input
with col1:
    default_text = "Wealth is not about having a lot of money; it is about having a lot of options.\nSpecific knowledge cannot be taught, but it can be learned."
    user_text = st.text_area("Script", value=default_text, height=350)

# RIGHT COLUMN: Settings
with col2:
    st.markdown("### Settings")

    # 1. Voice Toggle
    use_voice = st.toggle("Enable AI Voiceover", value=True)
    if not use_voice:
        st.caption("ℹ️ Silent Mode: Video will pace at 0.4s/word.")

    # 2. Font Selection
    font_choice = st.selectbox("Font Style", ["Anatoleum", "Google Sans", "Arial"])

    # Check status of font
    real_font_path = get_font_path(font_choice)
    if "arial.ttf" in real_font_path and font_choice != "Arial":
        st.caption("⚠️ Downloading font...")
    else:
        st.caption(f"✅ Active: {font_choice}")

    st.divider()

    if st.button("🚀 Generate Video", type="primary", use_container_width=True):
        if user_text:
            try:
                output_file = generate_video(user_text, real_font_path, use_voice)
                st.session_state["last_video"] = output_file
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter some text first.")

# RESULT AREA
if "last_video" in st.session_state and st.session_state["last_video"]:
    st.divider()
    st.markdown("### Result")

    # Center the video player
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.video(st.session_state["last_video"])

        with open(st.session_state["last_video"], "rb") as file:
            st.download_button(
                label="Download MP4",
                data=file,
                file_name="jiggymax_video.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
