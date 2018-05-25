# Kern Bot
![CircleCI](https://img.shields.io/circleci/project/github/Modelmat/Kern-Bot.svg)

[![Servers](https://discordbots.org/api/widget/servers/380598116488970261.svg)](https://discordbots.org/bot/380598116488970261) 
[![Owner](https://discordbots.org/api/widget/owner/380598116488970261.svg?noavatar=true)](https://discordbots.org/bot/380598116488970261) 
[![Status](https://discordbots.org/api/widget/status/380598116488970261.svg?noavatar=true)](https://discordbots.org/bot/380598116488970261)
[![Upvotes](https://discordbots.org/api/widget/upvotes/380598116488970261.svg?noavatar=true)](https://discordbots.org/bot/380598116488970261)
[![Library](https://discordbots.org/api/widget/lib/380598116488970261.svg?noavatar=true)](https://discordbots.org/bot/380598116488970261)
[![Server](https://discordapp.com/api/guilds/382780023926554625/widget.png?style=shield)](https://discord.gg/nHmAkgg)

Kern Bot is a bot by Modelmat#8218

It has multiple features include YouTube® search, Trivia, Contests (semi-working), dictionaries, and other Miscellaneous functions.

To add this bot to your server, use [this](https://discordapp.com/oauth2/authorize?client_id=380598116488970261&scope=bot&permissions=270336) link.



To run this by yourself (you MUST provide a reference to this bot somewhere.)
```bash
#Clone this bot
git clone https://github.com/Modelmat/Kern-Bot.git
#move to bot dir
cd Kern-Bot
#install requirements
python3 -m pip3 install -r requirements.txt
#make config files
touch client.secret
#run bot
python3 main.py
```

# Configuration
All the lines in each line in the docs will be like this. However, only enter the `ENVIRONMENT_VARIABLE`, ignoring the comments. These variables can also be environment variables (acessible by `os.environ`).
```py
ENVIRONMENT_VARIABLE # Description
```


`client.secret`
```py
AUTH_KEY     # Bot Token
APP_ID       # Oxford Dictionary API
APP_KEY      # Oxford Dictionary API
BOT_NAME     # Bot's Username
BOT_PREFIXES # Bot's Command Prefix - comma seperated
DBL_TOKEN    # Discordbots.org
DATABASE_URL # PostgreSQL DB Url with auth
GITHUB_OAUTH # GitHub OAuth token for Gists
```

**Example**:
{BOT_PREFIXES}
```py
!, ?, %  # note the spaces
```
{GITHUB_OAUTH}
```py
modelmat:403926033d001b5279df37cbbe5287b7c7c267fa # not real
```