import logging

from .. import util

import discord
from discord.ext import commands

from ..config import config

from ..config import config
from .. import db


class Misc(commands.Cog):

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    @commands.command(hidden=True)
    async def headpat(self, ctx):
        '''Usage: don't.'''
        if ctx.message.author.id in config.config.mods:
            await ctx.channel.send(
                util.get_random_index(config.lines.shutdown)
            )
            await ctx.bot.change_presence(status=discord.Status.offline)
            await ctx.bot.logout()
            await ctx.bot.close()
        else:
            await ctx.channel.send(util.get_random_index(config.lines.dumb))

    @commands.command(hidden=True)
    async def ping(self, ctx):
        '''Pings the bot to check that it hasn't died or something'''
        self._logger.info(ctx.message.author.id + " pinged")
        await ctx.channel.send("PONGU!")

    @commands.command()
    async def prefix(self, ctx, prefix: str = None):
        """
        Change the prefix for this bot.

        Note You must have permission to manage the server to do this.
        """

        with db.database.session() as session:
            user = db.database.getUserFromCtx(session, ctx, commit=False)[0]

            if prefix is None:
                await ctx.channel.send("The prefix is `{}`".format(
                    user.active_server.prefix
                ))
                return

            try:
                if user.checkPermissions(ctx):
                    # Change the server prefix
                    user.active_server.prefix = prefix
                    session.commit()

                    await ctx.channel.send(
                        "Successfully changed the prefix to `{}`".format(
                            user.active_server.prefix))
                else:
                    await ctx.channel.send(
                        "You don't have the permissions to change my prefix!")
            except Exception:
                await ctx.channel.send(
                    "You don't have the permissions to change my prefix!")

    @commands.command()
    async def active(self, ctx):
        """
        Get your active server

        Get the name of the server that is currently
        selected for when you are direct messaging this bot.
        """
        servers = ctx.bot.guilds

        with db.database.session() as session:
            active_server = session.query(db.schema.User).get(
                ctx.message.author.id).active_server

            try:
                server = [
                    s for s in servers if int(s.id) == active_server.id
                ][0]

                await ctx.channel.send(
                    "**{}** is currently the active server".format(str(server))
                )
            except IndexError:
                await ctx.channel.send(
                    ("No server is currently active, use `activate` to"
                     " activate a server")
                )

    @commands.command()
    async def activate(self, ctx):
        """
        Activate the current server for PM use
        """

        if ctx.message.channel.type in [discord.ChannelType.private,
                                        discord.ChannelType.group]:
            await ctx.channel.send(
                ("You can't use that command here.  Use it in a server to"
                 " activate that server.")
            )
            return

        with db.database.session() as session:
            db.database.getUserFromCtx(session, ctx, update_server=True)

            await ctx.channel.send(
                "**{}** is now your active server.".format(
                    str(ctx.message.server)))

    @commands.command(aliases=['getdm', 'getgm'])
    async def getmod(self, ctx):
        """
        Get the current moderator role
        """

        with db.database.session() as session:
            db_server = db.database.getServerFromCtx(session, ctx)[0]
            server = ctx.message.guild
            if server is None:

                async def error():
                    await ctx.channel.send("You can't use this command here")

                if db_server is None:
                    await error()
                    return

                sid = str(db_server.id)

                try:
                    server = next(i for i in ctx.bot.guilds if i.id == sid)
                except StopIteration:
                    await error()
                    return

            try:
                mod_id = str(db_server.mod_id)
                role = next(role for role in server.roles
                            if role.id == mod_id)
                await ctx.channel.send(
                    "The current moderator role is **{}**".format(role.name))
            except StopIteration:
                await ctx.channel.send("There is no moderator set")

    @commands.command(usage="<role>",
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
            await ctx.channel.send("You can't use that command here.")
            return

        message = list()

        with db.database.session() as session:
            server = db.database.getServerFromCtx(session, ctx, commit=False)[0]
            user = db.database.getUserFromCtx(session, ctx, update_server=True,
                                            commit=False)[0]

            member = user.getMember(ctx)

            try:
                if member.guild_permissions.manage_guild or \
                        member.id in config.config.mods:

                    role_name = role_name.lower()
                    try:
                        role = next(role for role in ctx.messages.guild.roles
                                    if role_name in
                                    [role.name.lower(), role.mention.lower()])
                        server.mod_id = role.id

                        name = role.name
                        if role.mentionable:
                            name = role.mention

                        session.commit()

                        message.append("I made {} a moderator!".format(name))

                        await ctx.channel.send('\n'.join(message))
                        return
                    except StopIteration:
                        await ctx.channel.send(
                            "I couldn't find the role: {}".format(role_name))
                else:
                    await ctx.channel.send(
                        "You don't have the permissions to change the moderator")
            except Exception as err:
                import traceback
                self._logger.error(traceback.extract_tb(err.__traceback__))
                self._logger.error(err)
                await ctx.channel.send(
                    "You don't have the permissions to change the moderator")
