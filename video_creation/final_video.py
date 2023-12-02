import multiprocessing
import os
import re
from os.path import exists

from typing import Any, Dict, Tuple

import ffmpeg
from rich.console import Console
from rich.progress import track
from translators import translate_text

from utils import settings
from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.subtitles import checkForMannulCheck, correct_sub_offset, add_aegisub_meta
from utils.videos import save_data


def name_normalize(name: str) -> str:
    lang = settings.config["reddit"]["thread"]["post_lang"]
    if lang:
        print_substep("Translating filename...")

        name = translate_text(name, to_language=lang)  # type: ignore

    name = re.sub(r'[?\\"%*:|<>]', "", name[:100])
    name = re.sub(r"( [w,W]\s?\/\s?[o,O,0])", r" without", name)
    name = re.sub(r"( [w,W]\s?\/)", r" with", name)
    name = re.sub(r"(\d+)\s?\/\s?(\d+)", r"\1 of \2", name)
    name = re.sub(r"(\w+)\s?\/\s?(\w+)", r"\1 or \2", name)
    name = re.sub(r"\/", r"", name)
    name = re.sub(r"\n", r" ", name)

    return name


def put_images(
    background_clip,
    durations,
    number_of_clips,
    reddit_id,
    title=True,
    post_sub=True,
    comment_sub=True,
):  # image_clips,
    """

    Utility to add text/image on background video

    """
    story_dur, comment_dur, title_dur = durations
    current_time = 0
    CWD = settings.cwd

    if settings.config["settings"]["allow_title"] and title:
        if settings.config["settings"]["allow_title_picture"]:
            if settings.config["image"]["title_style"] == 0:
                assert settings.sub_settings is not None

                final_sub_path = f"assets/temp/{reddit_id}/png/title.ass"
                background_clip = ffmpeg.filter(
                    background_clip,
                    "subtitles",
                    final_sub_path,
                    force_style=f"Alignment=10,PlayResX={W},PlayResY={H},Fontsize={settings.sub_settings['Fontsize']}",
                )

            elif settings.config["image"]["title_style"] == 1:
                picture = ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/png/title.png")[
                    "v"
                ].filter("scale", W * 0.7, -1)
                background_clip = background_clip.overlay(
                    picture,
                    enable=f"between(t,{current_time},{current_time + title_dur[0]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )

        current_time += title_dur[0]

    if (
        settings.config["settings"]["storymode"]
        and settings.config["settings"]["allow_post_picture"]
        and post_sub
    ):
        if settings.config["settings"]["style"] == 0:
            assert settings.sub_settings is not None

            in_path = f"assets/temp/{reddit_id}/png/postaudio.ass"
            final_sub_path = f"assets/temp/{reddit_id}/png/postaudio-off.ass"

            correct_sub_offset(in_path, final_sub_path, current_time)

            background_clip = ffmpeg.filter(
                background_clip,
                "subtitles",
                final_sub_path,
                force_style=f"PlayResX={W},PlayResY={H},Fontsize={int(settings.sub_settings['Fontsize'])}",
            )
            # to test  => Alignment=10,
            current_time += story_dur[0]

        elif settings.config["settings"]["style"] == 1:
            for i in track(range(number_of_clips[0]), "Collecting the image files..."):
                picture = ff_input(f"{CWD}/assets/temp/{reddit_id}/png/img{i}.png")

                background_clip = background_clip.overlay(
                    picture,
                    enable=f"between(t,{current_time},{current_time +  story_dur[i]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )
                print(f"between(t,{current_time},{current_time + story_dur[i]})")
                current_time += story_dur[i]

    if settings.config["settings"]["allow_comment"] and comment_sub:
        # for i in range(number_of_clips[1]):
        #     picture = ff_input(f"{CWD}/assets/temp/{reddit_id}/png/comment_{i}.png")

        #     background_clip = background_clip.overlay(
        #         picture,
        #         enable=f"between(t,{current_time},{current_time +  comment_dur[i]})",
        #         x="(main_w-overlay_w)/2",
        #         y="(main_h-overlay_h)/2",
        #     )
        for i in range(number_of_clips[1]):
            in_path = f"assets/temp/{reddit_id}/png/{i}.ass"
            final_sub_path = f"assets/temp/{reddit_id}/png/{i}-correct.ass"

            assert settings.sub_settings is not None

            correct_sub_offset(in_path, final_sub_path, current_time)

            background_clip = ffmpeg.filter(
                background_clip,
                "subtitles",
                final_sub_path,
                force_style=f"PlayResX={W},PlayResY={H},Fontsize={int(settings.sub_settings['Fontsize'])}",
            )

            current_time += comment_dur[i]

    return background_clip


def prepare_background(reddit_id: str, W: int, H: int) -> str:
    CWD = settings.cwd
    input_path = f"{CWD}/assets/temp/{reddit_id}/background.mp4"

    video_data = ffmpeg.probe(input_path)
    h, w = video_data["streams"][0]["height"], video_data["streams"][0]["width"]

    if W < w:
        output_path = f"{CWD}/assets/temp/{reddit_id}/background_noaudio.mp4"
        print_substep("Rendering video ...")
        output = (
            ffmpeg.input(input_path)
            .filter("scale", -1, H)
            .filter("crop", W, H)
            .output(
                output_path,
                an=None,
                **{
                    "c:v": "h264",
                    "b:v": "8M",
                    "threads": multiprocessing.cpu_count(),
                    "loglevel": "warning",
                    "stats": None,
                    "r": settings.config["settings"]["fps"],
                },
            )
            .overwrite_output()
        )
        output.run()
        input_path = output_path

    return input_path


def ff_input(in_path, scr_width=1):
    return ffmpeg.input(in_path)


def merge_background_audio(audio, reddit_id: str):
    """Gather an audio and merge with assets/backgrounds/background.mp3
    Args:
        audio (ffmpeg): The TTS final audio but without background.
        reddit_id (str): The ID of subreddit
    """
    background_audio_volume = settings.config["settings"]["background"][
        "background_audio_volume"
    ]
    if background_audio_volume == 0:
        return audio

    # sets volume to config
    bg_audio = ffmpeg.input(f"assets/temp/{reddit_id}/background.mp3").filter(
        "volume",
        background_audio_volume,
    )
    # Merges audio and background_audio
    merged_audio = ffmpeg.filter([audio, bg_audio], "amix", duration="longest")
    return merged_audio  # Return merged audio


def make_final_video(
    number_of_clips: list[int],
    length: float,
    durations: list[list[float]],
    reddit_obj: dict,
    background_config: Dict[str, Tuple[str, str, str, Any]],
):
    """Gathers audio clips, gathers all screenshots, stitches them together and saves the final video to assets/temp
    Args:
        number_of_clips (int): Index to end at when going through the screenshots'
        length (int): Length of the video
        durations (list[list[float]]) duration of title , posttext , comment
        reddit_obj (dict): The reddit object that contains the posts to read.
        background_config (Tuple[str, str, str, Any]): The background config to use.
    """
    # settings values
    global W, H
    W = int(settings.config["settings"]["resolution_w"])
    H = int(settings.config["settings"]["resolution_h"])
    allow_title = settings.config["settings"]["allow_title"]
    reddit_id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])
    CWD = settings.cwd

    # story_dur , comment_dur , title_dur = durations
    print_step("Creating the final video 🎥")
    print_substep(f"[bold green] Video Will Be: {length:.2f} Seconds Long", "green")
    checkForMannulCheck(
        settings.config["subtitle"]["mannual_sub_correction"],
        "Check the substitles in \n"
        + rf"{CWD}\assets\temp\{reddit_id}\png\postaudio.ass",
        f"{CWD}/assets/temp/{reddit_id}/png/postaudio.ass",
        sum(durations[0]),
        W,
        H,
    )
    background_clip = ffmpeg.input(prepare_background(reddit_id, W=W, H=H))
    # Gather all audio clips
    audio_clips = []
    if allow_title:
        audio_clips.append(ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/mp3/title.mp3"))

    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["style"] == 0:
            audio_clips.append(
                ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/mp3/postaudio.mp3")
            )

        elif settings.config["settings"]["style"] == 1:
            for i in track(range(number_of_clips[0]), "Collecting the audio files..."):
                audio_clips.append(
                    ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                )

    if settings.config["settings"]["allow_comment"]:
        for i in track(range(number_of_clips[1]), "Collecting the audio files..."):
            audio_clips.append(
                ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/mp3/{i}.mp3")
            )

    audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)

    ffmpeg.output(
        audio_concat,
        f"{CWD}/assets/temp/{reddit_id}/audio.mp3",
        **{
            "b:a": "192k",
            "loglevel": "warning",
            "stats": None,
        },
    ).overwrite_output().run()

    # Gather all images
    # screenshot_width = int((W * 90) // 100)# FIXME (make sure this work correctly in all settings)

    audio = ffmpeg.input(f"{CWD}/assets/temp/{reddit_id}/audio.mp3")
    audio = merge_background_audio(audio, reddit_id)

    title = re.sub(r"[^\w\s-]", "", reddit_obj["thread_title"])

    filename = f"{name_normalize(title)[:251]}"
    subreddit = settings.config["reddit"]["thread"]["subreddit"]

    if not exists(f"{CWD}/results/{subreddit}"):
        print_substep("The results folder didn't exist so I made it")
        os.makedirs(f"{CWD}/results/{subreddit}")

    if settings.config["settings"]["make_withoutsub"]:
        print_substep("making No subtitle version", "green")
        path = f"{CWD}/results/No_subtitles/{subreddit}/"
        os.makedirs(path, exist_ok=True)
        ffmpeg.output(
            put_images(
                background_clip,
                durations,
                number_of_clips,
                reddit_id,
                post_sub=False,
                comment_sub=False,
            ),
            audio,
            f"{path}/{filename}.mp4",
            f="mp4",
            **{
                "r": settings.config["settings"]["fps"],
                "c:v": "h264",
                "video_bitrate": "4m",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
                "preset": "ultrafast",
                "loglevel": "warning",
                "stats": None,
            },
        ).overwrite_output().run()

    else:
        final = ffmpeg.output(
            put_images(background_clip, durations, number_of_clips, reddit_id),
            audio,
            f"results/{subreddit}/{filename}.mp4",
            f="mp4",
            **{
                "r": settings.config["settings"]["fps"],
                "c:v": "h264",
                "video_bitrate": "4m",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
                "preset": "ultrafast"
                if settings.config["settings"]["fast_render"]
                else "medium",
                "loglevel": "warning",
                "stats": None,
            },
        ).overwrite_output()
        final.run()

        if settings.config["settings"]["fast_render"]:
            print_step(" ".join(final.compile()))

        final.run()

    save_data(
        subreddit,
        filename + ".mp4",
        title,
        reddit_id,
        background_config["video"][1],
        background_config["audio"][1],
    )
    print_step("Removing temporary files 🗑")

    if not settings.config["settings"]["fast_render"]:
        cleanups = cleanup(reddit_id)
        print_substep(f"Removed {cleanups} temporary files 🗑")
        print_substep("See result in the results folder!")

    print_step(
        f'Reddit title: {reddit_obj["thread_title"]} \n with Backgrounds : {background_config["video"][1] },{background_config["audio"][1]}'
    )
