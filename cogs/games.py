import asyncio
import html
from datetime import datetime

import async_timeout
import discord
from discord.ext import commands

import custom_classes as cc


def rgb(r, g, b):
    return discord.Colour.from_rgb(r, g, b)


TRIVIA_URL = "https://opentdb.com/api.php?amount=5"
COLOURS = {'easy': rgb(255, 211, 0), 'medium': rgb(232, 97, 0), 'hard': rgb(255, 36, 0)}
EMOJIS = {1: '1\u20e3', 2: '2\u20e3', 3: '3\u20e3', 4: '4\u20e3'}


class Games:
    """Games"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    async def add_reactions(self, message, number):
        for index in range(number):
            await message.add_reaction(EMOJIS[index + 1])
        await message.add_reaction("⏹")

    async def get_trivia_results(self, category=None):
        results = []
        if category is None:
            url = TRIVIA_URL
        else:
            category_id = self.bot.trivia_categories.get(category.lower())
            if category_id is None:
                raise ValueError(f"Category `{category}` does not exist.")
            url = f"{TRIVIA_URL}&category={category_id}"

        with async_timeout.timeout(10):
            async with self.bot.session.get(url) as resp:
                raw_results = (await resp.json())['results']

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
    @cc.group(invoke_without_command=True)
    async def trivia(self, ctx: cc.KernContext, *, category: str = None):
        """Provides a trivia functionality. 5 questions. Can pass a category"""
        results = await self.get_trivia_results(category)
        corrects = []

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

            msg = await ctx.send(embed=e, delete_after=20)

            def same(reaction, member):
                return ctx.message.author == member and reaction.emoji in list(
                    EMOJIS.values()) + ["⏹"] and reaction.message.id == msg.id

            self.bot.loop.create_task(self.add_reactions(msg, len(answers)))

            try:
                reaction, _ = await self.bot.wait_for("reaction_add", check=same, timeout=15)
            except asyncio.TimeoutError:
                await ctx.error("You took too long to add an emoji.", "Timeout")
                break

            if str(reaction) == "⏹":
                return ctx.command.reset_cooldown(ctx)

            your_answer = answers[int(str(reaction)[0]) - 1]
            corrects.append((your_answer, result['correct_answer']))

        if not corrects:
            return

        des = "You answered:"
        correct_qs = 0
        for answer in corrects:
            if answer[0] == answer[1]:
                correct_qs += 1
                des += f"\n✅ {answer[0]}"
            else:
                des += f"\n❌{answer[0]} ➡ {answer[1]}"

        des += "\n\nFor a total score of {}/{}".format(correct_qs, len(corrects))

        await ctx.success(des, "Results")
        ctx.command.reset_cooldown(ctx)

    @trivia.command(name="list")
    async def trivia_list(self, ctx):
        """Gives a list of possible categories usable with the trivia command"""
        cat_string = ""
        for category in self.bot.trivia_categories:
            cat_string += f"{category.title()}\n"
        await ctx.neutral(cat_string, "Categories:")

    @trivia.error
    async def trivia_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, ValueError):
            await ctx.error(error, "Category Not Found")
            ctx.command.reset_cooldown(ctx)


def setup(bot: cc.KernBot):
    bot.add_cog(Games(bot))
