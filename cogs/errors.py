import asyncio
import cgitb
import os
import traceback
import webbrowser

import aiofiles
import discord
from discord.ext import commands

import custom_classes as cc

cgitb.enable(format="raw")


class Errors:
    """Error Handling"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    async def on_command_error(self, ctx: cc.KernContext, error):
        error = getattr(error, "original", error)

        ignored = (commands.NotOwner, commands.CommandNotFound, discord.Forbidden)

        if isinstance(error, tuple(ignored)):
            return

        # This ignores any errors that are being handled at command or cog level
        command_ignored = ctx.command.handled_errors + ctx.cog.handled_errors

        if isinstance(error, tuple(command_ignored)):
            return

        elif isinstance(error, commands.CheckFailure):
            if isinstance(error, commands.NoPrivateMessage):
                await ctx.error("This command cannot be run in DMs",
                                "No DMs")

            elif await self.bot.is_owner(ctx.author):
                print(f"Owner reinvoked {ctx.command.qualified_name} "
                      f"due to a {error.__class__.__name__}: {error}")
                await ctx.reinvoke()

            elif isinstance(error, commands.MissingPermissions):
                await ctx.error(f"{error}", "Missing Required Permissions")

        elif isinstance(error, commands.DisabledCommand):
            if await self.bot.is_owner(ctx.author):
                print(f"Owner reinvoked {ctx.command.qualified_name} "
                      f"due to a {error.__class__.__name__}: {error}")
                await ctx.reinvoke()
            else:
                await ctx.error(f"`{ctx.command}` is disabled.",
                                "Command Disabled")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.error(f"Argument `{str(error.param).split(':')[0]}` is missing!",
                            "Missing Required Argument(s)")

        elif isinstance(error, commands.BadArgument):
            await ctx.error(str(error), "Bad Argument")

        elif isinstance(error, asyncio.TimeoutError):
            await ctx.error("The internet is gone?!?!?!?", "Timeout Error")

        elif isinstance(error, commands.CommandOnCooldown):
            if await self.bot.is_owner(ctx.author):
                print(f"Owner reinvoked {ctx.command.qualified_name} "
                      f"due to a {error.__class__.__name__}: {error}")
                await ctx.reinvoke()
            else:
                await ctx.error(f"🛑 This command can't be used for another {round(error.retry_after)} seconds",
                                "Command on Cooldown")

        else:
            # add more detailed debug
            await ctx.error(f"**This error is now known about 👍**\n```{error}```", type(error).__qualname__)

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
                async with aiofiles.open("error.html", mode="w", encoding="utf-8") as f:
                    await f.write(cgitb.html((type(error), error, error.__traceback__)))
                webbrowser.open_new_tab(f"file://{os.path.realpath('error.html')}")
                await asyncio.sleep(5)
                await self.bot.loop.run_in_executor(None, os.remove, "error.html")


def setup(bot: cc.KernBot):
    bot.add_cog(Errors(bot))
