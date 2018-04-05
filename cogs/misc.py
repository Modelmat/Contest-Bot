from datetime import datetime
import inspect
from collections import OrderedDict
import os
import hashlib
from platform import python_version
from pkg_resources import get_distribution
import async_timeout

import psutil

import discord
from discord.ext import commands

from custom_classes import KernBot

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


class Misc:
    """Miscellaneous functions"""

    def __init__(self, bot: KernBot):
        self.bot = bot
        self.process = psutil.Process()
        self.bot.remove_command('help')

    @commands.command()
    async def codestats(self, ctx):
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


    @commands.command()
    async def emoji(self, ctx, *, emoji):
        """Converts a Discord unicode emoji to a standard uncode emoji, for copying"""
        await ctx.send(f"`{emoji}`")

    @commands.command()
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

    @commands.command()
    async def raw(self, ctx, *, message=None):
        """Displays the raw code of a message.
        The message can be a message id, some text, or nothing (in which case it will be the most recent message not by you).
        ```{0}raw <message>```"""
        msg = None
        if message is not None:
            msg = await ctx.get_message(int(message))
        else:
            async for message in ctx.history(limit=10):
                if message.author == ctx.author:
                    continue
                msg = message
                break

        if msg is None:
            msg = ctx.message
            msg.content = msg.content.split('raw ')[1]

        raw = await commands.clean_content(escape_markdown=True).convert(
            ctx, msg.content)
        if raw:
            raw = f"​\n{raw}\n​"
        embed_text = str()
        if msg.embeds:
            embed_text += "*Message has {} embed(s).*".format(len(msg.embeds))
        embed = discord.Embed(
            description=raw + embed_text,
            timestamp=datetime.utcnow(),
            colour=discord.Colour.blurple())
        embed.set_author(
            name="Message by: {}".format(msg.author),
            icon_url=msg.author.avatar_url)
        await ctx.send(f"Message by: {msg.author}\n{raw} {embed_text}")

    @raw.error
    async def raw_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, discord.NotFound):
            await ctx.error("Incorrect message id provided",
                            "Message not found")
        elif isinstance(error, ValueError):
            await ctx.error("Message ID not an integer",
                            "Incorrect argument type")
        else:
            await ctx.error(error)

    @commands.command()
    async def ping(self, ctx):
        """Returns time taken for a internet packet to go from this bot to discord"""
        await ctx.send("Pong. Time taken: `{:.0f}ms`".format(
            self.bot.latency * 1000))

    def get_uptime(self):
        delta_uptime = datetime.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        output = str()
        if days > 0:
            output += "{} days\n".format(days)
        if hours > 0:
            output += "{} hours\n".format(hours)
        if minutes > 0:
            output += "{} minutes\n".format(minutes)
        if seconds > 0:
            output += "{} seconds\n".format(seconds)
        return output

    @commands.command(aliases=['stats'])
    async def info(self, ctx):
        """Returns information about the bot."""
        total_members = sum(1 for _ in self.bot.get_all_members())
        total_servers = len(self.bot.guilds)
        total_channels = sum(1 for _ in self.bot.get_all_channels())
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        ram_usage = self.process.memory_full_info().uss / 1024**2
        invite_url = f"https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot"
        embed = discord.Embed(
            description=
            f"[Invite URL]({invite_url})\n[Server Invite](https://discord.gg/nHmAkgg)\n[Bot Website](http://kern-bot.tk/)\n{self.bot.description}",
            color=0x00ff00)
        embed.set_author(
            name=self.bot.owner, icon_url=self.bot.owner.avatar_url)
        embed.add_field(
            name="#\u20e3 Server Statistics:",
            value="**Guilds**: {}\n**Channels**: {}\n**Users**: {}".format(
                total_servers, total_channels, total_members))
        embed.add_field(
            name="🔌 Resource Usage:",
            value="CPU: {:.2f} %\nRAM: {:.2f} MiB".format(
                cpu_usage, ram_usage))
        embed.add_field(name="⏰ Uptime:", value=self.get_uptime())
        embed.add_field(
            name="Running On:",
            value=f"""<:python:416194389853863939>: {python_version()}
<:discord:416194942520786945>: {get_distribution('discord.py').version} [discord.py]
<:git:417177301244051525>: {self.bot.latest_commit} [Up-To-Date: {self.bot.latest_commit == get_distribution('discord.py').version.split("+")[1]}]"""
        )
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.command()
    async def hug(self, ctx, *, item: str):
        """Hugs the given item
        ```{0}hug <item>```"""
        await ctx.send("«{}»".format(item))

    @commands.command()
    async def kiss(self, ctx, *, item: str):
        """Kisses the given item
        ```{0}kiss <item>```"""
        await ctx.send("💋{}💋".format(item))

    @commands.group(name="hash")
    async def _hash(self, ctx):
        """Hashes a string of text
        ```{0}hash <hasher> <text>```"""
        if ctx.invoked_subcommand is None:
            await ctx.error(f"Hash type {ctx.subcommand_passed} not found")

    @_hash.command(name="sha256")
    async def hash_sha256(self, ctx, *, text):
        """Hashes in SHA256"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.sha256(text.encode()).hexdigest()}```"
        )

    @_hash.command(name="sha224")
    async def hash_sha224(self, ctx, *, text):
        """Hashes in SHA224"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.sha224(text.encode()).hexdigest()}```"
        )

    @_hash.command(name="sha512")
    async def hash_sha512(self, ctx, *, text):
        """Hashes in SHA512"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.sha512(text.encode()).hexdigest()}```"
        )

    @_hash.command(name="sha1")
    async def hash_sha1(self, ctx, *, text):
        """Hashes in SHA1"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.sha1(text.encode()).hexdigest()}```"
        )

    @_hash.command(name="sha384")
    async def hash_sha384(self, ctx, *, text):
        """Hashes in SHA384"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.sha384(text.encode()).hexdigest()}```"
        )

    @_hash.command(name="md5")
    async def hash_md5(self, ctx, *, text):
        """Hashes in MD5"""
        await ctx.neutral(
            f"**Original:**```{text}```**Hashed:**```{hashlib.md5(text.encode()).hexdigest()}```"
        )

    @commands.command()
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

    @commands.command()
    async def invite(self, ctx):
        """Sends the bot's invite URL"""
        await ctx.send(
            f"Add to your server: https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot"
        )

    @commands.command(hidden=True)
    async def echo(self, ctx, *, text: commands.clean_content):
        """Echoes the text sent
        ```{0}echo <text>```"""
        await ctx.send(text)

    @commands.command()
    async def snowflake(self, ctx, snowflake: int):
        """Converts snowflake id into creation date.
        Bot requires no knowledge of user/emoji/guild/channel.
        Provides date in D/M/Y format
        ```{0}snowflake <id>```"""
        try:
            timestamp = int(f"{snowflake:b}" [:-22], 2) + 1420070400000
            date = datetime.utcfromtimestamp(float(timestamp) / 1000)
        except OverflowError:
            await ctx.error("Snowflake integer **way** too large", "")
        except ValueError:
            await ctx.error("Snowflake integer **way** too small", "")
        else:
            await ctx.send(date.strftime("%d/%m/%Y %H:%M:%S"))

    def make_commands(self, ctx):
        cogs_dict = OrderedDict()
        for cog in self.bot.cogs:
            if getattr(cog, "hidden", False):
                continue
            cogs_dict[cog] = cogs_dict.get(cog, []) + [
                cmd for cmd in self.bot.get_cog_commands(cog)
                if not cmd.hidden and cmd.can_run(ctx)
            ]
        for cmd in self.bot.commands:
            if cmd.cog_name is None and not cmd.hidden and cmd.can_run(ctx):
                cogs_dict['No Category'] = cogs_dict.get(
                    'No Category', []) + [[cmd.name] + cmd.aliases]
        cogs_dict = OrderedDict(
            [(key, val) for key, val in cogs_dict.items() if val])
        return cogs_dict

    @commands.command(name="help")
    async def _help(self, ctx, *, command: str = None):
        """Shows this message.
        ```{0}help [command]```"""
        cogs_dict = self.make_commands(ctx)
        embed = discord.Embed(color=discord.Colour.green())
        if command is None:
            command = "Help"
            embed.description = "{0}\nUse `{1}help command` for further detail.".format(
                self.bot.description, ctx.clean_prefix())
            for cog, cmds in cogs_dict.items():
                commands_l = []
                for cmd in cmds:
                    commands_l.append(f"{cmd}")
                embed.add_field(
                    name=cog.capitalize(),
                    value=", ".join(commands_l),
                    inline=False)

        elif command.lower() in [cog.lower() for cog in cogs_dict.keys()]:
            # actually a cog
            command = command.capitalize()
            embed.description = inspect.cleandoc(
                self.bot.get_cog(command).__doc__)
            for cmd in self.bot.get_cog_commands(command):
                if not cmd.hidden:
                    if cmd.help is None:
                        c_help = "No description"
                    else:
                        c_help = cmd.help.format(ctx.clean_prefix())
                    embed.add_field(
                        name=cmd.qualified_name, value=c_help, inline=False)

        elif self.bot.get_command(command) is not None:
            command = self.bot.get_command(command)
            if command.help is None:
                command_help = "No description"
            else:
                command_help = command.help.format(ctx.clean_prefix())
            embed.description = command_help
            if command.aliases:
                embed.add_field(
                    name="Aliases", value=", ".join(command.aliases))
            if isinstance(command, commands.Group):
                for cmd in command.commands:
                    if not cmd.hidden:
                        if cmd.help is None:
                            c_help = "No description"
                        else:
                            c_help = cmd.help.format(ctx.clean_prefix())
                        embed.add_field(
                            name=cmd.qualified_name,
                            value=c_help,
                            inline=False)

        else:
            return await ctx.error(f"The command `{command}` does not exist.",
                                   "")

        embed.timestamp = datetime.utcnow()
        embed.set_author(
            name=str(command).capitalize(), url="https://discord.gg/nHmAkgg")
        embed.set_footer(
            text="Requested by: {}".format(ctx.message.author),
            icon_url=ctx.message.author.avatar_url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Misc(bot))
