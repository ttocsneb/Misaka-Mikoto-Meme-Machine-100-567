import logging

from .. import util

import discord
from discord.ext import commands

from ..config import config

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
    async def prefix(self, ctx, prefix: str = None):
        """
        Change the prefix for this bot.

        Note You must have permission to manage the server to do this.
        """

        with db.database.session() as session:
            user = db.database.getUserFromCtx(session, ctx, commit=False)[0]

            if prefix is None:
                await self.bot.say("The prefix is `{}`".format(user.active_server.prefix))
                return

            try:
                if user.checkPermissions(ctx):
                    # Change the server prefix
                    user.active_server.prefix = prefix
                    session.commit()

                    await self.bot.say(
                        "Successfully changed the prefix to `{}`".format(
                            user.active_server.prefix))
                else:
                    await self.bot.say(
                        "You don't have the permissions to change my prefix!")
            except:
                await self.bot.say(
                    "You don't have the permissions to change my prefix!")

    @commands.command(pass_context=True)
    async def active(self, ctx):
        """
        Get your active server

        Get the name of the server that is currently
        selected for when you are direct messaging this bot.
        """
        bot = self.bot
        servers = bot.servers

        with db.database.session() as session:
            active_server = session.query(db.schema.User).get(
                ctx.message.author.id).active_server

            try:
                server = [s for s in servers if int(s.id) == active_server.id][0]

                await bot.say(
                    "**{}** is currently the active server".format(str(server)))
            except IndexError:
                await bot.say(
                    "No server is currently active, use `activate` to activate a server")

    @commands.command(pass_context=True)
    async def activate(self, ctx):
        """
        Activate the current server for PM use
        """

        if ctx.message.channel.type in [discord.ChannelType.private,
                                        discord.ChannelType.group]:
            await self.bot.say(
                "You can't use that command here.  Use it in a server to activate that server.")
            return

        with db.database.session() as session:
            db.database.getUserFromCtx(session, ctx, update_server=True)

            await self.bot.say(
                "**{}** is now your active server.".format(
                    str(ctx.message.server)))

    @commands.command(pass_context=True, aliases=['getdm', 'getgm'])
    async def getmod(self, ctx):
        """
        Get the current moderator role
        """

        with db.database.session() as session:
            db_server = db.database.getServerFromCtx(session, ctx)[0]
            server = ctx.message.server
            if server is None:

                async def error():
                    await self.bot.say("You can't use this command here")

                if db_server is None:
                    await error()
                    return

                sid = str(db_server.id)

                try:
                    server = next(i for i in self.bot.servers if i.id == sid)
                except StopIteration:
                    await error()
                    return

            try:
                mod_id = str(db_server.mod_id)
                role = next(role for role in server.roles
                            if role.id == mod_id)
                await self.bot.say(
                    "The current moderator role is **{}**".format(role.name))
            except StopIteration:
                await self.bot.say("There is no moderator set")

    @commands.command(pass_context=True, usage="<role>",
                      aliases=['setdm', 'setgm'])
    async def setmod(self, ctx, *, role_name: str):
        """
        Set a moderator role

        Most commonly used for the role of Game Master

        Anyone with the set role will have full access to all equations,
        tables, and stats on the server

        You must have permission to modify the server in order to change the
        moderator role
        """

        if ctx.message.channel.type in [discord.ChannelType.private,
                                        discord.ChannelType.group]:
            await self.bot.say("You can't use that command here.")
            return

        message = list()

        with db.database.session() as session:
            server = db.database.getServerFromCtx(session, ctx, commit=False)[0]
            user = db.database.getUserFromCtx(session, ctx, update_server=True,
                                            commit=False)[0]

            member = user.getMember(ctx)

            try:
                if member.server_permissions.manage_server or \
                        member.id in config.config.mods:

                    role_name = role_name.lower()
                    for role in ctx.message.server.roles:
                        if role_name in [role.name.lower(), role.mention.lower()]:
                            server.mod_id = role.id

                            name = role.name
                            if role.mentionable:
                                name = role.mention

                            session.commit()

                            if role.is_everyone:
                                message.append(
                                    "I don't recommend you to make everyone into a moderator, but you do you.\n")

                            message.append("I made {} a moderator!".format(name))

                            await self.bot.say('\n'.join(message))
                            return

                    await self.bot.say(
                        "I couldn't find the role: {}".format(role_name))
                else:
                    await self.bot.say(
                        "You don't have the permissions to change the moderator")
            except Exception as err:
                import traceback
                self._logger.error(traceback.extract_tb(err.__traceback__))
                self._logger.error(err)
                await self.bot.say(
                    "You don't have the permissions to change the moderator")
