from math import ceil

import discord


class Paginator:
    @classmethod
    async def init(cls, ctx, data: dict, max_fields: int = 5, base_embed: discord.Embed() = None):
        """data = {section_name: {title: value}}"""
        self = Paginator()
        self.message = None
        self.ctx = ctx
        self.embeds = {1: base_embed}
        self.max_fields = 5
        self.num_entries = data
        self.num_pages = ceil(sum([len(i) for i in data.values()]) / max_fields)

        await self.start_paginating(base_embed)

        return self

    async def start_paginating(self, base_embed):
        if base_embed:
            self.message = await self.ctx.send(embed=base_embed)
        else:
            # generate all embeds
            pass

    async def next_page(self):
        pass

    async def go_to_page(self, number):
        await self.message.edit(embed=self.embeds[number])
