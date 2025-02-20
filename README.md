# Skycast

Skycast is a bot that automatically shares podcast posts from [r/PodcastSharing](https://www.reddit.com/r/PodcastSharing) to [@shareapod.bsky.social](https://bsky.app/profile/shareapod.bsky.social).

---

## ⚙️ Setup & Configuration

### 1️⃣ Install uv
- Install the latest version of [uv](https://docs.astral.sh/uv/getting-started/installation/).

### 2️⃣ Create a Reddit Script App
- On the bot's Reddit account, go to [Reddit Apps](https://www.reddit.com/prefs/apps) and create a **script app**.
- You will receive a **Client ID** and **Client Secret**.  
  📌 [Example](https://imgur.com/QNzBmkN)

### 3️⃣ Get the Bot Files
- [Download the bot's files](https://github.com/oussama-gourari/Skycast/archive/refs/heads/main.zip).
- Extract the files to a folder and open it.

### 4️⃣ Configure Skycast
- Open `config.py` using a text editor and fill in the required credentials and details (don't forget to save):
   - `CLIENT_ID` and `CLIENT_SECRET`: obtained in step 4.
   - `REDDIT_USERNAME` and `REDDIT_PASSWORD`: Username and password of bot's Reddit account.
   - `BSKY_HANDLE` and `BSKY_PASSWORD`: Bluesky account's handle and password.
   - `BOT_HOSTER`: Reddit username (without the prefix u/) of the person hosting the bot.
   - `SUBREDDIT`: Subreddit name (without the prefix r/) where the bot will operate.
   - `BSKY_POST_TEXT_TEMPLATE`: The template used to generate the text of each Bluesky post.
      - The variable `post`, followed by a period (`.`) and an attribute name, all enclosed in curly braces (`{}`), can be used to include various details about the Reddit post being shared. For example, `{post.title}` will be replaced with the Reddit post's title, and `{post.link_flair_text}` will be replaced with the Reddit post’s flair.
      - To see the available attribute names, append `.json` to the end of any Reddit post URL (e.g., https://www.reddit.com/r/PodcastSharing/comments/1ij1ck2/the_s1e1_podcast_episode_200_the_office/.json).
   - `HASHTAGS`: List of hashtags to add at the bottom of each post on Bluesky, the `post` variable mentioned above can also be used here.
   - `SEPARATOR`: Used to separate the text from the hashtags on the Bluesky post, it is set to 2 line breaks (`\n`).
   - `CATCHUP_LIMIT`: Number of most-recent posts to start from (max=100). For example, if set to 5, the bot will start sharing to Bluesky starting from the 5 most-recent posts on the subreddit, set it to 0 if you want to share new posts only. Keep in mind that the bot saves on his Reddit account the posts he already shared, this is to prevent sharing the same post again if the bot is restarted.

### 5️⃣ Run the Bot
- Double-click **`Run.bat`** to start the bot. 🎉

---

## 📜 License
Skycast is provided under the [MIT License](https://github.com/oussama-gourari/Skycast/blob/main/LICENSE).

&copy; 2025, Oussama Gourari.
