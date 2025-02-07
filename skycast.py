"""Skycast.

A Reddit bot that shares posts from r/PodcastSharing to Bluesky.

Author: Oussama Gourari
Copyright: Copyright (c) 2025 Oussama Gourari. All rights reserved.
License: MIT License.
Github: https://github.com/oussama-gourari/
"""
import logging
import time
from http import HTTPStatus
from io import BytesIO
from platform import platform, python_version
from typing import Any

import httpx
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

from config import (
    BOT_HOSTER,
    BSKY_PASSWORD,
    BSKY_USERNAME,
    CLIENT_ID,
    CLIENT_SECRET,
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
BSKY_POST_URL = "https://bsky.app/profile/bot-tests.bsky.social/post/{post_id}"
BSKY_EXTRACT_URL = "https://cardyb.bsky.app/v1/extract?url={url}"
MAX_IMAGE_SIZE = 976560  # Bytes.
REQUESTS_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)
PRAWCORE_EXCEPTIONS = (
    BadJSON,
    RequestException,
    ServerError,
    TooManyRequests,
)

log = logging.getLogger("skycast")
original_session_request = Session.request


def print_error(error: str) -> None:
    """Prints an error with the time it occured."""
    t = time.strftime("%m/%d %H:%M:%S")
    print(f"[{t}] {error}")


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
            if isinstance(exception, RequestException):
                original_exception = exception.original_exception
                original_exception_name = original_exception.__class__.__name__
                log_msg += f"{original_exception_name}: {original_exception}"
            else:
                log_msg += str(exception)
            log.error(log_msg)
            print_error(log_msg)
            is_connection_exception = isinstance(
                original_exception, REQUESTS_EXCEPTIONS
            )
            if original_exception and not is_connection_exception:
                raise


Session.request = patched_session_request
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USER_AGENT,
)
subreddit = reddit.subreddit(SUBREDDIT)
# When uploading a blob (thumbnail image in here), sometimes the image
# data is large and if the network upload speed is slow, the request
# will take a while and raise `atproto_client.exceptions.InvokeTimeoutError`
# since the default timeout value is 5 seconds.
# The `atproto.Client` uses `https.Client` for requests and the timeout
# is not exposed, so we to create our own `httpx.Client` intance with the
# desired timeout value and pass it to `atproto.Client`.
request = Request()
request._client = httpx.Client(follow_redirects=True, timeout=60)
bsky_client = Client(request=request)
bsky_client.login(BSKY_USERNAME, BSKY_PASSWORD)


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
    log.setLevel("DEBUG")


def reddit_url(permalink: str) -> str:
    """Full Reddit URL from a permalink."""
    return f"https://www.reddit.com{permalink}"


def get(url: str) -> requests.Response:
    """Make an HTTP GET request to `url` and return the response."""
    while True:
        try:
            response = requests.get(url, timeout=30)
            log.info("HTTP %s: GET %s", response.status_code, url)
            return response
        except REQUESTS_EXCEPTIONS as exception:
            exception_name = exception.__class__.__name__
            log.error("%s: %s <- GET %s", exception_name, exception, url)
            print_error(exception)
            time.sleep(5)
            continue


def extract_info(submission_url: str) -> tuple:
    """Extract title, description, thumbnail image URL, and URI from
    a given `url`.
    """
    final_url = submission_url
    if submission_url.startswith("/r/"):  # Crosspost
        final_url = reddit_url(submission_url)
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
            image.thumbnail((500, 500))
            with BytesIO() as f:
                image.save(f, format=image.format, optimize=True)
                image_data = f.getvalue()
            log.debug("Reduced thumbnail image size: %s", len(image_data))
        return bsky_client.upload_blob(image_data).blob
    return None


def process_submission(submission: Submission) -> str:
    """Process a Reddit post."""
    blob, title, description, uri = extract_info(submission.url)
    external = External(
        thumb=blob,
        title=title,
        description=description,
        uri=uri,
    )
    # text_builder = client_utils.TextBuilder()
    bsky_post = bsky_client.post(
        text=submission.title + "\n#ShareAPodcast",
        embed=Main(external=external),
    )
    bsky_post_id = bsky_post.uri.split("/")[-1]
    return BSKY_POST_URL.format(post_id=bsky_post_id)


def main() -> None:
    """Main entry function for the bot."""
    try:
        for new_post in subreddit.stream.submissions(skip_existing=True):
            submission_url = reddit_url(new_post.permalink)
            log.info("Processing new post: %s", submission_url)
            bsky_post_url = process_submission(new_post)
            log.info("Bluesky post: %s <- %s", bsky_post_url, submission_url)
            log.debug("Saving processed post")
            new_post.save()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt")
        print_error("Keyboard interrupted")
    except Exception:  # pylint: disable=broad-except
        log.exception("Fatal exception:")
        print_error(
            "Something went wrong!, check the most-recent log file for "
            "details"
        )


if __name__ == "__main__":
    prepare_logger()
    main()
