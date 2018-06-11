import discord
from discord.ext import commands

import custom_classes as cc


async def manage_server_check(ctx):
    if await ctx.bot.is_owner(ctx.author):
        return True
    elif commands.has_permissions(manage_server=True):
        return True
    await ctx.error(
        "You do not have valid permissions to do this. (Manage Server Permission).",
        "Permissions Error")
    return False


class Settings:
    """Sets and gets the settings for the bot"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    @cc.group()
    async def get(self, ctx):
        """Commands related to determining the value of settings."""
        pass

    @commands.check(manage_server_check)
    @cc.group(name="set")
    async def _set(self, ctx):
        """Commands related to the changing of settings."""
        pass

    @get.command(name="channels")
    async def get_channels(self, ctx):
        """Get the channels used for the contests"""
        channels = await self.bot.database.get_contest_channels(ctx)
        if None not in channels:
            await ctx.send("​Channels for {}: <#{}> and <#{}>.".format(
                ctx.guild.name, *channels))
        else:
            await ctx.error("Channels are not set up", "Configuration Error:")

    @_set.command(name="channels")
    async def set_channels(self, ctx, *channels: discord.TextChannel):
        """Set the channels used for the contests"""
        if len(channels) == 1:
            channels *= 2
        elif len(channels) > 2:
            raise TypeError(
                "set channels takes 2 positional arguments but {} were given".
                format(len(channels)))
        receive_channel_id, output_channel_id = [
            channel.id for channel in channels
        ]
        await self.bot.database.set_contest_channels(ctx, receive_channel_id,
                                                     output_channel_id)
        await ctx.success("​Set channels to {} {}".format(
            *[channel.mention for channel in channels]))

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
            return await ctx.error(f"Prefix `{prefix}` is not in the list.",
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
