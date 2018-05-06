import inspect
import os
from typing import Dict

import discord
from discord.ext import commands
from fuzzywuzzy import process

import custom_classes as cc


class Discord:
    """Commands related to discord.py library"""
    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    async def __local_check(self, ctx):
        return "discord" in ctx.guild.name or await ctx.bot.is_owner(ctx.author)

    @cc.command()
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you can separate it by
        periods, e.g. tag.create for the create subcommand of the tag command
        or by spaces.
        """

        source_url = 'https://github.com/Modelmat/Kern-Bot'
        if command is None:
            return await ctx.send(source_url)

        obj = self.bot.get_command(command.replace('.', ' '))
        if obj is None:
            return await ctx.send('Could not find command.')

        # since we found the command we're looking for, presumably anyway, let's
        # try to access the code itself
        src = obj.callback.__code__
        lines, firstlineno = inspect.getsourcelines(src)
        if not obj.callback.__module__.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(src.co_filename).replace('\\', '/')
        else:
            location = obj.callback.__module__.replace('.', '/') + '.py'
            source_url = 'https://github.com/Rapptz/discord.py'

        final_url = f'<{source_url}/blob/master/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.send(final_url)

    async def generate(self, embed, obj, way="attributes"):
        if obj.get(way):
            embed.set_author(way.title())
            embed.clear_fields()
            for attr, val in obj[way].items():
                embed.add_field(name=attr, value=val)
        else:
            return embed

    @cc.command(aliases=["documentation", "rtfd"])
    async def docs(self, ctx, obj):
        """Displays the documentation for a discord command.
        e.g `discord.User` is User, and `commands.Bot` is Bot
        Note this is not paginated and is currently very spammy"""
        try:
            objs = [o[0] for o in process.extract(obj.lower(), self.bot.documentation.keys()) if o[1] > 75]
            obj = self.bot.documentation[obj]
        except KeyError:
            op = ""
            if objs:
                op = "\n**Did you mean:**\n\n- {}".format("\n- ".join(
                     [f"[{o}]({self.bot.documentation[o]['url']}])" for o in objs]
                ))
            return await ctx.error(f"Object `{obj}` does not exist{op}", "No Documentation Found")
        em = discord.Embed()
        em.description = f"""
**[*{obj['type']}* {obj['name']}{obj['arguments'].replace('*', '∗')}]({obj["url"]})**
{obj["description"]}
        """
        msg = await ctx.send(embed=em)
        # implement pagination


def setup(bot):
    bot.add_cog(Discord(bot))
