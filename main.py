from datetime import datetime, timedelta
from os import environ
import traceback
import asyncio
from platform import python_version
from pkg_resources import get_distribution
import async_timeout

import discord
from discord.ext import commands

import custom_classes as cc


# update: pip install -U git+https://github.com/Modelmat/discord.py@rewrite#egg=discord.py[voice]
def server_prefix(bot_prefixes: list):
    async def prefix(bots: cc.KernBot, message: discord.Message):
        if not message.guild:
            return commands.when_mentioned_or(*bot_prefixes)(bots, message)

        if bots.prefixes_cache.get(message.guild.id) is None:
            guild_prefixes = await bots.database.get_prefixes(message)
            bots.prefixes_cache[message.guild.id] = list(set(guild_prefixes))

        prefixes = []

        for prefix in sorted([*bot_prefixes, *bots.prefixes_cache[message.guild.id]], key=len):
            prefixes.append(prefix + " ")
            prefixes.append(prefix.upper() + "")
            prefixes.append(prefix)
            prefixes.append(prefix.upper())


        return commands.when_mentioned_or(*prefixes)(bots, message)

    return prefix


try:
    token = environ["AUTH_KEY"]
    name = environ["BOT_NAME"]
    bot_prefixes = environ["BOT_PREFIX"].split(", ")
    dbl_token = environ["DBL_TOKEN"]
except KeyError:
    with open("client.secret", encoding="utf-8") as file:
        lines = [l.strip() for l in file]
        token = lines[0]
        name = lines[3]
        bot_prefixes = lines[4].split(", ")
        dbl_token = lines[5]

bot = cc.KernBot(
    command_prefix=server_prefix(bot_prefixes),
    case_insensitive=True,
    description="Multiple functions, including contests, definitions, and more.",
    activity=discord.Game(name="Start-up 101"))


async def load_extensions(bots):
    await asyncio.sleep(2)
    for extension in bots.exts:
        try:
            bots.load_extension("cogs." + extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to load extension {extension}.')
            traceback.print_exc()
            await bot.suicide()


@bot.event
async def on_connect():
    await bot.update_dbots_server_count(dbl_token)
    with async_timeout.timeout(20):
        async with bot.session.get("https://api.github.com/repos/Modelmat/discord.py/commits/rewrite") as r:
            bot.latest_commit = "g" + (await r.json())['sha'][:7]
    await bot.pull_remotes()


@bot.event
async def on_guild_join(guild: discord.Guild):
    e = discord.Embed(
        title="Joined {} @ {}".format(guild.name,
                                      datetime.utcnow().strftime('%H:%M:%S UTC')),
        colour=discord.Colour.green(),
        timestamp=datetime.utcnow())
    await bot.logs.send(embed=e)
    await bot.update_dbots_server_count(dbl_token)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    e = discord.Embed(
        title="Left {} @ {}".format(guild.name,
                                    datetime.utcnow().strftime('%H:%M:%S UTC')),
        colour=discord.Colour.red(),
        timestamp=datetime.utcnow())
    await bot.logs.send(embed=e)
    await bot.update_dbots_server_count(dbl_token)


@bot.event
async def on_ready():
    await load_extensions(bot)
    await bot.change_presence(status=discord.Status.online)
    bot.owner = (await bot.application_info()).owner
    if bot.user.name != name:
        print(f"\nName changed from '{bot.user.name}' to '{name}'")
        await bot.user.edit(username=name)
    e = discord.Embed(
        title=f"Bot Online @ {datetime.utcnow().strftime('%H:%M:%S UTC')}",
        colour=discord.Colour.green(),
        timestamp=datetime.utcnow())
    print(f"""
Username:   {bot.user.name}
ID:         {bot.user.id}
Bot:        {bot.user.bot}
Guilds:     {len(bot.guilds)}
Members:    {sum(1 for _ in bot.get_all_members())}
Channels:   {sum(1 for _ in bot.get_all_channels())}
Python:     {python_version()}
Discord:    {get_distribution('discord.py').version}
Cur. Com:   {bot.latest_commit}
Up to Date: {bot.latest_commit == get_distribution('discord.py').version.split("+")[1]}
---------------
""")

    while bot.logs is None:
        await asyncio.sleep(1)
        bot.logs = bot.get_channel(382780308610744331)
    await bot.logs.send(embed=e)


@bot.event
async def on_resumed():
    if bot.latest_message_time > datetime.utcnow() + timedelta(seconds=30):
        em = discord.Embed(
            title=f"Resumed @ {datetime.utcnow().strftime('%H:%M:%S')}",
            description=f"Down since: {datetime.utcnow().strftime('%H:%M:%S')}",
            colour=discord.Colour.red())
        await bot.logs.send(embed=em)
    print(bot.latest_message_time)
    print(bot.latest_message_time == datetime.utcnow())
    print(datetime.utcnow() + timedelta(seconds=30))


@bot.event
async def on_socket_raw_receive(_):
    bot.latest_message_time = datetime.utcnow()


@bot.event
async def on_message(message: discord.Message):
    if bot.database is None or message.author.bot:
        return
    async with bot.database.lock:
        if " && " in message.content:
            cmds_run_before = []
            failed_to_run = {}
            messages = message.content.split(" && ")
            for msg in messages:
                message.content = msg
                ctx = await bot.get_context(message, cls=cc.CustomContext)
                if ctx.valid:
                    if msg.strip(ctx.prefix) not in cmds_run_before:
                        await bot.invoke(ctx)
                        cmds_run_before.append(msg.strip(ctx.prefix))
                    else:
                        failed_to_run[msg.strip(ctx.prefix)] = "This command has been at least once before."
                else:
                    if ctx.prefix is not None:
                        failed_to_run[msg.strip(ctx.prefix)] = "Command not found."

            if failed_to_run and len(failed_to_run) != len(message.content.split(" && ")):
                errors = ""
                for fail, reason in failed_to_run.items():
                    errors += f"{fail}: {reason}\n"
                await ctx.error(f"```{errors}```", "These failed to run:")

        else:
            # is a command returned
            ctx = await bot.get_context(message, cls=cc.CustomContext)
            await bot.invoke(ctx)


@commands.is_owner()
@bot.command(name="reload", hidden=True)
async def reload_cog(ctx, *cog_names: str):
    """Reload the cog `cog_name`"""
    good = []
    bad = []
    for cog_name in cog_names:
        try:
            bot.unload_extension("cogs." + cog_name)
            print(f"{cog_name} unloaded.", end=' | ')
            bot.load_extension("cogs." + cog_name)
            print(f"{cog_name} loaded.")
            good.append(cog_name)
        except:
            bad.append(cog_name)
            print(f"{cog_name} failed to load")
            traceback.print_exc()

    string = f"{len(good)} cog(s) reloaded successfully."
    if good:
        string += "\n**Success:**\n" + "\n".join(good)
    if bad:
        string += "\n**Fail:**\n" + "\n".join(bad)
    await ctx.neutral(string)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bot.start(token))
except KeyboardInterrupt:
    loop.run_until_complete(bot.suicide())
