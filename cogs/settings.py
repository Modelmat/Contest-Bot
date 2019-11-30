from discord.ext import commands

import custom_classes as cc


class Settings(commands.Cog):
    """Sets and gets the settings for the bot"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    @commands.guild_only()
    @cc.group()
    async def get(self, ctx):
        """Commands related to determining the value of settings."""
        pass

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @cc.group(name="set")
    async def _set(self, ctx):
        """Commands related to the changing of settings."""
        pass

    @_set.command(name="prefix")
    async def set_prefix(self, ctx, *, prefix: str):
        """Set the bot's prefix for this server"""
        prefix = prefix.strip("'").strip('"')
        self.bot.prefixes_cache.pop(ctx.guild.id, None)
        await ctx.send("Adding prefix `{}`".format(
            await self.bot.database.add_prefix(ctx, prefix)))

    @_set.command()
    async def remove_prefix(self, ctx, *, prefix: str):
        """Remove the bot's prefix"""
        try:
            self.bot.prefixes_cache.get(ctx.guild.id, []).remove(prefix)
        except ValueError:
            return await ctx.error(f"Prefix `{prefix}` does not exist.",
                                   "")

        await self.bot.database.remove_prefix(ctx, prefix)
        await ctx.success(f"Prefix {prefix} successfully removed.")

    @get.command(name="prefixes")
    async def get_prefixes(self, ctx):
        """Get the bot's prefix for this server"""
        prefixes = self.bot.prefixes_cache.get(ctx.guild.id) or [ctx.clean_prefix()]
        await ctx.send("Prefixes for {}: ```{}```".format(
            ctx.guild.name, ", ".join(prefixes)))

    @_set.command(name="max_rating")
    async def set_max_rating(self, ctx, max_rating: int):
        await self.bot.database.set_max_rating(ctx, max_rating)
        await ctx.success("Max rating set to {}".format(max_rating))

    @get.command(name="max_rating")
    async def get_max_rating(self, ctx):
        max_rating = await self.bot.database.get_max_rating(ctx) or 10
        await ctx.send(f"Max rating is {max_rating}")
        return max_rating


def setup(bot):
    bot.add_cog(Settings(bot))
