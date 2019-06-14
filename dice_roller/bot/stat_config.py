import logging
import asyncio

from discord.ext import commands

from .. import util, db
from ..db import config_loader
from ..config import config


class Config:

    _logger = logging.getLogger(__name__)

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def say(messages, string):
        if string:
            messages.append(str(string))

    async def send(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)

    def get_server(self, ctx: commands.Context, session, message,
                   commit=True) -> db.schema.Server:

        server = db.database.getServerFromCtx(session, ctx, commit=commit)[0]
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server.")
        return server

    def get_user(self, ctx: commands.Context, session, message,
                 commit=True) -> db.schema.User:
        user = db.database.getUserFromCtx(session, ctx, commit=commit)[0]
        if user is None and message is not None:
            self.say(
                message,
                "You aren't registered with any server and can't " + 
                "register here!"
            )
        return user

    @staticmethod
    def get_loader(message=None):
        desc_loader = config_loader.ConfigDescLookupLoader()
        try:
            text = util.read_uri(config.config.stat_config)
            return desc_loader.load_json(text).data
        except:
            import traceback
            traceback.print_exc()
            if message is not None:
                message.append("I can't find the list")

    @classmethod
    def get_config(cls, name, message=None, loader=None):
        if not loader:
            loader = cls.get_loader(message)
            if not loader:
                return

        conf_loader = config_loader.ConfigLoader()
        try:
            text = util.read_uri(loader[name.lower()].uri)
            return conf_loader.load_json(text).data
        except:
            import traceback
            traceback.print_exc()
            if message is not None:
                cls.say(message, "I can't find the config `{}`".format(name))

    @commands.group(pass_context=True, aliases=['conf', 'c'])
    async def config(self, ctx: commands.Context):
        """
        Configure the server stats

        There are several configurations already made that can be used.
        You can see them by the command `config list`

        You can implement a configuration by running the command
        `config set <config>`

        If there is another configuration that isn't available, you can use
        either a url to the config, or paste in the config directly.
        """

    @config.command(aliases=['ls'], name='list')
    async def c_list(self):
        """
        List all configurations provided
        """
        message = list()

        desc = self.get_loader(message)
        if not desc:
            await self.send(message)
            return

        self.say(message, "```markdown")
        for name, item in desc.items():
            self.say(message, "#{}\n- {}".format(name, item.desc))
        self.say(message, "```")

        await self.send(message)

    @config.command(pass_context=True, usage="<name>", aliases=['get'],
                    name='info')
    async def c_info(self, ctx: commands.Context, name: str):
        """
        Get info about a configuration

        Prints information about what will be changed when you apply a
        configuration
        """

        message = list()

        config = self.get_config(name, message)
        if not config:
            await self.send(message)
            return

        stats = db.data_models.Stats(None, config.stats)
        from .stats import Stats

        self.say(message, "{} will add the following:".format(name))
        self.say(message, "Stats:")

        self.say(message, "```python")
        for group in stats.iter_groups():
            Stats.print_group(message, stats.get_group(group))
        self.say(message, "```")

        await self.send(message)
