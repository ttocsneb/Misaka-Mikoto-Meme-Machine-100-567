import logging
import asyncio

import discord
from discord.ext import commands

from .. import config, db
from ..config import config as conf

from . import misc, dice, items


class Bot:

    def __init__(self):
        self.bot = None
        self._logger = logging.getLogger(__name__)

    def get_prefix(self, bot, message: discord.Message):
        """
        Dynamically get a server's prefix
        """
        if message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]:
            prefixes = [s.prefix for s in db.db.database.values()]
            return prefixes + [commands.when_mentioned(bot, message)]

        sid = message.server.id
        try:
            server = db.db.database[sid]
        except KeyError:
            self._logger.info("Setting up database for new server: %s", sid)
            server = db.schemas.Server(sid, conf.config.prefix)
            db.db.database[sid] = server
            db.db.dump(sid)

        # Add the optional @ mention
        return [server.prefix, commands.when_mentioned(bot, message)]

    def setup(self):
        self.bot = commands.Bot(
            command_prefix=self.get_prefix,
            description=conf.config.description,
            pm_help=None
        )

        self.bot.add_cog(misc.Misc(self.bot))
        self.bot.add_cog(dice.Dice(self.bot))
        self.bot.add_cog(items.Items(self.bot))


    def run(self):
        if self.bot is None:
            self.setup()
        
        @self.bot.event
        async def on_ready():
            self._logger.info("I'm online!")

            game_str = "with dice!"
            self._logger.info("Setting my activity to %s", game_str)
            game = discord.Game(name=game_str)

            await self.bot.change_presence(status=discord.Status.online, game=game)

            self._logger.info("______________")


        self.bot.run(conf.config.token)

    def stop(self):
        if self.bot is None:
            return
        # Nothing can be done right now to stop the bot from outside the server :/
