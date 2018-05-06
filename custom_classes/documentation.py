import aiohttp
from bs4 import BeautifulSoup


class CreateDocumentation:
    def __init__(self):
        self.documentation = {}
        self.api = "http://discordpy.readthedocs.io/en/rewrite/api.html"
        self.commands = "http://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html"

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
            "name"        : name,
            "arguments"   : sp,
            "type"        : "class",
            "url"         : str(url) + el.dt.a["href"],
            "description" : self.parse_ps(el),
            "attributes"  : self.get_code_text("attribute", el),
            "methods"     : self.get_code_text("method", el),
            "classmethods": self.get_code_text("classmethod", el),
            "operations"  : {op.dt.code.text: op.dd.p.text for op in getattr(el.dd.find("div", {"class": "operations"}), "findAll", self.fake)("dl", {"class": "describe"})},
        }

    def parse_data(self, el, url):
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name"       : name,
            "arguments"  : "",
            "type"       : "data",
            "url"        : str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
        }

    def parse_exception(self, el, url):
        if len(el.dt.text.split("(")) == 1:
            sp = "()"
        else:
            sp = "(" + el.dt.text.split("(")[1].strip("¶")
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name"       : name,
            "arguments"  : sp,
            "type"       : "exception",
            "url"        : str(url) + el.dt.a["href"],
            "description": self.parse_ps(el),
            "attributes" : self.get_code_text("attribute", el),
        }

    def parse_function(self, el, url):
        if len(el.dt.text.split("(")) == 1:
            sp = "()"
        else:
            sp = "(" + el.dt.text.split("(")[1].strip("¶")
        name = self.get_name(el)
        self.documentation[name.lower()] = {
            "name"       : name,
            "arguments"  : sp,
            "type"       : "function",
            "url"        : str(url) + el.dt.a["href"],
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
                self.parse_soup(BeautifulSoup(await r.text(encoding="utf-8"), "lxml"), r.url)
            async with s.get(self.commands) as r:
                self.parse_soup(BeautifulSoup(await r.text(encoding="utf-8"), "lxml"), r.url)
        return self.documentation
