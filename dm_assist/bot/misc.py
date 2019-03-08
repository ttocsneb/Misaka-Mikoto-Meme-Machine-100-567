import logging

from .. import util

import discord
from discord.ext import commands

from dm_assist.config import config

from ..config import config
from .. import db


class Misc:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)

    @commands.command(pass_context=True, hidden=True)
    async def headpat(self, ctx):
        '''Usage: don't.'''
        if ctx.message.author.id in config.config.mods:
            await self.bot.say(util.get_random_index(config.lines.shutdown))
            await self.bot.change_presence(status=discord.Status.offline)
            await self.bot.logout()
            await self.bot.close()
        else:
            await self.bot.say(util.get_random_index(config.lines.dumb))

    @commands.command(pass_context=True, hidden=True)
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
        
        if ctx.message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]:
            await self.bot.say("You can't use that command here.")
            return

        try:
            if ctx.message.author.server_permissions.manage_server or \
                    ctx.message.author.id in config.config.mods:
                # Change the server prefix
                server = db.getDb(ctx.message.server.id)
                session = server.createSession()
                data = server.getData(session)
                data.prefix = prefix[0]
                session.commit()

                # Change the database prefix
                servers = db.getServers()
                session = servers.createSession()
                server = servers.getServer(session, ctx.message.server.id)
                server.prefix = prefix[0]
                session.commit()

                await self.bot.say("Successfully changed the prefix to `{}`".format(server.prefix))
            else:
                await self.bot.say("You don't have the permissions to change my prefix!")
        except:
            await self.bot.say("You don't have the permissions to change my prefix!")

    @commands.command(pass_context=True)
    async def active(self, ctx):
        """
        Get your active PM server

        Get the name of the server that is currently
        selected for when you are private messaging this bot.
        """
        bot = self.bot
        servers = bot.servers

        conf = db.getServers()
        session = conf.createSession()

        user = session.query(db.conf.User).filter(
            db.conf.User.id==ctx.message.author.id
        ).first()

        active_server = user.active_server_id

        try:
            server = [s for s in servers if s.id == str(active_server)][0]

            await bot.say("**{}** is currently the active server".format(str(server)))
        except IndexError:
            await bot.say("No server is currently active, use `activate` to activate a server")

    @commands.command(pass_context=True)
    async def activate(self, ctx):
        """
        Activate the current server for PM use
        """

        if ctx.message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]:
            await self.bot.say("You can't use that command here.  Use it in a server to activate that server.")
            return

        server = db.getDb(ctx.message.server.id)

        session = server.createSession()
        server.getUser(session, ctx.message.author.id)

        await self.bot.say("**{}** is now your active server.".format(str(ctx.message.server)))

