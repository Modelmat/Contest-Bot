import asyncio
import traceback
from concurrent.futures import FIRST_COMPLETED
from datetime import datetime
from os import listdir
from signal import SIGTERM

import aioftp
import aiohttp
import async_timeout
import discord

import custom_classes as cc
from .data_classes import *
from .documentation import CreateDocumentation


class KernBot(commands.Bot):
    database = None
    latest_commit = None
    latest_message_time = None
    owner = None
    session = None

    demotivators = {}
    documentation = {}
    forecast = {}
    prefixes_cache = {}
    submission_channel = {}
    trivia_categories = {}
    weather = {}

    crypto = {"market_price": {}, "coins": []}

    def __init__(self, github_auth, log_channel, testing=False, debug=False,
                 *args, **kwargs):
        self.github_auth = aiohttp.BasicAuth(github_auth[0], github_auth[1])
        self.testing = testing

        self.launch_time = datetime.utcnow()
        self.ftp_client = aioftp.Client()

        super().__init__(*args, **kwargs)

        self.logs = self.get_channel(log_channel)
        self.database = cc.Database(self)

        extensions = sorted(
            [f"cogs.{ext}" for ext in listdir("cogs") if ".py" in ext]
        )

        try:
            self.loop.add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(self.close("SIGTERM Shutdown")))
        except NotImplementedError:
            pass

        self.loop.set_debug(debug)

        self.load_extensions(extensions)

    async def init(self):
        self.session = aiohttp.ClientSession()
        await self.ftp_client.connect("ftp.bom.gov.au", 21)
        await self.ftp_client.login()

        self.demotivators = await cc.get_demotivators(self.session)
        self.trivia_categories = await cc.get_trivia_categories(self.session)

        try:
            with async_timeout.timeout(30):
                async with self.session.get("https://min-api.cryptocompare.com/data/all/coinlist") as resp:
                    self.crypto['coins'] = {k.upper(): v for k, v in (await resp.json())['Data'].items()}
        except asyncio.TimeoutError:
            pass

        self.forecast = await cc.get_forecasts(self.ftp_client)
        # self.weather = await cc.get_weather(self.ftp_client)
        self.documentation = await CreateDocumentation().generate_documentation()

    def load_extensions(self, extensions):
        for extension in extensions:
            try:
                self.load_extension("cogs." + extension)
            except (discord.ClientException, ModuleNotFoundError, SyntaxError):
                print(f'Failed to load extension {extension}.')
                traceback.print_exc()
                quit()

    def add_cog(self, cog):
        error_coro = getattr(cog, f"_{cog.__class__.__name__}__error", None)
        if error_coro:
            cog.handled_errors = cc.Ast(error_coro).errors
        else:
            cog.handled_errors = []

        super().add_cog(cog)

    async def close(self, message="Shutting Down"):
        print(f"\n{message}\n")
        em = discord.Embed(title=f"{message} @ {datetime.utcnow().strftime('%H:%M:%S')}", colour=discord.Colour.red())
        em.timestamp = datetime.utcnow()
        await self.logs.send(embed=em)
        await self.database.pool.close()
        await self.session.close()
        await super().close()

    async def start(self, *args, **kwargs):
        await self.init()
        await super().start(*args, **kwargs)

    async def wait_for_any(self, events, checks, timeout=None):
        if not isinstance(checks, list):
            checks = [checks]
        if len(checks) == 1:
            checks *= len(events)
        mapped = zip(events, checks)
        to_wait = [self.wait_for(event, check=check) for event, check in mapped]
        done, _ = await asyncio.wait(to_wait, timeout=timeout, return_when=FIRST_COMPLETED)
        return done.pop().result()

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
