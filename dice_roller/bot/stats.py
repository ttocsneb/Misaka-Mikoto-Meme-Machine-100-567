import logging
import asyncio

from discord.ext import commands

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

    def get_server(self, ctx: commands.Context, session, message,
                   commit=True) -> db.schema.Server:

        server = db.database.getServerFromCtx(session, ctx, commit=commit)[0]
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server.")
        return server

    def get_user(self, ctx: commands.Context, session, message,
                 commit=True) -> db.schema.User:
        user = db.database.getUserFromCtx(session, ctx, commit=commit)[0]
        if user is None and message is not None:
            self.say(
                message,
                "You aren't registered with any server and can't " + 
                "register here!"
            )
        return user

    @classmethod
    def print_group(cls, message, group):

        if group.name:
            cls.say(message, '#{}:'.format(group.name))

        max_name_width = list()
        max_val_width = list()

        default = "?"

        mod = 2 if group.name else 0

        for stat in group.values():
            max_name_width.append(len(stat.name) + mod)
            if stat.calc is not None:
                try:
                    val = int(stat.calc) if int(stat.calc) == stat.calc \
                        else stat.calc
                except ValueError:
                    val = stat.calc
                max_val_width.append(len(str(val)))
            else:
                max_val_width.append(len(default))

        max_name_width = max(max_name_width)
        max_val_width = max(max_val_width)

        for name, stat in group.items():
            if stat.calc is not None:
                try:
                    val = int(stat.calc) if int(stat.calc) == stat.calc \
                        else stat.calc
                except ValueError:
                    val = stat.calc
            else:
                val = default

            if str(val) != stat.value:
                cls.say(
                    message,
                    "{0:>{wid_n}}  {1:<{wid_v}} = {2}".format(
                        name, val, stat.value, wid_n=max_name_width,
                        wid_v=max_val_width
                    )
                )
            else:
                cls.say(message, "{0:>{wid_n}}  {1}".format(
                    name, val, wid_n=max_name_width
                ))

    @classmethod
    def update_stats_equations(cls, session, server, eq: db.schema.Equation):
        """
        update the calculated equations for all stats that use the given
        equation
        """

        stats = session.query(db.schema.Stat).filter(
            db.schema.Stat.server_id == server.id
        ).all()

        errors = False

        for stat in stats:
            user = session.query(db.schema.User).get(stat.user_id)
            parsed = util.calculator.parse_args(stat.value.lower(), session,
                                                user)
            parsed = util.calculator._get_elements(parsed)

            if any(db.database.get_from_string(
                    session, db.schema.Equation, s, server.id) == eq
                    for s in parsed):

                try:
                    cls.calc_stat_value(session, user, stat)
                except util.BadEquation as be:
                    errors = True
                    cls._logger.warning(
                        "There was an error while calculating the stat value" +
                        " ({}): {}".format(str(stat), str(be)))

        return not errors

    @classmethod
    def calc_stat_value(cls, session, user: db.schema.User,
                        stat: db.schema.Stat, parse_randoms=False):
        """
        Calculate the stat values for the given stat, and all stats that depend
        on this stat.

        raises util.BadEquation error on a bad equation
        """

        # 5. set calc to None
        stat.calc = None

        # 1. check if there are dice rolls
        util.dice.logging_enabled = True
        eq = util.calculator.parse_args(stat.value, session, user,
                                        use_calculated=False)
        # 2. calculate equation
        value = util.calculator.parse_equation(eq, session, user)
        util.dice.logging_enabled = False

        dice = util.dice.rolled_dice

        if not dice or parse_randoms is True:
            # 3. set calc to calculated equation
            stat.calc = value

        # 6. check if there are dependent stats

        errors = False

        name = stat.fullname
        for st in user.stats.values():
            params = [fn for fn
                      in util.variables.getVariables(str(st.value).lower())]
            if name in params:
                try:
                    cls.calc_stat_value(session, user, st)
                except util.BadEquation:
                    errors = True

        if errors:
            raise util.BadEquation(
                "There were errors while calculating dependent stats.")

        return dice

    @commands.group(pass_context=True, aliases=['st', 'stat'])
    async def stats(self, ctx: commands.Context):
        """
        Manage your stats

        Stats can be used with equations and rolls.

        In order to use a stat in an equation/roll put the equation name in {}
        for a variable called foo, you would use {foo}

        stats can be grouped by putting a period between the group and the name

        the group is bar, and the name is foo: {bar.foo}
        """

        if ctx.invoked_subcommand is not None:
            return

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, True)
            if user is None:
                await self.send(message)
                return

            stats = user.stats

            if not stats:
                self.say(message, "You don't have any stats yet")
                await self.send(message)
                return

            self.say(message, "```python")

            for group in stats.iter_groups():
                self.print_group(message, stats.get_group(group))

            self.say(message, "```")

            await self.send(message)

    @stats.command(pass_context=True, usage="[group]", name='get')
    async def st_get(self, ctx: commands.Context, group=None):
        """
        Get a stat group

        Prints all the stats that are in a group
        """
        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, True)
            if user is None:
                await self.send(message)
                return

            group = db.data_models.Stats.remove_specials(group) if group \
                else None

            try:
                stats = user.stats.get_group(group)
            except KeyError:
                self.say(message, "You do not have the stat group `{}`".format(
                    group))
                await self.send(message)
                return

            self.say(message, "```python")

            self.print_group(message, stats)

            self.say(message, "```")

            await self.send(message)

    @stats.command(pass_context=True, usage="<stat> value",
                   aliases=['add', 'edit'], name='set')
    async def st_set(self, ctx: commands.Context, stat: str, *, value: str):
        """
        Set a stat

        A stat can be any number, even an equation!
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            stats = user.stats

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

            self.say(message, "Set **{}** stat to".format(str(stat)))
            self.say(message, "```python")
            if stat.calc is not None:
                calc = int(stat.calc) if int(stat.calc) == stat.calc \
                    else stat.calc
                if str(calc) == stat.value:
                    val = str(calc)
                else:
                    val = "{}  ({})".format(calc, stat.value)
            else:
                val = stat.value
            self.say(message, val)
            self.say(message, "```")

            await self.send(message)

    @stats.command(pass_context=True, usage="<stat>", aliases=['rm'],
                   name='del')
    async def st_del(self, ctx: commands.Context, stat: str):
        """
        Delete a stat
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            stats = user.stats

            try:
                del stats[stat.lower()]
                session.commit()

                self.say(message, "Deleted your **{}** stat".format(
                    stat.lower()))
            except KeyError:
                self.say(message, "Could not find **{}**".format(stat.lower()))

            await self.send(message)

    @stats.group(pass_context=True, name="clear")
    async def st_clear(self, ctx: commands.Context):
        """
        Clear all your stats

        You can clear everyone's stats by running the command `stats clear all`
        """

        if ctx.invoked_subcommand is not self.st_clear:
            return

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            stats = user.stats

            if not stats:
                self.say(message, "You don't have any stats to clear")
            else:
                user.stats.clear()
                session.commit()
                self.say(message, "Deleted all of your stats")

            await self.send(message)

    @st_clear.command(pass_context=True, name="all")
    async def st_clr_all(self, ctx: commands.Context):
        """
        Clear everyone's stats

        You have to be a moderator, or have permission to modify the server to
        run this command
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            if not user.checkPermissions(ctx):
                self.say(
                    message,
                    "You don't have permission to modify everybody's stats"
                )
                await self.send(message)
                return

            session.query(db.schema.Stat).filter_by(
                server_id=user.active_server_id
            ).delete()

            session.commit()

            self.say(message, "Successfully deleted all user's stats")

            await self.send(message)

    # Default Stats

    @commands.group(pass_context=True,
                    aliases=['defstats', 'confstats', 'ds', 'cs'])
    async def defaultstats(self, ctx: commands.Context):
        """
        default stats

        set default stats that will be given to all users on the server

        it works the same as normal stats, however random values will be
        rolled when they are applied

        ie. when the stats are applied, the stat bar: 1d20 will be rolled,
        and the result will be set to the user's stat bar.
        """

        if ctx.invoked_subcommand is not None:
            return

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, True)
            if user is None:
                await self.send(message)
                return

            stats = session.query(db.schema.RollStat).filter(
                db.schema.RollStat.server_id == user.active_server_id
            ).all()

            stats = db.data_models.Stats(user, stats)

            if not stats:
                self.say(message, "There are no default stats yet.")
                await self.send(message)
                return

            self.say(message, "Default Stats")
            self.say(message, "```python")

            for group in stats.iter_groups():
                self.print_group(message, stats.get_group(group))

            self.say(message, "```")

            await self.send(message)

    @defaultstats.command(pass_context=True, name="get", usage="[group]")
    async def ds_get(self, ctx: commands.Context, group=None):
        """
        List a group of default stats
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, True)
            if user is None:
                await self.send(message)
                return

            group = db.data_models.Stats.remove_specials(group) if group \
                else None

            stats = session.query(db.schema.RollStat).filter(
                db.schema.RollStat.server_id == user.active_server_id,
                db.schema.RollStat.group == group
            ).all()

            try:
                stats = db.data_models.Stats(user, stats).get_group(group)
            except KeyError:
                self.say(message, "there is no group `{}`".format(group))
                await self.send(message)
                return

            self.say(message, "```python")
            self.print_group(message, stats)
            self.say(message, "```")

            await self.send(message)

    @defaultstats.command(pass_context=True, name="apply", aliases=['roll'])
    async def ds_apply(self, ctx: commands.Context):
        """
        Apply the default stats to your stats

        If there are any random numbers, the result will be set instead of the
        equation.
        """
        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            # Send the typing signal to discord
            await self.bot.send_typing(ctx.message.channel)

            stats = user.stats
            defaults = session.query(db.schema.RollStat).filter(
                db.schema.RollStat.server_id == user.active_server_id
            ).order_by(db.schema.RollStat.group, db.schema.RollStat.name).all()

            randoms = \
                [k for k, v in util.calculator.precedence.items() if v >= 7]

            def is_random(eq):
                """
                Check if an equation is random

                It does this by checking if a primitive random function is in
                the equation
                """
                values = util.calculator._get_elements(eq.lower())
                try:
                    val = next(v for v in values if v in randoms)
                    return True
                except StopIteration:
                    pass
                return False

            # Separate the list of default stats into randoms and non-randoms
            random_stats = [d for d in defaults if is_random(d.value)]
            normal_stats = [d for d in defaults if d not in random_stats]

            # Set all the stats first
            for default in defaults:
                stats[stats.get_name(
                    default.group, default.name)] = default.value

            errors = list()

            # calculate the stats
            async def calc_stat(default_stats):
                """
                Calculate a list of RollStats for the user
                """
                for default in default_stats:
                    stat = stats[stats.get_name(default.group, default.name)]
                    try:
                        # Load more random numbers when low on rolled dice
                        if util.dice.low:
                            await util.dice.load_random_buffer()

                        dice = self.calc_stat_value(
                            session, user, stat,
                            parse_randoms=True
                        )

                        if dice:
                            stat.value = stat.calc

                            from .dice import Dice
                            self.say(message, Dice.print_dice(dice))
                            calc = \
                                int(stat.calc) if int(stat.calc) is stat.calc \
                                else stat.calc
                            self.say(message, "`{}`: **{}**".format(
                                stat.fullname, calc))
                    except util.BadEquation as be:
                        self.say(
                            errors, 
                            "There was an error while setting {}:".format(
                                stat.name)
                        )
                        self.say(errors, str(be))

            # Calculate random stats first
            await calc_stat(random_stats)
            # Calculate all other stats next
            await calc_stat(normal_stats)

            session.commit()

            message.extend(errors)

            self.say(message, "I set your stats!")

            await self.send(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @defaultstats.command(pass_context=True, usage="<stat> <value>",
                          name="set", aliases=['add', 'edit'])
    async def ds_set(self, ctx: commands.Context, stat_name: str, *,
                     value: str):
        """
        Set a default stat value
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            if not user.checkPermissions(ctx):
                self.say(message, "You don't have permission to do that.")
                await self.send(message)
                return

            group, name = db.data_models.Stats.parse_name(stat_name)

            stat = session.query(db.schema.RollStat).filter(
                db.schema.RollStat.server_id == user.active_server_id,
                db.schema.RollStat.name == name,
                db.schema.RollStat.group == group
            ).first()

            if stat is None:
                stat = db.schema.RollStat(server_id=user.active_server_id)
                stat.name = name
                stat.group = group
                session.add(stat)

            stat.value = value.lower()

            session.commit()

            self.say(message, "Changed the default stat for {} to".format(
                db.data_models.Stats.get_name(group, name)))
            self.say(message, "```python")
            self.say(message, stat.value)
            self.say(message, "```")

            await self.send(message)

    @defaultstats.command(pass_context=True, usage="<stat>", name="del",
                          aliases=['rm'])
    async def ds_del(self, ctx: commands.Context, stat_name: str):
        """
        Delete a default stat
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            if not user.checkPermissions(ctx):
                self.say(message, "You don't have permission to do that")
                await self.send(message)
                return

            group, name = db.data_models.Stats.parse_name(stat_name)

            stat = session.query(db.schema.RollStat).filter(
                db.schema.RollStat.server_id == user.active_server_id,
                db.schema.RollStat.name == name,
                db.schema.RollStat.group == group
            ).first()

            if stat is None:
                self.say(message,
                         "{} does not exist, so does not need to be deleted"
                         .format(db.data_models.Stats.get_name(group, name)))
                await self.send(message)
                return

            session.delete(stat)
            session.commit()

            self.say(message, "Deleted the default stat {}".format(
                db.data_models.Stats.get_name(group, name)))

            await self.send(message)

    @defaultstats.command(pass_context=True, name="clear")
    async def ds_clear(self, ctx: commands.Context):
        """
        Clear the default stats
        """

        message = list()

        with db.database.session() as session:
            user = self.get_user(ctx, session, message, False)
            if user is None:
                await self.send(message)
                return

            if not user.checkPermissions(ctx):
                self.say(message, "You don't have permission to do that")
                await self.send(message)
                return

            session.query(db.schema.RollStat).filter_by(
                server_id=user.active_server_id
            ).delete()

            session.commit()

            self.say(message, "Successfully cleared all default stats")
            await self.send(message)
