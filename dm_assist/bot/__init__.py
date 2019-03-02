import logging
import asyncio

import discord
from discord.ext import commands

from .. import config, db
from ..config import config as conf

from . import misc, dice, items, percentiles


class Bot:

    def __init__(self):
        self.bot = None
        self._logger = logging.getLogger(__name__)

    def get_prefix(self, bot, message: discord.Message):
        """
        Dynamically get a server's prefix
        """
        session = db.getServers().createSession()
        if message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]:
            user = session.query(db.conf.User).filter(db.conf.User.id==message.message.author.id).first()
            # Get all the prefixes from each server the user is a part of
            prefixes = [s.prefix for s in user.servers]
            return prefixes + [commands.when_mentioned(bot, message)]

        sid = message.server.id
        try:
            server = session.query(db.conf.Server).filter(db.conf.Server.id==sid).first()
        except KeyError:
            self._logger.info("Setting up database for new server: %s", sid)
            server = db.conf.Server(id=sid, prefix=conf.config.prefix)
            session.add(server)
            session.commit()
            db.getDb(sid)

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
        self.bot.add_cog(percentiles.Tables(self.bot))


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
