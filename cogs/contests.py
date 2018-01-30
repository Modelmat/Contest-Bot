import json
import traceback
import asyncio
import discord
from discord.ext import commands


class AlreadySubmitted(Exception):
    pass


async def manage_server_check(ctx):
    if commands.is_owner():
        return True
    elif commands.has_permissions(manage_server=True):
        return True
    await ctx.error("You do not have valid permissions to do this. (Manage Server Permission).", "Permissions Error")
    return False


class Contests:
    """Contest functions"""

    def __init__(self, bot):
        self.bot = bot
        self.bot_logs = self.bot.get_channel(bot.bot_logs_id)

    async def __error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, (TypeError, ValueError, AlreadySubmitted)):
            await ctx.error(error)
        else:
            print('Ignoring {} in command {}'.format(
                type(error).__qualname__, ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__)
            await ctx.error("An undhandled exception occurred. Don't worry, we know about it now. :thumbsup:")
            await ctx.error("```{}: {}```".format(type(error).__qualname__, error), title=f"Ignoring exception in command *{ctx.command}*:", channel=self.bot_logs, rqst_by=False)

    #pylint: disable-msg=too-many-arguments
    def generateEmbed(self, message_author: discord.User, title, description, image_url=None, colour=0x00ff00):
        """Generates a discord embed object off the given parameters

        Arguments:
            message_author {discord.User} -- Allows for the mention and user's logo to be added to the embed
            title {string} -- Title of the embed, the first heading
            description {string} -- The description of this object
            footer_text {string} -- The text shown in the footer, usually for commands that operate upon this

        Keyword Arguments:
            colour {hex} -- Used for the bar on the left's colour (default: {0x00ff00} -- green)
            image_url {string} -- The image shown at the bottom of the embed. (default: {""} -- no image)

        Returns:
            [discord.Embed] -- The embed object generated.
        """
        embed = discord.Embed(
            title=title, description=description, colour=colour)
        embed.set_author(
            name=f"Author: {message_author.display_name}", icon_url=message_author.avatar_url)
        if image_url is not None:
            embed.set_image(url=image_url)
        embed.set_thumbnail(url=message_author.avatar_url)
        return embed
    #pylint: enable-msg=too-many-arguments

    @commands.command()
    async def submit(self, ctx, *, args):
        """Submits an item into a contest. {}submit <title> | <description> | [imageURL]. Note the spaces"""
        input_split = tuple(args.split(" | "))
        if len(input_split) == 1:
            raise TypeError(
                "submit missing 2 required positional arguments: 'description' and 'image_url'")
        elif len(input_split) > 3:
            raise TypeError(
                "submit takes 3 positional arguments but {} were given".format(len(input_split)))
        title, description = input_split[0:2]
        if len(input_split) == 3:
            image_url = input_split[2]
        else:
            image_url = ""
        embed = self.generateEmbed(
            ctx.author, title, description, image_url, 0x00ff00)
        server_channels = await self.bot.database.get_contest_channels(ctx)
        if server_channels is None:
            return await ctx.error(f"No server channels are configured. Use {ctx.prefix}set channels to set your channels", title="Configuration Error:")
        if ctx.channel.id == server_channels[0]:
            channel = ctx.guild.get_channel(server_channels[1])
            if ctx.author.id in [sub['owner_id'] for sub in await self.bot.database.list_contest_submissions(ctx)]:
                raise AlreadySubmitted("You already have a contest submitted. To change your submission, delete it and resubmit.")
            submission_id = await self.bot.database.add_contest_submission(ctx, embed)
            footer_text = "Type `{0}vote {1} X` to vote for this. X is a number".format(
                ctx.prefix, submission_id)
            embed.set_footer(text=footer_text)
            await channel.send(embed=embed)
            if ctx.channel.id != server_channels[1]:
                await ctx.success(f"Submission sent in {channel.mention}")
        else:
            await ctx.error("Incorrect channel to submit in", delete_after=10)

    @commands.command(name="list", aliases=['list_submissions'])
    async def list_s(self, ctx):
        """Lists contest submissions for this server"""
        submissions = await self.bot.database.list_contest_submissions(ctx)
        if not submissions:
            return await ctx.error(f"The server `{ctx.guild.name}` has no contest submissions.", "No submissions")
        compiled = str()
        for index, submission in enumerate(submissions):
            embed = discord.Embed.from_data(json.loads(submission['embed']))
            s_id = submission['submission_id']
            author = ctx.guild.get_member(submission['owner_id'])
            rating = submission['rating'] or "NIL"
            compiled += f"{index + 1}). **{embed.title}** by {author.mention} [id: {s_id}]. **Rating:** `{rating}` points.\n"
        max_points = await self.bot.database.get_max_rating(ctx)
        await ctx.neutral(compiled, f"Submissions Leaderboard for {ctx.guild} [/{max_points}]")
        return [submission['submission_id'] for submission in submissions]

    @commands.command()
    async def vote(self, ctx, rating: int, submission_id: int):
        """Votes on a submission"""
        await self.bot.database.add_submission_rating(ctx, rating, submission_id)
        await ctx.success(f"Successfully voted on submission {submission_id}")

    @commands.command()
    async def remove(self, ctx):
        """Removes your submission"""
        await self.bot.database.remove_contest_submission(ctx)
        await ctx.success(f"{ctx.author.mention} Your submission was successfully removed.")

    @commands.check(manage_server_check)
    @commands.command()
    async def clear(self, ctx, submission_id: int):
        """Allows for users with manage_server perms to remove submissions that are deemed invalid"""
        await self.bot.database.clear_contest_submission(ctx, submission_id)
        await ctx.success(f"Submission with id {submission_id} successfully deleted.")

    @commands.check(manage_server_check)
    @commands.command()
    async def purge(self, ctx):
        """Purges all submissions"""
        length = len(await self.bot.database.list_contest_submissions(ctx))
        if length == 0:
            return await ctx.error(f"The server `{ctx.guild.name}` has no contest submission, so you cannot purge them.", "No submissions to purge:")
        await ctx.send("Are you sure? [Y/n] This deletes {} submissions".format(length))

        def check(m):
            return m.author == ctx.author
        try:
            message = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Time limit to reply exceeded.")
        if 'y' not in message.content.lower():
            return await ctx.send("Ok! Cancelling purge.")
        await self.bot.database.purge_contest_submissions(ctx)
        await ctx.success("{} submission(s) has been successfully purged.".format(length))


def setup(bot):
    bot.add_cog(Contests(bot))
