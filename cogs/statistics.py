#pylint: disable-msg=C0413
import io
import async_timeout
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import discord
from discord.ext import commands

class UpperConv(commands.Converter):
    async def convert(self, ctx, argument):
        return argument.upper()

class IntConv(commands.Converter):
    async def convert(self, ctx, argument):
        return int(argument)

class Statistics:
    def __init__(self, bot):
        self.bot = bot

    async def get_data(self, time_period, coin, currency, limit):
        if self.bot.statistics['market_price'].get(coin) is None or \
           self.bot.statistics['market_price'].get(time_period) is None:
            with async_timeout.timeout(10):
                async with self.bot.session.get(f"https://min-api.cryptocompare.com/data/histo{time_period}?fsym={coin}&tsym={currency}&limit={limit}") as resp:
                    js = await resp.json()
            if js['Response'] != "Success":
                raise ValueError(js['Message'])
            vals = js['Data']
            self.bot.statistics['market_price'][coin] = {
                time_period: {
                    'high': [[-i, v['high']] for i, v in enumerate(vals)],
                    'low': [[-i, v['low']] for i, v in enumerate(vals)]
                },
            }
        return self.bot.statistics['market_price'][coin][time_period]

    def gen_graph_embed(self, data, unit, coin, currency, limit):
        plt.figure()
        plt.plot([x[0] for x in data['high']], [y[1] for y in data['high']])
        plt.plot([x[0] for x in data['low']], [y[1] for y in data['low']])
        plt.title(coin)
        plt.legend(['High', 'Low'], loc='upper left')
        plt.xlabel(unit)
        plt.ylabel(f"Worth: {currency}")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        coin_data = self.bot.statistics['coins'][coin]
        graph_name = f"{coin}-{currency}-{limit}.png"
        graph = discord.File(buf, filename=graph_name)
        em = discord.Embed()
        em.set_author(name=coin_data['CoinName'], icon_url="https://www.cryptocompare.com" + coin_data['ImageUrl'])
        em.set_image(url=f"attachment://{graph_name}")
        return graph, em

    @commands.group(aliases=["crypto"])
    async def coin(self, ctx):
        """Provides information on cryptocurrencies
        ```{0}coin <coin>```"""
        #self.statistics [coin]
        print(ctx.invoked_subcommand)
        print(ctx.subcommand_passed)

    @coin.command(name="day", aliases=["daily"])
    async def coin_day(self, ctx, coin: UpperConv, currency: UpperConv = "USD", days: IntConv = 30):
        """Creates a graph upon day information of a currencies.
        ```{0}coin day <coin> [currency] [days]```"""
        async with ctx.typing():
            data = await self.get_data("day", coin, currency, days)
            graph, embed = self.gen_graph_embed(data, "Days", coin, currency, days)
            await ctx.send(file=graph, embed=embed)

    @coin.command(name="hour", aliases=["hourly"])
    async def coin_hour(self, ctx, coin: UpperConv, currency: UpperConv = "USD", hours: IntConv = 6):
        """Creates a graph upon day information of a currencies.
        ```{0}coin day <coin> [currency] [hours]```"""
        async with ctx.typing():
            data = await self.get_data("hour", coin, currency, hours)
            graph, embed = self.gen_graph_embed(data, "Hours", coin, currency, hours)
            await ctx.send(file=graph, embed=embed)

    @coin.command(name="minute")
    async def coin_minute(self, ctx, coin: UpperConv, currency: UpperConv = "USD", minutes: IntConv = 60):
        """Creates a graph upon day information of a currencies.
        ```{0}coin day <coin> [currency] [minutes]```"""
        async with ctx.typing():
            data = await self.get_data("minute", coin, currency, minutes)
            graph, embed = self.gen_graph_embed(data, "Minutes", coin, currency, minutes)
            await ctx.send(file=graph, embed=embed)

    @coin.error
    async def coin_error_handler(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, ValueError):
            await ctx.error('', str(error))
            # There is no data for the symbol {coin}
            # There is no data for the toSymbol {currency}
            # limit param is not an integer
        else:
            raise error(str(error))


def setup(bot):
    bot.add_cog(Statistics(bot))