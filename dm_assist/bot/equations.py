import logging
import asyncio

from discord.ext import commands

from ..config import config
from .. import util
from .. import db

class Equations:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)
    
    @staticmethod
    def say(messages, string):
        if string:
            messages.append(str(string))
    
    async def say_message(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)

    def check_permissions(self, ctx: commands.Context, eq: db.server.Equation):
        author = ctx.message.author

        if author.id == eq.creator_id:
            return True
        
        if author.id in config.config.mods:
            return True
        
        try:
            return author.server_permissions.manage_server
        except:
            return False
    
    def get_server(self, ctx: commands.Context) -> db.Server:
        return db.getDb(ctx.message.server.id)
    
    def get_user(self, ctx: commands.Context, session) -> db.server.User:
        return db.Server.getUser(session, ctx.message.author.id)
    
    def get_num_params(self, text):
        from string import Formatter
        params = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

        def is_int(text):
            try:
                return int(text)
            except ValueError:
                return False
        
        args = [p for p in params if is_int(p) is not False]
        return len(set(args))

    def get_equation(self, ctx, message, session, name) -> db.server.Equation:
        equation = db.Server.get_from_string(session, db.server.Equation, name, ctx.message.author.id)

        if equation is not None:
            return equation
        
        # There is no equation by the name or id given
        self.say(message, "Could not find `{}`".format(name))

    # Equations

    @commands.group(pass_context=True, aliases=['eq'])
    async def equations(self, ctx: commands.Context):
        """
        Manage equations

        Equations allow you to quickly perform math by creating your own
        functions that you can use in the roll command.
        """

        if ctx.invoked_subcommand is not None:
            return
        
        message = list()

        server = self.get_server(ctx)
        session = server.createSession()
        user = self.get_user(ctx, session)

        your_eqs = user.equations
        other_eqs = session.query(db.server.Equation).filter(
            db.server.Equation.creator_id!=user.id
        ).all()

        if len(your_eqs) + len(other_eqs) is 0:
            self.say(message, 'There are no equations yet.')
            await self.say_message(message)
            return
        
        self.say(message, 'here is a list of all the equations:')
        self.say(message, '```markdown\nYour Equations:\n' + '-' * 10)
        self.say(message, '\n'.join([eq.printName() for eq in your_eqs]))
        self.say(message, '\nOther Equations:\n' + '-' * 10)
        self.say(message, '\n'.join([eq.printName() for eq in other_eqs]))
        self.say(message, '```')
        await self.say_message(message)
    
    @equations.command(pass_context=True, usage='<eq name>')
    async def show(self, ctx: commands.Context, table_name: str):
        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        equation = self.get_equation(ctx, message, session, table_name)

        if equation is not None:
            self.say(message, equation.printName())
            self.say(message, "```python")
            self.say(message, equation.equation)
            self.say(message, "```")
        
        await self.say_message(message)

    @equations.command(pass_context=True, usage='<eq name> <equation>')
    async def add(self, ctx: commands.Context, table_name: str, *, equation: str):
        """
        Add a new equation

        Equations can accept all the same functions as a roll command,
        including other equations.

        An equation can also accept parameters which look like this
        {0}

        The number between the braces is the parameter number
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        user = self.get_user(ctx, session)
        data = server.getData(session)

        new_eq = db.server.Equation(id=data.getNewId())
        new_eq.name = table_name.lower()
        new_eq.creator_id = user.id
        new_eq.equation = equation.lower()
        new_eq.params = self.get_num_params(new_eq.equation)
        new_eq.desc = ''

        session.add(new_eq)
        session.commit()

        self.say(message, "Created Equation " + new_eq.printName())
        await self.say_message(message)
    
    @equations.command(pass_context=True, usage="<eq name> <description>")
    async def desc(self, ctx: commands.Context, table_name: str, *, description: str):
        """
        Set a description to an equation
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        equation = self.get_equation(ctx, message, session, table_name)

        if equation is not None:
            if self.check_permissions(ctx, equation):
                equation.desc = description
                session.commit()
                self.say(message, "Changed {} description".format(equation.printName()))
            else:
                self.say(message, "You don't have permission to do that")
        
        await self.say_message(message)
    
    @equations.command(pass_context=True, usage="<eq name> <equation>")
    async def edit(self, ctx: commands.Context, eq_name: str, *, eq):
        """
        Change an equation's equation
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        equation = self.get_equation(ctx, message, session, eq_name)

        if equation is not None:
            if self.check_permissions(ctx, equation):
                equation.equation = eq.lower()
                equation.params = self.get_num_params(eq)
                session.commit()
                self.say(message, "Changed {} equation".format(equation.printName()))
            else:
                self.say(message, "You don't have permission for that.")
        
        await self.say_message(message)
    
    @equations.command(pass_context=True, usage="<eq name>", name='del')
    async def _del(self, ctx: commands.Context, eq_name: str):
        """
        Deletes an equation
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        equation = self.get_equation(ctx, message, session, eq_name)

        if equation is not None:
            if self.check_permissions(ctx, equation):
                name = equation.printName()
                session.delete(equation)
                session.commit()
                self.say(message, "Deleted " + name)
            else:
                self.say(message, "Sorry, your not allowed to do that :/")
        
        await self.say_message(message)

    @equations.command(pass_context=True, usage="<eq name> [<param 0>,]", aliases=['roll'])
    async def calc(self, ctx: commands.Context, eq_name: str, *args):
        """
        Calculate the equation

        If the equation uses any parameters, you must include them
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()
        user = self.get_user(ctx, session)


        equation = self.get_equation(ctx, message, session, eq_name)

        if equation is not None:
            try:
                eq = util.calculator.parse_args(equation.equation, session, user, args)
                util.dice.logging_enabled = True
                value = util.calculator.parse_equation(eq, session, user)
                util.dice.logging_enabled = False

                dice = util.dice.rolled_dice
                if len(dice) > 0:
                    from .dice import Dice
                    self.say(message, Dice.print_dice(dice))
                    self.say(message, Dice.print_dice_one_liner(dice + [(value, "sum")]))

                self.say(message, "**{}**".format(value))
            except util.BadEquation as be:
                self.say(message, be)

        await self.say_message(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())
    
    # Stats

    @commands.group(pass_context=True, aliases=['st'])
    async def stats(self, ctx: commands.Context):
        """
        Manage your stats

        Stats can be used with equations, and rolls.

        They are usefull because you can have a universal equation with special
        parameter for each peson using it.

        The most common use for stats in terms of rpgs is the level stat. Some
        equations need to modified by the user's level, and it gets annoying to
        enter your level each time you use the equation.  Stats allow you to
        enter a variable once, and have it automatically applied every time you
        use an equation
        """

        if ctx.invoked_subcommand is not None:
            return
        
        message = list()

        server = self.get_server(ctx)
        session = server.createSession()
        user = self.get_user(ctx, session)

        stats = user.stats

        if len(stats) is 0:
            self.say(message, "You don't have any stats yet")
            await self.say_message(message)
            return

        self.say(message, "```python")

        max_width = max([len(stat.name) for stat in stats])

        for stat in stats:
            self.say(message, "{0: >{width}}  {1}".format(
                stat.name, stat.value, width=max_width)
            )

        self.say(message, "```")

        await self.say_message(message)
    
    @stats.command(pass_context=True, usage="<stat> value", aliases=['add', 'edit'], name="set")
    async def st_set(self, ctx: commands.Context, stat: str, *, value: str):
        """
        Set a stat

        A stat can be any number, even an equation!
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        user = self.get_user(ctx, session)

        stats = user.getStats()

        stats[stat.lower()] = value.lower()

        session.commit()

        self.say(message, "Set **{}** stat to".format(stat.lower()))
        self.say(message, "```python")
        self.say(message, value.lower())
        self.say(message, "```")

        await self.say_message(message)
    
    @stats.command(pass_context=True, usage="<stat>", aliases=['rm'], name='del')
    async def st_del(self, ctx: commands.Context, stat: str):
        """
        Delete a stat
        """

        message = list()

        server = self.get_server(ctx)
        session = server.createSession()

        user = self.get_user(ctx, session)

        stats = user.getStats()

        try:
            del stats[stat.lower()]
            session.commit()

            self.say(message, "Deleted your **{}** stat".format(stat.lower()))
        except KeyError:
            self.say(message, "Could not find **{}**".format(stat.lower()))
        
        await self.say_message(message)