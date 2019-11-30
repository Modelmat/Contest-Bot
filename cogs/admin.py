import asyncio

import discord
from discord.ext import commands

import custom_classes as cc


class Admin(cc.KernCog):
    """Administration commands."""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.group(invoke_without_command=True)
    async def delete(self, ctx):
        """Deletes the last message sent by this bot"""
        async for message in ctx.channel.history(limit=100):
            if message.author == self.bot.user:
                await message.delete()
                await ctx.success("Message deleted.")
                return
        await ctx.error("No messages were found.")

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @delete.command()
    async def delete_clean(self, ctx, num_messages=200, other: bool = False):
        """Removes all messages for num_messages by this bot.
        Other specifies clearing everyone else's messages"""

        def is_me(m):
            return m.author == ctx.guild.me

        if other:
            deleted = await ctx.channel.purge(limit=num_messages)

        else:
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                deleted = await ctx.channel.purge(limit=num_messages,
                                                  check=is_me)
            else:
                deleted = await ctx.channel.purge(limit=num_messages,
                                                  check=is_me,
                                                  bulk=False)

        await ctx.success(f"`{len(deleted)}/{num_messages}`",
                          "Messages Cleaned", delete_after=10)

    @delete_clean.error
    async def delete_clean_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, discord.Forbidden):
            await ctx.error("\N{OCTAGONAL SIGN} Kern does not have the "
                            "required permissions to clean messages. Please"
                            'ensure Kern has the "Manage Messages" permission.')

    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @delete.command(name="id")
    async def delete_by_id(self, ctx, *message_ids: int):
        """Deletes message from list of ids/id"""
        for m_id in message_ids:
            msg = await ctx.get_message(m_id)
            if msg.author == self.bot.user:
                await msg.delete()
                await ctx.success("Message deleted")
                if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                    await asyncio.sleep(5)
                    await ctx.message.delete()
            else:
                await ctx.error("The bot did not send that message.")
                if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                    await asyncio.sleep(5)
                    await ctx.message.delete()

    @commands.guild_only()
    @commands.command(hidden=True)
    async def roles(self, ctx, *, member: discord.Member = None):
        """Shows the roles of the bot or member"""
        if member is None:
            roles = ", ".join([role.name.strip('@') for role in ctx.guild.roles])
            await ctx.success(f"```ini\n[{roles}]```", f"Roles for `{ctx.guild.name}`:")
        else:
            roles = ", ".join([role.name.strip('@') for role in member.roles])
            await ctx.success(f"```ini\n[{roles}]```", f"Roles for `{member.display_name}`:")

    @commands.guild_only()
    @commands.group(aliases=["permissions"])
    async def perms(self, ctx):
        """Permissions command group top (does nothing)"""
        pass

    @perms.command(name="user", aliases=["member"])
    async def perms_user(self, ctx, *, member: discord.Member):
        """Shows the permissions for this member."""
        perms = ctx.channel.permissions_for(member)
        pos = ", ".join([name for name, has in perms if has])
        neg = ", ".join([name for name, has in perms if not has])
        await ctx.send(f"Permissions for member `{member}`: ```ini\n[{pos}]``````css\n[{neg}]```")

    @commands.guild_only()
    @perms.command(name="role")
    async def perms_role(self, ctx, *, role: discord.Role):
        """Shows the permissions for a role"""
        d_pos = [name for name, has in ctx.guild.default_role.permissions if has]
        pos = ", ".join([name for name, has in role.permissions if name in d_pos or has])
        neg = ", ".join([name for name, has in role.permissions if name not in pos])
        await ctx.send(f"Permissions for role `{role}`: ```ini\n[{pos}]``````css\n[{neg}]```")


def setup(bot):
    bot.add_cog(Admin(bot))
