from discord.ext import commands
from urllib.parse import urlparse

FORECAST_XML = [
    "IDN11060.xml",  # NSW/ACT
    "IDD10207.xml",  # NT
    "IDQ11295.xml",  # QLD
    "IDS10044.xml",  # SA
    "IDT16710.xml",  # TAS
    "IDV10753.xml",  # VIC
    "IDW14199.xml",  # WA
]

WEATHER_XML = [
    "IDN60920.xml",  # NSW/ACT
    "IDD60920.xml",  # NT
    "IDQ60920.xml",  # QLD
    "IDS60920.xml",  # SA
    "IDT60920.xml",  # TAS
    "IDV60920.xml",  # VIC
    "IDW60920.xml",  # WA
]


def chunks(s, n):
    for start in range(0, len(s), n):
        yield s[start:start + n]


def replace_backticks(content, do_it):
    if not do_it:
        return content
    if content.endswith("```") and (len(content.split("```")) - 1) % 2 == 1:
        content = "```" + content
    elif (len(content.split("```")) - 1) % 2 == 1:
        content += "```"
    elif len(content.split("```")) == 1:
        content += "```"
        content = "```" + content
    return content


class Url(commands.Converter):
    async def convert(self, ctx, argument):
        url = str(argument)
        if "://" not in url:
            url = "https://" + url
        if "." not in url:
            url += ".com"  # A bad assumption
        url = urlparse(url).geturl()

        return url


class CoinError(Exception):
    def __init__(self, message, coin, currency, limit):
        self.message = message
        self.coin = coin
        self.currency = currency
        self.limit = limit

    def __str__(self):
        return self.message

    def __repr__(self):
        return "CoinError({0.message}, {0.coin}, {0.currency}, {0.limit})".format(self)


class AlreadySubmitted(Exception):
    pass


class UpperConv(commands.Converter):
    async def convert(self, ctx, argument):
        return argument.upper()


class IntConv(commands.Converter):
    async def convert(self, ctx, argument):
        return int(argument)
