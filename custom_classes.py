from urllib.parse import urlparse
from io import BytesIO
from signal import SIGTERM
import sys
from os import listdir
from os.path import isfile, join
from datetime import datetime
import asyncio
from concurrent.futures import FIRST_COMPLETED
from random import choice
from xml.etree.ElementTree import fromstring
import async_timeout

import aiohttp
import aioftp

import discord
from discord.ext import commands
import xmljson

import database as db

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
XML_PARSER = xmljson.GData(dict_type=dict)


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


class KernBot(commands.Bot):
    def __init__(self, prefix, debug=False, *args, **kwargs):
        self.prefix = prefix

        self.session = None
        self.owner = None
        self.latest_message_time = None
        self.latest_commit = None
        self.prefixes_cache = {}

        self.launch_time = datetime.utcnow()
        self.crypto = {"market_price": {}, "coins": []}
        self.weather = {}

        super().__init__(*args, **kwargs)

        self.logs = self.get_channel(382780308610744331)

        self.exts = sorted(
            [extension for extension in [f.replace('.py', '') for f in listdir("cogs") if isfile(join("cogs", f))]])

        self.loop.create_task(self.init())

        self.status_task = self.loop.create_task(self.status_changer())

        try:
            self.loop.add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(self.suicide("SIGTERM Shutdown")))
        except NotImplementedError:
            pass

        self.database = db.Database(self)

        self.loop.set_debug(debug)

    async def init(self):
        self.session = aiohttp.ClientSession()
        with async_timeout.timeout(30):
            async with self.session.get("https://min-api.cryptocompare.com/data/all/coinlist") as resp:
                self.crypto['coins'] = {k.upper(): v for k, v in (await resp.json())['Data'].items()}

        await asyncio.wait([self.get_forecast("anon/gen/fwo/" + link) for link in FORECAST_XML])
        # await asyncio.wait([self.get_weather("anon/gen/fwo/" + link) for link in WEATHER_XML])

    async def download_xml(self, link):
        xml = BytesIO()
        with async_timeout.timeout(10):
            async with aioftp.ClientSession("ftp.bom.gov.au", 21) as client:
                async with client.download_stream(link) as stream:
                    async for block in stream.iter_by_block():
                        xml.write(block)
        return xml

    async def get_forecast(self, link):
        data = XML_PARSER.data(fromstring((await self.download_xml(link)).getvalue()))
        forecast = data["product"]["forecast"]["area"]
        for loc in forecast:
            if loc["type"] == "location":
                self.weather[loc["description"].lower()] = loc  # week

        self.weather['EXPIRY'] = datetime.strptime(data['product']['amoc']['expiry-time']['$t'], '%Y-%m-%dT%H:%M:%SZ')

        return data

    # async def get_weather(self, link):
    #     data = XML_PARSER.data(fromstring((await self.download_xml(link)).getvalue()))
    #     observations = data["product"]["observations"]
    #     print(type(observations))
    #     for station in observations:
    #         print(station)
    #         print(type(station))
    #         break

    #     return data

    async def suicide(self, message="Shutting Down"):
        print(f"\n{message}\n")
        em = discord.Embed(title=f"{message} @ {datetime.utcnow().strftime('%H:%M:%S')}", colour=discord.Colour.red())
        em.timestamp = datetime.utcnow()
        await self.logs.send(embed=em)
        await self.database.pool.close()
        self.session.close()
        await self.close()
        self.status_task.cancel()
        sys.exit(0)

    async def wait_for_any(self, events, checks, timeout=None):
        if not isinstance(checks, list):
            checks = [checks]
        if len(checks) == 1:
            checks *= len(events)
        mapped = zip(events, checks)
        to_wait = [self.wait_for(event, check=check) for event, check in mapped]
        done, _ = await asyncio.wait(to_wait, timeout=timeout, return_when=FIRST_COMPLETED)
        return done.pop().result()

    async def status_changer(self):
        await self.wait_until_ready()
        activities = {
            "for new contests.": discord.ActivityType.watching,
            "{len(0.guilds)} servers.": discord.ActivityType.watching,
            "bot commands": discord.ActivityType.listening,
            "prefix {0.prefix}": discord.ActivityType.listening,
        }
        while not self.is_closed():
            message, activity_type = choice(list(activities.items()))
            activity = discord.Activity(name=message.format(self), type=activity_type)
            await self.change_presence(activity=activity)
            await asyncio.sleep(60)

    def get_emojis(self, *ids):
        emojis = []
        for e_id in ids:
            emojis.append(str(self.get_emoji(e_id)))
        return emojis

    async def update_dbots_server_count(self, dbl_token):
        url = f"https://discordbots.org/api/bots/{self.user.id}/stats"
        headers = {"Authorization": dbl_token}
        payload = {"server_count": len(self.guilds)}
        with async_timeout.timeout(10):
            await self.session.post(url, data=payload, headers=headers)

    async def pull_remotes(self):
        with async_timeout.timeout(20):
            async with self.session.get("https://api.backstroke.co/_88263c5ef4464e868bfd0323f9272d63"):
                pass

    class ResponseError(Exception):
        pass


class CustomContext(commands.Context):
    def clean_prefix(self):
        user = self.bot.user
        prefix = self.prefix.replace(user.mention, '@' + user.name)
        return prefix

    async def add_reaction(self, reaction):
        try:
            await self.message.add_reaction(reaction)
        except discord.Forbidden:
            pass

    async def del_reaction(self, reaction):
        try:
            await self.message.remove_reaction(reaction, self.guild.me)
        except discord.Forbidden:
            pass

    async def __embed(self, title, description, colour, rqst_by, timestamp, channel, *args, **kwargs):
        e = discord.Embed(colour=colour)
        if title is not None:
            e.title = str(title)
        if description is not None:
            e.description = str(description)
        if rqst_by:
            e.set_footer(icon_url=self.message.author.avatar_url)
        if timestamp:
            e.timestamp = datetime.utcnow()
        if channel is None:
            return await self.send(embed=e, *args, **kwargs)
        return await channel.send(embed=e, *args, **kwargs)

    async def error(self, error, title="Error:", *args, channel: discord.TextChannel = None, **kwargs):
        if isinstance(error, Exception):
            if title == "Error:":
                title = error.__class__.__name__
            error = str(error)
        return await self.__embed(title, error, discord.Colour.red(), False, False, channel, *args, **kwargs)

    async def success(self,
                      success,
                      title="Success:",
                      *args,
                      channel: discord.TextChannel = None,
                      rqst_by=True,
                      timestamp=True,
                      **kwargs):
        return await self.__embed(title, success, discord.Colour.green(), rqst_by, timestamp, channel, *args, **kwargs)

    async def neutral(self,
                      text,
                      title=None,
                      *args,
                      channel: discord.TextChannel = None,
                      rqst_by=True,
                      timestamp=True,
                      **kwargs):
        return await self.__embed(title, text, discord.Colour.blurple(), rqst_by, timestamp, channel, *args, **kwargs)

    async def warning(self,
                      warning,
                      title=None,
                      *args,
                      channel: discord.TextChannel = None,
                      rqst_by=True,
                      timestamp=True,
                      **kwargs):
        return await self.__embed(title, warning, discord.Colour.blurple(), rqst_by, timestamp, channel, *args,
                                  **kwargs)

    async def send(self,
                   content: str = None,
                   *,
                   tts=False,
                   embed=None,
                   file=None,
                   files=None,
                   delete_after=None,
                   nonce=None):
        if content:
            contents = list(chunks(str(content), 1900))
            do_it = bool("```" in contents[-1])
            for cnt in contents[:-1]:
                cnt = replace_backticks(cnt, do_it)
                await super().send(cnt, delete_after=delete_after, tts=tts, nonce=nonce)
            contents[-1] = replace_backticks(contents[-1], do_it)
            return await super().send(
                contents[-1], tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce)
        return await super().send(
            content=content, tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce)


class Url(commands.Converter):
    async def convert(self, ctx, argument):
        url = str(argument)
        if "://" not in url:
            url = "https://" + url
        if "." not in url:
            url += (".com")  # A bad assumption
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


class UpperConv(commands.Converter):
    async def convert(self, ctx, argument):
        return argument.upper()


class IntConv(commands.Converter):
    async def convert(self, ctx, argument):
        return int(argument)
