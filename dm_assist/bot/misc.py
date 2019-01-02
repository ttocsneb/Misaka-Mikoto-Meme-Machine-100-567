import logging

from .. import util

import discord
from discord.ext import commands

from dm_assist.config import config

from ..config import config
from ..db import db


class Misc:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)

    @commands.command(pass_context=True)
    async def headpat(self, ctx):
        '''Usage: don't.'''
        if ctx.message.author.id in config.config.mods:
            await self.bot.say(util.get_random_index(config.lines.shutdown))
            await self.bot.change_presence(status=discord.Status.offline)
            await self.bot.logout()
            await self.bot.close()
        else:
            await self.bot.say(util.get_random_index(config.lines.dumb))

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        '''Pings the bot to check that it hasn't died or something'''
        self._logger.info(ctx.message.author.id + " pinged")
        await self.bot.say("PONGU!")
    
    @commands.command(pass_context=True)
    async def prefix(self, ctx, prefix: str):
        """
        Change the prefix for this bot.

        Note You must have permission to manage the server to do this.
        """
        if ctx.message.author.server_permissions.manage_server:
            server = db.database[ctx.message.server.id]
            server.prefix = prefix[0]
            server.save()
            await self.bot.say("Successfully changed the prefix to `{}`".format(server.prefix))
        else:
            await self.bot.say("You don't have the permissions to change my prefix!")
