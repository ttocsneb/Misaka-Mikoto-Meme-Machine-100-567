import logging
import re

from discord.ext import commands

from ..config import config
from .. import util
from ..db import db, schemas

class Tables:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)
        self._name_regex = re.compile(r"([\S]+(?=:)|(?<=:)[\d]+|[^:\s]+|(?<!\S)(?=:))")
    
    @staticmethod
    def say(messages, string):
        if string:
            messages.append(str(string))
    
    async def say_message(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)
    
    def get_table(self, message, server: schemas.Server, name: str) -> schemas.Table:
        table_name = re.findall(self._name_regex, name)

        if len(table_name) > 1:
            try:
                return server.table(int(table_name[1]))
            except KeyError:
                pass
            except ValueError:
                pass
        
        try:
            return server.table_name(table_name[0])
        except KeyError:
            self.say(message, "Could not find `{}`".format(name))
            return None
    
    def check_permissions(self, ctx: commands.Context, table: schemas.Table):
        author = ctx.message.author

        if author.id == table.creator.id:
            return True
        
        if author.id in config.config.mods:
            return True
        
        try:
            return author.server_permissions.manage_server
        except:
            return False

    def get_server(self, ctx: commands.Context) -> schemas.Server:
        return db.database[ctx.message.server.id]
    
    def get_user(self, ctx: commands.Context, server: schemas.Server) -> schemas.User:
        return server.get_user(ctx.message.author.id)

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

    @commands.group(pass_context=True)
    async def tables(self, ctx: commands.Context):
        """
        Shows a list of all the tables
        """

        if ctx.invoked_subcommand is not None:
            return

        message = list()

        server = self.get_server(ctx)
        user = self.get_user(ctx, server)

        all_tables = server.tables

        if len(all_tables) is 0:
            self.say(message, 'Ther are no tables yet.')
            await self.say_message(message)
            return

        your_tables = [table for table in all_tables if table.creator.id == user.id]
        other_tables = [table for table in all_tables if table not in your_tables]

        self.say(message, 'here is a list of all the tables:')
        self.say(message, '```\nYour Tables:\n' + '-' * 10)
        self.say(message, '\n#'.join([i.print_name() for i in your_tables]))
        self.say(message, '\nOther Tables:\n' + '-' * 10)
        self.say(message, '\n@'.join([i.print_name() for i in other_tables]))
        self.say(message, '```')
        await self.say_message(message)
    
    @tables.command(pass_context=True, usage="<table> [items]")
    async def add(self, ctx, table_name: str, *, items=None):
        """
        Create a new table

        The optional items are can be in any CSV format.

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
        
        2	Armorer
        2	Bowyer/fletcher
        6	Farmer/gardener
        4	Fisher (netting)


        this is from excel, which is tab seperated.
        other formats are also accepted such as comma seperated:

        2,Armorer
        2,Bowyer/fletcher
        6,Farmer/gardener
        4,Fisher (netting)
        """

        message = list()

        server = self.get_server(ctx)
        user = self.get_user(ctx, server)

        percentiles = None
        if items is not None:
            table = self.parse_csv(message, items)
            percentiles = [schemas.Percentile(*p) for p in table]
        new_table = schemas.Table(table_name.lower(), percentiles=percentiles, creator=user)
        server.add_table(new_table)
        server.save()

        self.say(message, "Created table " + new_table.print_name())
        await self.say_message(message)
    
    @tables.command(pass_context=True, name='del', usage="<table>")
    async def _del(self, ctx:commands.Context, table: str):
        """
        Deletes a table
        """

        message = list()

        server = self.get_server(ctx)

        table = self.get_table(message, server, table.lower())
        if table is not None:
            if self.check_permissions(ctx, table):
                self.say(message, "Deleted" + table.print_name())
                server.tables.remove(table)
                server.save()
            else:
                self.say(message, "You don't have the permissions to delete that table!")
        
        await self.say_message(message)
    
    @tables.command(pass_context=True, usage="<table> <description>")
    async def desc(self, ctx:commands.Context, table: str, *, description):
        """
        Sets the description of a table
        """

        message = list()

        server = self.get_server(ctx)

        table = self.get_table(message, server, table.lower())

        if table is not None:
            if self.check_permissions(ctx, table):
                table.desc = description
                server.save()
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

        server = self.get_server(ctx)

        table = self.get_table(message, server, table.lower())
        if table is not None:
            if self.check_permissions(ctx, table):
                hidden = hide[0].lower()

                # Check if the first character is true, false, yes, no, 1, 0
                if hidden not in b'tfyn01':
                    self.say(message, "You must say yes or no")
                else:
                    # Convert the string into a bool
                    table.hidden = hidden in b'ty1'
                    server.save()
                    self.say(message, "Changed {} to be {}".format(table.print_name(), "secret" if table.hidden else "public"))
            else:
                self.say(message, "You can't do that, you don't have the permissions")




# - table show <table>:                  Print all the possible items in a table
# - table roll <table> [value]:          Rolls an item on the table
# - table add <table> <items>:           Add items to the table
# - table insert <table> <index> <items>:Insert items into the table
# - table del <table> <index>:           Delete an item in the table
# - table edit <table> <index> <item>:   Change the content of the item
# - table clear <table>:                 Delete all items in the table
