A [Reddit](https://www.reddit.com/) bot that shares posts from [r/PodcastSharing](https://www.reddit.com/r/PodcastSharing) to [Bluesky](https://bsky.app/profile/shareapod.bsky.social).

## Setup
1. Download and install the latest version of [Python](https://www.python.org/).
2. Download bot's files and extract them to a folder and open it.
3. Execute `Install Requirements.bat`, this will install the required Python packages for the bot.
4. [Create a script app on Reddit](https://www.reddit.com/prefs/apps) bot's account, you will get a Reddit ***Client ID*** and ***Client Secret***.

## Configuration
Using a text editor, open `config.py` file and fill-in the credentials and details as follows:

   - `BOT_HOSTER`: Reddit username (without the prefix u/) of the person hosting the bot.
   - `SUBREDDIT`: Subreddit name (without the prefix r/) where the bot will operate.
   - `CLIENT_ID` and `CLIENT_SECRET`: obtained in step 4 of the setup process.
   - `REDDIT_USERNAME` and `REDDIT_PASSWORD`: Reddit bot's account username and password.
   - `BSKY_USERNAME` and `BSKY_PASSWORD`: Bluesky account username and password.

## License
Skycast is provided under the [MIT License](https://github.com/oussama-gourari/Hs-Cards/blob/main/LICENSE).

- Copyright ©, 2025, Oussama Gourari.
