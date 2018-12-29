import logging

from .. import util

from discord.ext import commands

from dm_assist.config import config

from ..config import config


class Misc:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)

    @commands.command(pass_context=True)
    async def headpat(self, ctx):
        '''Usage: don't.'''
        if ctx.message.author.id in config.config.mods:
            await self.bot.say(util.get_random_index(config.lines.shutdown))
            self.bot.logout()
            self.bot.close()
            raise SystemExit
        else:
            await self.bot.say(util.get_random_index(config.lines.dumb))

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        '''Pings the bot to check that it hasn't died or something'''
        self._logger.info(ctx.message.author.id + " pinged")
        await self.bot.say("PONGU!")