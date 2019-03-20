import logging
import asyncio

from discord.ext import commands

from ..config import config
from .. import util, db

class Stats:

    _logger = logging.getLogger(__name__)

    def __init__(self, bot):
        self.bot = bot
    
    @staticmethod
    def say(messages, string):
        if string:
            messages.append(str(string))
    
    async def send(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)
    
    def get_server(self, ctx: commands.Context, message=None) -> db.Server:

        server = db.getDbFromCtx(ctx)
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server.")
        return server

    def get_user(self, ctx: commands.Context, session) -> db.server.User:
        return db.Server.getUser(session, ctx.message.author.id)
    
    @classmethod
    def update_stats_equations(cls, session, eq: db.server.Equation):
        """
        update the calculated equations for all stats that use the given equation
        """

        stats = session.query(db.server.Stat).all()

        errors = False

        for stat in stats:
            user = session.query(db.server.User).get(stat.user_id)
            parsed = util.calculator.parse_args(stat.value.lower(), session, user)
            parsed = util.calculator._get_elements(parsed)

            if any(db.Server.get_from_string(session, db.server.Equation, s) == eq for s in parsed):
                
                try:
                    cls.calc_stat_value(session, user, stat)
                except util.BadEquation as be:
                    errors = True
                    cls._logger.warning("There was an error while calculating the stat value ({}): {}".format(str(stat), str(be)))
        
        return not errors

    @classmethod
    def calc_stat_value(cls, session, user: db.server.User, stat: db.server.Stat, parse_randoms=False):
        """
        Calculate the stat values for the given stat, and all stats that depend on this stat.

        raises util.BadEquation error on a bad equation
        """

        # 5. set calc to None
        stat.calc = None

        # 1. check if there are dice rolls
        util.dice.logging_enabled = True
        eq = util.calculator.parse_args(stat.value, session, user)
        # 2. calculate equation
        value = util.calculator.parse_equation(eq, session, user)
        util.dice.logging_enabled = False

        dice = util.dice.rolled_dice

        if len(dice) is 0 or parse_randoms is True:
            # 3. set calc to calculated equation
            stat.calc = value
        
        # 6. check if there are dependent stats

        errors = False

        from string import Formatter
        name = stat.name.lower()
        for st in user.stats:
            params = [fn for _, fn, _, _ in Formatter().parse(str(st.value).lower()) if fn is not None]
            if name in params:
                try:
                    cls.calc_stat_value(session, user, st)
                except util.BadEquation:
                    errors = True
        
        if errors:
            raise util.BadEquation("There were errors while calculating dependent stats.")
        
        return dice

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

    @commands.group(pass_context=True, aliases=['rollstats', 'confstats', 'gs', 'rs', 'cs'])
    async def getstats(self, ctx: commands.Context):
        """
        Get and configure default stats

        By running this command, you will be given default stats.

        If you have permission to edit the server, or are a dm, you can change
        what the default stats are.
        """

        if ctx.invoked_subcommand is not None:
            return

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()

        stats = session.query(db.server.RollStat).order_by(
            db.server.RollStat.name
        ).all()

        if len(stats) is 0:
            self.say(message, "There are no default stats yet.")
            await self.send(message)
            return

        self.say(message, "```python")

        max_name_width = max([len(stat.name) for stat in stats])

        for stat in stats:
            self.say(message, "{0: >{width}}  {1}".format(
                stat.name, stat.value,
                width=max_name_width
            ))
        
        self.say(message, "```")

        await self.send(message)
    
    @getstats.command(pass_context=True, name="apply", aliases=['roll'])
    async def gs_apply(self, ctx: commands.Context):
        """
        Apply the default stats to your stats

        If there are any random numbers, the result will be set instead of the
        equation.
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()

        # Send the typing signal to discord
        await self.bot.send_typing(ctx.message.channel)

        user = self.get_user(ctx, session)

        stats = user.getStats()
        defaults = session.query(db.server.RollStat).all()

        # Set all the stats first
        for default in defaults:
            stats[default.name] = default.value
        
        errors = list()

        # calculate the stats
        for default in defaults:
            stat = stats[default.name]
            try:
                if util.dice.low:
                    await util.dice.load_random_buffer()

                dice = self.calc_stat_value(session, user, stat, parse_randoms=True)

                if len(dice) is not 0:
                    stat.value = stat.calc

                    from .dice import Dice
                    self.say(message, Dice.print_dice(dice))
                    calc = int(stat.calc) if int(stat.calc) is stat.calc else stat.calc
                    self.say(message, "{}: **{}**".format(stat.name, calc))
            except util.BadEquation as be:
                self.say(errors, "There was an error while setting {}:".format(stat.name))
                self.say(errors, str(be))

        session.commit()

        message.extend(errors)

        self.say(message, "I set your stats!")

        await self.send(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @getstats.command(pass_context=True, name="show")
    async def gs_show(self, ctx: commands.Context):
        """
        Show all the default stats
        """

    @getstats.command(pass_context=True, usage="<stat> <value>", name="set", aliases=['add', 'edit'])
    async def gs_set(self, ctx: commands.Context, stat_name: str, *, value: str):
        """
        Set a default stat value
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        if not user.checkPermissions(ctx):
            self.say(message, "You don't have permission to do that.")
            await self.send(message)
            return

        stat = session.query(db.server.RollStat).filter(
            db.server.RollStat.name==stat_name.lower()
        ).first()

        if stat is None:
            data = db.Server.getData(session)
            stat = db.server.RollStat(id=data.getNewId())
            stat.name = stat_name.lower()
            session.add(stat)
        
        stat.value = value.lower()

        session.commit()

        self.say(message, "Changed the default stat for {} to".format(stat.name))
        self.say(message, "```python")
        self.say(message, stat.value)
        self.say(message, "```")

        await self.send(message)

    @getstats.command(pass_context=True, usage="<stat>", name="del", aliases=['rm'])
    async def gs_del(self, ctx: commands.Context, stat_name: str):
        """
        Delete a default stat
        """

        message = list()
        
        server = self.get_server(ctx, message)
        if server is None:
            await self.send(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        if not user.checkPermissions(ctx):
            self.say(message, "You don't have permission to do that")
            await self.send(message)
            return
        
        stat = session.query(db.server.RollStat).filter(
            db.server.RollStat.name==stat_name.lower()
        ).first()

        if stat is None:
            self.say(message, "{} does not exist, so does not need to be deleted".format(stat_name.lower()))
            await self.send(message)
            return

        session.delete(stat)
        session.commit()

        self.say(message, "Deleted the default stat {}".format(stat_name.lower()))

        await self.send(message)
