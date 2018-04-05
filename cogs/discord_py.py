import inspect
import os
from typing import Dict

import discord
from discord.ext import commands

from custom_classes import CreateDocumentation


class DiscordPy:
    documentation: Dict[str, dict]

    def __init__(self, bot):
        self.bot = bot
        self.documentation = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        self.documentation = await CreateDocumentation().generate_documentation()
        print('Got Docs')

    async def __local_check(self, ctx):
        return "discord" in ctx.guild.name or await ctx.bot.is_owner(ctx.author)

    @commands.command()
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you can separate it by
        periods, e.g. tag.create for the create subcommand of the tag command
        or by spaces.
        ```{0}source <command>```
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

    @commands.command(aliases=["documentation", "rtfd"])
    async def docs(self, ctx, obj):
        """Displays the documentation for a discord command.
        e.g `discord.User` is User, and `commands.Bot` is Bot
        Note this is not paginated and is very spammy
        ```{0}docs <object>```"""
        try:
            obj = self.documentation[obj.lower()]
        except KeyError:
            return await ctx.error(f"Object `{obj}` does not exist", "No Documentation Found")
        em = discord.Embed(title=f"*{obj['type']}* {obj['name']}{obj['arguments']}", description=obj["description"],
                           url=obj["url"])
        msg = await ctx.send(embed=em)
        # implement pagination


def setup(bot):
    bot.add_cog(DiscordPy(bot))
