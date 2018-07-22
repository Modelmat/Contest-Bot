import asyncio
from collections import defaultdict

import discord

import custom_classes as cc


def _check(command_):
    return True


async def filter_commands(ctx, long_doc, check):
    cogs_dict = defaultdict(list)

    for command in set(ctx.bot.walk_commands()):
        if not command.hidden and await command.safe_can_run(ctx) and check(command):
            description = command.long_doc if long_doc else command.short_doc
            cogs_dict[command.cog_name or "No Category"].append({
                "name": command.qualified_name,
                "value": description or "No description.",
                "inline": False,
            })

    return {k: sorted(cogs_dict[k], key=lambda c: c["name"])
            for k in sorted(cogs_dict.keys())}


class Paginator:
    @classmethod
    async def from_commands(cls, ctx, base_embed=None, emojis=None, max_fields=5,
                            initial_page=1, long_doc=False, check=_check,
                            include_base_embed=True):
        if base_embed is None:
            base_embed = discord.Embed()

        if include_base_embed:
            embeds = [base_embed]
        else:
            embeds = []

        base_embed_dict = base_embed.to_dict()
        base_embed_dict.pop("fields", None)
        base_embed_dict.pop("description", None)
        total_commands = 0

        for cog, commands in (await filter_commands(ctx, long_doc, check)).items():
            for index, chunk in enumerate(cc.chunks(commands, max_fields)):
                embed = discord.Embed.from_data(base_embed_dict)
                embed.title = f"{base_embed.title} - {cog} ({index + 1})"

                for command in chunk:
                    total_commands += 1
                    embed.add_field(**command)

                embeds.append(embed)

        # noinspection PyProtectedMember
        getattr(base_embed, "_footer", {})["text"] = f"{total_commands} commands"
        return cls(ctx, embeds, emojis, initial_page)

    def __init__(self, ctx, embeds, emojis=None, initial_page=1):
        self.ctx = ctx
        self.bot = ctx.bot
        self.embeds = embeds
        self.message = None
        self.current_page = initial_page
        self.closed = False

        self.emojis = emojis or {
             "⏮": self.first,
             "◀": self.previous_page,
             "▶": self.next_page,
             "⏭": self.last,
             "🔢": self.number,
             "⏹": self.exit,
        }

    async def add_reactions(self):
        if len(self.embeds) == 1:
            self.closed = True
            return

        while not self.message:
            await asyncio.sleep(0.1)
        for emoji in self.emojis:
            await self.message.add_reaction(emoji)

    async def start_paginating(self):
        self.bot.loop.create_task(self.add_reactions())
        self.message = await self.ctx.send(embed=self.embeds[
                                           self.current_page - 1])

        def check(reaction, member):
            return str(reaction) in self.emojis and \
                   member == self.ctx.author and \
                   reaction.message.id == self.message.id

        while not self.closed:
            try:
                emoji, user = await self.bot.wait_for("reaction_add",
                                                      timeout=20,
                                                      check=check)

                if await self.emojis.get(str(emoji), self.null)():
                    break
            except asyncio.TimeoutError:
                break

            try:
                await self.message.remove_reaction(str(emoji), user)
            except discord.Forbidden:
                pass

        if not self.closed:
            try:
                await self.message.clear_reactions()
            except discord.Forbidden:
                await self.message.delete()
                await self.ctx.send(embed=self.embeds[self.current_page - 1])

        self.closed = True

    async def go_to_page(self, number):
        await self.message.edit(embed=self.embeds[number - 1])

    async def first(self):
        await self.go_to_page(1)

    async def previous_page(self):
        if self.current_page != 1:
            self.current_page -= 1
            await self.go_to_page(self.current_page)

    async def next_page(self):
        if self.current_page != len(self.embeds):
            self.current_page += 1
            await self.go_to_page(self.current_page)

    async def last(self):
        await self.go_to_page(len(self.embeds))

    async def number(self):
        temp_message = await self.ctx.send("Which page do you want to go to?")

        def check(message_):
            return message_.author == self.ctx.author

        message = await self.bot.wait_for("message", timeout=20, check=check)
        try:
            number = int(message.content)
        except ValueError:
            await self.ctx.error("That was not a number.",
                                 "Invalid Input",
                                 delete_after=5)
            await temp_message.delete()
            return

        if 0 < number <= len(self.embeds):
            await self.go_to_page(number)

        else:
            await self.ctx.error(f"Number is not in range `0 < n <= "
                                 f"{len(self.embeds)}`",
                                 "Invalid Input",
                                 delete_after=5)

        await temp_message.delete()

    async def exit(self):
        """This returns True so that the paginator knows to exit"""
        return True

    async def null(self):
        """This is a backup function when an emoji is not in the valid list"""
        pass
