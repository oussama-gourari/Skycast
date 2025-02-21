"""Credentials and settings. Check README.md for details."""

# Reddit credentials.
CLIENT_ID = ""
CLIENT_SECRET = ""
REDDIT_USERNAME = ""
REDDIT_PASSWORD = ""

# Bluesky credentials.
BSKY_HANDLE = "shareapod.bsky.social"
BSKY_PASSWORD = ""

# Settings.
BOT_HOSTER = ""
SUBREDDIT = "PodcastSharing"
TITLE_REGEX = r"^\[.+?\]"
BSKY_POST_TEXT_TEMPLATE = "({post.link_flair_text}) {post.title}"
HASHTAGS = [
    "ShareAPodcast",
    # "{post.link_flair_text}",
]
SEPARATOR = "\n\n"
CATCHUP_LIMIT = 0
