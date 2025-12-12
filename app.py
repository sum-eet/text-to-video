import streamlit as st
import os
import numpy as np
import moviepy.editor as mp
from gtts import gTTS
import tempfile
from PIL import Image, ImageDraw, ImageFont
from proglog import ProgressBarLogger  # NEW: Required for real-time progress

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="JIGGYMAX | Viral Video Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --- CUSTOM LOGGER FOR REAL-TIME PROGRESS ---
class StreamlitLogger(ProgressBarLogger):
    """
    Hooks into MoviePy's internal logger to update Streamlit's progress bar
    based on the ACTUAL frames being rendered.
    """

    def __init__(self, st_progress_bar, status_text, start_ratio=0.0, end_ratio=1.0):
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
        self.start_ratio = start_ratio
        self.end_ratio = end_ratio

    def bars_callback(self, bar, attr, value, old_value=None):
        # 't' is the bar identifier for time/frames in MoviePy
        if bar == "t":
            total = self.bars[bar]["total"]
            if total > 0:
                percentage = value / total
                # Map the MoviePy percentage (0-1) to our reserved Streamlit range (e.g. 20%-100%)
                current_st_pct = self.start_ratio + (
                    percentage * (self.end_ratio - self.start_ratio)
                )

                # Update UI
                self.st_progress_bar.progress(min(current_st_pct, 1.0))
                self.status_text.text(f"Rendering: {int(percentage * 100)}% complete")


# --- NAVIGATION STATE ---
if "page" not in st.session_state:
    st.session_state.page = "home"


def go_to_tool():
    st.session_state.page = "tool"


def go_to_home():
    st.session_state.page = "home"


# --- 1. LANDING PAGE ---
def render_landing_page():
    st.markdown(
        """
        <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {padding: 0; max-width: 100%;}
            body { background-color: #050505; color: white; font-family: 'Inter', sans-serif; }
            
            .blob-cont { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; overflow: hidden; background: #050505; }
            .blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.6; animation: float 10s infinite ease-in-out; }
            .blob-1 { background: #4f46e5; width: 600px; height: 600px; top: -100px; left: -100px; }
            .blob-2 { background: #ec4899; width: 500px; height: 500px; bottom: -100px; right: -100px; animation-delay: 2s; }
            
            @keyframes float {
                0% { transform: translate(0, 0) scale(1); }
                33% { transform: translate(30px, -50px) scale(1.1); }
                66% { transform: translate(-20px, 20px) scale(0.9); }
                100% { transform: translate(0, 0) scale(1); }
            }

            .hero-container { min-height: 85vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            h1 { font-size: clamp(3rem, 8vw, 7rem); font-weight: 800; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px; line-height: 1;}
            p { font-size: 1.25rem; color: #94a3b8; max-width: 600px; margin-bottom: 40px; }
            .badge { background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 50px; border: 1px solid rgba(255,255,255,0.2); margin-bottom: 20px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; color: #a5b4fc; }
            
            .custom-footer { width: 100%; padding: 40px 20px; text-align: center; color: #525252; font-size: 0.9rem; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.5); backdrop-filter: blur(10px); }
        </style>
        <div class="blob-cont"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.markdown(
            """
            <div class="hero-container">
                <div class="badge">✨ JIGGYMAX v2.1</div>
                <h1>TEXT TO <br> VIDEO.</h1>
                <p>JIGGYMAX turns boring scripts into viral kinetic typography. <br>Real-time rendering engine active.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("Launch Studio 🚀", type="primary", use_container_width=True):
                go_to_tool()
                st.rerun()

    st.markdown(
        """<div class="custom-footer"><p>&copy; 2025 JIGGYMAX.</p></div>""",
        unsafe_allow_html=True,
    )


# --- 2. THE TOOL LOGIC ---


def get_font_object(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        return ImageFont.load_default()


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


def generate_video(text_input, font_path):
    # PROGRESS: Start
    progress_bar = st.progress(0)
    status_text = st.empty()

    # PHASE 1: AUDIO (0-10%)
    status_text.text("Synthesizing Audio...")
    progress_bar.progress(0.05)

    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "temp_audio.mp3")
    output_path = os.path.join(temp_dir, "output_video.mp4")

    clean_text = text_input.replace("\n", " ").strip()
    tts = gTTS(clean_text, lang="en")
    tts.save(audio_path)

    audio_clip = mp.AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    words = clean_text.split()
    if len(words) == 0:
        return None
    SECONDS_PER_WORD = audio_duration / len(words)

    progress_bar.progress(0.10)

    # PHASE 2: LAYOUT CALCULATION (10-20%)
    status_text.text("Calculating Responsive Layout...")

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

    # Create Layouts
    chunks = list(range(0, len(words), WORDS_PER_SCREEN))
    total_chunks = len(chunks)

    for idx, chunk_index in enumerate(chunks):
        batch_words = words[chunk_index : chunk_index + WORDS_PER_SCREEN]
        batch_duration = len(batch_words) * SECONDS_PER_WORD

        screen_clips = []
        bg_clip = mp.ColorClip(size=(VIDEO_W, VIDEO_H), color=(0, 0, 0)).set_duration(
            batch_duration
        )
        screen_clips.append(bg_clip)

        # Dynamic Scaling Logic
        lines_data = []
        total_block_height = 0

        for line_idx in range(0, len(batch_words), WORDS_PER_LINE):
            line_words = batch_words[line_idx : line_idx + WORDS_PER_LINE]
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

        # Incremental update during prep phase (10% -> 20%)
        prep_progress = 0.10 + ((idx + 1) / total_chunks * 0.10)
        progress_bar.progress(prep_progress)

    if final_clips:
        # PHASE 3: RENDERING (20% - 100%)
        # This is where we attach our custom logger
        status_text.text("Rendering Video Frames (This is the heavy part)...")

        final_video = mp.concatenate_videoclips(final_clips)
        final_video = final_video.set_audio(audio_clip)

        # Initialize our custom logger
        # It maps the internal rendering progress (0-1) to Streamlit's 0.20-1.00 range
        logger = StreamlitLogger(
            progress_bar, status_text, start_ratio=0.20, end_ratio=1.0
        )

        # We pass the logger to write_videofile
        final_video.write_videofile(
            output_path, fps=24, audio_codec="aac", logger=logger  # <--- THE MAGIC HOOK
        )

        status_text.success("Generation Complete!")
        return output_path
    return None


def render_tool_page():
    st.markdown(
        """<style>.stApp { background-color: #0e0e0e; } [data-testid="stSidebar"] { display: none; }</style>""",
        unsafe_allow_html=True,
    )

    col_back, col_title = st.columns([1, 10])
    with col_back:
        if st.button("←", help="Back to Home"):
            go_to_home()
            st.rerun()
    with col_title:
        st.markdown("## ⚡ JIGGYMAX Studio")
    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        default_text = "Wealth is not about having a lot of money; it is about having a lot of options.\nSpecific knowledge cannot be taught, but it can be learned."
        user_text = st.text_area("Script", value=default_text, height=300)

    with col2:
        st.markdown("### Settings")
        st.info("Aspect Ratio: 16:10 (MacBook)")
        repo_font_path = "Anatoleum.ttf"
        if os.path.exists(repo_font_path):
            st.success(f"Font: {repo_font_path}")
            active_font = repo_font_path
        else:
            st.warning("Font: System Default")
            active_font = "arial.ttf"

        if st.button("🚀 Generate Video", type="primary", use_container_width=True):
            if user_text:
                try:
                    output_file = generate_video(user_text, active_font)
                    st.session_state["last_video"] = output_file
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter some text.")

    if "last_video" in st.session_state and st.session_state["last_video"]:
        st.divider()
        st.markdown("### Result")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.video(st.session_state["last_video"])
            with open(st.session_state["last_video"], "rb") as file:
                st.download_button(
                    "Download MP4",
                    data=file,
                    file_name="jiggymax_video.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )


# --- ROUTER ---
if st.session_state.page == "home":
    render_landing_page()
elif st.session_state.page == "tool":
    render_tool_page()
