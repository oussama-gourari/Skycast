# Skycast

Skycast is a bot that shares podcast posts from [r/PodcastSharing](https://www.reddit.com/r/PodcastSharing) to [@shareapod.bsky.social](https://bsky.app/profile/shareapod.bsky.social).

---

## ⚙️ Setup & Configuration

### 1️⃣ Create a Reddit Script App

- On the bot's Reddit account, go to [Reddit Apps](https://www.reddit.com/prefs/apps) and create a **script app**.
  ![https://imgur.com/g3kglxH](https://i.imgur.com/g3kglxH.png)
- You will receive a **Client ID** and **Client Secret**.
  ![https://imgur.com/a2DRzC5](https://i.imgur.com/a2DRzC5.png)

### 2️⃣ Download Skycast

- [Download the bot's files](https://github.com/oussama-gourari/Skycast/archive/refs/heads/main.zip).
- Extract the files to a folder and open it.

### 3️⃣ Configure Skycast

- Inside the **`src`** folder, rename the file ![**config_template.py**](/src/config_template.py) to **`config.py`**.

- Open it using a text editor and fill in the required credentials and details as follows:
  
  - `CLIENT_ID` and `CLIENT_SECRET`: obtained in step 1.
  
  - `REDDIT_USERNAME` and `REDDIT_PASSWORD`: Username and password of bot's Reddit account.
  
  - `BSKY_HANDLE` and `BSKY_PASSWORD`: Bluesky account's handle and password.
  
  - `BOT_HOSTER`: Reddit username (without the prefix u/) of the person hosting the bot.
  
  - `SUBREDDIT`: Subreddit name (without the prefix r/) where the bot will operate.
  
  - `TITLE_REGEX`: Regular expression checked against each post's title to decide if it should be shared or not.
  
  - `BSKY_POST_TEXT_TEMPLATE`: The template used to generate the text of each Bluesky post.
    
    - The variable `post`, followed by a period (`.`) and an attribute name, all enclosed in curly braces (`{}`), can be used to include various details about the Reddit post being shared. For example, `{post.title}` will be replaced with the Reddit post's title, and `{post.link_flair_text}` will be replaced with the Reddit post’s flair.
    - To see the available attribute names, add `.json` to the end of any Reddit post URL (e.g., https://www.reddit.com/r/PodcastSharing/comments/1ij1ck2/the_s1e1_podcast_episode_200_the_office/.json).
  
  - `HASHTAGS`: List of hashtags to add at the bottom of each post on Bluesky, the `post` variable mentioned above can also be used here.
  
  - `SEPARATOR`: Used to separate the text from the hashtags on the Bluesky post, it is set to 2 line breaks (`\n`).
  
  - `CATCHUP_LIMIT`: Number of most-recent posts to start from (max=100). For example, if set to 5, the bot will start sharing to Bluesky starting from the 5 most-recent posts on the subreddit, set it to 0 if you want to share new posts only. Keep in mind that the bot saves on his Reddit account the posts he already shared, this is to prevent sharing the same post again if the bot is restarted.
  
  - `CHECK_EVERY`: The number of minutes the bot waits before checking for new posts again if no new posts were found in the last check. This helps reduce workload and cost, especially when running the bot on cloud services like Google Cloud.

- Save then exit the file.

## 🤖 Run Skycast

The following steps are for running Skycast either locally on your machine, or on a Google Cloud Compute Engine Debian VM:

### 🖥️ Locally

*Running Skycast for the first time might take some time to load.*

- On Windows, double-click ![**Run_Windows.bat**](/Run_Windows.bat) to start the bot.

- On Linux, open the terminal in the root directory of the bot's files and execute the following command: `bash Run_Linux`.

If Skycast stops due to an error, a `log.log` file will be available under the `logs` directory.

### ☁️ Google Cloud Compute Engine Debian VM

- Create a project on [Google Cloud Resource Manager](https://console.cloud.google.com/cloud-resource-manager).
  
  ![](https://i.imgur.com/pVWSjHj.png)

- From the notifications menu, select the newly created project.
  
  ![](https://i.imgur.com/130YL0a.png)

- Under Resources, click Compute Engine, then click Create Instance then Enable the Compute Engine API if not already enabled.

- Before proceeding with the VM configuration, we need to create an SSH key pair to be able to communicate with the VM from your local machine. On Windows 10 or later, open the Command Prompt and type the following command, replace `WINDOWS_USER` with your username on the Windows machine, `SSH_KEY_FILENAME` and `VM_USERNAME` are of your choice *(don't use space in them)*:
  
  ``ssh-keygen -t rsa -f C:\Users\WINDOWS_USER\.ssh\SSH_KEY_FILENAME -C VM_USERNAME``
  
  Once you run the above command, you will be asked to enter a passphrase, I would suggest leaving it empty ***as long as you are on your personnal machine and no one else has access to it***, this is to avoid entering the passphrase each time you try to connect to the VM.
  
  2 files will be generated, a private key file `C:\Users\WINDOWS_USER\.ssh\SSH_KEY_FILENAME` which acts like a password and ***should not be shared with anyone***, and a public key file `C:\Users\WINDOWS_USER\.ssh\SSH_KEY_FILENAME.pub`. Open the public key file using a text editor, it's *entire content* is the public key **required** in the next steps.
  
  In the below example screenshot, `WINDOWS_USER` is *Utilisateur*, `SSH_KEY_FILENAME` is *skycast_vm*, and `VM_USERNAME` is *my-vm-username*.
  
  ![](https://i.imgur.com/NdmLdSV.png)

- The following VM configuration steps are meant to create a VM with minimal resources in order to reduce it's cost:
  
  - In the Navigation menu, click Machine configuration, select `E2` from the table and choose `e2-micro (2 vCPU, 1 core, 1 GB memory)` under Machine type.
    
    ![](https://i.imgur.com/xwxBQGk.png)
  
  - In the Navigation menu, click OS and storage, then click Change, select `Standard persistent disk` under Boot disk type, and make sure `Debian` is selected under Operating system.
    
    ![](https://i.imgur.com/6Cr7Taj.png)
  
  - In the Navigation menu, click Data protection, then select `No backups`.
    
    ![](https://i.imgur.com/FQruAKQ.png)
  
  - In the Navigation menu, click Networking, then expand Network interfaces and select `Standard` under Network Service Tier, and make sure that `Ephemeral` is selected under External IPv4 address.
    
    ![](https://i.imgur.com/RQmaJE9.png)
  
  - In the Navigation menu, click Security, scroll down then expand Manage Access, under `Add manually generated SSH keys` click Add Item, then paste the SSH public key previously generated.
    
    ![](https://i.imgur.com/GS2Cj8i.png)

- Click Create at the bottom to start the VM. The VM's External IP will be shown in a table, in this example it is `35.208.22.253`:
  
  ![](https://i.imgur.com/5PQu2jp.png)

- Using a text editor, open the file [**Run_Google_Cloud_Debian_VM.bat**](/Run_Google_Cloud_Debian_VM.bat) and put in `SSH_KEY_FILENAME`, `VM_USERNAME`, and `VM_External_IP` as shown in the example screenshot below. Save and exit the file.
  
  ![](https://i.imgur.com/z56Jq7f.png)

- To start Skycast on the VM, double-click [**Run_Google_Cloud_Debian_VM.bat**](/Run_Google_Cloud_Debian_VM.bat). Each time you will be asked if you want to update Skycast on the VM, unless you want to in the future, leave it empty, which will default to `N` *(No)* then press Enter.
  
  Since it's the first time, you will be asked `Are you sure you want to continue connecting (yes/no/[fingerprint])?`, type `yes` then press Enter. The script will install the necessary tools on the VM, whenever you are asked `Do you want to continue? [Y/n]` type `Y` then press Enter.
  
  Your `config.py` will be uploaded to the VM and Skycast should now be running 🚀 *(might take some time to load the first time)*.
  
  ![](https://i.imgur.com/F4LzADs.png)
  
  The window can be closed and Skycast will still be running on the cloud VM. If later you want to stop Skycast or check on it, simply double-click [**Run_Google_Cloud_Debian_VM.bat**](/Run_Google_Cloud_Debian_VM.bat) again.
  
  ***If you make changes to the `config.py` file, Skycast must be stopped then started again for the changes to take effect.***

- If Skycast stops due to an error, type `exit` then press Enter, a log file will be downloaded from the VM and will be available under the `logs` directory as `log_vm.log`.
  
  ![](https://i.imgur.com/Eo77600.png)

---

## 📜 License

Skycast is provided under the [MIT License](https://github.com/oussama-gourari/Skycast/blob/main/LICENSE).

&copy; 2025, Oussama Gourari.
