# pylint: disable-msg=C0413
import io
from inspect import Parameter
from datetime import datetime, timedelta

import async_timeout
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fuzzywuzzy import process

import discord
from discord.ext import commands

import custom_classes as cc

ICON_CODES = {
    1 : "☀",
    2 : "🌙",
    3 : "🌤",
    4 : "☁",
    6 : "🌁",
    8 : "🌧",
    9 : "💨",
    10: "🌫",
    11: "🌦",
    13: "🌧",
    14: "🌬",
    15: "❄",
    16: "🌨",
    17: "⛈",
    18: "🌧",
    19: "🌀",
}
ELEMENT_CODES = {
    "precipitation_range"    : "Precipitation: ",
    "air_temperature_minimum": "Min: ",
    "air_temperature_maximum": "Max: ",
}


def get_delta(time_period, limit):
    if time_period == "day":
        return timedelta(days=limit // 4)
    elif time_period == "hour":
        return timedelta(hours=limit // 4)
    elif time_period == "minute":
        return timedelta(minutes=limit // 4)
    return timedelta(minutes=10)


class Statistics:
    """Function related to statistics"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot

    async def get_data(self, time_period, coin, currency, limit):
        if self.bot.crypto['market_price'].get(coin) is None or \
                self.bot.crypto['market_price'][coin].get(currency) is None or \
                self.bot.crypto['market_price'][coin][currency].get(time_period) is None or \
                self.bot.crypto['market_price'][coin][currency][time_period]['timestamp'] < datetime.utcnow():
            with async_timeout.timeout(10):
                async with self.bot.session.get(
                        f"https://min-api.cryptocompare.com/data/histo{time_period}?fsym={coin}&tsym={currency}&limit={limit}"
                ) as resp:
                    js = await resp.json()
            if js['Response'] != "Success":
                raise cc.CoinError(js['Message'], coin, currency, limit)
            vals = js['Data']
            self.bot.crypto['market_price'][coin] = {
                currency: {
                    time_period: {
                        'high'     : [[-i, v['high']] for i, v in enumerate(vals)],
                        'low'      : [[-i, v['low']] for i, v in enumerate(vals)],
                        'timestamp':
                            datetime.utcnow() + get_delta(time_period, limit),
                    },
                },
            }
        return self.bot.crypto['market_price'][coin][currency][time_period]

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
        coin_data = self.bot.crypto['coins'][coin]
        graph_name = f"{coin}-{currency}-{limit}.png"
        graph = discord.File(buf, filename=graph_name)
        em = discord.Embed()
        em.set_author(
            name=coin_data['CoinName'],
            icon_url="https://www.cryptocompare.com" + coin_data['ImageUrl'])
        em.set_image(url=f"attachment://{graph_name}")
        return graph, em

    @cc.group(aliases=["crypto"])
    async def coin(self, ctx):
        """Provides information on cryptocurrencies
        This root command is not working."""
        # self.statistics [coin]
        if ctx.invoked_subcommand is None and ctx.subcommand_passed is None:
            raise commands.MissingRequiredArgument(
                param=Parameter(
                    name="currency", kind=Parameter.POSITIONAL_ONLY))

        elif ctx.invoked_subcommand is None and ctx.subcommand_passed:
            # do stuff with subcommand_passed
            return await ctx.error(
                f"Not implemented yet. Try `{ctx.prefix}coin day`.", "")

    @coin.command(name="list")
    async def coin_list(self, ctx):
        """Provides a list of possible coin names."""
        await ctx.neutral(
            """All coins names are in shorthand format.
For a full list of coins, the orange text underneath the coin names [here](https://www.cryptocompare.com/coins/list/USD/1) is the key.
Full name support is incoming.""",
            rqst_by=False,
            timestamp=False)

    @coin.command(name="day", aliases=["daily", "days"])
    async def coin_day(self, ctx, coin: cc.UpperConv, currency: cc.UpperConv = "USD", days: cc.IntConv = 30):
        """Creates a graph upon day information of a currencies."""
        async with ctx.typing():
            data = await self.get_data("day", coin, currency, days)
            print('done')
            graph, embed = self.gen_graph_embed(data, "Days", coin, currency,
                                                days)
            await ctx.send(file=graph, embed=embed)

    @coin.command(name="hour", aliases=["hourly", "hours"])
    async def coin_hour(self, ctx, coin: cc.UpperConv, currency: cc.UpperConv = "USD", hours: cc.IntConv = 6):
        """Creates a graph upon day information of a currencies."""
        async with ctx.typing():
            data = await self.get_data("hour", coin, currency, hours)
            graph, embed = self.gen_graph_embed(data, "Hours", coin, currency,
                                                hours)
            await ctx.send(file=graph, embed=embed)

    @coin.command(name="minute", aliases=["minutes"])
    async def coin_minute(self, ctx, coin: cc.UpperConv, currency: cc.UpperConv = "USD", minutes: cc.IntConv = 60):
        """Creates a graph upon day information of a currencies."""
        async with ctx.typing():
            data = await self.get_data("minute", coin, currency, minutes)
            graph, embed = self.gen_graph_embed(data, "Minutes", coin,
                                                currency, minutes)
            await ctx.send(file=graph, embed=embed)

    @coin_day.error
    @coin_minute.error
    @coin_hour.error
    async def coin_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, cc.CoinError):
            if "toSymbol" in str(error):
                await ctx.error(f"Currency `{error.currency}` does not exist.",
                                "")
            elif "symbol" in str(error):
                await ctx.error(f"Coin `{error.coin}` does not exist.", "")
            elif "limit param" in str(error):
                await ctx.error(f"Limit `{error.limit}` is not a number.", "")
            else:
                await ctx.error(f"Un unknown error has occurred.", "")
                await self.bot.logs.send(repr(error))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.error(str(error), "Missing Argument")

        else:
            await ctx.error(error)

    @cc.command(hidden=True)
    async def auweather(self, ctx, *, location):
        await ctx.send(await self.bot.get_weather())

    @cc.command(hidden=True)
    async def auforecast(self, ctx, *, location):
        # add weekdays, then RADAR images, and current temp etc.
        try:
            loc = self.bot.weather[location.lower()]
        except KeyError:
            em = discord.Embed(
                title="Unknown Location",
                description=f"🏙 `{location}` not found.")
            location = process.extractOne(location.lower(), self.bot.weather.keys())
            if location[1] > 75:
                em.add_field(name="Did you mean?", value=location[0])
            return await ctx.send(embed=em)

        place = loc['description']
        em = discord.Embed(title=place)
        em.set_footer(text="Source: Bureau of Meteorology")
        em.timestamp = datetime.strptime(
            loc["forecast-period"][0]["start-time-utc"], '%Y-%m-%dT%H:%M:%SZ')
        em.set_image(
            url="http://www.bom.gov.au/radar/IDR713.gif?20180318121051")

        for day in loc['forecast-period']:
            print(day)
            if isinstance(day["element"], dict):
                day["element"] = [day["element"]]
            name = datetime.strptime(day["end-time-utc"],
                                     "%Y-%m-%dT%H:%M:%SZ").strftime("%A")
            emoji_name = ICON_CODES[day["element"][0]["$t"]]
            print(day["element"][0]["$t"])
            print(day["text"][0]["$t"])
            value = day["text"][0]["$t"] + "\n**Chance of Rain:** " + day["text"][1]["$t"] + "\n"
            for el in day["element"]:
                if el["type"] == "forecast_icon_code":
                    continue
                value += f"**{ELEMENT_CODES[el['type']]}**{el['$t']}\n"

            em.add_field(name=emoji_name + name, value=value)

        await ctx.send(embed=em)
        # for item in loc['forecast-period']:
        #    print(item, end="\n\n\n")


def setup(bot):
    bot.add_cog(Statistics(bot))
