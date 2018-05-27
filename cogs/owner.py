from os import execl, system
from sys import executable, argv
import asyncio
import io
import textwrap
from contextlib import redirect_stdout
from datetime import datetime

import discord
from discord.ext import commands

import custom_classes as cc


class Owner:
    """Owner only commands"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.hidden = True
        self._last_result = None

    async def __local_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @cc.command(hidden=True)
    async def update_lib(self, ctx):
        await self.bot.pull_remotes()
        await ctx.send("""Instigated Pull Request. To update;
```pip install -U git+https://github.com/Modelmat/discord.py@rewrite#egg=discord.py[voice]```""")

    @cc.group(hidden=True)
    async def vps(self, ctx):
        """Commands for controlling the VPS"""
        pass

    @vps.command()
    async def stop(self, ctx):
        """Stops the VPS Server"""
        system('heroku ps:scale worker=0 --app discord-kern-bot')
        await ctx.success("Stopping VPS instance")

    @vps.command()
    async def start(self, ctx):
        """Starts the VPS server"""
        system('heroku ps:scale worker=1 --app discord-kern-bot')
        await ctx.success("Starting VPS instance")

    @cc.command(hidden=True, aliases=['restart'])
    async def rebirth(self, ctx):
        """Owner of this bot only command; Restart the bot"""
        await ctx.success("", f"Restarting @ {datetime.utcnow().strftime('%H:%M:%S')}", rqst_by=False)
        await self.bot.suicide("Restarting")
        execl(executable, 'python "' + "".join(argv) + '"')

    @cc.command(hidden=True, aliases=['shutdown', 'die'])
    async def suicide(self, ctx):
        """Owner of this bot only command; Shutdown the bot"""
        await ctx.success("", f"Shutting Down @ {datetime.utcnow().strftime('%H:%M:%S')}", rqst_by=False)
        await self.bot.suicide()

    @cc.command(hidden=True)
    async def leave(self, ctx):
        """Leaves this server"""
        await ctx.success("Leaving `{}`".format(ctx.guild))
        await ctx.guild.leave()

    @cc.command(hidden=True)
    async def servers(self, ctx):
        """Sends the servers this bot is in"""
        await ctx.send("My servers:```ini\n[{}]```".format(", ".join([guild.name for guild in self.bot.guilds])))

    @cc.command(hidden=True)
    async def announce(self, ctx, *, message):
        """Announces a message to everyone"""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    break
        await ctx.send("Success.")

    @cc.command(hidden=True, name="eval", aliases=['exec'])
    async def k_eval(self, ctx, *, body: str):
        """Evaluates code"""

        def cleanup_code(content):
            if content.startswith('```') and content.endswith('```'):
                return '\n'.join(content.split('\n')[1:-1])

            # remove `foo`
            return content.strip('` \n')

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()

        if ctx.invoked_with == "exec":
            body = "return " + body.split("\n")[0]

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        loading_emoji = self.bot.get_emoji(395834326450831370)

        try:
            exec(to_compile, env)

        except asyncio.TimeoutError as e:
            await ctx.add_reaction("👎")
            return await ctx.error("Function timed out.", e.__class__.__name__ + ':')

        except Exception as e:
            await ctx.add_reaction("👎")
            return await ctx.error(f'```\n{e}\n```', e.__class__.__name__ + ':')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                await ctx.add_reaction(loading_emoji)
                ret = await func()

        except Exception as e:
            await ctx.error(f'```py\n{e}\n```', e.__class__.__name__ + ":")
            await ctx.add_reaction("👎")
            await ctx.del_reaction(loading_emoji)

        else:
            value = stdout.getvalue()
            await ctx.add_reaction("👍")
            await ctx.del_reaction(loading_emoji)
            if ret is None:
                if value:
                    await ctx.send(f"**Input:**\n```py\n{body}\n```\n**Returns:**\n```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"**Input:**\n```py\n{body}\n```\n**Returns:**\n```py\n{value}{ret}\n```")

def setup(bot):
    bot.add_cog(Owner(bot))
