import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import ass
import stable_whisper as ts
import whisper

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import Page, sync_playwright

from utils import settings
from utils.console import print_step
from utils.imagenarator import imagemaker
from utils.subtitles import add_aegisub_meta, checkForMannulCheck
from utils.voice import sanitize_text


def get_all_stlyings() -> Tuple[Tuple[int, ...], Tuple[int, ...], Dict[str, Any]]:
    """

    get all styling settings

    """
    theme = settings.config["settings"]["theme"]
    if theme == "dark":
        bgcolor = (
            *settings.config["image"]["dark_bg_color"],
            0
            if settings.config["image"]["bg_is_transparent"]
            else settings.config["image"]["bg_trans"],
        )
        txtcolor: Tuple[int, ...] = tuple(settings.config["image"]["dark_text_color"])
       
    else:
        bgcolor = (255, 255, 255, 255)
        txtcolor = (0, 0, 0)

    return bgcolor, txtcolor, get_subtitle_styling()


def get_screenshots_of_reddit_posts(
    reddit_object: Dict, screenshot_num: List[int]
) -> None:
    """
    Gets screenshots/subtitle of reddit posts as seen on the web. Gets to assets/temp/png

    Args:
        reddit_object (Dict): Reddit object received from reddit/subreddit.py
        screenshot_num (int): Number of screenshots to download
    """

    print_step("Downloading screenshots of reddit posts...")

    reddit_id = reddit_object["thread_id"]

    # ! Make sure the reddit screenshots folder exists
    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)

    bgcolor, txtcolor, sub_styling = get_all_stlyings()

    if settings.config["settings"]["style"] == 1:

        imagemaker(
            theme=bgcolor,
            reddit_obj=reddit_object,
            txtclr=txtcolor,
        )
    #=== title ===#
    if (
        settings.config["settings"]["allow_title"]
        and settings.config["settings"]["allow_title_picture"]
        and settings.config["image"]["title_style"] == 1
    ):
        render_page = render_title(reddit_object)
        make_screenshot(render_page, reddit_id)


    if settings.config["settings"]["make_withoutsub"]:
        return

    options = {}

    if not settings.config["subtitle"]["auto_detect_sub_lang"]:
        options.update({"language": settings.config["reddit"]["thread"]["post_lang"] or "en"})

    word_level = settings.config["subtitle"]["word_highlight"]

    model = whisper.load_model(
        settings.config["subtitle"]["model_choice"]
    )  # {tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large}

    #=== post ===#
    if (
        settings.config["settings"]["allow_title"]
        and settings.config["settings"]["allow_title_picture"]
        and settings.config["image"]["title_style"] == 0
    ):
        
        sub_path = f"assets/temp/{reddit_id}/png/title.ass"
        result = model.transcribe(f"assets/temp/{reddit_id}/mp3/title.mp3", word_timestamps=True, **options)  # type: ignore
        raw_sub_path = f"assets/temp/{reddit_id}/mp3/title.json"
        with open(raw_sub_path, "w") as f:
            json.dump(result, f)

        result = ts.WhisperResult(raw_sub_path)
        result = result.split_by_length(
            settings.config["subtitle"]["characters_at_time"]
        )
        result.to_ass(
            sub_path,
            word_level=word_level,
            tag=(r"{\1c&H34ebde&}", r"{\r}"),
            highlight_color=False,
            font_size=0,
            **sub_styling,
        )

        add_animation(sub_path)

        #=== post ===#

    if all(
        (
            settings.config["settings"]["storymode"],
            settings.config["settings"]["style"] == 0,
            settings.config["settings"]["allow_post_picture"],
        )
    ):
        sub_path = f"assets/temp/{reddit_id}/png/postaudio.ass"
        result = model.transcribe(f"assets/temp/{reddit_id}/mp3/postaudio.mp3", temperature=0, word_timestamps=True, **options)  # type: ignore
        raw_sub_path = f"assets/temp/{reddit_id}/mp3/postaudio.json"

        with open(raw_sub_path, "w") as f:
            json.dump(result, f)

        result = ts.WhisperResult(raw_sub_path)
        result = result.split_by_length(settings.config["subtitle"]["characters_at_time"])  # type: ignore
        result.to_ass(
            sub_path,
            tag=(r"{\1c&H34ebde&}", r"{\r}"),
            highlight_color=False,  # type: ignore
            font_size=0,
            word_level=word_level,
            **sub_styling,
        ) 

        add_animation(sub_path)


    if settings.config["settings"]["allow_comment"]:
        for i in range(screenshot_num[1]):

            sub_path = f"assets/temp/{reddit_id}/png/{i}.ass"
            result = model.transcribe(f"assets/temp/{reddit_id}/mp3/{i}.mp3", temperature=0, word_timestamps=True, **options)  # type: ignore

            raw_sub_path = f"assets/temp/{reddit_id}/mp3/{i}.json"

            with open(raw_sub_path, "w") as f:
                json.dump(result, f)

            result = ts.WhisperResult(raw_sub_path)
            result = result.split_by_length(settings.config["subtitle"]["characters_at_time"])  # type: ignore
            result.to_ass(
                sub_path,
                tag=(r"{\1c&H34ebde&}", r"{\r}"),
                highlight_color=False,  # type: ignore
                font_size=0,
                word_level=word_level,
                **sub_styling,
            ) 

            add_animation(sub_path)        


def get_subtitle_styling() -> Dict[str, Any]:
    """

    Opens settings

    """
    with open(f"{settings.cwd}/settings.ass", encoding="utf_8_sig") as f:
        doc = ass.parse(f)
    style = doc.styles[0]

    stylings = {
        "Fontname": style.fontname,
        "Fontsize": int(style.fontsize),
        "PrimaryColour": style.primary_color.to_ass(),
        "SecondaryColour": style.secondary_color.to_ass(),
        "OutlineColour": style.outline_color.to_ass(),
        "BackColour": style.back_color.to_ass(),
        "Bold": int(style.bold),
        "Italic": int(style.italic),
        "Underline": int(style.underline),
        "StrikeOut": int(style.strike_out),
        "ScaleX": style.scale_x,
        "ScaleY": style.scale_y,
        "Spacing": style.spacing,
        "Angle": style.angle,
        "BorderStyle": style.border_style,
        "Outline": style.outline,
        "Shadow": style.shadow,
        "Alignment": style.alignment,
        "MarginL": style.margin_l,
        "MarginR": style.margin_r,
        "MarginV": style.margin_v,
        "Encoding": style.encoding,
        "H": settings.config["settings"]["resolution_h"],
        "W": settings.config["settings"]["resolution_w"],
    }
    settings.sub_settings = stylings

    return stylings


def add_animation(file: str) -> None:
    if not settings.config["subtitle"]["add_animation"]:
        return

    with open(file, encoding="utf_8_sig") as f:
        doc = ass.parse(f)
    f.close()

    # {\\fscx95\\fscy95\\t(0,150,\\fscx100\\fscy100)}
    #  \\fscx95  set scale to 95%
    #  \\fscy95  set scale to 95%
    # \\t(0,150,\\fscx100\\fscy100)} set the fscx95 fscy95 to 100 in 150ms

    for d in doc.events:
        d.text = "{\\fscx95\\fscy95\\t(0,150,\\fscx100\\fscy100)}" + d.text

    with open(file, "w", encoding="utf_8_sig") as f:
        doc.dump_file(f)


def render_title(obj: Dict[str, Any]):
    title = obj["thread_title"]
    comment_num = obj.get("num_comments", "99+")
    upvote_num = obj.get("upvotes", "99+")
    subreddit = obj.get("subreddit", "")

    template_dir = "template"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("base.html")
    output_from_parsed_template = template.render(
        subreddit=subreddit, title=title, comment_num=comment_num, upvote_num=upvote_num
    )
    # print(output_from_parsed_template)

    # to save the results
    scr_page = f"{settings.cwd}/{template_dir}/rendered.html"
    with open(scr_page, "w", encoding="utf-8") as fh:
        fh.write(output_from_parsed_template)
    return scr_page


def make_screenshot(scr_page, reddit_id):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()  # headless=False
        context = browser.new_context(device_scale_factor=3)
        page: Page = context.new_page()
        page.goto("file://" + scr_page)
        # page.set_viewport_size()

        page.locator("#title").screenshot(
            path=settings.cwd.joinpath("assets", "temp", reddit_id, "png", "title.png"),
            type="png",
            omit_background=True,
        )
        context.close()
        browser.close()

