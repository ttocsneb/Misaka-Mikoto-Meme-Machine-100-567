import logging
import asyncio

from discord.ext import commands

from ..config import config
from .. import util
from .. import db

class Tables:

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

    def get_table(self, ctx, message, session, name: str) -> db.server.Table:
        table = db.Server.get_from_string(session, db.server.Table, name, ctx.message.author.id)

        if table is not None:
            return table
        
        # Could not find table
        self.say(message, "Could not find `{}`".format(name))
    
    def get_server(self, ctx: commands.Context, message = None) -> db.Server:
        # If the message is not part of a server, get the active server from the author

        server = db.getDbFromCtx(ctx)
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server right now :/")
                self.say(message, "Activate the server you want to use first.")
        return server
    
    def get_user(self, ctx: commands.Context, session) -> db.server.User:
        return db.Server.getUser(session, ctx.message.author.id)

    def parse_csv(self, messages, string:str) -> list():
        from io import StringIO
        import csv
        buffer = StringIO(string)

        # Find the delimeter
        try:
            dialect = csv.Sniffer().sniff(buffer.read(1024))
        except csv.Error:
            # default to excel dialects
            self.say(messages, "I had trouble reading your csv, double check the values to make sure I didn't make any mistakes")
            dialect = csv.excel()
        buffer.seek(0)

        reader = csv.reader(buffer, dialect)

        def parse(l):
            try:
                return int(l[0])
            except:
                return 1

        return [(parse(l), l[1]) for l in reader]

    # Tables
    
    async def show_all_tables(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        your_tables = session.query(db.server.Table).filter(
            db.server.Table.creator_id==user.id
        ).all()
        other_tables = session.query(db.server.Table).filter(
            db.server.Table.creator_id!=user.id
        ).all()

        if len(your_tables) + len(other_tables) is 0:
            self.say(message, 'There are no tables yet.')
            await self.say_message(message)
            return

        self.say(message, 'here is a list of all the tables:')
        self.say(message, '```markdown\nYour Tables:\n' + '-' * 10)
        self.say(message, '\n'.join([i.print_name() for i in your_tables]))
        self.say(message, '\nOther Tables:\n' + '-' * 10)
        self.say(message, '\n'.join([i.print_name() for i in other_tables]))
        self.say(message, '```')
        await self.say_message(message)

    @commands.group(pass_context=True, aliases=['table', 'tab', 't'])
    async def tables(self, ctx: commands.Context):
        """
        Create or delete tables
        
        When adding items to tables, use the following format

        I recommend using this google sheet to help create
        a table: https://docs.google.com/spreadsheets/d/1A5Yo9XGMekLBUP8MYf-I-ZilmH-A1rbPd6SfUJZRCdU/edit?usp=sharing

        The format of the cells are as follows:
        
        | Weight |      Value       |
        |--------|------------------|
        |      2 | Armorer          |
        |      2 | Bowyer/fletcher  |
        |      6 | Farmer/gardener  |
        |      4 | Fisher (netting) |


        the csv format would become:
        
        2:Armorer
        2:Bowyer/fletcher
        6:Farmer/gardener
        4:Fisher (netting)

        Excel uses tab seperated values which discord does not particularly like.
        All other formats should work.
        """
        await self.show_all_tables(ctx)
    
    @tables.command(pass_context=True, usage="<table> <item(s)>", aliases=['create'])
    async def new(self, ctx, table_name: str, *, items: str):
        """
        Create a new table
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)
        data = server.getData(session)

        new_table = db.server.Table(id=data.getNewId())
        new_table.creator_id = user.id
        new_table.name = table_name.lower()
        new_table.desc = ''
        new_table.hidden = False

        percentiles = None
        if items is not None:
            table = self.parse_csv(message, items)
            percentiles = [db.server.Percentile(
                id=data.getNewId(),
                weight=p[0],
                value=p[1]) for p in table]

            new_table.percentiles.extend(percentiles)
        session.add(new_table)
        session.commit()

        self.say(message, "Created table " + new_table.print_name())
        await self.say_message(message)
    
    @tables.command(pass_context=True, name='deltable', usage="<table>", aliases=['deltab'])
    async def _del(self, ctx:commands.Context, table: str):
        """
        Deletes a table
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table.lower())
        if table is not None:
            if user.checkPermissions(ctx, table):
                self.say(message, "Deleted" + table.print_name())

                session.delete(table)
                session.commit()
            else:
                self.say(message, "You don't have the permissions to delete that table!")
        
        await self.say_message(message)
    
    @tables.command(pass_context=True, usage="<table> <description>")
    async def desc(self, ctx:commands.Context, table: str, *, description):
        """
        Sets the description of a table
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table.lower())

        if table is not None:
            if user.checkPermissions(ctx, table):
                table.desc = description
                session.commit()
                self.say(message, "Changed {} Description".format(table.print_name()))
            else:
                self.say(message, "You don't have the permissions for that")
        
        await self.say_message(message)

    @tables.command(pass_context=True, usage="<table> <true|false>")
    async def hide(self, ctx:commands.Context, table: str, hide: str):
        """
        Sets a table to be secret(Only you can know the contents), or public
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table.lower())
        if table is not None:
            if user.checkPermissions(ctx, table):
                hidden = hide[0].lower()

                # Check if the first character is true, false, yes, no, 1, 0
                if hidden not in 'tfyn01':
                    self.say(message, "You must say yes or no")
                else:
                    # Convert the string into a bool
                    table.hidden = hidden in 'ty1'
                    session.commit()
                    self.say(message, "Changed {} to be {}".format(table.print_name(), "secret" if table.hidden else "public"))
            else:
                self.say(message, "You can't do that, you don't have the permissions")

        await self.say_message(message)
    
    # tab

    @tables.command(pass_context=True, usage='<table>')
    async def show(self, ctx: commands.Context, table_name: str):
        """
        Show all the items in a table.
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table_name.lower())

        messages = list()
        if table is not None:
            self.say(message, table.print_name() + ' `(1-{} [1d{}])`'.format(len(table.getItems()), table.get_roll_sides()))


            if len(table.percentiles) is 0:
                self.say(message, "There is nothing here yet.")
                await self.say_message(message)
                return

            # Don't display the contents of the table if it is hidden and the user is not authorized
            if not table.hidden or user.checkPermissions(ctx, table):
                table_cont = list()
                table_cont.extend(table.print_all_percentiles())

                messages = list(message)

                if len('\n'.join(table_cont + message)) > 2000 - 8:
                    mess = list()
                    for m in table_cont:
                        mess.append(m)
                        if len('\n'.join(mess)) > 2000 - 8:
                            mess.pop()
                            messages.append('```markdown\n' + '\n'.join(mess) + '```')
                            mess = [m]
                    messages.append('```markdown\n' + '\n'.join(mess) + '```')
                    self.say(message, 'The list is too long, I sent it to you')
                elif table.hidden:
                    self.say(message, 'The list is hidden, I sent it to you to protect its privacy.')
                    messages.append('```markdown\n' + '\n'.join(table_cont) + '```')
                    messages = ['\n'.join(messages)]
                else:
                    message.append('```markdown\n' + '\n'.join(table_cont) + '```')
                    messages = list()
            else:
                self.say(message, "```This table is hidden, you aren't allowed to see all the items inside```")

        await self.say_message(message)

        for m in messages:
            await self.bot.send_message(ctx.message.author, m)
    
    @tables.command(pass_context=True, usage='<table> [value]')
    async def roll(self, ctx: commands.Context, table_name: str, value=None):
        """
        Roll a value for the table, if you rolled a value, you may enter the value you rolled.
        """

        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            max_val = len(table.getItems())
            # Validate the entered number
            if value is not None:
                fail = False
                try:
                    value = int(value)
                    if value > max_val or value < 1:
                        self.say(message, 'The number should be in the range `(1-{})`'.format(max_val))
                        fail = True
                except ValueError:
                    self.say(message, 'You must enter a number!')
                    fail = True
                if fail:
                    await self.say_message(message)
                    return
            else:  # Generate a random number
                dice = table.get_roll_sides()
                util.dice.logging_enabled = True
                while True:
                    value = util.dice.roll(dice)
                    if value <= max_val:
                        break
                util.dice.logging_enabled = False
                dice = util.dice.rolled_dice
                from .dice import Dice
                self.say(message, Dice.print_dice(dice))
            
            perc = table.getItems()[value - 1]

            self.say(message, '**{}**'.format(value))
            self.say(message, perc.value)
        
        await self.say_message(message)

        
        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @tables.command(pass_context=True, name='add', usage='<table> <item(s)>')
    async def tab_add(self, ctx: commands.Context, table_name: str, *, items):
        """
        Add items to the table
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        data = server.getData(session)
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            if user.checkPermissions(ctx, table):
                csv = self.parse_csv(message, items)
                percs = [db.server.Percentile(
                    id=data.getNewId(),
                    weight=p[0],
                    value=p[1]) for p in csv]

                table.percentiles.extend(percs)
                session.commit()
                self.say(message, "Added items to " + table.print_name())
            else:
                self.say(message, "You don't have permission here")
        
        await self.say_message(message)

    @tables.command(pass_context=True, usage='<table> <index> <item(s)>')
    async def insert(self, ctx: commands.Context, table_name: str, index: int, *, items):
        """
        Insert items into the table at a given position
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)
        data = server.getData(session)

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            if index < 1 or index > len(table.getItems()):
                self.say(message, "You can only insert items into `1-{}`".format(len(table.getItems())))
                await self.say_message(message)
                return

            if user.checkPermissions(ctx, table):
                csv = self.parse_csv(message, items)
                percs = [db.server.Percentile(
                    id=data.getNewId(),
                    weight=p[0],
                    value=p[1]
                ) for p in csv]

                # Insert the new items into the table
                table.percentiles[index-1:index-1] = percs

                session.commit()
                self.say(message, "Added items to " + table.print_name())
            else:
                self.say(message, "You don't have permission here")
        
        await self.say_message(message)

    @tables.command(pass_context=True, name='del', usage='<table> <index> [number]', aliases=['rm'])
    async def tab_del(self, ctx: commands.Context, table_name: str, index: int, num: int = 1):
        """
        Delete a (number of) item(s) from the table
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            if user.checkPermissions(ctx, table):
                if index < 1 or index > len(table.getItems()):
                    self.say(message, "Index should be in the range of `1-{}`".format(len(table.getItems())))
                elif num < 1:
                    self.say(message, "You must delete at least 1 item")
                else:
                    if num is 1:
                        self.say(message, "Deleted item from " + table.print_name())
                    else:
                        self.say(message, "Deleted {} items from {}".format(num, table.print_name()))

                    start_index = table.percentiles.index(table.getItems()[index-1])
                    end_index = min(start_index + num, len(table.percentiles))
                    del table.percentiles[slice(start_index, end_index)]

                    session.commit()
            else:
                self.say(message, "You don't have the permissions")
        
        await self.say_message(message)

    @tables.command(pass_context=True, usage='<table> <index> <item(s)>')
    async def replace(self, ctx: commands.Context, table_name: str, index: int, *, items):
        """
        Replace the content of the item(s) starting at the given index
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)
        data = server.getData(session)

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            if user.checkPermissions(ctx, table):
                if index < 1 or index > len(table.getItems()):
                    self.say(message, "The range is `1-{}`".format(len(table.getItems())))
                else:
                    csv = self.parse_csv(message, items)
                    percs = [db.server.Percentile(
                        id=data.getNewId(),
                        weight=p[0],
                        value=p[1]
                    ) for p in csv]

                    start_index = table.percentiles.index(table.getItems()[index - 1])
                    end_index = start_index + len(percs)

                    table.percentiles[slice(start_index,end_index)] = percs
                    session.commit()

                    self.say(message, "Replaced {} item{} in {}".format(len(percs), 's' if len(percs) > 1 else '', table.print_name()))
            else:
                self.say(message, "You can't do that, you don't have my permission")

        await self.say_message(message)

    @tables.command(pass_context=True, usage='<table>')
    async def clear(self, ctx: commands.Context, table_name: str):
        """
        Delete all the items in the table
        """
        message = list()

        server = self.get_server(ctx, message)
        if server is None:
            await self.say_message(message)
            return
        session = server.createSession()
        user = self.get_user(ctx, session)

        table = self.get_table(ctx, message, session, table_name.lower())

        if table is not None:
            if user.checkPermissions(ctx, table):
                table.percentiles.clear()
                session.commit()
                self.say(message, "Removed all items from " + table.print_name())
            else:
                self.say(message, "You don't have permission to do this.")

        await self.say_message(message)
