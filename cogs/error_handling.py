import asyncio
import cgitb
import os
import traceback
import webbrowser

import aiofiles
import discord
from discord.ext import commands

from custom_classes import KernBot

cgitb.enable()

class Errors:
    """Error Handling"""
    def __init__(self, bot: KernBot):
        self.bot = bot

    async def on_command_error(self, ctx, error):
        # This prevents any commands already handled locally being run here.
        error = getattr(error, "original", error)
        if hasattr(ctx.command, 'on_error') or \
           hasattr(ctx.cog, f'_{ctx.cog.__class__.__name__}__error'):
            return

        ignored = (commands.NotOwner, commands.CheckFailure, commands.CommandNotFound, discord.Forbidden)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.error(f"Argument `{error.param}` is missing!", "Missing Required Argument(s)")

        elif isinstance(error, commands.BadArgument):
            await ctx.error(str(error), "Bad Argument")

        elif isinstance(error, asyncio.TimeoutError):
            await ctx.error("The internet is gone?!?!?!?", "Timeout Error")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.error(f"🛑 This command can't be used for another {round(error.retry_after)} seconds",
                            "Command on Cooldown")

        else:
            # add more detailed debug
            # await ctx.error(f"**This error is now known about 👍**\n```{error}```", type(error).__qualname__)

            await self.bot.logs.send("""
**Command:** {}
**Error:** {}
**Member: ** {}
**Guild: ** {}
```py\n{}```
            """.format(ctx.command,
                       type(error).__qualname__,
                       ctx.author,
                       ctx.guild, "".join(traceback.format_exception(type(error),
                                                                     error,
                                                                     error.__traceback__)
                                          )))
            traceback.print_exception(type(error), error, error.__traceback__)

            if self.bot.testing:
                async with aiofiles.open("error.html", mode="w") as f:
                    await f.write(cgitb.html((type(error), error, error.__traceback__)))
                webbrowser.open_new_tab(f"file://{os.path.realpath('error.html')}")
                await asyncio.sleep(5)
                await self.bot.loop.run_in_executor(None, os.remove, "error.html")


def setup(bot: commands.Bot):
    bot.add_cog(Errors(bot))
