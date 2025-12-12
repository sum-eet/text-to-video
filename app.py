# import streamlit as st
# import os
# import numpy as np
# import moviepy.editor as mp
# from gtts import gTTS
# import tempfile
# from PIL import Image, ImageDraw, ImageFont

# # --- CONFIGURATION ---
# st.set_page_config(page_title="Text-to-Video SaaS", page_icon="🎥", layout="centered")

# st.title("⚡ Text to Viral Video (No-ImageMagick Version)")
# st.write("Turn your text into a kinetic video instantly.")


# # --- HELPER: DRAW TEXT WITH PIL (BYPASSES IMAGEMAGICK) ---
# def create_pil_text_clip(text, font_path, font_size, color, size):
#     """
#     Creates a MoviePy ImageClip using standard Python libraries (PIL).
#     This avoids the ImageMagick security policy error entirely.
#     """
#     # 1. Create a transparent image
#     img = Image.new("RGBA", size, (0, 0, 0, 0))
#     draw = ImageDraw.Draw(img)

#     # 2. Load Font
#     try:
#         font = ImageFont.truetype(font_path, font_size)
#     except IOError:
#         # Fallback to default if custom font fails
#         font = ImageFont.load_default()

#     # 3. Calculate Text Size to center it locally (if needed) or just draw
#     # Note: textbbox is the modern way to get size in PIL
#     left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
#     text_w, text_h = right - left, bottom - top

#     # 4. Draw Text
#     # We draw at (0,0) because we will position the clip in MoviePy
#     # But we need the image to be big enough to hold the text
#     txt_img = Image.new("RGBA", (text_w + 20, text_h + 20), (0, 0, 0, 0))
#     draw_txt = ImageDraw.Draw(txt_img)
#     draw_txt.text((0, 0), text, font=font, fill=color)

#     # 5. Convert to Numpy Array for MoviePy
#     return mp.ImageClip(np.array(txt_img))


# # --- GENERATOR ENGINE ---
# def generate_video(text_input, font_path):
#     temp_dir = tempfile.mkdtemp()
#     audio_path = os.path.join(temp_dir, "temp_audio.mp3")
#     output_path = os.path.join(temp_dir, "output_video.mp4")

#     # Generate Audio
#     clean_text = text_input.replace("\n", " ").strip()
#     tts = gTTS(clean_text, lang="en")
#     tts.save(audio_path)

#     # Calculate Timing
#     audio_clip = mp.AudioFileClip(audio_path)
#     audio_duration = audio_clip.duration
#     words = clean_text.split()
#     if len(words) == 0:
#         return None
#     SECONDS_PER_WORD = audio_duration / len(words)

#     # Video Settings
#     VIDEO_SIZE = (1920, 1200)
#     FONT_SIZE = 130

#     # Layout Config
#     WORD_GAP = 35
#     LINE_GAP = 50
#     WORDS_PER_LINE = 3
#     LINES_PER_SCREEN = 4
#     WORDS_PER_SCREEN = 12
#     LEFT_MARGIN = 150

#     final_clips = []
#     progress_bar = st.progress(0)
#     total_chunks = len(range(0, len(words), WORDS_PER_SCREEN))

#     # --- RENDER LOOP ---
#     for idx, chunk_index in enumerate(range(0, len(words), WORDS_PER_SCREEN)):
#         batch_words = words[chunk_index : chunk_index + WORDS_PER_SCREEN]
#         batch_duration = len(batch_words) * SECONDS_PER_WORD

#         screen_clips = []

#         # Black Background
#         bg_clip = mp.ColorClip(size=VIDEO_SIZE, color=(0, 0, 0)).set_duration(
#             batch_duration
#         )
#         screen_clips.append(bg_clip)

#         # Calculate Vertical Center
#         # Estimating height manually since we aren't using TextClip metrics same way
#         # 1.2 is a rough line-height multiplier
#         total_block_height = (LINES_PER_SCREEN * (FONT_SIZE * 1.2)) + (
#             (LINES_PER_SCREEN - 1) * LINE_GAP
#         )
#         start_y = (VIDEO_SIZE[1] - total_block_height) / 2

#         for line_idx in range(0, len(batch_words), WORDS_PER_LINE):
#             line_words = batch_words[line_idx : line_idx + WORDS_PER_LINE]
#             current_x = LEFT_MARGIN

#             # 1. Measure & Create Clips using PIL
#             word_clips_data = []
#             for w in line_words:
#                 # Create the clip using our helper function
#                 # We pass VIDEO_SIZE just for reference, but the clip is sized to the text
#                 clip = create_pil_text_clip(
#                     w, font_path, FONT_SIZE, "white", VIDEO_SIZE
#                 )
#                 word_clips_data.append((w, clip, clip.w, clip.h))

#             # 2. Place Words
#             for i, (word_text, clip, w_width, w_height) in enumerate(word_clips_data):
#                 word_batch_index = line_idx + i
#                 light_up_time = word_batch_index * SECONDS_PER_WORD
#                 pos_y = start_y + (line_idx / WORDS_PER_LINE) * (w_height + LINE_GAP)

#                 # Dim Word (Opacity 0.25)
#                 dim_clip = (
#                     clip.set_position((current_x, pos_y))
#                     .set_duration(batch_duration)
#                     .set_opacity(0.25)
#                 )

#                 # Bright Word (Opacity 1.0)
#                 bright_duration = batch_duration - light_up_time
#                 if bright_duration > 0:
#                     bright_clip = (
#                         clip.set_position((current_x, pos_y))
#                         .set_start(light_up_time)
#                         .set_duration(bright_duration)
#                     )

#                     screen_clips.append(dim_clip)
#                     screen_clips.append(bright_clip)
#                 else:
#                     screen_clips.append(dim_clip)

#                 current_x += w_width + WORD_GAP

#         screen_composite = mp.CompositeVideoClip(
#             screen_clips, size=VIDEO_SIZE
#         ).set_duration(batch_duration)
#         final_clips.append(screen_composite)

#         if total_chunks > 0:
#             progress_bar.progress(min((idx + 1) / total_chunks, 1.0))

#     if final_clips:
#         final_video = mp.concatenate_videoclips(final_clips)
#         final_video = final_video.set_audio(audio_clip)
#         final_video.write_videofile(output_path, fps=24, audio_codec="aac")
#         return output_path
#     return None


# # --- UI ---
# st.markdown("### 1. Enter Your Text")
# default_text = "Wealth is not about having a lot of money; it is about having a lot of options.\nSpecific knowledge cannot be taught, but it can be learned."
# user_text = st.text_area("Paste your script here:", value=default_text, height=150)

# repo_font_path = "Anatoleum.ttf"
# if os.path.exists(repo_font_path):
#     st.info(f"✅ Using Brand Font: {repo_font_path}")
#     active_font = repo_font_path
# else:
#     st.warning(f"⚠️ {repo_font_path} not found. Using default system font.")
#     active_font = "arial.ttf"  # Fallback

# if st.button("🚀 Generate Video"):
#     if user_text:
#         with st.spinner("Rendering..."):
#             try:
#                 output_file = generate_video(user_text, active_font)
#                 st.success("Video Ready!")
#                 st.video(output_file)
#                 with open(output_file, "rb") as file:
#                     st.download_button(
#                         "Download MP4",
#                         data=file,
#                         file_name="viral_video.mp4",
#                         mime="video/mp4",
#                     )
#             except Exception as e:
#                 st.error(f"Error: {e}")
#     else:
#         st.warning("Please enter some text.")
import streamlit as st
import os
import numpy as np
import moviepy.editor as mp
from gtts import gTTS
import tempfile
from PIL import Image, ImageDraw, ImageFont

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="TypeHype | Viral Video Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- NAVIGATION STATE MANAGEMENT ---
if "page" not in st.session_state:
    st.session_state.page = "home"


def go_to_tool():
    st.session_state.page = "tool"


def go_to_home():
    st.session_state.page = "home"


# --- 1. THE SEXY LANDING PAGE (HTML/CSS INJECTION) ---
def render_landing_page():
    # This CSS hides the default Streamlit elements (header, hamburger menu, footer)
    # and injects the high-end landing page styles.
    st.markdown(
        """
        <style>
            /* HIDE STREAMLIT UI */
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem; max-width: 100%;}
            
            /* MODERN RESET & FONTS */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
            
            body {
                background-color: #050505;
                font-family: 'Inter', sans-serif;
                color: white;
                overflow-x: hidden;
            }

            /* ANIMATED BACKGROUND BLOBS */
            .blob-cont {
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                z-index: -1;
                overflow: hidden;
                background: #050505;
            }
            .blob {
                position: absolute;
                border-radius: 50%;
                filter: blur(80px);
                opacity: 0.6;
                animation: float 10s infinite ease-in-out;
            }
            .blob-1 { background: #4f46e5; width: 600px; height: 600px; top: -100px; left: -100px; animation-delay: 0s; }
            .blob-2 { background: #ec4899; width: 500px; height: 500px; bottom: -100px; right: -100px; animation-delay: 2s; }
            .blob-3 { background: #8b5cf6; width: 400px; height: 400px; top: 40%; left: 40%; animation-delay: 4s; opacity: 0.4; }

            @keyframes float {
                0% { transform: translate(0, 0) scale(1); }
                33% { transform: translate(30px, -50px) scale(1.1); }
                66% { transform: translate(-20px, 20px) scale(0.9); }
                100% { transform: translate(0, 0) scale(1); }
            }

            /* HERO SECTION */
            .hero-container {
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 20px;
                position: relative;
            }
            
            .badge {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 8px 16px;
                border-radius: 50px;
                font-size: 0.8rem;
                letter-spacing: 1px;
                text-transform: uppercase;
                margin-bottom: 24px;
                backdrop-filter: blur(10px);
                color: #a5b4fc;
            }

            h1 {
                font-size: 5rem;
                font-weight: 800;
                line-height: 1.1;
                margin-bottom: 24px;
                letter-spacing: -2px;
                background: linear-gradient(to right, #fff, #94a3b8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            p {
                font-size: 1.25rem;
                color: #94a3b8;
                max-width: 600px;
                line-height: 1.6;
                margin-bottom: 48px;
            }

            /* GLASS CARDS */
            .glass-card {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 24px;
                padding: 40px;
                backdrop-filter: blur(20px);
                transition: transform 0.3s ease;
            }
            .glass-card:hover {
                transform: translateY(-5px);
                border-color: rgba(255, 255, 255, 0.1);
            }

            /* MEDIA QUERIES */
            @media (max-width: 768px) {
                h1 { font-size: 3rem; }
                p { font-size: 1rem; }
            }
        </style>

        <div class="blob-cont">
            <div class="blob blob-1"></div>
            <div class="blob blob-2"></div>
            <div class="blob blob-3"></div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # HERO CONTENT
    # We use Streamlit columns to center the layout perfectly
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.markdown(
            """
            <div class="hero-container">
                <div class="badge">✨ The New Standard for Viral Video</div>
                <h1>Turn text into <br> kinetic art.</h1>
                <p>
                    Stop editing word-by-word. TypeHype automatically syncs your script, 
                    generates AI voiceovers, and applies the "bionic reading" effect 
                    used by top creators.
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # THE CTA BUTTON
        # We place a native Streamlit button here but style the area around it
        # This button triggers the Python state change
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("Launch Studio 🚀", type="primary", use_container_width=True):
                go_to_tool()
                st.rerun()

    # FEATURES GRID
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(
            """
            <div class="glass-card">
                <h3>⚡ Zero Editing</h3>
                <p style="font-size: 0.9rem; margin-bottom: 0;">AI handles the timing. You just write the script. No timeline, no keyframes.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    with f2:
        st.markdown(
            """
            <div class="glass-card">
                <h3>🎨 Bionic Focus</h3>
                <p style="font-size: 0.9rem; margin-bottom: 0;">Our "Dim/Bright" opacity engine forces viewers to read along, boosting retention.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    with f3:
        st.markdown(
            """
            <div class="glass-card">
                <h3>📱 Multi-Format</h3>
                <p style="font-size: 0.9rem; margin-bottom: 0;">Export for TikTok (9:16) or LinkedIn/MacBook (16:10) in seconds.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )


# --- 2. THE TOOL LOGIC (EXISTING PYTHON CODE) ---
# Helper: Create PIL Text Clip (Bypasses ImageMagick)
def create_pil_text_clip(text, font_path, font_size, color, size):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = right - left, bottom - top
    txt_img = Image.new("RGBA", (text_w + 20, text_h + 20), (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(txt_img)
    draw_txt.text((0, 0), text, font=font, fill=color)
    return mp.ImageClip(np.array(txt_img))


def generate_video(text_input, font_path):
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

    VIDEO_SIZE = (1920, 1200)
    FONT_SIZE = 130
    WORD_GAP = 35
    LINE_GAP = 50
    WORDS_PER_LINE = 3
    LINES_PER_SCREEN = 4
    WORDS_PER_SCREEN = 12
    LEFT_MARGIN = 150

    final_clips = []
    progress_bar = st.progress(0)
    total_chunks = len(range(0, len(words), WORDS_PER_SCREEN))

    bg_clip = mp.ColorClip(size=VIDEO_SIZE, color=(0, 0, 0)).set_duration(
        0.1
    )  # Placeholder

    for idx, chunk_index in enumerate(range(0, len(words), WORDS_PER_SCREEN)):
        batch_words = words[chunk_index : chunk_index + WORDS_PER_SCREEN]
        batch_duration = len(batch_words) * SECONDS_PER_WORD

        screen_clips = []
        bg_clip = mp.ColorClip(size=VIDEO_SIZE, color=(0, 0, 0)).set_duration(
            batch_duration
        )
        screen_clips.append(bg_clip)

        total_block_height = (LINES_PER_SCREEN * (FONT_SIZE * 1.2)) + (
            (LINES_PER_SCREEN - 1) * LINE_GAP
        )
        start_y = (VIDEO_SIZE[1] - total_block_height) / 2

        for line_idx in range(0, len(batch_words), WORDS_PER_LINE):
            line_words = batch_words[line_idx : line_idx + WORDS_PER_LINE]
            current_x = LEFT_MARGIN

            word_clips_data = []
            for w in line_words:
                clip = create_pil_text_clip(
                    w, font_path, FONT_SIZE, "white", VIDEO_SIZE
                )
                word_clips_data.append((w, clip, clip.w, clip.h))

            for i, (word_text, clip, w_width, w_height) in enumerate(word_clips_data):
                word_batch_index = line_idx + i
                light_up_time = word_batch_index * SECONDS_PER_WORD
                pos_y = start_y + (line_idx / WORDS_PER_LINE) * (w_height + LINE_GAP)

                dim_clip = (
                    clip.set_position((current_x, pos_y))
                    .set_duration(batch_duration)
                    .set_opacity(0.25)
                )
                bright_duration = batch_duration - light_up_time
                if bright_duration > 0:
                    bright_clip = (
                        clip.set_position((current_x, pos_y))
                        .set_start(light_up_time)
                        .set_duration(bright_duration)
                    )
                    screen_clips.append(dim_clip)
                    screen_clips.append(bright_clip)
                else:
                    screen_clips.append(dim_clip)

                current_x += w_width + WORD_GAP

        screen_composite = mp.CompositeVideoClip(
            screen_clips, size=VIDEO_SIZE
        ).set_duration(batch_duration)
        final_clips.append(screen_composite)
        if total_chunks > 0:
            progress_bar.progress(min((idx + 1) / total_chunks, 1.0))

    if final_clips:
        final_video = mp.concatenate_videoclips(final_clips)
        final_video = final_video.set_audio(audio_clip)
        final_video.write_videofile(output_path, fps=24, audio_codec="aac")
        return output_path
    return None


def render_tool_page():
    # Back Button
    if st.button("← Back to Home"):
        go_to_home()
        st.rerun()

    st.markdown("## 🎥 Studio")

    col1, col2 = st.columns([2, 1])

    with col1:
        default_text = "Wealth is not about having a lot of money; it is about having a lot of options.\nSpecific knowledge cannot be taught, but it can be learned."
        user_text = st.text_area("Script", value=default_text, height=300)

    with col2:
        st.markdown("### Settings")
        st.info("Aspect Ratio: 16:10 (MacBook)")
        st.info("Voice: Google US English")

        repo_font_path = "Anatoleum.ttf"
        if os.path.exists(repo_font_path):
            st.success(f"Font: {repo_font_path}")
            active_font = repo_font_path
        else:
            st.warning("Font: System Default")
            active_font = "arial.ttf"

        if st.button("🚀 Generate Video", type="primary", use_container_width=True):
            if user_text:
                with st.spinner("Rendering Kinetic Typography..."):
                    try:
                        output_file = generate_video(user_text, active_font)
                        st.session_state["last_video"] = output_file
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter some text.")

    # Show Video Result
    if "last_video" in st.session_state and st.session_state["last_video"]:
        st.divider()
        st.markdown("### Result")
        st.video(st.session_state["last_video"])
        with open(st.session_state["last_video"], "rb") as file:
            st.download_button(
                "Download MP4",
                data=file,
                file_name="typehype_video.mp4",
                mime="video/mp4",
            )


# --- ROUTER ---
if st.session_state.page == "home":
    render_landing_page()
elif st.session_state.page == "tool":
    render_tool_page()
