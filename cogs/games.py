import asyncio
import html
from datetime import datetime
from random import shuffle

import async_timeout

import discord
from discord.ext import commands
from custom_classes import KernBot


def rgb(r, g, b):
    return discord.Colour.from_rgb(r, g, b)


TRIVIA_URL = "https://opentdb.com/api.php?amount=5"
COLOURS = {'easy': rgb(255, 211, 0), 'medium': rgb(232, 97, 0), 'hard': rgb(255, 36, 0)}
EMOJIS = {1: '1\u20e3', 2: '2\u20e3', 3: '3\u20e3', 4: '4\u20e3'}


class Games:
    """Games"""
    def __init__(self, bot: KernBot):
        self.bot = bot

    async def trivia_categories(self, category=None):
        with async_timeout.timeout(10):
            async with self.bot.session.get("https://opentdb.com/api_category.php") as resp:
                cats = (await resp.json())['trivia_categories']

        categories = {}
        for cat in cats:
            categories[cat['name'].lower()] = cat['id']

        if not category:
            return categories

        c_id = categories.get(category.lower())
        if c_id is None:
            raise ValueError("Category `{}` does not exist.".format(category))
        return c_id

    async def get_trivia_results(self, category=None):
        results = []
        if category is None:
            url = TRIVIA_URL
        else:
            url = TRIVIA_URL + "&category=" + str(await self.trivia_categories(category))

        with async_timeout.timeout(10):
            async with self.bot.session.get(url) as resp:
                raw_results =  (await resp.json())['results']

        for r in raw_results:
            d = {}
            for k, v in r.items():
                if isinstance(v, list):
                    t = []
                    for i in v:
                        t.append(html.unescape(i))
                    d[k] = t
                else:
                    d[k] = html.unescape(v)
            results.append(d)

        return results

    @commands.cooldown(1, 30, commands.BucketType.channel)
    @commands.group(invoke_without_command=True)
    async def trivia(self, ctx: commands.Context, *, category: str = None):
        """Provides a trivia functionality. 5 questions. Can pass a category"""
        results = await self.get_trivia_results(category)
        corrects = {}

        for result in results:
            colour = COLOURS[result['difficulty']]
            category = result['category']
            question = "*{}*\n".format(result['question'])

            e = discord.Embed(title=category, description=question, colour=colour)
            e.set_footer(text="Data from Open Trivia Database", icon_url=ctx.author.avatar_url)
            e.timestamp = datetime.utcnow()

            answers = result['incorrect_answers'] + [result['correct_answer']]
            answers.sort(reverse=True)

            for index, question in enumerate(answers):
                e.description += "\n{} {}".format(EMOJIS[index + 1], question)

            msg = await ctx.send(embed=e, delete_after=15)

            for index in range(len(answers)):
                await msg.add_reaction(EMOJIS[index + 1])
            await msg.add_reaction("⏹")

            def same(reaction, member):
                return ctx.message.author == member and reaction.emoji in list(
                    EMOJIS.values()) + ["⏹"] and reaction.message.id == msg.id

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", check=same, timeout=15)
            except asyncio.TimeoutError:
                await ctx.error("You took too long to add an emoji.", "Timeout Error")
                break

            if str(reaction) == "⏹":
                ctx.command.reset_cooldown(ctx)
                return

            corrects[answers[int(str(reaction)[0]) - 1]] = result['correct_answer']

        if not corrects:
            return

        des = "You answered:"
        correct_qs = 0
        for yours, correct in corrects.items():
            if yours == correct:
                correct_qs += 1
                des += f"\n✅ {correct}"
            else:
                des += f"\n❌{yours} ➡ {correct}"
        des += "\n\nFor a total score of {}/{}".format(correct_qs, len(corrects))

        await ctx.success(des, "Results")
        ctx.command.reset_cooldown(ctx)

    @trivia.command(name="list")
    async def trivia_list(self, ctx):
        """Gives a list of possible categories usable with the trivia command"""
        cat_string = ""
        for category in await self.trivia_categories():
            cat_string += f"{category.title()}\n"
        await ctx.neutral(cat_string, "Categories:")

    @trivia.error
    async def trivia_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, ValueError):
            await ctx.error(error, "Category Not Found")
            ctx.command.reset_cooldown(ctx)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.error(f"🛑 This command can't be used for another {round(error.retry_after)}",
                            "Command on Cooldown")
        else:
            await ctx.error(error)
            ctx.command.reset_cooldown(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Games(bot))
