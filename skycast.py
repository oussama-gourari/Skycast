"""Skycast.

A bot that shares podcast posts from r/PodcastSharing to Bluesky.

Author: Oussama Gourari
Copyright: Copyright (c) 2025 Oussama Gourari. All rights reserved.
License: MIT License.
Github: https://github.com/oussama-gourari/Skycast
"""
import logging
import re
import textwrap
import time
from http import HTTPStatus
from io import BytesIO
from platform import platform, python_version

import atproto.exceptions # type: ignore
import httpx
import praw  # type: ignore
import requests  # type: ignore
from atproto import Client, client_utils  # type: ignore
from atproto_client.models.app.bsky.embed.external import External, Main  # type: ignore
from atproto_client.models.blob_ref import BlobRef  # type: ignore
from atproto_client.request import Request  # type: ignore
from humanize import precisedelta
from PIL import Image
from praw.models import Submission  # type: ignore
from prawcore.exceptions import (  # type: ignore
    BadJSON,
    Forbidden,
    NotFound,
    OAuthException,
    Redirect,
    RequestException,
    ResponseException,
    ServerError,
    TooManyRequests,
)
from prawcore.sessions import Session  # type: ignore
from rich.live import Live
from tenacity import RetryCallState, retry
from tenacity.wait import wait_exponential

from config import (
    BOT_HOSTER,
    BSKY_HANDLE,
    BSKY_PASSWORD,
    BSKY_POST_TEXT_TEMPLATE,
    CATCHUP_LIMIT,
    CLIENT_ID,
    CLIENT_SECRET,
    HASHTAGS,
    REDDIT_PASSWORD,
    REDDIT_USERNAME,
    SEPARATOR,
    SUBREDDIT,
)

BOT_VERSION = "0.2"
LOG_LEVEL = "DEBUG"
# Only submissions which fullfil this regex are processed.
TITLE_RULE = re.compile(r"^\[.+?\]")

# Reddit constants.
REDDIT_USER_AGENT = (
    f"{platform(terse=True)};Python-{python_version()}:"
    f"New podcasts posts to Bluesky bot:v{BOT_VERSION} (by /u/{BOT_HOSTER})"
)

# Bluesky constants.
BSKY_POST_URL = "https://bsky.app/profile/{handle}/post/{post_id}"
BSKY_EXTRACT_URL = "https://cardyb.bsky.app/v1/extract?url={url}"
BSKY_POST_MAX_TEXT_LENGTH = 300
MAX_IMAGE_SIZE = 976560  # Bytes.
THUMBNAIL_RESOLUTION = (500, 500)

# HTTP Requests constants.
REQUESTS_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
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
OTHER_PRAWCORE_EXCEPTIONS = (
    ResponseException,
    OAuthException,
    Redirect,
    Forbidden,
    NotFound,
)
RETRY_EXCEPTIONS = PRAWCORE_EXCEPTIONS + REQUESTS_EXCEPTIONS + ATPROTO_EXCEPTIONS
EXCEPTIONS_DESCRIPTIONS = {
    requests.exceptions.ConnectionError: "Network connection is unavailable",
    requests.exceptions.ConnectTimeout: "Network timeout occurred",
    requests.exceptions.ReadTimeout: "Network timeout occurred",
    atproto.exceptions.NetworkError: "Network connection is unavailable",
    atproto.exceptions.InvokeTimeoutError: "Network timeout occurred",
    ResponseException: "Reddit authentication error: wrong client ID and/or client secret",
    OAuthException: "Reddit authentication error: wrong username and/or password",
    Redirect: "The subreddit r/{subreddit} probably doesn't exist",
    Forbidden: "The subreddit r/{subreddit} is probably set to private (only approved members can access it)",
    NotFound: "The subreddit r/{subreddit} is probably banned",
}
HTTPX_CLIENT_TIMEOUT = 60  # Seconds.
REQUESTS_TIMEOUT = 30  # Seconds.
SLEEP_BEFORE_RETRY_MULTIPLIER = 5
MAX_SLEEP_BEFORE_RETRY = 300  # Seconds.

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
# request will take a while and raise `atproto_client.exceptions.InvokeTimeoutError`.
# The `atproto.Client` uses `httpx.Client` for requests and the timeout
# value is 5 seconds by default and is not exposed, so we have to
# create an `httpx.Client` instance with the desired timeout and pass
# it to `atproto.Client`.
request = Request()
request._client = httpx.Client(  # pylint: disable=protected-access
    follow_redirects=True,
    timeout=HTTPX_CLIENT_TIMEOUT,
)
bsky_client = Client(request=request)
live = Live("", auto_refresh=False, transient=True)
prev_status = ""
prev_sub_status = ""


def should_retry_request(retry_state: RetryCallState) -> bool:
    """Callback to decide whether to retry or not on a network
    exception.
    """
    exception = retry_state.outcome.exception()  # type: ignore
    if not exception and retry_state.attempt_number > 1:
        console_log("[green]Successfully resumed")
    return isinstance(exception, RETRY_EXCEPTIONS)


def on_network_exception(retry_state: RetryCallState) -> None:
    """Callback on network exceptions before retrying the request."""
    exception = retry_state.outcome.exception()  # type: ignore
    exception_name = exception.__class__.__name__
    log.error("%s: %s", exception_name, exception)
    if isinstance(exception, RequestException):
        original_exception = exception.original_exception
        if not isinstance(original_exception, REQUESTS_EXCEPTIONS):
            raise exception
        exception_description = EXCEPTIONS_DESCRIPTIONS[original_exception.__class__]
    else:
        exception_description = EXCEPTIONS_DESCRIPTIONS.get(
            exception.__class__, "Reddit server error"
        )
    sleep_amount = precisedelta(int(retry_state.upcoming_sleep))
    exception_description += f", retrying after {sleep_amount}"
    console_log(exception_description, is_error=True)
    while retry_state.upcoming_sleep > 0:
        sleep_amount = precisedelta(int(retry_state.upcoming_sleep))
        update_status(
            f"Sleeping for {sleep_amount} before attempting to resume",
            cache=False,
        )
        time.sleep(min(1, retry_state.upcoming_sleep))
        retry_state.upcoming_sleep -= 1
    update_status(prev_status, prev_sub_status)


def get_request(url: str) -> requests.Response:
    """Make an HTTP GET request to `url` and return the response."""
    log.info("GET %s", url)
    response = requests.get(url, timeout=REQUESTS_TIMEOUT)
    log.info("HTTP %s: GET %s", response.status_code, url)
    return response


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


def update_status(
    status: str = "",
    sub_status: str = "",
    cache: bool = True,
) -> None:
    """Update the rich `live` with the new `status` and
    'sub_status'.
    """
    global prev_status
    global prev_sub_status
    status = status or prev_status
    if cache:
        prev_status = status
        prev_sub_status = sub_status
    msg = status
    if sub_status:
        msg += f" : {sub_status}"
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


def reddit_full_url(permalink: str) -> str:
    """Full Reddit URL from a permalink."""
    return f"https://www.reddit.com{permalink}"


def reddit_short_url(submission: Submission) -> str:
    """Short URL for a Reddit submission."""
    return f"https://redd.it/{submission.id}"


def bsky_login() -> bool:
    """Login to Bluesky."""
    log.debug("Logging in to Bluesky")
    update_status("Logging in to Bluesky")
    try:
        return bsky_client.login(BSKY_HANDLE, BSKY_PASSWORD)
    except atproto.exceptions.UnauthorizedError as exception:
        log.error(exception)
        console_log(
            f"Bluesky login error: {exception.response.content.message}",
            is_error=True,
        )
        return False


def recent_submissions() -> list[Submission] | None:
    """Fetch 100 most-recent submissions on `SUBREDDIT` catching
    errors that could be encountered as a first request to Reddit.
    """
    log.debug("Fetching recent submissions")
    update_status("Fetching Reddit posts")
    try:
        return list(subreddit.new(limit=100))
    except OTHER_PRAWCORE_EXCEPTIONS as exception:
        log.error("%s: %s", exception.__class__.__name__, exception)
        if (type(exception) == ResponseException
                and exception.response.status_code != HTTPStatus.UNAUTHORIZED):
            raise
        exception_description = EXCEPTIONS_DESCRIPTIONS[exception.__class__]
        console_log(
            exception_description.format(subreddit=subreddit),
            is_error=True,
        )
    return None


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
    # not implemented here as the quota should be very sufficient in
    # this use case.
    update_status(sub_status="extracting metadata")
    extract_data = get_request(extract_url).json()
    if "Error" in extract_data or not extract_data["image"]:
        return None, final_url, "", final_url
    blob = get_blob(extract_data["image"])
    return (
        blob,
        extract_data["title"],
        extract_data["description"],
        extract_data["url"],
    )


def get_blob(image_url: str) -> BlobRef | None:
    """Upload an image from `image_url` to create a `Blobref`."""
    update_status(sub_status="downloading thumbnail")
    thumb_image_request = get_request(image_url)
    if thumb_image_request.status_code != HTTPStatus.OK:
        return None
    image_data = thumb_image_request.content
    image_size = len(image_data)
    log.debug("Thumbnail image size: %s", image_size)
    if image_size > MAX_IMAGE_SIZE:
        update_status(sub_status="reducing thumbnail size")
        image = Image.open(BytesIO(image_data))
        image.thumbnail(THUMBNAIL_RESOLUTION)
        with BytesIO() as f:
            image.save(f, format=image.format, optimize=True)
            image_data = f.getvalue()
        log.debug("Reduced thumbnail image size: %s", len(image_data))
    update_status(sub_status="uploading blob")
    return atproto_retry(bsky_client.upload_blob, image_data).blob


def build_post_text(submission: Submission) -> client_utils.TextBuilder:
    """Build the text used in the Bluesky post from a `submission`."""
    text_builder = client_utils.TextBuilder()
    hashtags = [hashtag.format(post=submission) for hashtag in HASHTAGS]
    hashtags_length = (
        len(" ".join(hashtags)) +
        len(hashtags)  # For the # sign before each hashtag.
    )
    remaining_length = (
        BSKY_POST_MAX_TEXT_LENGTH -
        hashtags_length -
        (len(SEPARATOR) if hashtags else 0)
    )
    text = BSKY_POST_TEXT_TEMPLATE.format(post=submission)
    text = textwrap.shorten(text, width=remaining_length)
    text_builder.text(text)
    if hashtags:
        text_builder.text(SEPARATOR)
    for i, hashtag in enumerate(hashtags):
        text_builder.tag(f"#{hashtag}", hashtag)
        if i != (len(hashtags) - 1):
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
    update_status(sub_status="constructing post text")
    text = build_post_text(submission)
    update_status(sub_status="posting to Bluesky")
    bsky_post = atproto_retry(
        bsky_client.post,
        text,
        embed=Main(external=external),
    )
    bsky_post_id = bsky_post.uri.split("/")[-1]
    return BSKY_POST_URL.format(
        handle=bsky_client.me.handle,
        post_id=bsky_post_id,
    )


def verify_submission(
    submission: Submission,
    recent: list[Submission],
) -> tuple[bool, str | None]:
    """Verify if `submission` should be skipped or not."""
    invalid_title = TITLE_RULE.search(submission.title) is None
    catchup = recent[:max(0, CATCHUP_LIMIT)]
    past_catchup = submission in recent and submission not in catchup
    to_skip = True
    reason = None
    if past_catchup:
        pass
    elif invalid_title:
        reason = "title doesn't conform to formatting rule"
    elif submission.saved:
        reason = "already shared"
    else:
        to_skip = False
    if to_skip:
        log.info(
            "Skipping post: %s - invalid_title=%s - saved=%s - past_catchup=%s",
            reddit_full_url(submission.permalink),
            invalid_title,
            submission.saved,
            past_catchup,
        )
    return to_skip, reason


def main(recent: list[Submission]) -> None:
    """Continuously fetch submissions and process them."""
    for new_post in subreddit.stream.submissions():
        submission_url = reddit_full_url(new_post.permalink)
        short_url = reddit_short_url(new_post)
        to_skip, reason = verify_submission(new_post, recent)
        if to_skip:
            if reason:
                console_log(f"{short_url} -> Skipped ({reason})")
            continue
        log.info("Processing post: %s", submission_url)
        update_status(f"Processing post {short_url}")
        bsky_post_url = process_submission(new_post)
        log.info("Bluesky post: %s", bsky_post_url)
        console_log(f"{short_url} -> {bsky_post_url}")
        log.info("Saving processed post")
        update_status(sub_status="saving post to Reddit")
        new_post.save()
        update_status("Waiting for new posts")


def run() -> None:
    """Entry function for the bot."""
    prepare_logger()
    live.console.rule("[deep_sky_blue3]Skycast", style="deep_sky_blue3")
    live.start()
    try:
        if bsky_login() and (recent := recent_submissions()) is not None:
            main(recent)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt")
        console_log("Stopped by user")
    except Exception:  # pylint: disable=broad-except
        log.exception("Fatal exception:")
        console_log(
            "Something went wrong!, check log file for details",
            is_error=True,
        )
    live.stop()
    console_log("Exiting")


network_retry = retry(
    retry=should_retry_request,
    wait=wait_exponential(
        multiplier=SLEEP_BEFORE_RETRY_MULTIPLIER,
        max=MAX_SLEEP_BEFORE_RETRY,
    ),
    before_sleep=on_network_exception,
)
get_request = network_retry(get_request)
atproto_retry = network_retry(lambda fn, *args, **kwargs: fn(*args, **kwargs))
Session.request = network_retry(Session.request)


if __name__ == "__main__":
    run()
