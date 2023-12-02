# from pprint import pprint
import re
from typing import Any, Dict

import praw
from praw.models import MoreComments
from prawcore.exceptions import ResponseException

from utils import settings
from utils.console import print_step, print_substep, takeinput
from utils.id import link_to_id
from utils.posttextparser import parseComment, posttextparser
from utils.subreddit import get_subreddit_undone
from utils.videos import check_done
from utils.voice import sanitize_text


def get_subreddit_threads(POST_ID: str | None) -> Dict[str, Any]:
    """
    Returns a list of threads from the AskReddit subreddit.
    """
    if settings.config["settings"]["manul_data"]:
        return get_mannual_data()

    print_substep("Logging into Reddit.")

    content: Dict[str, Any] = dict()
    ######################################################################################################################
    if settings.config["reddit"]["creds"]["2fa"]:
        print(
            "\nEnter your two-factor authentication code from your authenticator app.\n"
        )
        code = input("> ")
        print()
        pw = settings.config["reddit"]["creds"]["password"]
        passkey = f"{pw}:{code}"
    else:
        passkey = settings.config["reddit"]["creds"]["password"]
    username = settings.config["reddit"]["creds"]["username"]
    if str(username).casefold().startswith("u/"):
        username = username[2:]
    try:
        reddit = praw.Reddit(
            client_id=settings.config["reddit"]["creds"]["client_id"],
            client_secret=settings.config["reddit"]["creds"]["client_secret"],
            user_agent="Accessing Reddit threads",
            username=username,
            passkey=passkey,
            check_for_async=False,
        )
    except ResponseException as e:
        if e.response.status_code == 401:
            print("Invalid credentials - please check them in config.toml")
        raise e
    except Exception as ex:
        print("Something went wrong...")
        raise ex

    ######################################################################################################################
    # Ask user for subreddit input
    print_step("Getting subreddit threads...")
    if not settings.config["reddit"]["thread"][
        "subreddit"
    ]:  # note to user. you can have multiple subreddits via reddit.subreddit("redditdev+learnpython")
        try:
            subreddit = reddit.subreddit(
                re.sub(
                    r"r\/", "", input("What subreddit would you like to pull from? ")
                )
                # removes the r/ from the input
            )
        except ValueError:
            subreddit = reddit.subreddit("askreddit")
            print_substep("Subreddit not defined. Using AskReddit.")
    else:
        sub = settings.config["reddit"]["thread"]["subreddit"]
        print_substep(f"Using subreddit: r/{sub} from TOML config")
        subreddit_choice = sub
        if (
            str(subreddit_choice).casefold().startswith("r/")
        ):  # removes the r/ from the input
            subreddit_choice = subreddit_choice[2:]
        subreddit = reddit.subreddit(subreddit_choice)

    ######################################################################################################################
    if POST_ID:  # would only be called if there are multiple queued posts
        POST_ID = link_to_id(POST_ID)
        submission = reddit.submission(POST_ID)

    else:
        threads = subreddit.hot(limit=25)
        submission = get_subreddit_undone(threads, subreddit)

    if submission is None:
        print("post not found")
        exit()
    #    return get_subreddit_threads(POST_ID)
    # # submission already done. rerun

    if settings.config["settings"]["storymode"]:
        if (
            not submission.selftext
            and settings.config["reddit"]["thread"]["post_id"] != ""
        ):
            print_substep("You are trying to use story mode on post with no post text")
            exit()
        elif not submission.selftext:
            print_substep(
                "You are trying to use story mode on post with no post text"
            )  # not allow postid post with no self text it story == true
            return get_subreddit_threads(POST_ID)
        else:
            # Check for the length of the post text
            if (
                len(submission.selftext)
                > (settings.config["settings"]["storymode_max_length"] or 2000)
                and not POST_ID
            ):
                print_substep(
                    f"Post is too long ({len(submission.selftext)}), retrying with a different post. ({settings.config['settings']['storymode_max_length']} character limit)"
                )
                return get_subreddit_threads(POST_ID)
    elif not submission.num_comments:
        return get_subreddit_threads(POST_ID)

    ######################################################################################################################

    submission = check_done(submission)  # double-checking

    upvotes = submission.score
    ratio = submission.upvote_ratio * 100
    num_comments = submission.num_comments
    threadurl = f"https://reddit.com{submission.permalink}"

    print_substep(f"Video will be: {submission.title} :thumbsup:", style="bold green")
    print_substep(f"Thread url is : {threadurl  } :thumbsup:", style="bold green")
    print_substep(f"Thread has {upvotes} upvotes", style="bold blue")
    print_substep(f"Thread has a upvote ratio of {ratio}%", style="bold blue")
    print_substep(f"Thread has {num_comments} comments", style="bold blue")

    content["thread_url"] = threadurl
    content["thread_title"] = submission.title
    content["upvotes"] = upvotes
    content["num_comments"] = num_comments
    content["thread_id"] = submission.id
    content["subreddit"] = submission.subreddit.display_name
    content["comments"] = []
    content["is_nsfw"] = submission.over_18
    ######################################################################################################################

    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["style"] == 1:
            text = submission.selftext
            content["thread_post"] = posttextparser(text)
        else:
            content["thread_post"] = (
                takeinput("thread_post", content=submission.selftext)
                if settings.config["pereference"]["manual_text_correct"]
                else submission.selftext
            )

    if settings.config["settings"]["allow_comment"]:
        # submission.comments.replace_more(limit=2)
        for top_level_comment in submission.comments:  # type: ignore
            if isinstance(top_level_comment, MoreComments):
                continue

            if (
                len(content["comments"])
                >= settings.config["settings"]["max_allowed_com"]
            ):  # iteration offset
                break

            comment_body = top_level_comment.body
            if comment_body in ["[removed]", "[deleted]"]:
                continue

            if top_level_comment.stickied:
                continue

            sanitised = sanitize_text(comment_body)
            if not sanitised or sanitised == " ":
                continue

            if not len(comment_body) <= int(
                settings.config["reddit"]["thread"]["max_comment_length"]
            ):
                continue

            if not len(comment_body) >= int(
                settings.config["reddit"]["thread"]["min_comment_length"]
            ):
                continue

            if not (
                top_level_comment.author is not None
                and sanitize_text(comment_body) is not None
            ):  # if errors occur with this change to if not.
                continue

            if not settings.config["settings"]["auto_selection"]:
                print(
                    "---------------------------------------\n"
                    + comment_body
                    + "\n---------------------------------------"
                )

                q = input(
                    "Press 'a' if you want this or 'z' to dismiss or any button to skip :"
                )
                if q not in ("a", "z", "i"):
                    break
                if q == "z":
                    continue
                if q == "i":
                    comment_body = input("copy past from above>")
                # if q == "a":
                #     pass
                # print("---------------------------------------")

            content["comments"].append(
                {
                    "comment_body": parseComment(comment_body),
                    "comment_url": top_level_comment.permalink,
                    "comment_id": top_level_comment.id,
                }
            )

    # pprint(content)
    print_substep("Received subreddit threads Successfully.", style="bold green")
    return content


def get_mannual_data() -> dict[str, Any]:
    """
    Fuction to take manual input

    """
    content = dict()

    new = True
    if settings.config["settings"]["use_temp"]:
        new = False
    content["thread_title"] = takeinput("title", new)
    content["thread_id"] = takeinput("id", new)
    content["subreddit"] = takeinput("subreddit", new)
    content["thread_post"] = takeinput("threadpost", new)
    return content
