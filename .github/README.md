<h2 align="center">
    ───「 ᴄʟᴏɴɪғʏ 」───
</h2>

<p align="center">
  <img src="https://i.ibb.co/23JNhkRC/clonify.jpg" alt="Clonify Logo">
</p>

<p align="center">
<a href="https://github.com/TeamProBots/Clonify"><img src="https://img.shields.io/github/stars/TeamProBots/Clonify?color=black&logo=github&logoColor=black&style=for-the-badge" alt="Stars" /></a>
<a href="https://github.com/TeamProBots/Clonify/network/members"> <img src="https://img.shields.io/github/forks/TeamProBots/Clonify?color=black&logo=github&logoColor=black&style=for-the-badge" alt="Forks" /></a>
<a href="https://github.com/TeamProBots/Clonify/blob/master/LICENSE"> <img src="https://img.shields.io/badge/License-MIT-blueviolet?style=for-the-badge" alt="License" /> </a>
<a href="https://www.python.org/"> <img src="https://img.shields.io/badge/Written%20in-Python-orange?style=for-the-badge&logo=python" alt="Python" /> </a>
<a href="https://github.com/TeamProBots/Clonify/commits/master"> <img src="https://img.shields.io/github/last-commit/TeamProBots/Clonify?color=blue&logo=github&logoColor=green&style=for-the-badge" alt="Last Commit" /></a>
</p>

<p align="center"><img src="https://camo.githubusercontent.com/0b26c9160fb9f58f42db5d7185898a24d69f583444fe512d799a20db91face2c/68747470733a2f2p726f66696c652d636f756e7465722e676c697463682e6d652f5961736972416b687461722f636f756e742e737667" alt="Profile Views"></p>

Clonify is a powerful Telegram bot designed for playing music and videos in group voice chats. It also features a unique cloning capability, allowing users to create their own instances of the music bot.

<p align="center">
<b>𝗗𝗘𝗣𝗟𝗢𝗬𝗠𝗘𝗡𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦</b>
</p>

<h3 align="center">
    ─「 ᴅᴇᴩʟᴏʏ ᴏɴ ʜᴇʀᴏᴋᴜ 」─
</h3>

<p align="center"><a href="https://dashboard.heroku.com/new?template=https://github.com/TeamProBots/Clonify"> <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy to Heroku"></a></p>
<p align="center"><i>Note: Heroku's free tier may have limitations. For optimal performance, consider a VPS or other hosting solutions.</i></p>

<br />

---

### 🔧 Quick Setup (VPS/Local Machine)

Setting up Clonify on your own server provides more control and potentially better performance.

1.  **System Update & Prerequisites:**
    ```bash
    sudo apt-get update && sudo apt-get upgrade -y
    sudo apt-get install python3-pip ffmpeg git curl -y 
    ```

2.  **Python Version:**
    This project requires **Python 3.11.4**, as specified in `runtime.txt`. Ensure you have this version or a compatible one (Python 3.9+ is generally recommended for Pyrogram). You can use tools like `pyenv` to manage multiple Python versions.

3.  **PIP Setup:**
    ```bash
    sudo pip3 install -U pip
    ```

4.  **Node.js Installation (for some dependencies):**
    ```bash
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash # Using a slightly newer nvm version
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion
    nvm install v18 # Or a recent LTS version
    ```
    *Run `source ~/.bashrc` or restart your terminal if `nvm` command is not found after installation.*

5.  **Clone the Repository:**
    ```bash
    git clone https://github.com/TeamProBots/Clonify && cd Clonify
    ```

6.  **Install Dependencies:**
    ```bash
    pip3 install -U -r requirements.txt
    ```

7.  **Configure Environment Variables:**
    *   Copy the sample environment file:
        ```bash
        cp sample.env .env
        ```
    *   Edit the `.env` file with your actual values using a text editor like `nano` or `vi`:
        ```bash
        nano .env 
        # or
        vi .env 
        ```
    *   **Essential Variables to Configure:**
        *   `API_ID`: Your Telegram API ID from my.telegram.org.
        *   `API_HASH`: Your Telegram API Hash from my.telegram.org.
        *   `BOT_TOKEN`: Your Telegram Bot Token from @BotFather.
        *   `MONGO_DB_URI`: Your MongoDB connection string.
        *   `STRING_SESSION`: Pyrogram User Session String (critical for assistant client). Generate this by running `python3 generate_string_session.py` (you might need to create this script or use an existing session generator).
        *   `OWNER_ID`: Your Telegram User ID.
        *   `LOGGER_ID`: ID of the group/channel where the bot should send logs and requires an active voice chat. This must be a valid group/channel ID where the bot is an admin.
        *   Other variables like `SUDOERS`, `SUPPORT_CHAT`, `UPSTREAM_REPO` can be configured as needed.

8.  **Set up `tmux` (Optional but Recommended for background running):**
    ```bash
    sudo apt install tmux -y && tmux
    ```

9.  **Run the Bot:**
    ```bash
    bash start 
    ```
    *If not using `tmux`, you might want to use `nohup bash start &` or a process manager like `systemd` for persistent running.*

---

### 🛠 Commands & Usage

Clonify offers a range of commands to enhance your music listening experience on Telegram:

| Command                 | Description                                 |
|-------------------------|---------------------------------------------|
| `/play <song name/url>` | Play the requested song or stream.          |
| `/vplay <song name/url>`| Play video stream.                          |
| `/pause`                | Pause the currently playing stream.         |
| `/resume`               | Resume the paused stream.                   |
| `/skip`                 | Skip the current track.                     |
| `/stop` or `/end`       | Stop playback and clear the queue.          |
| `/queue`                | Display the list of songs in the queue.     |
| `/clone <bot token>`    | Create a clone of this music bot.           |
| `/help`                 | Show the help menu with all commands.       |

For a full list of commands and their detailed usage, use the `/help` command with the bot.

---

###  troubleshooting

If you encounter issues while running Clonify, here are some common problems and solutions:

*   **Invalid `STRING_SESSION`**:
    *   **Problem**: The assistant client (userbot) fails to start, or you see errors related to authentication (`AuthKeyError`, `UserDeactivatedBan`, etc.).
    *   **Explanation**: The `STRING_SESSION` is a Pyrogram user session string that allows the bot's assistant client to operate under a user account. If this string is invalid, expired, or the account associated with it is banned or deleted, the assistant cannot function.
    *   **Solution**: Ensure you have a valid, freshly generated Pyrogram V2 session string. Use a reliable session generator script. Double-check that it's correctly copied into your `.env` file.

*   **`NoActiveGroupCall` Error**:
    *   **Problem**: The bot replies with an error indicating "No Active Group Call" or fails to play music, often showing this error in logs.
    *   **Explanation**: Clonify requires an active voice chat in the group/channel specified by your `LOGGER_ID` environment variable. The bot uses this chat for its main operations and logging. If there's no ongoing voice chat in that specific logger group/channel, this error will occur.
    *   **Solution**:
        1.  Verify that your `LOGGER_ID` in the `.env` file is correct and points to your intended log group/channel.
        2.  Ensure there is an active voice chat (VC) running in that `LOGGER_ID` group/channel *before* you try to play music or use commands that require an active call. The bot usually joins this VC on startup if configured correctly.

*   **Network Issues**:
    *   **Problem**: The bot connects to Telegram but has trouble with voice calls (e.g., distorted audio, frequent disconnections, inability to stream).
    *   **Explanation**: Telegram voice calls can be sensitive to network conditions on the server where the bot is hosted. Firewalls, restrictive NAT configurations, or general network instability can interfere.
    *   **Solution**:
        1.  Check your server's firewall settings to ensure UDP traffic on necessary port ranges is allowed.
        2.  If behind NAT, ensure proper port forwarding or consider using a server with a public IP address if possible.
        3.  Test your server's network connectivity and bandwidth.

*   **Dependency Problems**:
    *   **Problem**: Errors during startup or command usage related to missing packages or incorrect versions.
    *   **Explanation**: Clonify relies on specific versions of Python libraries listed in `requirements.txt` and system packages like `ffmpeg` and `nodejs`.
    *   **Solution**:
        1.  Ensure you have installed all dependencies using `pip3 install -U -r requirements.txt`.
        2.  Verify that `ffmpeg` and `nodejs` (accessible via `node` command) are correctly installed and in your system's PATH.
        3.  Check your Python version against the one specified in `runtime.txt` (Python 3.11.4 for this version).

*   **Checking Logs**:
    *   **Problem**: You encounter an issue not listed above, or the error message is unclear.
    *   **Explanation**: Clonify produces logs that can provide detailed information about errors and its operational flow.
    *   **Solution**: Check the console output if running directly, or look for log files if configured. These logs often contain specific error messages or tracebacks that can help pinpoint the issue. (The subtask to enhance logging aims to make these logs even more helpful).

*   **Outdated Configuration or Code**:
    *   **Problem**: Bot behaves unexpectedly, or some features don't work after an update.
    *   **Solution**: Ensure your local repository is up-to-date with the main Clonify repository (`git pull upstream master` or the relevant branch). Also, check `sample.env` for any new or changed environment variables that you might need to update in your `.env` file.

If you continue to experience issues, seek help in the [Support Group](#support).

---
<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" alt="Separator">

<h3 id="support" align="center">
    ─「 sᴜᴩᴩᴏʀᴛ 」─
</h3>

<p align="center">
<a href="https://t.me/ProBotGc"><img src="https://img.shields.io/badge/-Support%20Group-blue.svg?style=for-the-badge&logo=Telegram" alt="Support Group"></a>
</p>

<p align="center">
<a href="https://t.me/ProBotts"><img src="https://img.shields.io/badge/-Update%20Channel-blue.svg?style=for-the-badge&logo=Telegram" alt="Update Channel"></a>
</p>

<br />

---

<br />

- <b> _Sᴩᴇᴄɪᴀʟ ᴛʜᴀɴᴋs ᴛᴏ [ʏᴀsɪʀ](https://github.com/YasirAkhtar) ғᴏʀ [Cʟᴏɴɪғʏ](https://github.com/TeamProBots/Clonify)._ </b>