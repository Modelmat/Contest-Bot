import asyncio
from xml.etree.ElementTree import fromstring

import xmljson
from async_timeout import timeout
from bs4 import BeautifulSoup

XML_PARSER = xmljson.GData(dict_type=dict)
DEMOTIVATOR_URL = "https://despair.com/collections/posters"
TRIVIA_CATEGORIES_URL = "https://opentdb.com/api_category.php"
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


async def get_demotivators(session):
    demotivators = {}

    try:
        async with timeout(10):
            async with session.get(DEMOTIVATOR_URL) as r:
                soup = BeautifulSoup((await r.read()).decode("utf-8"), "lxml")
    except asyncio.TimeoutError:
        return {}

    for div in soup.find_all("div", {"class": "column"}):
        if div.a and div.a.div:
            a = div.a
            demotivators[a["title"].lower()] = {
                "title"      : a["title"],
                "img_url"    : f"http:{a.div.img['data-src']}",
                "product_url": f"https://despair.com{a['href']}",
                "quote"      : a.find("span", {"class": "price"}).p.string,
            }

    return demotivators


async def get_trivia_categories(session):
    trivia_categories = {}
    try:
        async with timeout(10):
            async with session.get(TRIVIA_CATEGORIES_URL) as r:
                categories = (await r.json())["trivia_categories"]
    except asyncio.TimeoutError:
        return {}

    for category in categories:
        trivia_categories[category["name"].lower()] = category["id"]

    return trivia_categories


async def download_ftp(client, link):
    async with timeout(10):
        async with client.download_stream(link) as stream:
            return b"".join([b async for b in stream.iter_by_block()])


async def get_forecasts(client):
    forecasts = {}

    async def get_forecast(link):
        json = XML_PARSER.data(fromstring(await download_ftp(client, link)))
        for location in json["product"]["forecast"]["area"]:
            if location["type"] == "location": # some are region codes
                forecasts[location["description"].lower()] = location

    for link in FORECAST_XML:
        await get_forecast(f"anon/gen/fwo/{link}")

    return forecasts

# async def get_weather(self, link):
#     # await asyncio.wait([self.get_weather("anon/gen/fwo/" + link) for link in WEATHER_XML])
#     data = XML_PARSER.data(fromstring((await self.download_xml(link)).getvalue()))
#     observations = data["product"]["observations"]
#     print(type(observations))
#     for station in observations:
#         print(station)
#         print(type(station))
#         break
#
#     return data

if __name__ == "__main__":
    import aioftp
    import aiohttp
    session = aiohttp.ClientSession()
    loop = asyncio.get_event_loop()
    client = aioftp.Client()
    # loop.run_until_complete(client.connect("ftp.bom.gov.au", 21))
    # loop.run_until_complete(client.login())

    # loop.run_until_complete(download_ftp(client, "/anon/gen/fwo/IDA00009.gif"))
    # loop.run_until_complete(get_forecast(client, "anon/gen/fwo/" + FORECAST_XML[0]))
    # loop.run_until_complete(get_forecasts(client))
    # print(loop.run_until_complete(get_trivia_categories(session)))
    # print(loop.run_until_complete(get_demotivators(session)))

