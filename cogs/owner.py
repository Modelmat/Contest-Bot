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

ANNOUNCEMENT_FOOTER = "\n\n*This is an automated message sent by the bot's " \
                      "owner to inform you of a change in this bot which " \
                      "might cause issues in the operation of this bot in " \
                      "your server. Please feel free to send this " \
                      "announcement to the rest of your server*"


class Owner:
    """Owner only commands"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.hidden = True
        self._last_result = None

    async def __local_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @cc.command(hidden=True)
    async def restart(self, ctx):
        """Owner of this bot only command; Restart the bot"""
        await ctx.success("", f"Restarting @ {datetime.utcnow().strftime('%H:%M:%S')}", rqst_by=False)
        await self.bot.close("Restarting")
        execl(executable, 'python "' + "".join(argv) + '"')

    @cc.command(hidden=True, aliases=["die"])
    async def shutdown(self, ctx):
        """Owner of this bot only command; Shutdown the bot"""
        await ctx.success("", f"Shutting Down @ {datetime.utcnow().strftime('%H:%M:%S')}", rqst_by=False)
        await self.bot.close()

    @commands.guild_only()
    @cc.command(hidden=True)
    async def leave(self, ctx):
        """Leaves this server"""
        await ctx.success(f"Leaving `{ctx.guild.name}`")
        await ctx.guild.leave()

    @cc.command(hidden=True)
    async def announce(self, ctx, *, message):
        """Sends a message to all server owners"""
        for guild in self.bot.guilds:
            if "discord" in guild.name.lower():
                continue

            try:
                await guild.owner.send(message + ANNOUNCEMENT_FOOTER)
            except discord.Forbidden:
                pass

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
