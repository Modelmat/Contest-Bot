import asyncio
import traceback
import warnings
from datetime import datetime, timedelta
from os import environ
from platform import python_version

import async_timeout
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pkg_resources import get_distribution

import custom_classes as cc

warnings.filterwarnings("ignore", category=UserWarning, module="fuzzywuzzy")


def server_prefix(default_prefixes: list):
    async def get_prefix(bots: cc.KernBot, message: discord.Message):
        if not message.guild:
            return commands.when_mentioned_or(*default_prefixes)(bots, message)

        if bots.prefixes_cache.get(message.guild.id) is None:
            guild_prefixes = await bots.database.get_prefixes(message)
            bots.prefixes_cache[message.guild.id] = list(set(guild_prefixes))

        guild_prefixes = []
        for prefix in sorted([*default_prefixes, *bots.prefixes_cache[message.guild.id]], key=lambda x: len(x)):
            guild_prefixes.append(prefix + " ")
            guild_prefixes.append(prefix.upper() + "")
            guild_prefixes.append(prefix)
            guild_prefixes.append(prefix.upper())

        return commands.when_mentioned_or(*guild_prefixes)(bots, message)

    return get_prefix


load_dotenv()


token = environ["TOKEN"]
name = environ["BOT_NAME"]
prefixes = environ["BOT_PREFIXES"].split(", ")
dbl_token = environ["DBL_TOKEN"]
github_auth = environ["GITHUB_AUTH"].split(":")
testing = bool(environ.get("TESTING", ""))

description = f"""Kern is a discord bot by Modelmat#8218.

Its original concept was for a contests bot, but this has expanded to incorporate many other functions as the owner sees fit.

It is in active development and as such any errors found can be reported to the owner in the support server which is linked below.

"""

bot = cc.KernBot(
    github_auth,
    command_prefix=server_prefix(prefixes),
    case_insensitive=True,
    description=description,
    activity=discord.Game(name="Start-up 101"),
    testing=testing)


@bot.event
async def on_connect():
    await bot.update_dbots_server_count(dbl_token)
    with async_timeout.timeout(20):
        async with bot.session.get("https://api.github.com/repos/rapptz/discord.py/commits/rewrite") as r:
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
    bot.invite_url = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(270336))

    activity = discord.Activity(name=f"for prefix k; in {len(bot.guilds)} servers",
                                type=discord.ActivityType.watching)
    await bot.change_presence(activity=activity)

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
Testing:    {testing}
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


@bot.event
async def on_socket_raw_receive(_):
    bot.latest_message_time = datetime.utcnow()


@bot.event
async def on_message(message: discord.Message):
    if bot.database is None or not bot.database.ready or message.author.bot:
        return
    if " && " in message.content:
        cmds_run_before = []
        failed_to_run = {}
        messages = message.content.split(" && ")
        for msg in messages:
            message.content = msg
            ctx = await bot.get_context(message, cls=cc.KernContext)
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
        ctx = await bot.get_context(message, cls=cc.KernContext)
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


bot.run(token)