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
FONT_MAP = {
    "Anatoleum": {
        "file": "Anatoleum.ttf",
    },
    "Google Sans": {
        "file": "Roboto-Bold.ttf",
        "url": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    },
    "Arial": {
        "file": "Arimo-Bold.ttf",
        "url": "https://github.com/googlefonts/arimo/raw/main/fonts/ttf/Arimo-Bold.ttf",
    },
}


def get_font_path(font_choice):
    data = FONT_MAP.get(font_choice, FONT_MAP["Arial"])
    filename = data["file"]
    if os.path.exists(filename):
        return filename
    if "url" in data:
        with st.spinner(f"Downloading {font_choice}..."):
            try:
                r = requests.get(data["url"], timeout=10)
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename
            except:
                pass
    return "arial.ttf"


def get_font_object(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()


# --- CUSTOM LOGGER ---
class StreamlitLogger(ProgressBarLogger):
    def __init__(self, bar, status):
        super().__init__(
            init_state=None,
            bars=None,
            ignored_bars=None,
            logged_bars="all",
            min_time_interval=0,
            ignore_bars_under=0,
        )
        self.bar = bar
        self.status = status

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == "t":
            total = self.bars[bar]["total"]
            if total > 0:
                pct = value / total
                self.bar.progress(min(0.2 + (pct * 0.8), 1.0))
                self.status.text(f"Rendering: {int(pct * 100)}%")


# --- GEOMETRY ENGINE (FIXED) ---


def create_pil_text_clip(text, font_path, font_size, color):
    """
    Creates a perfectly sized text image with safety padding to prevent cropping.
    """
    font = get_font_object(font_path, font_size)

    # 1. Measure precise bounding box
    # We use a dummy image to measure
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = dummy.textbbox((0, 0), text, font=font)

    text_w = right - left
    text_h = bottom - top

    # 2. Add SAFETY PADDING (Critical for the "cropping" fix)
    # We add 20% padding to width and 50% to height to handle accents/descenders
    w_padding = int(text_w * 0.2) + 20
    h_padding = int(text_h * 0.5) + 20

    final_w = text_w + w_padding
    final_h = text_h + h_padding

    img = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 3. Draw Centered
    # We explicitly calculate the center position
    x_pos = (final_w - text_w) / 2 - left
    y_pos = (final_h - text_h) / 2 - top

    draw.text((x_pos, y_pos), text, font=font, fill=color)

    # Return clip and the VISUAL width (not the image width) for spacing
    return mp.ImageClip(np.array(img)), final_w, final_h


def generate_video(text_input, font_path, use_voice):
    progress_bar = st.progress(0)
    status_text = st.empty()

    clean_text = text_input.replace("\n", " ").strip()
    words = clean_text.split()
    if not words:
        return None

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "output_video.mp4")

    # --- AUDIO PHASE ---
    if use_voice:
        status_text.text("Synthesizing Audio...")
        audio_path = os.path.join(temp_dir, "temp.mp3")
        gTTS(clean_text).save(audio_path)
        audio_clip = mp.AudioFileClip(audio_path)
        audio_dur = audio_clip.duration
        sec_per_word = audio_dur / len(words)
    else:
        status_text.text("Timing (Silent Mode)...")
        audio_clip = None
        sec_per_word = 0.4

    progress_bar.progress(0.1)

    # --- LAYOUT CONSTANTS ---
    VIDEO_W, VIDEO_H = 1920, 1200
    BASE_FONT_SIZE = 130
    MARGIN_X = 150
    # Safe Width for Text (Video Width - Margins)
    SAFE_WIDTH = VIDEO_W - (MARGIN_X * 2)

    WORD_GAP = 30
    # FIXED LINE HEIGHT: This prevents the "overlap" bug.
    # Lines are now spaced by font size, not by word height.
    LINE_SPACING_FACTOR = 1.4

    WORDS_PER_LINE = 3
    LINES_PER_SCREEN = 4
    WORDS_PER_SCREEN = 12

    final_clips = []
    chunks = list(range(0, len(words), WORDS_PER_SCREEN))

    for chunk_idx in chunks:
        batch_words = words[chunk_idx : chunk_idx + WORDS_PER_SCREEN]
        batch_dur = len(batch_words) * sec_per_word

        screen_clips = []
        screen_clips.append(
            mp.ColorClip(size=(VIDEO_W, VIDEO_H), color=(0, 0, 0)).set_duration(
                batch_dur
            )
        )

        # --- 1. CALCULATE SCALING ---
        # We determine the Font Size for this ENTIRE SCREEN first.
        # This prevents one huge word from breaking the layout.

        current_font_size = BASE_FONT_SIZE
        screen_fits = False

        while not screen_fits and current_font_size > 40:
            screen_fits = True
            temp_font = get_font_object(font_path, current_font_size)

            # Check every line in this batch
            for i in range(0, len(batch_words), WORDS_PER_LINE):
                line = batch_words[i : i + WORDS_PER_LINE]
                # Measure line width
                total_w = 0
                for w in line:
                    # Use getlength for accurate horizontal measurement
                    total_w += temp_font.getlength(w)
                total_w += (len(line) - 1) * WORD_GAP

                if total_w > SAFE_WIDTH:
                    screen_fits = False
                    current_font_size -= 10
                    break  # Restart with smaller font

        # --- 2. GENERATE CLIPS ---
        lines_data = []
        # Calculate fixed line height based on the chosen font size
        FIXED_LINE_HEIGHT = current_font_size * LINE_SPACING_FACTOR

        for i in range(0, len(batch_words), WORDS_PER_LINE):
            line_words = batch_words[i : i + WORDS_PER_LINE]
            l_clips = []
            for w in line_words:
                clip, w_w, w_h = create_pil_text_clip(
                    w, font_path, current_font_size, "white"
                )
                l_clips.append((clip, w_w))
            lines_data.append(l_clips)

        # --- 3. POSITIONING ---
        # Center the block vertically based on fixed line heights
        total_block_h = len(lines_data) * FIXED_LINE_HEIGHT
        start_y = (VIDEO_H - total_block_h) / 2

        global_w_idx = 0
        current_y = start_y

        for line in lines_data:
            current_x = MARGIN_X

            for clip, w_w in line:
                # Timing
                start = global_w_idx * sec_per_word

                # Dimmed version (Always visible)
                dim = (
                    clip.set_position((current_x, current_y))
                    .set_duration(batch_dur)
                    .set_opacity(0.25)
                )
                screen_clips.append(dim)

                # Bright version (Timed)
                dur = batch_dur - start
                if dur > 0:
                    bright = (
                        clip.set_position((current_x, current_y))
                        .set_start(start)
                        .set_duration(dur)
                    )
                    screen_clips.append(bright)

                # Advance X using the clip's visual width
                # Note: We subtract a bit of the safety padding we added earlier for tighter visual spacing
                visual_width = w_w * 0.85
                current_x += visual_width + WORD_GAP
                global_w_idx += 1

            # Advance Y by fixed amount (Fixes overlapping)
            current_y += FIXED_LINE_HEIGHT

        comp = mp.CompositeVideoClip(
            screen_clips, size=(VIDEO_W, VIDEO_H)
        ).set_duration(batch_dur)
        final_clips.append(comp)

    if final_clips:
        status_text.text("Merging & Encoding...")
        final = mp.concatenate_videoclips(final_clips)
        if audio_clip:
            final = final.set_audio(audio_clip)

        logger = StreamlitLogger(progress_bar, status_text)
        final.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac", logger=logger
        )

        progress_bar.progress(1.0)
        status_text.success("Done!")
        return output_path
    return None


# --- UI ---
st.markdown(
    """<style>.stApp { background-color: #0e0e0e; } #MainMenu, footer {visibility: hidden;}</style>""",
    unsafe_allow_html=True,
)
st.title("⚡ JIGGYMAX Studio")

c1, c2 = st.columns([2, 1])
with c1:
    txt = st.text_area(
        "Script",
        "Wealth is not about having a lot of money; it is about having a lot of options.",
        height=350,
    )
with c2:
    st.markdown("### Settings")
    voice = st.toggle("AI Voice", True)
    font = st.selectbox("Font", ["Anatoleum", "Google Sans", "Arial"])

    if st.button("🚀 Generate", type="primary", use_container_width=True):
        if txt:
            try:
                path = get_font_path(font)
                out = generate_video(txt, path, voice)
                st.session_state["vid"] = out
            except Exception as e:
                st.error(f"Error: {e}")

if "vid" in st.session_state:
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.video(st.session_state["vid"])
        with open(st.session_state["vid"], "rb") as f:
            st.download_button(
                "Download MP4", f, "jiggy.mp4", "video/mp4", use_container_width=True
            )
