A Reddit bot that shares posts from [r/PodcastSharing](https://www.reddit.com/r/PodcastSharing) to [Bluesky](https://bsky.app/profile/shareapod.bsky.social).

## Setup & Configuration
1. Download and install the latest version of [Python](https://www.python.org/).
2. Download bot's files and extract them to a folder and open it.
3. Run `Install Requirements.bat`, this will install the required Python packages for the bot.
4. [Create a script app on Reddit](https://www.reddit.com/prefs/apps) bot's account, you will get a Reddit ***Client ID*** and ***Client Secret***. [*Example*](https://imgur.com/QNzBmkN)
5. Using a text editor, open `config.py` file and fill-in the credentials and details as follows (don't forget to save):
   - `CLIENT_ID` and `CLIENT_SECRET`: obtained in step 4.
   - `REDDIT_USERNAME` and `REDDIT_PASSWORD`: Reddit bot's account username and password.
   - `BSKY_HANDLE` and `BSKY_PASSWORD`: Bluesky account handle and password.
   - `BOT_HOSTER`: Reddit username (without the prefix u/) of the person hosting the bot.
   - `SUBREDDIT`: Subreddit name (without the prefix r/) where the bot will operate.
   - `HASHTAGS`: List of hashtags to add at the bottom of each post on Bluesky.
   - `CATCHUP_LIMIT`: Number of most-recent posts to start from, for example, if set to 5, the bot will start sharing to Bluesky starting from the 5 most-recent posts on the subreddit, set it to 0 if you want to share new posts only. Keep in mind that the bot saves on his Reddit account the posts he already shared, this is to prevent sharing the same post again if the bot is restarted.
6. Double-click `Run.bat` to run the bot.

## License
Skycast is provided under the [MIT License](https://github.com/oussama-gourari/Skycast/blob/main/LICENSE).

- Copyright ©, 2025, Oussama Gourari.
