import discord
from discord.ext import commands

from .. import config
from ..config import config as conf

from . import misc, dice


class Bot:

    def __init__(self):
        self.bot = None

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

        self.bot.run(conf.config.token)

    def stop(self):
        if self.bot is None:
            return
        self.bot.logout()
        self.bot.close()