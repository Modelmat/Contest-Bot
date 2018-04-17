import os
from random import randint
import ssl
import json
from socket import gaierror

import asyncio

import discord
from discord.ext import commands
import asyncpg

# https://magicstack.github.io/asyncpg/current/
# https://magicstack.github.io/asyncpg/current/api/index.html#prepared-statements

submissions_table = """CREATE TABLE IF NOT EXISTS submissions (
                       submission_id INT NOT NULL UNIQUE,
                       embed JSONB NOT NULL,
                       server_id BIGINT NOT NULL,
                       owner_id BIGINT NOT NULL,
                       rating INTEGER
                    )"""

servers_table = """
                CREATE TABLE IF NOT EXISTS servers (
                    server_id BIGINT NOT NULL UNIQUE,
                    receive_channel_id BIGINT,
                    vote_channel_id BIGINT,
                    prefixes VARCHAR[],
                    default_prefix_enabled BOOL DEFAULT FALSE,
                    max_rating INTEGER
                )
                """


class DudPool:
    _closed = True

    async def close(self):
        return


class Database:
    """Accessing database functions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ready = False
        try:
            self.dsn = os.environ["DATABASE_URL"]
        except KeyError:
            with open("client.secret", "r") as database_file:
                lines = [l.strip() for l in database_file]
                self.dsn = lines[6]

        self.pool = None
        if __name__ in '__main__':
            asyncio.get_event_loop().run_until_complete(self.init())
        else:
            bot.loop.create_task(self.init())

    async def init(self):
        ssl_object = ssl.create_default_context()
        ssl_object.check_hostname = False
        ssl_object.verify_mode = ssl.CERT_NONE
        try:
            self.pool = await asyncpg.create_pool(self.dsn, ssl=ssl_object)
        except (asyncpg.exceptions.InvalidCatalogNameError,
                asyncpg.exceptions.InvalidPasswordError,
                ValueError, TimeoutError, gaierror) as e:
            em = discord.Embed(title="Database failed to connect",
                               description="Prefixes will still work, most other db commands will not",
                               colour=discord.Colour.orange())
            print(e.__class__.__name__, str(e))
            self.pool = DudPool()
            while self.bot.logs is None:
                print('enter')
                await asyncio.sleep(1)
            await self.bot.logs.send(embed=em)
            return await self.bot.suicide("Database not connected")

        async with self.pool.acquire() as con:
            if not await con.fetch("SELECT relname FROM pg_class WHERE relname = 'servers'"):
                await con.execute(servers_table)
                print("Created servers table")
            if not await con.fetch("SELECT relname FROM pg_class WHERE relname = 'submissions'"):
                await con.execute(submissions_table)
                print("Created submissions table")

        self.ready = True

    async def generate_id(self):
        """Generate the ID needed to index the submissions"""
        async with self.pool.acquire() as con:
            submission_id_list = await con.fetchrow("SELECT submission_id FROM submissions")
        submission_id = "{:06}".format(randint(0, 999999))
        if not submission_id_list:
            return submission_id
        while submission_id in submission_id_list:
            submission_id = "{:06}".format(randint(0, 999999))
        return int(submission_id)

    async def set_contest_channels(self, ctx, *channels):
        sql = """INSERT INTO servers (server_id, receive_channel_id, vote_channel_id)
                 VALUES ($1, $2, $3)
                 ON CONFLICT (server_id) DO UPDATE
                    SET receive_channel_id = excluded.receive_channel_id,
                        vote_channel_id = excluded.vote_channel_id;"""
        async with self.pool.acquire() as con:
            await con.execute(sql, ctx.guild.id, *channels)

    async def get_contest_channels(self, ctx):
        sql = """SELECT receive_channel_id, vote_channel_id FROM servers
                 WHERE server_id = $1"""
        async with self.pool.acquire() as con:
            channels = await con.fetchrow(sql, ctx.guild.id)
        return channels

    async def add_prefix(self, ctx, prefix: str):
        sql = """UPDATE servers SET prefixes = array_append(prefixes, $1)
                    WHERE server_id = $2"""
        async with self.pool.acquire() as con:
            await con.execute(sql, prefix, ctx.guild.id)
        return prefix

    # async def enable_default_prefix(self, ctx):

    async def get_prefixes(self, ctx):
        async with self.pool.acquire() as con:
            prefixes = await con.fetchval("SELECT prefixes FROM servers WHERE server_id = $1", ctx.guild.id) or []
        return prefixes

    async def remove_prefix(self, ctx, prefix):
        async with self.pool.acquire() as con:
            await con.execute("UPDATE servers SET prefixes = array_remove(prefixes, $1) WHERE server_id = $2",
                              prefix, ctx.guild.id)

    async def add_contest_submission(self, ctx, embed: discord.Embed):
        sub_id = int(await self.generate_id())
        async with self.pool.acquire() as con:
            await con.execute("""INSERT INTO submissions (server_id, owner_id, submission_id, embed) VALUES ($1, $2, $3, $4)""",
                              ctx.guild.id, ctx.author.id, sub_id, json.dumps(embed.to_dict()))
        return sub_id

    async def get_contest_submission(self, submission_id: int):
        async with self.pool.acquire() as con:
            embed = await con.fetchval("SELECT embed FROM submissions WHERE submission_id = $1", submission_id)
        return discord.Embed.from_data(json.loads(embed))

    async def list_contest_submissions(self, ctx):
        async with self.pool.acquire() as con:
            submissions = await con.fetch("SELECT owner_id, submission_id, embed, rating FROM submissions WHERE server_id = $1 ORDER BY rating",
                                          ctx.guild.id)
        return submissions

    async def remove_contest_submission(self, ctx):
        async with self.pool.acquire() as con:
            await con.execute('DELETE FROM submissions WHERE owner_id = $1 AND server_id = $2', ctx.author.id, ctx.guild.id)

    async def clear_contest_submission(self, ctx, submission_id: int):
        async with self.pool.acquire() as con:
            await con.execute('DELETE FROM submissions WHERE submission_id = $1 AND server_id = $2', submission_id, ctx.guild.id)

    async def purge_contest_submissions(self, ctx):
        async with self.pool.acquire() as con:
            await con.execute("DELETE FROM submissions WHERE server_id = $1", ctx.guild.id)

    async def set_max_rating(self, ctx, max_rating: int):
        async with self.pool.acquire() as con:
            await con.execute("UPDATE servers SET max_rating = $1 WHERE server_id = $2", max_rating, ctx.guild.id)

    async def get_max_rating(self, ctx):
        async with self.pool.acquire() as con:
            return await con.fetchval("SELECT max_rating FROM servers WHERE server_id = $1", ctx.guild.id)

    async def add_submission_rating(self, ctx, rating: int, submission_id: int):
        async with self.pool.acquire() as con:
            max_rating = await self.get_max_rating(ctx) or 10
            if int(rating) > int(max_rating):
                raise ValueError("The rating was greater than the maximum rating allowed (defaults to 10).")
            await con.execute("UPDATE submissions SET rating = $1 WHERE submission_id = $2 AND server_id = $3", rating, submission_id, ctx.guild.id)

    async def get_submission_rating(self, ctx, submission_id: int):
        async with self.pool.acquire() as con:
            return await con.fetchval("SELECT rating FROM submissions WHERE submission_id = $1 AND server_id = $2", submission_id, ctx.guild.id)


if __name__ in '__main__':
    db_hi = Database('lol')
