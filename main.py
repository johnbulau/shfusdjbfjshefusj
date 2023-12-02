#!/usr/bin/env python
from os import name
from subprocess import Popen
import sys
from pathlib import Path

from prawcore import ResponseException

from reddit.subreddit import get_subreddit_threads
from utils import settings
from utils.cleanup import shutdown
from utils.console import print_markdown, print_step
from video_creation.background import (
    chop_backgrounds,
    download_background,
    get_background_config,
)
from video_creation.final_video import make_final_video
from video_creation.screenshot_maker import get_screenshots_of_reddit_posts
from video_creation.voices import save_text_to_mp3
from utils.ffmpeg_download import ffmpeg_install

__VERSION__ = "2.9.3"


def main(POST_ID=None) -> None:
    global reddit_object
    reddit_object = get_subreddit_threads(POST_ID)
    # redditid  = id(reddit_object)
    length, number_of_comments, audio_durations = save_text_to_mp3(reddit_object)
    # length = math.ceil(length)
    get_screenshots_of_reddit_posts(reddit_object, number_of_comments)
    bg_config = get_background_config()
    download_background(bg_config)
    chop_backgrounds(bg_config, length, reddit_object)
    make_final_video(
        number_of_comments, length, audio_durations, reddit_object, bg_config
    )


def run_many(times) -> None:
    for x in range(1, times + 1):
        print_step(
            f'on the {x}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[x % 10]} iteration of {times}'
        )  # correct 1st 2nd 3rd 4th 5th....
        main()
        Popen("cls" if name == "nt" else "clear", shell=True).wait()


# def shutdown(reddit_id= None) -> NoReturn:
#     """
#     Shutdown the bot and clear any temp
#     """
#     # try:
#     if reddit_id:
#         if no_of_file:=cleanup(reddit_id) :
#             print_markdown(f"## Cleared temp {no_of_file} files")

#     # except:
#         # pass
#     print("Exiting...")
#     sys.exit()


def run() -> None:
    print(
        """
       ooooooooo.                   .o8        .o8   o8o      .       .                .o8                          
       `888   `Y88.                "888       "888   `"'    .o8     .o8               "888                          
        888   .d88'  .ooooo.   .oooo888   .oooo888  oooo  .o888oo .o888oo oooo  oooo   888oooo.   .ooooo.  oooo d8b 
        888ooo88P'  d88' `88b d88' `888  d88' `888  `888    888     888   `888  `888   d88' `88b d88' `88b `888""8P 
        888`88b.    888ooo888 888   888  888   888   888    888     888    888   888   888   888 888ooo888  888     
        888  `88b.  888    .o 888   888  888   888   888    888 .   888 .  888   888   888   888 888    .o  888     
       o888o  o888o `Y8bod8P' `Y8bod88P" `Y8bod88P" o888o   "888"   "888"  `V88V"V8P'  `Y8bod8P' `Y8bod8P' d888b    

    """
    )

    # print_markdown(
    #     "### Thanks for using this tool! [Feel free to contribute to this project on GitHub!](https://lewismenelaws.com) If you have any questions, feel free to reach out to me on Twitter or submit a GitHub issue. You can find solutions to many common problems in the [Documentation](): https://reddit-video-maker-bot.netlify.app/"
    # )
    # checkversion(__VERSION__)

    """
    main function to run bot

    """

    directory = Path(__file__).parent.absolute()
    settings.cwd = directory

    ffmpeg_install()
    config = settings.check_toml(
        f"{directory}/utils/.config.template.toml", "config.toml"
    )
    if not config:
        sys.exit()

    post_ids: str = config["reddit"]["thread"]["post_id"]
    try:
        if post_ids and len(post_ids.split("+")) > 1:
            for index, post_id in enumerate(post_ids.split("+")):
                index += 1
                print_step(
                    f'on the {index}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[index % 10]} post of {len(post_ids.split("+"))}'
                )
                main(post_id)
                # Popen("cls" if name == "nt" else "clear", shell=True).wait()
        elif post_ids:
            print_step(f"Runing one time with {post_ids} !!")
            main(post_ids)
        elif config["settings"]["times_to_run"]:
            run_many(config["settings"]["times_to_run"])
        else:
            main()
    except KeyboardInterrupt:
        shutdown(reddit_object.get("thread_post"))
    except ResponseException:
        # error for invalid credentials
        print_markdown("## Invalid credentials")
        print_markdown("Please check your credentials in the config.toml file")
        shutdown()
    except Exception as err:
        try:
            print_step(
                f"Sorry, something went wrong! Try again, and feel free to report this issue at the Discord.\n"
                + str(err)
                + f"version:{__VERSION__}"
                + f'\nstm {config["settings"]["storymode"]}, stmm {config["settings"]["style"]},  ptl {len(reddit_object.get("thread_post",""))}'
            )
        except:
            print_step("something went wrong")
            raise err
        raise err


if __name__ == "__main__":
    run()
