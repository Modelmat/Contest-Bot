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


class Misc:
    """Miscellaneous functions"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.process = psutil.Process()
        self.bot.remove_command('help')

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
    async def please(self, ctx, action: commands.clean_content, item: commands.clean_content, *, person: commands.clean_content="you"):
        """You can now make this bot do things!"""
        if len(action) < 3:
            return await ctx.error(f"{action} is not long enough.", "Invalid Input")
        elif action[-2] in "aeiou" and action[-1] not in "aeiou" and action[-3] not in "aeiou":
            action = action[:-1]
        elif action[-2:] == "ie":
            action = action[-2:] + "y"
        elif action[-1] == "e":
            action = action[:-1]
        await ctx.send(f"I am {action}ing {item} {person}")

    @cc.command()
    async def codestats(self, ctx):
        """Provides information about the bot's code"""
        line_count = 0
        cog_count = 0
        files = [f for f in os.listdir(".") if ".py" in f] + ["cogs/" + f for f in os.listdir("cogs") if ".py" in f]
        for f_name in files:
            cog_count += 1
            with open(f_name, encoding="utf-8") as f:
                line_count += len(f.readlines())
        await ctx.neutral(f"""**Lines**: {line_count}
**Cogs**: {cog_count}
**Commands**: {len(ctx.bot.commands)}""",
                          "Code Statistics", timestamp=False)

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

    async def clean_content(self, ctx, content):
        return await commands.clean_content(escape_markdown=True).convert(ctx, content)

    @cc.command()
    async def raw(self, ctx, *, message=None):
        """Displays the raw code of a message.
        The message can be a message id, some text, or nothing (in which case it will be the most recent message not by you)."""
        if message:
            try:
                message = await ctx.get_message(int(message))
            except ValueError:
                message = message
        else:
            async for msg in ctx.history(limit=100):
                if msg.author != ctx.author:
                    message = msg
                    break

        embed = None
        content = await self.clean_content(ctx, message.content)

        if message.embeds:
            embed = message.embeds[0]
            embed.description = await self.clean_content(ctx, embed.description or "")
            for index, field in enumerate(embed.fields):
                value = await self.clean_content(ctx, field.value)
                embed.set_field_at(index, name=field.name, value=value)

        await ctx.send(content, embed=embed)

    @raw.error
    async def raw_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.NotFound):
            await ctx.error("Incorrect message id provided",
                            "Message not found")
        elif isinstance(error, ValueError):
            await ctx.error("Message ID not an integer",
                            "Incorrect argument type")

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
        Hasers are: sha256, sha512, sha1, md5"""
        hash_types = ["sha256", "sha512", "sha1", "md5"]
        if hash_type in hash_types:
            hasher = eval(f"hashlib.{hash_type}")
            await ctx.neutral(f"**Hashed:** ```{hasher(text.encode()).hexdigest()}```")
        else:
            await ctx.error(f"Hasher {hash_type} not found")

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

    async def make_commands(self, ctx, long_description=False):
        total_commands = 0
        cogs_dict = defaultdict(list)
        for command in set(self.bot.walk_commands()):
            if not command.hidden and await command.can_run(ctx):
                if long_description:
                    value = command.long_doc
                else:
                    value = command.short_doc or "No description."
                data = {"name": command.qualified_name,
                        "value": value}
                cogs_dict[command.cog_name or "No Category"].append(data)
                total_commands += 1

        return cogs_dict, total_commands

    @cc.command(name="help")
    async def _help(self, ctx, *, command: str = None):
        """Shows this message."""
        cogs_dict, total_commands = await self.make_commands(ctx, bool(command))
        embed = discord.Embed(title="Help",
                              description=self.bot.description,
                              colour=discord.Colour.green(),
                              timestamp=datetime.utcnow())
        embed.set_footer(text=f"{total_commands} commands",
                         icon_url=ctx.author.avatar_url)
        embed.add_field(name="Links", value=(f"[Invite URL]({self.bot.invite_url})\n"
                                             f"[Server Invite](https://discord.gg/nHmAkgg)\n"
                                             f"[Bot Website](https://kern-bot.carrd.co/)"))

        if not command:
            await ctx.paginate(cogs_dict, embed)

        elif command.title() in cogs_dict:
            cog_dict = {command.title(): cogs_dict[command.title()]}
            await ctx.paginate(cog_dict, embed, page=2, max_fields=3)

        else:
            cmd = self.bot.get_command(command)
            if await cmd.can_run(ctx):
                embed.clear_fields()
                embed.description = cmd.long_doc
                for subcommand in getattr(cmd, "commands", []):
                    embed.add_field(name=subcommand.name,
                                    value=subcommand.long_doc,
                                    inline=False)

                await ctx.send(embed=embed)
            else:
                await ctx.error(f"The command `{command}` does not exist.", "")


def setup(bot):
    bot.add_cog(Misc(bot))
