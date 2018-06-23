# Installing

If you wish to run an instance of Kern Bot yourself, please acknowledge the source of 
my work. Please also read the [license](LICENSE) and note that
```
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
```

Step 1) Clone the bot from the GitHub repository
```bash
$ git clone https://github.com/Modelmat/Kern-Bot.git && cd Kern-Bot
```
Step 2) Install the requirements needed (on linux `python3 -m pip`)
```bash
$ pip install -r requirements.txt
```
Step 3) Create the secrets file. Fill out out by following [these](#secrets) steps.
```bash
$ echo > .env
```
Step 4) Run the bot
```bash
$ py main.py
```

# Secrets
The `.env` file should be a dotnev-style file (KEY=VALUE), with the follow keys:
```
TOKEN        # Bot Token
APP_ID       # Oxford Dictionary API
APP_KEY      # Oxford Dictionary API
BOT_NAME     # Bot's Username (updated if different)
BOT_PREFIXES # Bot's Command Prefix - comma seperated
DBL_TOKEN    # Discordbots.org
DATABASE_URL # PostgreSQL DB Url with auth
GITHUB_AUTH  # GitHub OAuth token for Gists
```
For example, the `BOT_PREFIXES` could be:
```
BOT_PREFIXES=!, ?
```
or the github AUTH:
```
GITHUB_AUTH=username:oauth_key
```

# Database Permissions
This bot assumes a database user which has atleast all non-superuser permissions. 
For reference, the database system automatically sets it up like so:
```sql
CREATE ROLE user_name;
ALTER ROLE user_name WITH LOGIN PASSWORD 'password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE database_name OWNER user_name;
REVOKE ALL ON DATABASE database_name FROM PUBLIC;
GRANT CONNECT ON DATABASE database_name TO user_name;
GRANT ALL ON DATABASE database_name TO user_name;
```