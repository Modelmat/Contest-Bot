import aiofiles
from datetime import datetime
import inspect
from collections import defaultdict
import os
import hashlib
from platform import python_version
from pkg_resources import get_distribution
import async_timeout

import psutil

import discord
from discord.ext import commands

import custom_classes as cc

COUNTRY_CODES = {
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "DE": "Germany",
    "DK": "Denmark",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "IR": "Islamic Republic of Iran",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "TR": "Turkey",
    "US": "United States of America"
}

INDEXES = {
    "1": "ˢᵗ",
    "2": "ⁿᵈ",
    "3": "ʳᵈ",
}


async def clean_content(ctx, content):
    return await commands.clean_content(escape_markdown=True).convert(ctx, content)


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.embeds = []


class Misc:
    """Miscellaneous functions"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.process = psutil.Process()
        self.bot.remove_command('help')

    @commands.guild_only()
    @cc.command(aliases=["whowerefirst"])
    async def whowasfirst(self, ctx, number: int=1):
        """Provides the first x number of members in this guild
        Requires a maximum of ten members"""
        if number > 10 or number == 0:
            return await ctx.error(f"{number} is too big. Try less than 11.", "Bad Argument")
        mems = sorted(ctx.guild.members, key=lambda x: x.joined_at)[:number]
        oup = ""
        for i, mem in enumerate(mems, start=1):
            oup += f"{mem.mention} was {i}{INDEXES.get(str(i), 'ᵗʰ')}\n"
        await ctx.neutral(oup, "First Member(s)", timestamp=ctx.guild.created_at, footer="Guild created at")

    @commands.guild_only()
    @cc.command()
    async def whatwas(self, ctx, member: discord.Member=None):
        """Provides the index of a member in joining this guild"""
        if not member:
            member = ctx.author
        mems = sorted(ctx.guild.members, key=lambda x: x.joined_at)
        index = mems.index(member) + 1
        end = INDEXES.get(str(index)[-1], "ᵗʰ")
        await ctx.neutral(f"{member.mention} was {index}{end}")

    @cc.command()
    async def codestats(self, ctx):
        """Provides statistics on the bot's code"""
        cog_count = len(self.bot.cogs)
        commands_count = len(set(self.bot.walk_commands()))

        line_count = 0
        directories = [".", "cogs", "custom_classes"]
        files = [f"{d}/{f}" for d in directories for f in os.listdir(d) if ".py" in f]
        for file in files:
            async with aiofiles.open(file, encoding="utf-8") as f:
                line_count += len(await f.readlines())

        await ctx.neutral(f"""**Lines**: {line_count}
**Cogs**: {cog_count}
**Files**: {len(files)}
**Commands**: {commands_count}""", timestamp=False)


    @cc.command()
    async def emoji(self, ctx, *, emoji):
        """Converts a Discord unicode emoji to a standard uncode emoji, for copying"""
        await ctx.send(f"`{emoji}`")

    @cc.command()
    async def person(self, ctx):
        """Generates a random person"""
        with async_timeout.timeout(10):
            async with self.bot.session.get(
                    "https://randomuser.me/api/?noinfo") as resp:
                data = (await resp.json())['results'][0]
        names = data['name']
        name = "{} {} {}".format(names['title'].capitalize(),
                                 names['first'].capitalize(),
                                 names['last'].capitalize())
        location = data['location']
        login = data['login']

        em = discord.Embed(
            colour=discord.Colour.dark_purple(),
            title=name,
            description="**Gender**: " + data['gender'].capitalize() +
            "\n**Born**: " + data['dob'])
        address = "**Street**: {}\n**City**: {}\n**State**: {}\n**Postcode**: {}\n**Country**: {}".format(
            " ".join([w.capitalize() for w in location['street'].split(" ")]),
            location['city'].capitalize(), location['state'].capitalize(),
            location['postcode'], COUNTRY_CODES[data['nat']])
        logins = "**Username**: {}\n**Password**: {}".format(
            login['username'], login['password'])
        contact_details = "**Email**: {}\n**Phone**: {}\n**Mobile**: {}".format(
            data['email'].split("@")[0] + "@gmail.com", data['phone'],
            data['cell'])
        em.add_field(name="Address:", value=address, inline=False)
        em.add_field(name="Login Details:", value=logins, inline=False)
        em.add_field(
            name="Contact Details", value=contact_details, inline=False)
        em.set_thumbnail(url=data['picture']['large'])

        await ctx.send(embed=em)

    @cc.command()
    async def raw(self, ctx, *, message=None):
        """Displays the raw code of a message.
        The message can be a message id, some text, or nothing (in which case it will be the most recent message not by you)."""
        if message:
            try:
                message = await ctx.get_message(int(message))
            except ValueError:
                message = FakeMessage(message)
        else:
            async for msg in ctx.history(limit=100):
                if msg.author != ctx.author:
                    message = msg
                    break

        embed = None
        content = await clean_content(ctx, message.content)

        if message.embeds:
            embed = message.embeds[0]
            embed.description = await clean_content(ctx,
                                                    embed.description or "")
            for index, field in enumerate(embed.fields):
                value = await clean_content(ctx, field.value)
                embed.set_field_at(index, name=field.name, value=value)

        await ctx.send(content, embed=embed)

    @raw.error
    async def raw_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.NotFound):
            await ctx.error("Incorrect message id provided",
                            "Message not found")

    @cc.command()
    async def ping(self, ctx):
        """Returns time taken for a internet packet to go from this bot to discord"""
        await ctx.send("Pong. Time taken: `{:.0f}ms`".format(
            self.bot.latency * 1000))

    @property
    def uptime(self):
        delta_uptime = datetime.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        output = str()
        if days > 0:
            output += "{} days, ".format(days)
        if hours > 0:
            output += "{} hours, ".format(hours)
        if minutes > 0:
            output += "{} minutes, ".format(minutes)
        if seconds > 0:
            output += "{} seconds".format(seconds)
        return output

    @cc.command(aliases=['stats', 'about'])
    async def info(self, ctx):
        """Returns information about the bot."""
        embed = discord.Embed(description=self.bot.description, colour=0x00ff00)
        embed.set_author(name=self.bot.owner, icon_url=self.bot.owner.avatar_url)
        embed.description += f"""

**Bot Details**
<:channels:432082250465804289> **Channels** {sum(1 for _ in self.bot.get_all_channels())}
<:servers:432077842285854720> **Servers** {len(self.bot.guilds)}
<:members:432082250436444162> **Members** {sum(1 for _ in self.bot.get_all_members())} 
<:ram:432080886985654273> **RAM Usage** {self.process.memory_full_info().uss / 1024**2} MB
<:cpu:432077839228076033> **CPU Usage** {self.process.cpu_percent() / psutil.cpu_count()} % 
<:uptime:432082654335336457> **Uptime** {self.uptime}
<:python:416194389853863939> **Python** {python_version()}
<:discord:416194942520786945> **Discord.py** {get_distribution('discord.py').version}
<:git:417177301244051525> **Git** {self.bot.latest_commit} [Up-To-Date: {self.bot.latest_commit == get_distribution('discord.py').version.split("+")[1]}]
"""
        embed.add_field(name="Links", value=(f"[Invite URL]({self.bot.invite_url})\n"
                                             f"[Server Invite](https://discord.gg/nHmAkgg)\n"
                                             f"[Bot Website](https://kern-bot.carrd.co/)"))
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text="Hover over emojis")
        await ctx.send(embed=embed)

    @cc.group(name="hash")
    async def _hash(self, ctx, hash_type, *, text):
        """Hashes a string of text
        Hashers available are: sha256, sha512, sha1, md5"""
        hash_types = ["sha256", "sha512", "sha1", "md5"]
        if hash_type in hash_types:
            hasher = eval(f"hashlib.{hash_type}")
            await ctx.neutral(f"**Hashed:** ```{hasher(text.encode()).hexdigest()}```")
        else:
            await ctx.error(f"Hasher {hash_type} not found")

    @commands.guild_only()
    @cc.command()
    async def tree(self, ctx):
        """Provides a directory tree like view of the server's channels"""
        tree_string = f"For user {ctx.author}\n{ctx.guild}\n"
        for cat_tup in ctx.guild.by_category():
            if cat_tup[0] is not None:
                tree_string += f"|-- {cat_tup[0].name.upper()}\n"
            for channel in cat_tup[1]:
                prefix = str()
                if isinstance(channel, discord.TextChannel):
                    prefix += "📨"
                    if channel.is_nsfw():
                        prefix += "⛔"
                elif isinstance(channel, discord.VoiceChannel):
                    prefix += "🔊"
                tree_string += "|  |--{}\n".format(
                    f"{prefix} {channel.name.lower()} ({channel.permissions_for(ctx.author).value})"
                )

        await ctx.send(f"```fix\n{tree_string}```")

    @cc.command()
    async def invite(self, ctx):
        """Sends the bot's invite URL"""
        await ctx.send(f"<{self.bot.invite_url}>")

    @cc.command(hidden=True)
    async def echo(self, ctx, *, text: commands.clean_content):
        """Echoes the text sent"""
        await ctx.send(text)

    @cc.command()
    async def snowflake(self, ctx, snowflake: int):
        """Converts snowflake id into creation date.
        Bot requires no knowledge of user/emoji/guild/channel.
        Provides date in D/M/Y format"""
        try:
            timestamp = int(f"{snowflake:b}" [:-22], 2) + 1420070400000
            date = datetime.utcfromtimestamp(float(timestamp) / 1000)
        except OverflowError:
            await ctx.error("Snowflake integer **way** too large", "")
        except ValueError:
            await ctx.error("Snowflake integer **way** too small", "")
        else:
            await ctx.send(date.strftime("%d/%m/%Y %H:%M:%S"))

    @cc.command(name="help")
    async def _help(self, ctx, *, command: str = None):
        """Shows this message."""
        embed = discord.Embed(title="Help",
                              description=self.bot.description,
                              colour=discord.Colour.green(),
                              timestamp=datetime.utcnow())
        embed.set_footer(icon_url=ctx.author.avatar_url)
        embed.add_field(name="Links", value=(f"[Invite URL]({self.bot.invite_url})\n"
                                             f"[Server Invite](https://discord.gg/nHmAkgg)\n"
                                             f"[Bot Website](https://kern-bot.carrd.co/)"))

        if not command:
            paginator = await cc.Paginator.from_commands(ctx, embed)
            await paginator.start_paginating()

        elif command.title() in self.bot.cogs:
            def check(command_):
                return command_.cog_name == command.title()
            paginator = await cc.Paginator.from_commands(ctx, embed,
                                                         max_fields=3,
                                                         initial_page=2,
                                                         long_doc=True,
                                                         check=check)

            await paginator.start_paginating()

        else:
            cmd = self.bot.get_command(command)
            if not cmd or not await cmd.can_run(ctx):
                return await ctx.error(f"The command `{command}` does not exist.", "")

            def check(command_):
                if command_ in cmd.commands:
                    return True
                return command_ == cmd

            paginator = await cc.Paginator.from_commands(ctx, embed,
                                                         max_fields=3,
                                                         long_doc=True,
                                                         check=check,
                                                         include_base_embed=False)

            await paginator.start_paginating()


def setup(bot):
    bot.add_cog(Misc(bot))
