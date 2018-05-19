from math import ceil
import custom_classes as cc
import discord
import asyncio


class Paginator:
    def __init__(self, ctx, data: dict, base_embed, **kwargs):
        self.ctx = ctx
        self.bot = ctx.bot
        self.base_embed = base_embed
        self.embeds = [self.base_embed]
        self.max_fields = kwargs.get("max_fields", 5)
        self.data = data

        self.EMOJIS = kwargs.pop("emojis", {"⏮": self.first,
                                            "◀": self.previous_page,
                                            "▶": self.next_page,
                                            "⏭": self.last,
                                            "🔢": self.get_number,
                                            "⏹": self.exit,
                                            })

        self.message: discord.Message = None
        self.num_pages = ceil(sum([len(i) for i in data.values()]) / self.max_fields)
        self.current_page = 0

        self.bot.loop.create_task(self.add_reactions())
        self.bot.loop.create_task(self.start_paginating(kwargs.get("page", 1)))

    async def first(self):
        await self.go_to_page(1)

    async def last(self):
        await self.go_to_page(len(self.embeds))

    async def add_reactions(self):
        while not self.message:
            await asyncio.sleep(0.1)
        for emoji in self.EMOJIS:
            await self.message.add_reaction(emoji)

    async def exit(self):
        raise asyncio.TimeoutError("exit")

    async def get_number(self):
        def check(msg):
            return msg.author == self.ctx.author
        message = await self.bot.wait_for("message", timeout=15, check=check)
        try:
            number = int(message.content)
        except ValueError:
            return await self.ctx.error(f"That was not a number!")

        await self.go_to_page(number)

    def generate_embed(self, title, index):
        embed = discord.Embed(title=f"{self.base_embed.title} - {title} ({index})")
        embed.colour = self.base_embed.colour
        embed._footer = self.base_embed._footer
        embed.timestamp = self.base_embed.timestamp

        return embed

    async def start_paginating(self, page):
        if self.embeds:
            self.message = await self.ctx.send(embed=self.embeds[0])
        else:
            self.message = await self.ctx.send("Loading Help...")

        for section, values in self.data.items():
            for i, chunked_values in enumerate(cc.chunks(values, self.max_fields)):
                embed = self.generate_embed(section, i + 1)
                for chunk in chunked_values:
                    embed.add_field(name=chunk['name'], value=chunk['value'], inline=False)
                self.embeds.append(embed)

        await self.go_to_page(page)
        await self.message.edit(content=None)
        await self.listen()

    async def listen(self):
        def check(react, user):
            return str(react) in self.EMOJIS and user == self.ctx.author and react.message.id == self.message.id

        try:
            while True:
                reaction, mem = await self.bot.wait_for("reaction_add", timeout=30, check=check)
                cur_emoji = str(reaction)
                await self.EMOJIS.get(cur_emoji)()
                try:
                    await self.message.remove_reaction(cur_emoji, mem)
                except discord.Forbidden:
                    pass

        except asyncio.TimeoutError:
            await self.message.delete()

    async def next_page(self):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.message.edit(embed=self.embeds[self.current_page])

    async def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            await self.message.edit(embed=self.embeds[self.current_page])

    async def go_to_page(self, number):
        if 0 < number < len(self.embeds) + 1:
            self.current_page = number - 1
            await self.message.edit(embed=self.embeds[number - 1])
        else:
            await self.ctx.error(f"Number not in range `0 < n < {len(self.embeds) + 1}`")
