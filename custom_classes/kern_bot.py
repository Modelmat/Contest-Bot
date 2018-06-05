from datetime import datetime, timedelta
import asyncio
import sys
import traceback
from concurrent.futures import FIRST_COMPLETED
from io import BytesIO
from os import listdir
from os.path import isfile, join
from random import choice
from signal import SIGTERM
from xml.etree.ElementTree import fromstring
import aioftp
import aiohttp
import async_timeout
from bs4 import BeautifulSoup
import xmljson
from collections import defaultdict

import discord
from discord.ext import commands

from . import database as db
from .documentation import CreateDocumentation
from .data_classes import *
import custom_classes as cc

XML_PARSER = xmljson.GData(dict_type=dict)


class KernBot(commands.Bot):
    def __init__(self, github_auth, testing=False, debug=False, *args, **kwargs):
        self.github_auth = aiohttp.BasicAuth(github_auth[0], github_auth[1])
        self.testing = testing

        self.session = None
        self.owner = None
        self.latest_message_time = None
        self.latest_commit = None
        self.invite_url = None
        self.documentation = {}
        self.prefixes_cache = {}
        self.contest_channels = defaultdict(list)
        self.weather = {}
        self.demotivators = {}
        self.tasks = []
        self.trivia_categories = {}

        self.launch_time = datetime.utcnow()
        self.crypto = {"market_price": {}, "coins": []}

        super().__init__(*args, **kwargs)

        self.logs = self.get_channel(382780308610744331)

        self.exts = sorted(
            [extension for extension in [f.replace('.py', '') for f in listdir("cogs") if isfile(join("cogs", f))]])

        self.add_task(self.init())
        self.add_task(self.status_changer())
        self.add_task(self.get_demotivators())
        self.add_task(self.get_trivia_categories())

        try:
            self.loop.add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(self.suicide("SIGTERM Shutdown")))
        except NotImplementedError:
            pass

        self.database = db.Database(self)

        self.loop.set_debug(debug)

        self.load_extensions()

    async def init(self):
        self.session = aiohttp.ClientSession()
        try:
            with async_timeout.timeout(30):
                async with self.session.get("https://min-api.cryptocompare.com/data/all/coinlist") as resp:
                    self.crypto['coins'] = {k.upper(): v for k, v in (await resp.json())['Data'].items()}
        except asyncio.TimeoutError:
            pass

        await asyncio.wait([self.get_forecast("anon/gen/fwo/" + link) for link in FORECAST_XML])
        # await asyncio.wait([self.get_weather("anon/gen/fwo/" + link) for link in WEATHER_XML])
        self.documentation = await CreateDocumentation().generate_documentation()

    def load_extensions(self):
        for extension in self.exts:
            try:
                self.load_extension("cogs." + extension)
            except (discord.ClientException, ModuleNotFoundError, SyntaxError):
                print(f'Failed to load extension {extension}.')
                traceback.print_exc()
                quit()

    def add_task(self, function):
        self.tasks.append(self.loop.create_task(function))

    def add_cog(self, cog):
        error_coro = getattr(cog, f"_{cog.__class__.__name__}__error", None)
        if error_coro:
            cog.handled_errors = cc.Ast(error_coro).errors
        else:
            cog.handled_errors = []

        super().add_cog(cog)

    async def get_trivia_categories(self):
        try:
            with async_timeout.timeout(10):
                async with self.session.get("https://opentdb.com/api_category.php") as resp:
                    cats = (await resp.json())['trivia_categories']
        except asyncio.TimeoutError:
            return

        categories = {}
        for cat in cats:
            self.trivia_categories[cat['name'].lower()] = cat['id']

    async def get_demotivators(self):
        url = "https://despair.com/collections/posters"
        try:
            with async_timeout.timeout(10):
                async with self.session.get(url) as resp:
                    soup = BeautifulSoup((await resp.read()).decode('utf-8'), "lxml")
        except asyncio.TimeoutError:
            return

        for div_el in soup.find_all('div', {'class': 'column'}):
            a_el = div_el.a
            if a_el and a_el.div:
                title = a_el['title']
                img_url = "http:" + a_el.div.img['data-src']
                product_url = "http://despair.com" + a_el['href']
                quote = a_el.find('span', {'class': 'price'}).p.string
                self.demotivators[title.lower()] = {
                    'title'      : title,
                    'img_url'    : img_url,
                    'quote'      : quote,
                    'product_url': product_url
                }

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
        await self.session.close()
        await self.close()
        [task.cancel() for task in self.tasks]
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
            "for new contests."       : discord.ActivityType.watching,
            "{len(0.guilds)} servers.": discord.ActivityType.watching,
            "bot commands"            : discord.ActivityType.listening,
            "prefix {0.prefix}"       : discord.ActivityType.listening,
        }
        while not self.is_closed():
            message, activity_type = choice(list(activities.items()))
            activity = discord.Activity(name=message.format(self), type=activity_type)
            await self.change_presence(activity=activity)
            await asyncio.sleep(600)

    def get_emojis(self, *ids):
        emojis = []
        for e_id in ids:
            emojis.append(str(self.get_emoji(e_id)))
        return emojis

    async def update_dbots_server_count(self, dbl_token):
        url = f"https://discordbots.org/api/bots/{self.user.id}/stats"
        headers = {"Authorization": dbl_token}
        payload = {"server_count": len(self.guilds)}
        try:
            with async_timeout.timeout(10):
                await self.session.post(url, data=payload, headers=headers)
        except asyncio.TimeoutError:
            pass

    async def pull_remotes(self):
        try:
            with async_timeout.timeout(20):
                await self.session.get("https://api.backstroke.co/_88263c5ef4464e868bfd0323f9272d63")
        except asyncio.TimeoutError:
            pass
