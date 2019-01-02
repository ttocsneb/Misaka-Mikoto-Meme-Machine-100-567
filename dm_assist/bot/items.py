import asyncio

from discord.ext import commands

from ..config import config
from .. import util
from ..db import db, schemas


class Items:

    def __init__(self, bot):
        self.bot = bot
    
    @staticmethod
    def say(messages, string):
        messages.append(string)
    
    async def say_message(self, messages):
        await self.bot.say('\n'.join(messages))

    def get_item(self, message, server, name: str) -> schemas.Item:

        import re
        # Seperate the name from the id with support for emojis
        item_name = re.findall(r"([\S]+(?=:)|(?<=:)[\d]+|[^:\s]+|(?<!\S)(?=:))", name)

        if len(item_name) > 1:
            try:
                item = server.item(int(item_name[1]))
                return item
            except KeyError:
                pass
            except ValueError:
                pass

        try:
            item = server.item_name(item_name[0])
            return item
        except KeyError:
            self.say(message, "Could not find `{}`".format(name))
            return None


    @commands.command(pass_context=True)
    async def item(self, ctx: commands.Context, *params):
        """
        manipulate the server's items.  say `help item` for more details

        - item:                                 lists all the items
        - item add <item>:                      adds a new item
        - item del <item>:                      deletes an item

        - item <item>:                          lists item equations
        - item <item> add <name> <equation>:    adds a new equation
        - item <item> del <name>:               deletes an equation
        - item <item> edit <name> <equation>:   edits an item equation

        item can either be the item's name (`sword`), name and id (`sword:5`), or just id (`:5`)
        """

        message = []

        server = db.database[ctx.message.server.id]

        params = [p.lower() for p in params]

        def usage():
            prefix = server.prefix
            self.say(message, 'Usage:\n```\n')
            self.say(message, prefix + 'item add <item>')
            self.say(message, prefix + 'item del <item>')
            self.say(message, prefix + 'item <item> add <name> <equation>')
            self.say(message, prefix + 'item <item> del <name>')
            self.say(message, prefix + 'item <item> edit <name> <equation>\n```')

        if len(params) is 0:  # List Items
            if len(server.items) is 0:
                self.say(message, 'There are no items.')
                await self.say_message(message)
                return
            items = '\n'.join([i.short_desc for i in server.items])
            self.say(message, 'here is a list of all the items:')
            self.say(message, '```\n{}\n```'.format(items))
            await self.say_message(message)
            return
        
        if len(params) is 1:  # Describe Item
            params = params[0]

            # Check for not enough arguments
            if params in ['add', 'del']:
                self.say(message, 'Usage: `{pre}item {} <item>`'.format(params, pre=server.prefix))
                await self.say_message(message)
                return

            item = self.get_item(message, server, params)

            if item is not None:
                self.say(message, '```')
                self.say(message, item.description)
                self.say(message, '```')
            
            await self.say_message(message)
            return
        
        if len(params) is 2:
            
            # check for not enough arguments
            if params[1] in ['add', 'del', 'edit']:
                if params[1] == 'del':
                    self.say(message, 'Usage: `{pre}item <item> del <name>`'.format(
                        pre=server.prefix))
                else:
                    self.say(message, 'Usage: `{pre}item <item> {} <name> <equation>`'.format(
                        params[1], pre=server.prefix))
                await self.say_message(message)
                return
            
            if params[0] in ['add', 'del']:
                if params[0] == 'add':  # Add item
                    item = schemas.Item(params[1])
                    server.add_item(item)
                    self.say(message, "Added " + item.short_desc)
                    self.say(message, "Use `{pre}item {} add <name> <equation>` to give it an equation".format(
                        item.short_desc, pre=server.prefix))
                else:
                    item = self.get_item(message, server, params[1])
                    if item is not None:
                        if params[0] == 'del':  # Delete item
                            self.say(message, "Deleted " + item.short_desc)
                            server.items.remove(item)
                        server.save()
            else:
                usage()

            await self.say_message(message)
            return
        
        if len(params) is 3:

            # Check for not enough arguments
            if params[1] in ['add', 'edit']:
                self.say(message, 'Usage: `{pre}item <item> {} <name> <equation>`'.format(params[1], pre=server.prefix))
                await self.say_message(message)
                return
            
            if params[1] == 'del':  # Delete equation
                item = self.get_item(message, server, params[0])
                if item is not None:
                    equation = item.equations.get(params[2])
                    if equation is not None:
                        self.say(message, "Deleted {} from {}".format(params[2].capitalize(), item.short_desc))
                        del item.equations[params[2]]
                    else:
                        self.say(message, "Could not find {} in {}".format(params[2].capitalize(), item.short_desc))
            else:
                usage()
            
            await self.say_message(message)
            return
        
        # Check if these commands are valid
        if params[1] in ['add', 'edit']:
            item = self.get_item(message, server, params[0])
            if item is not None:
                if params[1] == 'add':  # Add Equation
                    if item.equations.get(params[2]) is not None:
                        self.say(message, "{} already exists, use `{pre}item {} edit {} {}` to change its equation".format(
                            params[2].capitalize(), params[0], params[2], ' '.join(params[3:]), pre=server.prefix))
                    else:
                        item.equations[params[2]] = ' '.join(params[3:])
                        self.say(message, "added equation {} for {}".format(params[2].capitalize(), item.short_desc))
                elif params[1] == 'edit':  # Edit Equation
                    if item.equations.get(params[2]) is None:
                        self.say(message, "{} doesn't exists, use `{pre}item {} add {} {}` to add that equation".format(
                            params[2].capitalize(), params[0], params[2], ' '.join(params[3:]), pre=server.prefix))
                    else:
                        item.equations[params[2]] = ' '.join(params[3:])
                        self.say(message, "edited equation {} in {}".format(params[2].capitalize(), item.short_desc))
                server.save()
        else:
            usage()

        await self.say_message(message)
