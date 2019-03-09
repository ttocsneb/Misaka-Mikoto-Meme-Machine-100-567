import logging
import asyncio

from discord.ext import commands

from ..config import config
from .. import util, db

class Stats:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)
    
    @staticmethod
    def say(messages, string):
        if string:
            messages.append(str(string))
    
    async def send(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)
    
    def check_permissions(self, ctx: commands.Context):
        author = ctx.message.author

        if author.id in config.config.mods:
            return True
        
        try:
            return author.server_permissions.manage_server
        except:
            return False

    def get_server(self, ctx: commands.Context, message=None) -> db.Server:

        server = db.getDbFromCtx(ctx)
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server.")
        return server

    def get_user(self, ctx: commands.Context, session) -> db.server.User:
        return db.Server.getUser(session, ctx.message.author.id)
    
    def calc_stat_value(self, session, user: db.server.User, stat: db.server.Stat):
        """
        Calculate the stat values for the given stat, and all stats that depend on this stat.

        raises util.BadEquation error on a bad equation
        """
        # 1. check if there are dice rolls
        util.dice.logging_enabled = True
        eq = util.calculator.parse_args(stat.value, session, user)
        # 2. calculate equation
        value = util.calculator.parse_equation(eq, session, user)
        util.dice.logging_enabled = False

        dice = util.dice.rolled_dice

        if len(dice) is 0:
            # 3. set calc to calculated equation
            stat.calc = value
        else:
            # 5. set calc to None
            stat.calc = None
        
        # 6. check if there are dependent stats
        from string import Formatter
        name = stat.name.lower()
        for st in user.stats:
            params = [fn for _, fn, _, _ in Formatter().parse(st.value.lower()) if fn is not None]
            if name in params:
                self.calc_stat_value(session, user, st)

    @commands.group(pass_context=True, aliases=['st', 'stat'])
    async def stats(self, ctx: commands.Context):
        """
        Manage your stats

        Stats can be used with equations and rolls.

        They are usefull because you can have a universal equation with special
        parameter for each person using it.

        The most common use for stats in terms of rpgs is the level stat. Some
        equations need to modified by the user's level, and it gets annoying to
        enter your level each time you use the equation.  Stats allow you to
        enter a variable once, and have it automatically applied every time you
        use an equation
        """

        if ctx.invoked_subcommand is not None:
            return
        
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        
        session = server.createSession()
        user = self.get_user(ctx, session)

        stats = user.stats

        if len(stats) is 0:
            self.say(message, "You don't have any stats yet")
            await self.send(message)
            return
        
        self.say(message, "```python")

        max_name_width = list()
        max_val_width = list()

        default = "?"

        for stat in stats:
            max_name_width.append(len(stat.name))
            if stat.calc is not None:
                val = int(stat.calc) if int(stat.calc) == stat.calc else stat.calc
                max_val_width.append(len(str(val)))
            else:
                max_val_width.append(len(default))

        max_name_width = max(max_name_width)
        max_val_width = max(max_val_width)

        for stat in stats:
            if stat.calc is not None:
                val = int(stat.calc) if int(stat.calc) == stat.calc else stat.calc
            else:
                val = default
            
            if str(val) != stat.value:
                self.say(message, "{0:>{wid_n}}  {1:<{wid_v}} = {2}".format(
                    stat.name, val, stat.value, wid_n=max_name_width, wid_v=max_val_width
                ))
            else:
                self.say(message, "{0:>{wid_n}}  {1}".format(
                    stat.name, val, wid_n=max_name_width
                ))

        self.say(message, "```")

        await self.send(message)
    
    @stats.command(pass_context=True, usage="<stat> value", aliases=['add', 'edit'], name='set')
    async def st_set(self, ctx: commands.Context, stat: str, *, value: str):
        """
        Set a stat

        A stat can be any number, even an equation!
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()

        user = self.get_user(ctx, session)

        stats = user.getStats()

        stats[stat.lower()] = value.lower()

        stat = stats[stat.lower()]

        try:
            self.calc_stat_value(session, user, stat)
        except util.BadEquation as be:
            self.say(message, "Invalid equation: " + str(be))
            await self.send(message)
            session.rollback()
            return
        session.commit()

        self.say(message, "Set **{}** stat to".format(stat.name))
        self.say(message, "```python")
        if stat.calc is not None:
            calc = int(stat.calc) if int(stat.calc) == stat.calc else stat.calc
            if str(calc) == stat.value:
                val = str(calc)
            else:
                val = "{}  ({})".format(calc, stat.value)
        else:
            val = stat.value
        self.say(message, val)
        self.say(message, "```")

        await self.send(message)

    @stats.command(pass_context=True, usage="<stat>", aliases=['rm'], name='del')
    async def st_del(self, ctx: commands.Context, stat: str):
        """
        Delete a stat
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()

        user = self.get_user(ctx, session)

        stats = user.getStats()

        try:
            del stats[stat.lower()]
            session.commit()

            self.say(message, "Deleted your **{}** stat".format(stat.lower()))
        except KeyError:
            self.say(message, "Could not find **{}**".format(stat.lower()))
        
        await self.send(message)
