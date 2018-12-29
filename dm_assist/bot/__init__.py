import logging
import asyncio

import discord
from discord.ext import commands

from .. import config
from ..config import config as conf

from . import misc, dice


class Bot:

    def __init__(self):
        self.bot = None
        self._logger = logging.getLogger(__name__)

    def setup(self):
        self.bot = commands.Bot(
            command_prefix=commands.when_mentioned_or(conf.config.prefix),
            description='An attempt to understand the confusing world around me.'
        )

        self.bot.add_cog(misc.Misc(self.bot))
        self.bot.add_cog(dice.Roleplay(self.bot))


    def run(self):
        if self.bot is None:
            self.setup()
        
        @self.bot.event
        async def on_ready():
            self._logger.info("I'm online!")

            game_str = "say {}help".format(conf.config.prefix)
            self._logger.info("Setting my activity to %s", game_str)
            game = discord.Game(name=game_str)

            await self.bot.change_presence(status=discord.Status.idle, game=game)

            self._logger.info("______________")


        self.bot.run(conf.config.token)

    def stop(self):
        if self.bot is None:
            return
        # Nothing can be done right now to stop the bot from outside the server :/
