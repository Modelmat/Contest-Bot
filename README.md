[![Discord Bots](https://discordbots.org/api/widget/380598116488970261.svg?usernamecolor=FFFFFF&topcolor=000000)](https://discordbots.org/bot/380598116488970261) 

# Kern Bot

Kern Bot is a bot by [![Modelmat](https://discordbots.org/api/widget/owner/380598116488970261.svg?noav)](https://discordbots.org/bot/380598116488970261) 

It has multiple features include YouTube® search, Trivia, Contests (semi-working), dictionaries, and other Miscellaneous functions.

To add this bot to your server, use [this](https://discordapp.com/oauth2/authorize?client_id=380598116488970261&scope=bot) link.



To run this by yourself (you MUST provide a reference to this bot somewhere.)
```bash
#Clone this bot
git clone https://github.com/Modelmat/Kern-Bot.git
#move to bot dir
cd Kern-Bot
#install requirements
python3 -m pip3 install -r requirements.txt
#make config files
touch client_secret.txt
touch database_secret.txt
#run bot
python3 main.py
```

# Configuration
All the lines in each line in the docs will be like this. However, only enter the `ENVIRONMENT_VARIABLE`, ignoring the description. These variables can also be environment variables (acessible by `os.environ`).
```
ENVIRONMENT_VARIABLE {Description}
```


`client_secret.txt`
```
AUTH_KEY {Bot Token}
APP_ID {Oxford Dictionary API}
APP_KEY {Oxford Dictionary API}
BOT_NAME {Bot's Username}
BOT_PREFIX {Bot's Command Prefix}
DBL_TOKEN {Discordbot.org Prefix}
```
`database_secret.txt`
```
DATABASE_URL {A PostgreSQL DB URL}
```

**Example**:
`database_secret.txt`
```
postgres://user:pass@server.com:port/database
```
