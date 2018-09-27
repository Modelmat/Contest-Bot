from os import environ
from random import sample

import async_timeout
import discord
from dotenv import load_dotenv

import custom_classes as cc

load_dotenv()
# Add: https://developer.oxforddictionaries.com/documentation#!/Search/get_search_source_lang, and check for no definitions (key error)


class Dictionary:
    """Provides dictionary functionality"""

    def __init__(self, bot: cc.KernBot):
        self.bot = bot
        self.dictionary_base_url = 'https://od-api.oxforddictionaries.com/api/v1/entries/en/{}'
        self.headers = {
            "Accept": "application/json",
            "app_id": environ["APP_ID"],
            "app_key": environ["APP_KEY"],
        }

    async def _result_parser(self, results: list):
        for lexicalEntry in results:
            for entry in lexicalEntry['entries']:
                for sense in entry['senses']:
                    keys = ['domains', 'definitions', 'examples']
                    yield [
                        lexicalEntry.get('lexicalCategory', ''),
                        *[sense.get(key, []) for key in keys]
                    ]
                    for subsense in sense.get('subsenses', []):
                        yield [
                            lexicalEntry.get('lexicalCategory', ''),
                            *[subsense.get(key, []) for key in keys]
                        ]

    async def _get_dic_request(self, url):
        with async_timeout.timeout(10):
            async with self.bot.session.get(
                    url, headers=self.headers) as response:
                if not response.status == 200:
                    return
                r_json = await response.json()
                return r_json['results']

    async def _word_not_found(self, term):
        results = await self._get_dic_request(
            "https://od-api.oxforddictionaries.com/api/v1/search/en?q={}&prefix=false&limit=5".
            format(term))
        similar_words = [match['word'] for match in results]
        similar_words = [
            "[{}](https://en.oxforddictionaries.com/definition/{})".format(
                term.capitalize(), "_".join(term.split()))
            for term in similar_words
        ]
        embed = discord.Embed(
            title="Error:",
            description="No matches found for `{}`.".format(term),
            colour=0xff0000)
        if bool(similar_words):
            embed.add_field(
                name="Did you mean?", value="\n".join(similar_words))
        return embed

    @cc.command(aliases=['synonyms'])
    async def synonym(self, ctx, *, term):
        """Return an embed of synonyms for the word passed.`"""
        async with ctx.typing():
            data = await self._get_dic_request(
                self.dictionary_base_url.format(term.lower()) + "/synonyms")
            if data is None:
                await ctx.send(embed=await self._word_not_found(term))
                return

            lexical_entries = data[0]['lexicalEntries']
            lexicon = dict()
            for entry in lexical_entries:
                lexicon[entry['lexicalCategory']] = [
                    synonym['text']
                    for synonym in entry['entries'][0]['senses'][0]['synonyms']
                ]
            embed = discord.Embed(title="Synonyms: {}".format(
                term.capitalize(),
                colour=0x00ff00,
                url='https://en.oxforddictionaries.com/thesaurus/{}'.format(
                    term)))
            for category, synonyms in lexicon.items():
                synonym_list = [
                    "[{}](https://en.oxforddictionaries.com/definition/{})".
                    format(term.capitalize(), "_".join(term.split()))
                    for term in synonyms[:5:]
                ]
                if len(synonym_list) > 1:
                    category += "s:"
                embed.add_field(
                    name=category.capitalize(), value="\n".join(synonym_list))
            embed.set_author(
                name="Antonyms for: {}".format(term),
                url='https://en.oxforddictionaries.com/definition/{}'.format(
                    "_".join(term.split())))

            await ctx.send(embed=embed)

    @cc.command(aliases=['antonyms'])
    async def antonym(self, ctx, *, term):
        """Return an embed of antonyms for the word passed."""
        async with ctx.typing():
            data = await self._get_dic_request(
                self.dictionary_base_url.format(term.lower()) + "/antonyms")
            if data is None:
                await ctx.send(embed=await self._word_not_found(term))
                return

            lexical_entries = data[0]['lexicalEntries']
            lexicon = dict()
            for entry in lexical_entries:
                lexicon[entry['lexicalCategory']] = [
                    antonym['text']
                    for antonym in entry['entries'][0]['senses'][0]['antonyms']
                ]
            embed = discord.Embed(title="antonyms: {}".format(
                term.capitalize(),
                colour=0x00ff00,
                url='https://en.oxforddictionaries.com/thesaurus/{}'.format(
                    term)))
            for category, antonyms in lexicon.items():
                antonym_list = [
                    "[{}](https://en.oxforddictionaries.com/definition/{})".
                    format(term.capitalize(), "_".join(term.split()))
                    for term in antonyms[:5:]
                ]
                if len(antonym_list) > 1:
                    category += "s:"
                embed.add_field(
                    name=category.capitalize(), value="\n".join(antonym_list))
            embed.set_author(
                name="Antonyms for: {}".format(term),
                url='https://en.oxforddictionaries.com/thesaurus/{}'.format(
                    "_".join(term.split())))

            await ctx.send(embed=embed)

    @cc.command(aliases=['meaning'])
    async def define(self, ctx, *, term):
        """Return an embed of definitions for the word passed. Includes image and more."""
        async with ctx.typing():
            data = await self._get_dic_request(
                self.dictionary_base_url.format(term.lower()))
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
                colour=0x00ff00,
                url='https://en.oxforddictionaries.com/definition/{}'.format(
                    "_".join(term.split())))
            for lexical_category, base_definitions in category_list.items():
                value = ""
                print(len(base_definitions), type(base_definitions))
                if len(base_definitions) > 5:
                    sample_size = 5
                else:
                    sample_size = len(base_definitions)
                definitions = sample(base_definitions, sample_size)
                for definition in base_definitions:
                    for domain in definition[1]:
                        value += "*{}*, ".format(domain)
                    mean = definition[2]
                    if mean:
                        value += definition[2][0].capitalize()
                    for example in definition[3]:
                        value += "\n*{}.*".format(example['text'].capitalize())
                    value += "\n\n"
                embed.add_field(
                    name=lexical_category, value=value, inline=False)

            ipa_string = str()
            for entry in results:
                if 'pronunciations' in entry:
                    for pronunciation in entry['pronunciations']:
                        ipa_string += "**{}:** {}\n".format(
                            entry['lexicalCategory'],
                            pronunciation['phoneticSpelling'])
                    embed.add_field(name="Pronunciation", value=ipa_string)

            if 'etymologies' in data[0]["lexicalEntries"][0]['entries'][0]:
                etymology = data[0]["lexicalEntries"][0]['entries'][0][
                    'etymologies'][0]
                embed.add_field(name="Word Origin:", value=etymology)

            if len(category_list) == 1 and next(
                    iter(category_list)) == "Residual":
                url_term = term.upper()
            else:
                url_term = term.capitalize()

            embed.set_author(
                name="Definition for: {}".format(url_term),
                url='https://en.oxforddictionaries.com/definition/{}'.format(
                    "_".join(term.split())))

            embed.set_footer(
                text="Results provided by the Oxford Dictionary",
                icon_url="https://en.oxforddictionaries.com/apple-touch-icon-180x180.png"
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Dictionary(bot))
