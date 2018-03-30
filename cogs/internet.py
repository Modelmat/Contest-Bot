import random
from asyncio import sleep, TimeoutError as a_TimeoutError
from collections import OrderedDict
from datetime import datetime
from random import sample

import async_timeout
from bs4 import BeautifulSoup
from tabulate import tabulate
import aiogoogletrans

from fuzzyfinder.main import fuzzyfinder

import discord
from discord.ext import commands
import custom_classes as cc

PROTOCOLS = ['ssh', 'smb', 'smtp', 'ftp', 'imap', 'http', 'https', 'pop', 'htcpcp', 'telnet', 'tcp', 'ipoac']
TABLE_HEADERS = ["PORT", "PROTOCOL", "SECURE"]


def gen_data():
    fake_ports = sorted([random.randint(0, 65535) for i in range(random.randint(0, 10))])
    protocols = random.sample(PROTOCOLS, len(fake_ports))
    secured = [random.choice(["'false'", 'true']) for i in fake_ports]
    table_data = list(zip(fake_ports, protocols, secured))
    table = str(tabulate(table_data, TABLE_HEADERS, tablefmt="rst"))
    open_data = [data[0:3] for data in table_data if data[2]]
    open_ports = ", ".join([str(data[0]) for data in open_data if data[2] == "true"])
    return table_data, table, open_ports, open_data


class Internet:
    """Web functions (that make requests)"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.translator = aiogoogletrans.Translator()

    async def get_youtube_videos(self, page_url, cutoff_length=80, result_length=5):
        results = OrderedDict()
        vids = []

        with async_timeout.timeout(10):
            async with self.bot.session.get(page_url) as resp:
                soup = BeautifulSoup((await resp.read()).decode('utf-8'), "lxml")

        for link in soup.find_all('a', href=True):
            url = link.get('href', "")
            title = link.get('title', "")
            if "/watch" in url and title and not title.startswith('https') and "googleads" not in url:
                if not url.startswith('https://www.youtube.com'):
                    url = 'https://www.youtube.com' + url
                results[title] = url

        for vid, url in results.items():
            vid = vid.replace("[", "⦋").replace("]", "⦌")
            if vid.isupper():
                vid = vid[:int(cutoff_length * 3 / 4)] + "..."
            if len(vid) > cutoff_length:
                vid = vid[:cutoff_length] + "..."
            vids.append(f"[{vid}]({url})")

        return vids[:result_length]

    @commands.group(invoke_without_command=True)
    async def youtube(self, ctx, *, keyword: str):
        """Searches YouTube for a video
        ```{0}youtube <keyword>```"""
        url = f"https://www.youtube.com/results?search_query={keyword}&sp=EgIQAQ%253D%253D"
        vids = await self.get_youtube_videos(url)

        if len(keyword) > 40:
            keyword = keyword[:40] + "..."

        results = "\n".join(vids)
        await ctx.neutral(results, f"YouTube Search Results for: {keyword}")

    @youtube.command()
    async def trending(self, ctx, num_results=5):
        """Gets current trending videos
        ```{0}youtube tending [num_results: 5]```"""
        url = "https://www.youtube.com/feed/trending"
        vids = await self.get_youtube_videos(url, 77, num_results)
        results = "\n".join([f"{index+1}) {title}" for index, title in enumerate(vids)])
        await ctx.neutral(results, "YouTube Trending")

    @youtube.command()
    async def channel(self, ctx, channel, num_videos=5):
        """Get a channel's latest 5 videos
        ```{0}youtube channel [num_videos: 5]```"""
        pass

    @youtube.command()
    async def playlist(self, ctx, playlist, num_videos=5):
        """Get a playlist's 1st 5 videos
        ```{0}youtube playlist [num_videos: 5]```"""
        pass

    async def get_demotivators(self):
        demotivators = {}
        url = "https://despair.com/collections/posters"
        with async_timeout.timeout(10):
            async with self.bot.session.get(url) as resp:
                soup = BeautifulSoup((await resp.read()).decode('utf-8'), "lxml")

        for div_el in soup.find_all('div', {'class': 'column'}):
            a_el = div_el.a
            if a_el and a_el.div:
                title = a_el['title']
                img_url = "http:" + a_el.div.img['data-src']
                product_url = "http://despair.com" + a_el['href']
                quote = a_el.find('span', {'class': 'price'}).p.string
                demotivators[title.lower()] = {
                    'title': title,
                    'img_url': img_url,
                    'quote': quote,
                    'product_url': product_url
                }

        return demotivators

    @commands.command()
    async def demotivate(self, ctx, *, search_term):
        """Provides an embed with a demotivating quote & poster
        ```{0}demotivate <search_term>```"""
        async with ctx.typing():
            search_term = search_term.lower()
            demotivators = await self.get_demotivators()
            dem = demotivators.get(search_term)
            if dem is None:
                sugs = list(fuzzyfinder(search_term, demotivators.keys()))
                if not sugs:
                    return await ctx.error("No demotivator found.")
                dem = demotivators.get(sugs[0])
            e = discord.Embed(colour=discord.Colour.green(), description=dem['quote'])
            e.set_author(
                name=dem['title'],
                url=dem['product_url'],
                icon_url="http://cdn.shopify.com/s/files/1/0535/6917/t/29/assets/favicon.png?3483196325227810892",
            )
            e.set_footer(
                text="Data from Despair, Inc • Requested by: {}".format(ctx.message.author),
                icon_url=ctx.message.author.avatar_url)
            e.timestamp = datetime.utcnow()
            e.set_image(url=dem['img_url'])
            await ctx.send(embed=e)

    @commands.command(hidden=True)
    async def hack(self, ctx, *, url: cc.Url):
        """Starts a fake hacking instance on a specified URL.
        ```{0}hack <url>```"""
        loading, th, hu, te, on = self.bot.get_emojis(395834326450831370, 396890900783038499, 396890900158218242,
                                                      396890900753547266, 396890900426653697)
        table_data, table, open_ports, open_data = gen_data()

        msg = await ctx.send(f"Looking for open ports in <{url}>")
        content = msg.content
        await msg.edit(content=f"{content}\nPort: {th}{hu}{te}{on}{loading}")
        await sleep(10)

        if not open_ports:
            return await msg.edit(content=f":x: Port scan complete. No insecure ports found.")

        await msg.edit(
            content=
            f"Port scan complete. Scan report: ```ml\n{table}```\n{loading}Attempting to bruteforce insecure ports: ({open_ports})"
        )

        # Now do fake atatck on unsecure port (note, add a RFC 1149 reference)

    async def create_video(self, text):
        with async_timeout.timeout(20):
            async with self.bot.session.post(
                    url="http://talkobamato.me/synthesize.py", data={"input_text": text}) as resp:
                if resp.status >= 400:
                    raise self.bot.ResponseError(f"Obama responded with status {resp.status}")
                text = await resp.text()
                url = resp.url

        while '<source src="' not in text:
            with async_timeout.timeout(10):
                async with self.bot.session.get(url) as resp:
                    text = await resp.text()

        start = text.index('<source src="') + len('<source src="')
        end = text.index('" type="video/mp4">')
        link = "http://talkobamato.me/" + text[start:end]
        return link

    @commands.command()
    async def obama(self, ctx, *, text: str):
        """Makes obama speak.
        ```{0}obama <text>```"""
        if len(text) - len(ctx.prefix + "obama") > 280:
            return await ctx.send("A maximum character total of 280 is enforced. You sent: `{}` characters".format(
                len(text)))
        async with ctx.typing():
            link = await self.create_video(text)
            await ctx.send(link)

    @obama.error
    async def obama_error_handler(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, a_TimeoutError):
            await ctx.error("Obama server is not responding.", "Request Timed Out")
        else:  # includes bot response error
            await ctx.error(error)

    @commands.command(aliases=["translate_mixup", "googletrans"])
    async def translate(self, ctx, *, text):
        """Translates text to 5 random languages then back to English."""
        async with ctx.typing():
            prevlang = "en"
            for language in sample(list(aiogoogletrans.LANGUAGES), 5):
                if len(language) > 2:
                    continue
                text = (await self.translator.translate(text, dest=language, src=prevlang)).text
                prevlang = language
            result = await self.translator.translate(text, dest="en")
            await ctx.send("**End result:**\n```{}```".format(result.text))


def setup(bot):
    bot.add_cog(Internet(bot))
