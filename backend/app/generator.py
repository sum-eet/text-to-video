import os
import numpy as np
import moviepy.editor as mp
from gtts import gTTS
import tempfile
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
FONT_PATH = "/code/Anatoleum.ttf"  # Path inside Docker
if not os.path.exists(FONT_PATH):
    FONT_PATH = "arial.ttf"  # Fallback


def get_font_object(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        return ImageFont.load_default()


def measure_text_width(text, font):
    img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left


def create_pil_text_clip(text, font_size, color):
    font = get_font_object(font_size)
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


def render_jiggy_video(text_input: str, job_id: str):
    """
    Generates a video and returns the path to the file.
    """
    # 1. Setup Paths
    output_filename = f"{job_id}.mp4"
    output_path = os.path.join("/tmp/jiggy_videos", output_filename)
    temp_audio_path = os.path.join("/tmp/jiggy_videos", f"{job_id}.mp3")

    # 2. Audio Generation
    clean_text = text_input.replace("\n", " ").strip()
    tts = gTTS(clean_text, lang="en")
    tts.save(temp_audio_path)

    audio_clip = mp.AudioFileClip(temp_audio_path)
    audio_duration = audio_clip.duration
    words = clean_text.split()
    if not words:
        return None
    SECONDS_PER_WORD = audio_duration / len(words)

    # 3. Layout Constants
    VIDEO_W, VIDEO_H = 1920, 1200
    BASE_FONT_SIZE = 130
    LEFT_MARGIN = 150
    RIGHT_MARGIN = 150
    MAX_TEXT_WIDTH = VIDEO_W - (LEFT_MARGIN + RIGHT_MARGIN)
    WORD_GAP = 35
    LINE_GAP = 40
    WORDS_PER_LINE = 3
    LINES_PER_SCREEN = 4
    WORDS_PER_SCREEN = 12

    final_clips = []

    # 4. Render Loop
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

        # Line Breaking & Font Scaling
        for line_idx in range(0, len(batch_words), WORDS_PER_LINE):
            line_words = batch_words[line_idx : line_idx + WORDS_PER_LINE]
            current_font_size = BASE_FONT_SIZE
            line_fits = False

            while not line_fits and current_font_size > 40:
                temp_font = get_font_object(current_font_size)
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
                clip, w_w, w_h = create_pil_text_clip(w, current_font_size, "white")
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

    # 5. Final Export
    if final_clips:
        final_video = mp.concatenate_videoclips(final_clips)
        final_video = final_video.set_audio(audio_clip)

        # Write file
        final_video.write_videofile(
            output_path, fps=24, audio_codec="aac", logger=None  # Silence logs
        )

        # Cleanup Audio
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        return output_path

    return None
