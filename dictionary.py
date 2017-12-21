import asyncio
from os import environ
import re
import json

import aiohttp
import async_timeout
import discord
from discord.ext import commands

# Add: https://developer.oxforddictionaries.com/documentation#!/Search/get_search_source_lang, and check for no definitions (key error)

class Dictionary:
    """Provides dictionary functionality"""
    def __init__(self, bot):
        self.bot = bot
        self.bot_logs = self.bot.get_channel(382780308610744331)
        self.dictionary_base_URL = 'https://od-api.oxforddictionaries.com/api/v1/entries/en/{}'
        self.image_base_url = 'https://duckduckgo.com/'
        try:
            app_id = environ["APP_ID"]
            app_key = environ["APP_KEY"]
        except KeyError:
            with open("client_secret.txt", encoding="utf-8") as file:
                lines = [l.strip() for l in file]
                app_id = lines[1]
                app_key = lines[2]
        self.headers = {"Accept": "application/json",
                        "app_id": app_id,
                        "app_key": app_key}

    def validate(self, dictionary, key, return_value):
        if key in dictionary:
            return dictionary[key]
        else:
            return return_value

    async def _result_parser(self, results: list):
        for lexicalEntry in results:
            for entry in lexicalEntry['entries']:
                for sense in entry['senses']:
                    keys =  ['domains', 'definitions', 'examples']
                    yield [self.validate(lexicalEntry, 'lexicalCategory', ""), *[self.validate(sense, key, []) for key in keys]]
                    
                    for subsense in self.validate(sense, 'subsenses', []):
                        yield [self.validate(lexicalEntry, 'lexicalCategory', ""), *[self.validate(subsense, key, []) for key in keys]]

    async def _get_dic_request(self, url):
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(url, headers=self.headers) as response:
                    if not response.status == 200:
                        return
                    json = await response.json()
                    return json['results']

    async def _get_key(self, term):
        parameters = {'q': term}
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.post(self.image_base_url, data=parameters) as response:
                    text_response = await response.text()
            return re.search(r'vqd=(\d+)\&', text_response, re.M | re.I)

    async def _get_image(self, term):
        search_obj = await self._get_key(term)
        params = (
            ('l', 'wt-wt'),
            ('o', 'json'),
            ('q', term),
            ('vqd', search_obj.group(1)),
            ('f', ',,,'),
            ('p', '2')
        )
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(self.image_base_url + "i.js", params=params) as response:
                    json_response = json.loads(await response.text())
                    results = json_response['results']
            return results[0]['image']

    async def _word_not_found(self, term):
        results = await self._get_dic_request("https://od-api.oxforddictionaries.com/api/v1/search/en?q={}&prefix=false&limit=5".format(term))
        similar_words = [match['word'] for match in results]
        similar_words = ["[{}](https://en.oxforddictionaries.com/definition/{})".format(
            term.capitalize(), "_".join(term.split())) for term in similar_words]
        embed = discord.Embed(
            title="Error:", description="No matches found for `{}`.".format(term), colour=0xff0000)
        if bool(similar_words):
            embed.add_field(name="Did you mean?",
                            value="\n".join(similar_words))
        return embed

    @commands.command(aliases=['synonyms', 's'])
    async def synonym(self, ctx, *, term):
        """Return an embed of synonyms for the word passed."""
        await ctx.trigger_typing()
        data = await self._get_dic_request(self.dictionary_base_URL.format(term.lower()) + "/synonyms")
        if data is None:
            await ctx.send(embed=await self._word_not_found(term))
            return

        lexical_entries = data[0]['lexicalEntries']
        lexicon = dict()
        for entry in lexical_entries:
            lexicon[entry['lexicalCategory']] = [synonym['text']
                                                 for synonym in entry['entries'][0]['senses'][0]['synonyms']]
        embed = discord.Embed(title="Synonyms: {}".format(term.capitalize(
        ), colour=0x00ff00, url='https://en.oxforddictionaries.com/thesaurus/{}'.format(term)))
        for category, synonyms in lexicon.items():
            synonym_list = ["[{}](https://en.oxforddictionaries.com/definition/{})".format(
                term.capitalize(), "_".join(term.split())) for term in synonyms[:5:]]
            if len(synonym_list) > 1:
                category += "s:"
            embed.add_field(name=category.capitalize(),
                            value="\n".join(synonym_list))
        embed.set_author(name="Antonyms for: {}".format(
            term), url='https://en.oxforddictionaries.com/definition/{}'.format("_".join(term.split())))

        await ctx.send(embed=embed)

    @commands.command(aliases=['antonyms', 'a'])
    async def antonym(self, ctx, *, term):
        """Return an embed of antonyms for the word passed."""
        await ctx.trigger_typing()
        data = await self._get_dic_request(self.dictionary_base_URL.format(term.lower()) + "/antonyms")
        if data is None:
            await ctx.send(embed=await self._word_not_found(term))
            return

        lexical_entries = data[0]['lexicalEntries']
        lexicon = dict()
        for entry in lexical_entries:
            lexicon[entry['lexicalCategory']] = [antonym['text']
                                                 for antonym in entry['entries'][0]['senses'][0]['antonyms']]
        embed = discord.Embed(title="antonyms: {}".format(term.capitalize(
        ), colour=0x00ff00, url='https://en.oxforddictionaries.com/thesaurus/{}'.format(term)))
        for category, antonyms in lexicon.items():
            antonym_list = ["[{}](https://en.oxforddictionaries.com/definition/{})".format(
                term.capitalize(), "_".join(term.split())) for term in antonyms[:5:]]
            if len(antonym_list) > 1:
                category += "s:"
            embed.add_field(name=category.capitalize(),
                            value="\n".join(antonym_list))
        embed.set_author(name="Antonyms for: {}".format(
            term), url='https://en.oxforddictionaries.com/thesaurus/{}'.format("_".join(term.split())))

        await ctx.send(embed=embed)

    @commands.command(aliases=['define', 'd'])
    async def meaning(self, ctx, *, term):
        """Return an embed of definitions for the word passed. Includes image and more."""
        await ctx.trigger_typing()
        data = await self._get_dic_request(self.dictionary_base_URL.format(term.lower()))
        if data is None:
            await ctx.send(embed=await self._word_not_found(term))
            return

        results = data[0]['lexicalEntries']
        category_list = {}

        async for definition in self._result_parser(results):
            if definition[0] in category_list:
                category_list[definition[0]].append(definition)
            else:
                category_list[definition[0]] = [definition]

        embed = discord.Embed(
            colour=0x00ff00, url='https://en.oxforddictionaries.com/definition/{}'.format("_".join(term.split())))

        for lexical_category, definitions in category_list.items():
            value = ""
            for definition in definitions:
                for domain in definition[1]:
                    value += "*{}*, ".format(domain)
                value += definition[2][0].capitalize()
                for example in definition[3]:
                    value += "\n*{}.*".format(example['text'].capitalize())
                value += "\n\n"
            embed.add_field(name=lexical_category, value=value, inline=False)

        ipa_string = str()
        for entry in results:
            if 'pronunications' in entry:
                for pronunciation in entry['pronunciations']:
                    ipa_string += "**{}:** {}\n".format(
                        entry['lexicalCategory'], pronunciation['phoneticSpelling'])
                embed.add_field(name="Pronunciation", value=ipa_string)

        if 'etymologies' in data[0]["lexicalEntries"][0]['entries'][0]:
            etymology = data[0]["lexicalEntries"][0]['entries'][0]['etymologies'][0]
            embed.add_field(name="Word Origin:", value=etymology)

        if len(category_list) == 1 and next(iter(category_list)) == "Residual":
            url_term = term.upper()
        else:
            url_term = term.capitalize()

        embed.set_author(name="Definition for: {}".format(
            url_term), url='https://en.oxforddictionaries.com/definition/{}'.format("_".join(term.split())))

        embed.set_thumbnail(url=await self._get_image(term))
        embed.set_footer(text="Requested by: {} | Results provided by the Oxford Dictionary".format(
            ctx.message.author), icon_url='https://en.oxforddictionaries.com/apple-touch-icon-180x180.png')
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Dictionary(bot))
