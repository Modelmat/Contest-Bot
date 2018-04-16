from urllib.parse import urlparse
from io import BytesIO
from signal import SIGTERM
import sys
from os import listdir
from os.path import isfile, join
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import FIRST_COMPLETED
from random import choice
from xml.etree.ElementTree import fromstring
import async_timeout
from bs4 import BeautifulSoup
from math import ceil

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
    def __init__(self, testing=False, debug=False, *args, **kwargs):
        self.testing = testing

        self.session = None
        self.owner = None
        self.latest_message_time = None
        self.latest_commit = None
        self.obama_is_up = (datetime.utcnow() - timedelta(days=1), True)
        self.documentation = {}
        self.prefixes_cache = {}
        self.weather = {}

        self.launch_time = datetime.utcnow()
        self.crypto = {"market_price": {}, "coins": []}

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
        self.documentation = await CreateDocumentation().generate_documentation()

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


class CustomContext(commands.Context):
    async def paginator(self, num_entries, max_fields=5, base_embed=discord.Embed()):
        return await Paginator.init(self, num_entries, max_fields, base_embed)

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

    async def __embed(self, title, description, colour, rqst_by, timestamp, channel, footer, **kwargs):
        e = discord.Embed(colour=colour)
        if title is not None:
            e.title = str(title)
        if description is not None:
            e.description = str(description)
        if rqst_by:
            e.set_footer(icon_url=self.message.author.avatar_url)
        if footer:
            e.set_footer(text=footer)
        if timestamp:
            e.timestamp = datetime.utcnow()
        if channel is None:
            return await self.send(embed=e, **kwargs)
        return await channel.send(embed=e, **kwargs)

    async def error(self, error, title="Error:", channel: discord.TextChannel=None, footer=None, **kwargs):
        if isinstance(error, Exception):
            if title == "Error:":
                title = error.__class__.__name__
            error = str(error)
        return await self.__embed(title, error, discord.Colour.red(), False, False, channel, footer, **kwargs)

    async def success(self, success, title="Success:", channel: discord.TextChannel = None, rqst_by=True, timestamp=True, footer=None, **kwargs):
        return await self.__embed(title, success, discord.Colour.green(), rqst_by, timestamp, channel, footer, **kwargs)

    async def neutral(self, text, title=None, channel: discord.TextChannel=None, rqst_by=True, timestamp=True, footer=None, **kwargs):
        return await self.__embed(title, text, 0x36393E, rqst_by, timestamp, channel, footer, **kwargs)

    async def warning(self, warning, title=None, channel: discord.TextChannel=None, rqst_by=True, timestamp=True, footer=None, **kwargs):
        return await self.__embed(title, warning, discord.Colour.orange(), rqst_by, timestamp, channel, footer, **kwargs)

    async def upload(self, content):
        async with self.bot.session.post("http://mystb.in/documents", data=content) as r:
            link = "http://mystb.in/" + (await r.json())["key"] + ".py"
        return link

    async def send(self, content: str = None, *, tts=False, embed=None, file=None, files=None, delete_after=None, nonce=None):
        if content and len(content) > 1990:
            content = "**Output too long**:" + await self.upload(content)

        return await super().send(content=content, tts=tts, embed=embed, file=file, files=files, delete_after=delete_after, nonce=nonce)


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


class CreateDocumentation:
    def __init__(self):
        self.documentation = {}
        self.api = "http://rapptz.github.io/discord.py/docs/api.html"
        self.commands = "http://rapptz.github.io/discord.py/docs/ext/commands/api.html"

    @staticmethod
    def parse_ps(el):
        return "\n".join([ele.text for ele in el.dd.findAll("p", recursive=False)])

    @staticmethod
    def fake(*args):
        return []

    @staticmethod
    def get_name(el):
        return el.dt["id"].replace("discord.", "").replace("ext.commands.", "")

    def get_code_text(self, type, element):
        return {el.dt.code.text.lower(): self.parse_ps(el) for el in element.dd.findAll("dl", {"class": type})}

    def parse_class(self, el, url):
        if len(el.dt.text.split("(")) == 1:
            sp = "()"
        else:
            sp = "(" + el.dt.text.split("(")[1].strip("¶")
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name": name,
            "arguments": sp,
            "type": "class",
            "url": str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
            "attributes": self.get_code_text("attribute", el),
            "methods": self.get_code_text("method", el),
            "classmethods" : self.get_code_text("classmethod", el),
            "operations": {op.dt.code.text:op.dd.p.text for op in getattr(el.dd.find("div", {"class":"operations"}), "findAll", self.fake)("dl", {"class": "describe"})},
        }

    def parse_data(self, el, url):
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name": name,
            "arguments": "",
            "type": "data",
            "url": str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
        }

    def parse_exception(self, el, url):
        if len(el.dt.text.split("(")) == 1:
            sp = "()"
        else:
            sp = "(" + el.dt.text.split("(")[1].strip("¶")
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name": name,
            "arguments": sp,
            "type": "exception",
            "url": str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
            "attributes": self.get_code_text("attribute", el),
        }

    def parse_function(self, el, url):
        if len(el.dt.text.split("(")) == 1:
            sp = "()"
        else:
            sp = "(" + el.dt.text.split("(")[1].strip("¶")
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name": name,
            "arguments": sp,
            "type": "function",
            "url": str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
        }

    def parse_element(self, element, url):
        if "class" in element.get("class", []):
            self.parse_class(element, url)
        elif "data" in element.get("class", []):
            self.parse_data(element, url)
        elif "exception" in element.get("class", []):
            self.parse_exception(element, url)
        elif "function" in element.get("class", []):
            self.parse_function(element, url)

    def parse_soup(self, soup, url):
        for el in soup.findAll("div", {"class": "section"}):
            if el['id'] == "api-reference":
                continue
            for ele in el.findAll("dl"):
                self.parse_element(ele, url)
            for ele in el.findAll("div"):
                self.parse_element(ele, url)

    async def generate_documentation(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(self.api) as r:
                self.parse_soup(BeautifulSoup(await r.text(), "lxml"), r.url)
            async with s.get(self.commands) as r:
                self.parse_soup(BeautifulSoup(await r.text(), "lxml"), r.url)
        return self.documentation

class Paginator:
    @classmethod
    async def init(cls, ctx: CustomContext, data: dict, max_fields: int=5, base_embed: discord.Embed()=None):
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
            #generate all embeds
            pass

    async def next_page(self):
        pass

    async def go_to_page(self, number):
        await self.message.edit(embed=self.embeds[number])