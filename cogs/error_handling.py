import asyncio
import traceback

import discord
from discord.ext import commands

from custom_classes import KernBot


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

        elif isinstance(error, self.bot.ResponseError):
            await ctx.error(error, "Response Code > 400:")

        elif isinstance(error, commands.CommandOnCooldown):
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
                       type(error).__qualname__, ctx.author, ctx.guild, "".join(
                           traceback.format_exception(type(error), error, error.__traceback__))))


def setup(bot: commands.Bot):
    bot.add_cog(Errors(bot))
