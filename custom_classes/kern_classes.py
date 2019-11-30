from datetime import datetime

import discord
from discord.ext import commands

from custom_classes import Ast


class KernCog(commands.Cog, metaclass=commands.CogMeta):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        for command in self.walk_commands():
            if hasattr(command, "on_error"):
                command.handled_errors = Ast(command.on_error).errors
            else:
                command.handled_errors = []

        cog_error_handler = self._get_overridden_method(self.cog_command_error)
        if cog_error_handler:
            self.handled_errors = Ast(cog_error_handler)
        else:
            self.handled_errors = []

        return self


class KernContext(commands.Context):
    def clean_prefix(self):
        user = self.bot.user
        prefix = self.prefix.replace(user.mention, '@' + user.name)
        return prefix

    async def add_reaction(self, reaction):
        try:
            await self.message.add_reaction(reaction)
        except discord.Forbidden:
            pass

    async def del_reaction(self, reaction):
        try:
            me = self.guild.me if self.guild else self.bot.user
            await self.message.remove_reaction(reaction, me)
        except discord.Forbidden:
            pass

    async def __embed(self, title, description, colour, rqst_by, timestamp, channel, footer, **kwargs):
        e = discord.Embed(colour=colour)
        if title is not None:
            e.title = str(title)
        if description is not None:
            e.description = str(description)
        if rqst_by:
            e.set_footer(icon_url=self.message.author.avatar_url)
        if footer:
            e.set_footer(text=footer)
        if timestamp is True:
            timestamp = datetime.utcnow()
        if isinstance(timestamp, datetime):
            e.timestamp = timestamp
        if channel is None:
            return await self.send(embed=e, **kwargs)
        return await channel.send(embed=e, **kwargs)

    async def error(self, error, title="Error:", channel: discord.TextChannel = None, footer=None, **kwargs):
        if isinstance(error, Exception):
            if title == "Error:":
                title = error.__class__.__name__
            error = str(error)
        return await self.__embed(title, error, discord.Colour.red(), False, False, channel, footer, **kwargs)

    async def success(self, success, title="Success:", channel: discord.TextChannel = None, rqst_by=True, timestamp=None, footer=None, **kwargs):
        return await self.__embed(title, success, discord.Colour.green(), rqst_by, timestamp, channel, footer, **kwargs)

    async def neutral(self, text, title=None, channel: discord.TextChannel = None, rqst_by=True, timestamp=None, footer=None, **kwargs):
        return await self.__embed(title, text, 0x36393E, rqst_by, timestamp, channel, footer, **kwargs)

    async def warning(self, warning, title=None, channel: discord.TextChannel = None, rqst_by=True, timestamp=None, footer=None, **kwargs):
        return await self.__embed(title, warning, discord.Colour.orange(), rqst_by, timestamp, channel, footer, **kwargs)

    async def upload(self, content):
        json = {"files": {"output.md": {"content": content}}}
        async with self.bot.session.post("https://api.github.com/gists", json=json, auth=self.bot.github_auth) as r:
            link = (await r.json())["html_url"]
        return link

    async def send(self, content: str = None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None):
        content = str(content) if content is not None else None
        if content and len(content) > 1990:
            content = "**Output too long**: " + await self.upload(content)

        return await super().send(content=content, tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce)
