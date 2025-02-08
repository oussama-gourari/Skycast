"""Skycast.

A Reddit bot that shares posts from r/PodcastSharing to Bluesky.

Author: Oussama Gourari
Copyright: Copyright (c) 2025 Oussama Gourari. All rights reserved.
License: MIT License.
Github: https://github.com/oussama-gourari/Skycast
"""
import logging
import time
from http import HTTPStatus
from io import BytesIO
from platform import platform, python_version
from typing import Any, Callable

import atproto.exceptions # type: ignore
import httpx  # type: ignore
import praw  # type: ignore
import requests  # type: ignore
from atproto import Client, client_utils  # type: ignore
from atproto_client.models.app.bsky.embed.external import External, Main  # type: ignore
from atproto_client.models.blob_ref import BlobRef  # type: ignore
from atproto_client.request import Request  # type: ignore
from PIL import Image
from praw.models import Submission  # type: ignore
from prawcore.exceptions import (  # type: ignore
    BadJSON,
    RequestException,
    ServerError,
    TooManyRequests,
)
from prawcore.sessions import Session  # type: ignore
from rich.live import Live

from config import (
    BOT_HOSTER,
    BSKY_HANDLE,
    BSKY_PASSWORD,
    CATCHUP_LIMIT,
    CLIENT_ID,
    CLIENT_SECRET,
    HASHTAGS,
    REDDIT_PASSWORD,
    REDDIT_USERNAME,
    SUBREDDIT,
)

# Contants.
BOT_VERSION = "0.1"
REDDIT_USER_AGENT = (
    f"{platform(terse=True)};Python-{python_version()}:"
    f"New podcasts posts to Bluesky bot:v{BOT_VERSION} (by /u/{BOT_HOSTER})"
)
BSKY_POST_URL = "https://bsky.app/profile/{handle}/post/{post_id}"
BSKY_EXTRACT_URL = "https://cardyb.bsky.app/v1/extract?url={url}"
MAX_IMAGE_SIZE = 976560  # Bytes.
THUMBNAIL_RESOLUTION = (500, 500)
BSKY_POST_MAX_TEXT_LENGTH = 300
REQUESTS_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)
ATPROTO_EXCEPTIONS = (
    atproto.exceptions.NetworkError,
    atproto.exceptions.InvokeTimeoutError,
)
PRAWCORE_EXCEPTIONS = (
    BadJSON,
    RequestException,
    ServerError,
    TooManyRequests,
)
HTTPX_CLIENT_TIMEOUT = 60  # Seconds.
REQUESTS_TIMEOUT = 30  # Seconds.
SLEEP_BEFORE_RETRY_ON_ERROR = 5  # Seconds.
HASHTAGS_LENGTH = (
    len(" ".join(HASHTAGS)) +
    len(HASHTAGS)  # For the # sign before each hashtag.
)
LOG_LEVEL = "DEBUG"


log = logging.getLogger("skycast")
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT,
)
subreddit = reddit.subreddit(SUBREDDIT)
# When uploading a blob (thumbnail image in this case), sometimes the
# image data is large and if the network upload speed is slow, the
# request will take a while and raise `atproto_client.exceptions.InvokeTimeoutError`
# The `atproto.Client` uses `httpx.Client` for requests and the timeout
# value is 5 seconds by default and is not exposed, so we have to
# create an `httpx.Client` intance with the desired timeout and pass it
# to `atproto.Client`.
request = Request()
request._client = httpx.Client(  # pylint: disable=protected-access
    follow_redirects=True,
    timeout=HTTPX_CLIENT_TIMEOUT,
)
bsky_client = Client(request=request)
bsky_client.login(BSKY_HANDLE, BSKY_PASSWORD)
live = Live("", auto_refresh=False, transient=True)
original_session_request = Session.request


def patched_session_request(*args, **kwargs) -> Any:
    """Patch `prawcore.sessions.Session.request` method, to allow
    for catching `PRAWCORE_EXCEPTIONS` then retrying the request
    before they propagate to `praw.models.util.stream_generator`,
    which will prevent breaking the generator and allow us to resume it.

    Args:
        *args: Positional arguments passed to the original
            `prawcore.sessions.Session.request` method.
        **kwargs: Keyword arguments passed to the original
            `prawcore.sessions.Session.request` method.

    Returns:
        Any: Return value from the original method.
    """
    while True:
        try:
            return original_session_request(*args, **kwargs)
        except PRAWCORE_EXCEPTIONS as exception:
            exception_name = exception.__class__.__name__
            log_msg = f"prawcore.{exception_name}: "
            original_exception = None
            retry = True
            if isinstance(exception, RequestException):
                original_exception = exception.original_exception
                original_exception_name = original_exception.__class__.__name__
                log_msg += f"{original_exception_name}: {original_exception}"
                if isinstance(original_exception, requests.exceptions.ConnectionError):
                    error = "Network connection is unavailable"
                elif isinstance(original_exception, requests.exceptions.Timeout):
                    error = "Network timeout occurred"
                else:
                    error = "Unexpected network error"
                    retry = False
            else:
                log_msg += str(exception)
                error = "Reddit server error"
            log.error(log_msg)
            if retry:
                error += ", retrying"
            console_log(error, is_error=True)
            is_connection_exception = isinstance(
                original_exception, REQUESTS_EXCEPTIONS
            )
            if original_exception and not is_connection_exception:
                raise


def retry_atproto_request(function: Callable, *args, **kwargs) -> Any:
    """Retry an atproto `function` that makes an HTTP call in case of
    `ATPROTO_EXCEPTION`.
    """
    while True:
        try:
            return function(*args, **kwargs)
        except ATPROTO_EXCEPTIONS as exception:
            exception_name = exception.__class__.__name__
            log.error("%s: %s", exception_name, exception)
            if isinstance(exception, atproto.exceptions.NetworkError):
                error = "Network connection is unavailable"
            else:  # atproto.exceptions.InvokeTimeoutError
                error = "Network timeout occurred"
            console_log(
                error + f", retrying after {SLEEP_BEFORE_RETRY_ON_ERROR} seconds",
                is_error=True,
            )
            time.sleep(SLEEP_BEFORE_RETRY_ON_ERROR)


def prepare_logger() -> None:
    """Sets the handler, formatter, and level for `log`."""
    handler = logging.FileHandler(
        filename="log.log",
        mode="w",
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname).1s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(LOG_LEVEL)


def reddit_full_url(permalink: str) -> str:
    """Full Reddit URL from a permalink."""
    return f"https://www.reddit.com{permalink}"


def reddit_short_url(submission: Submission) -> str:
    """Short URL for a Reddit submission."""
    return f"https://redd.it/{submission.id}"


def get(url: str) -> requests.Response:
    """Make an HTTP GET request to `url` and return the response."""
    while True:
        try:
            response = requests.get(url, timeout=REQUESTS_TIMEOUT)
            log.info("HTTP %s: GET %s", response.status_code, url)
            return response
        except REQUESTS_EXCEPTIONS as exception:
            exception_name = exception.__class__.__name__
            log.error("%s: %s <- GET %s", exception_name, exception, url)
            if isinstance(exception, requests.exceptions.ConnectionError):
                error = "Network connection is unavailable"
            else:  # requests.exceptions.Timeout
                error = "Network timeout occurred"
            console_log(
                f"{error}, retrying after {SLEEP_BEFORE_RETRY_ON_ERROR} seconds",
                is_error=True,
            )
            time.sleep(SLEEP_BEFORE_RETRY_ON_ERROR)


def extract_info(submission_url: str) -> tuple:
    """Extract title, description, thumbnail image URL, and URI from
    a given `url`.
    """
    final_url = submission_url
    if submission_url.startswith("/r/"):  # Crosspost
        final_url = reddit_full_url(submission_url)
    extract_url = BSKY_EXTRACT_URL.format(url=final_url)
    # At the time of writting this, the `BSKY_EXTRACT_URL` has a rate
    # limit of 100 requests per 5 minutes, the rate limiting logic is
    # not implemented here as the quota is should be very sufficient in
    # this use case.
    extract_data = get(extract_url).json()
    if "Error" not in extract_data and extract_data["image"]:
        blob = get_blob(extract_data["image"])
        return (
            blob,
            extract_data["title"],
            extract_data["description"],
            extract_data["url"],
        )
    return None, final_url, "", final_url


def get_blob(image_url: str) -> BlobRef | None:
    """Upload an image from `image_url` to create a `Blobref`."""
    thumb_image_request = get(image_url)
    if thumb_image_request.status_code == HTTPStatus.OK:
        image_data = thumb_image_request.content
        image_size = len(image_data)
        log.debug("Thumbnail image size: %s", image_size)
        if image_size > MAX_IMAGE_SIZE:
            image = Image.open(BytesIO(image_data))
            image.thumbnail(THUMBNAIL_RESOLUTION)
            with BytesIO() as f:
                image.save(f, format=image.format, optimize=True)
                image_data = f.getvalue()
            log.debug("Reduced thumbnail image size: %s", len(image_data))
        return retry_atproto_request(bsky_client.upload_blob, image_data).blob
    return None


def build_post_text(submission_title: str) -> client_utils.TextBuilder:
    """Build the text used in the Bluesky post from a `submission_title`."""
    text_builder = client_utils.TextBuilder()
    remaining_length = (
        BSKY_POST_MAX_TEXT_LENGTH -
        HASHTAGS_LENGTH -
        # 2 is for the line returns added between the text and the hashtags.
        (2 if HASHTAGS else 0)
    )
    if len(submission_title) > remaining_length:
        title = submission_title[:remaining_length-3] + "..."
    else:
        title = submission_title
    text_builder.text(title)
    if HASHTAGS:
        text_builder.text("\n\n")
    for i, hashtag in enumerate(HASHTAGS):
        text_builder.tag(f"#{hashtag}", hashtag)
        if i != (len(HASHTAGS) - 1):
            text_builder.text(" ")
    return text_builder


def process_submission(submission: Submission) -> str:
    """Process a Reddit post."""
    thumbnail, title, description, uri = extract_info(submission.url)
    external = External(
        thumb=thumbnail,
        title=title,
        description=description,
        uri=uri,
    )
    text = build_post_text(submission.title)
    bsky_post = retry_atproto_request(
        bsky_client.post,
        text,
        embed=Main(external=external),
    )
    bsky_post_id = bsky_post.uri.split("/")[-1]
    return BSKY_POST_URL.format(
        handle=bsky_client.me.handle,
        post_id=bsky_post_id,
    )


def update_status(msg: str) -> None:
    """Update the rich `live` with the new `msg`."""
    live.update(
        f">> {msg} ..."
        "\n[italic grey50]To stop the bot properly, press Control+C[none]",
        refresh=True,
    )


def console_log(msg: str, is_error=False) -> None:
    """Log `msg` above the current status."""
    t = time.strftime("%m/%d %H:%M:%S")
    style = "[red]" if is_error else "[none]"
    live.console.print(f"[{t}] {style}{msg}[none]")


def main() -> None:
    """Main entry function for the bot."""
    live.console.rule("[deep_sky_blue3]Skycast", style="deep_sky_blue3")
    live.start()
    try:
        recent = list(subreddit.new(limit=100))
        catchup = recent[:max(0, CATCHUP_LIMIT)]
        update_status("Waiting for new posts")
        for new_post in subreddit.stream.submissions():
            if new_post.saved or (new_post in recent and new_post not in catchup):
                continue
            submission_url = reddit_full_url(new_post.permalink)
            log.info("Processing post: %s", submission_url)
            short_url = reddit_short_url(new_post)
            update_status(f"Processing post {short_url}")
            bsky_post_url = process_submission(new_post)
            log.info("Bluesky post: %s <- %s", bsky_post_url, submission_url)
            console_log(f"{short_url} -> {bsky_post_url}")
            log.debug("Saving processed post")
            new_post.save()
            update_status("Waiting for new posts")
    except KeyboardInterrupt:
        log.info("Keyboard interrupt")
        console_log("Keyboard interrupted")
    except Exception:  # pylint: disable=broad-except
        log.exception("Fatal exception:")
        console_log(
            "Something went wrong!, check log file for details",
            is_error=True,
        )
    live.stop()


if __name__ == "__main__":
    Session.request = patched_session_request
    prepare_logger()
    main()
