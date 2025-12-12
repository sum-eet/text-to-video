import streamlit as st
import os
import shutil

# --- ROBUST SECURITY FIX FOR STREAMLIT CLOUD ---
# (Must be at the very top of the file)
if os.name == "posix":  # Only run on Linux (Streamlit Cloud)
    try:
        # 1. Define locations
        system_policy_path = "/etc/ImageMagick-6/policy.xml"
        local_policy_path = os.path.join(os.getcwd(), "policy.xml")

        # 2. logical check: If we haven't already fixed it...
        if not os.path.exists(local_policy_path):
            if os.path.exists(system_policy_path):
                with open(system_policy_path, "r") as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    # 3. The Smart Fix:
                    # If line restricts "@" pattern, comment it out.
                    if 'pattern="@*"' in line and 'rights="none"' in line:
                        new_lines.append(f"\n")
                    else:
                        new_lines.append(line)

                with open(local_policy_path, "w") as f:
                    f.writelines(new_lines)
            else:
                # Fallback if system path differs
                with open(local_policy_path, "w") as f:
                    f.write(
                        '<policymap><policy domain="path" rights="read|write" pattern="@*" /></policymap>'
                    )

        # 4. Force ImageMagick to use OUR local policy file
        os.environ["MAGICK_CONFIGURE_PATH"] = os.getcwd()

    except Exception as e:
        st.error(f"Security Patch Failed: {e}")

# --- MAIN IMPORTS ---
import moviepy.editor as mp
from moviepy.config import change_settings
from gtts import gTTS
import tempfile

# Force binary path for Linux
if os.name == "posix":
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

st.set_page_config(page_title="Text-to-Video SaaS", page_icon="🎥", layout="centered")

st.title("⚡ Text to Viral Video")
st.write("Turn your text into a kinetic video instantly.")


# --- THE GENERATOR ENGINE ---
def generate_video(text_input, font_path):
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "temp_audio.mp3")
    output_path = os.path.join(temp_dir, "output_video.mp4")

    # Generate Audio
    clean_text = text_input.replace("\n", " ").strip()
    tts = gTTS(clean_text, lang="en")
    tts.save(audio_path)

    # Calculate Timing
    audio_clip = mp.AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    words = clean_text.split()
    if len(words) == 0:
        return None
    SECONDS_PER_WORD = audio_duration / len(words)

    # Video Settings
    VIDEO_SIZE = (1920, 1200)
    FONT_SIZE = 130
    COLOR_BRIGHT = "white"
    WORD_GAP = 35
    LINE_GAP = 50
    WORDS_PER_LINE = 3
    LINES_PER_SCREEN = 4
    WORDS_PER_SCREEN = 12
    LEFT_MARGIN = 150

    final_clips = []

    progress_bar = st.progress(0)
    total_chunks = len(range(0, len(words), WORDS_PER_SCREEN))

    # --- GENERATION LOOP ---
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
                try:
                    temp_clip = mp.TextClip(
                        w, fontsize=FONT_SIZE, font=font_path, color="white"
                    )
                except Exception:
                    temp_clip = mp.TextClip(
                        w, fontsize=FONT_SIZE, font="Liberation-Sans", color="white"
                    )
                word_clips_data.append((w, temp_clip.w, temp_clip.h))

            for i, (word_text, w_width, w_height) in enumerate(word_clips_data):
                word_batch_index = line_idx + i
                light_up_time = word_batch_index * SECONDS_PER_WORD
                pos_y = start_y + (line_idx / WORDS_PER_LINE) * (w_height + LINE_GAP)

                # Dim Word
                dim_clip = (
                    mp.TextClip(
                        word_text, fontsize=FONT_SIZE, font=font_path, color="white"
                    )
                    .set_position((current_x, pos_y))
                    .set_duration(batch_duration)
                    .set_opacity(0.25)
                )

                # Bright Word
                bright_duration = batch_duration - light_up_time
                if bright_duration > 0:
                    bright_clip = (
                        mp.TextClip(
                            word_text, fontsize=FONT_SIZE, font=font_path, color="white"
                        )
                        .set_position((current_x, pos_y))
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


# --- FRONTEND UI ---
st.markdown("### 1. Enter Your Text")
default_text = "Wealth is not about having a lot of money; it is about having a lot of options.\nSpecific knowledge cannot be taught, but it can be learned."
user_text = st.text_area("Paste your script here:", value=default_text, height=150)

repo_font_path = "Anatoleum.ttf"
if os.path.exists(repo_font_path):
    st.info(f"✅ Using Brand Font: {repo_font_path}")
    active_font = repo_font_path
else:
    st.warning(f"⚠️ {repo_font_path} not found. Using default system font.")
    active_font = "Liberation-Sans-Narrow"

if st.button("🚀 Generate Video"):
    if user_text:
        with st.spinner("Rendering... This usually takes 15-30 seconds."):
            try:
                output_file = generate_video(user_text, active_font)
                st.success("Video Ready!")
                st.video(output_file)
                with open(output_file, "rb") as file:
                    st.download_button(
                        "Download MP4",
                        data=file,
                        file_name="viral_video.mp4",
                        mime="video/mp4",
                    )
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter some text.")
