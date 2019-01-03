import logging
import asyncio

from discord.ext import commands

from ..config import config
from .. import util
from ..db import db, schemas


class Items:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)
    
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
                    server.save()
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
                        server.save()
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
                        server.save()
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

    @commands.command(pass_context=True)
    async def rolli(self, ctx: commands.Context, item: str, name=None, *params):
        """
        Roll an item's equation

        Usage: <item> [name] [param0] [param1] ...

        If you don't specify an equation name, then the top equation will be used.

        Note: you cannot add paramters if you don't specify the name

        Parameters are manditory if the equation uses them.  a paramter is specified by {0}, {1}, etc.
        """

        item = item.lower()

        message = list()

        server = db.database[ctx.message.server.id]
        user = server.get_user(ctx.message.author.id)
        
        item_obj = self.get_item(message, server, item)
        if item_obj is None:
            await self.say_message(message)
            return
        
        if len(item_obj.equations) is 0:
            self.say(message, "{} doesn't have any equations yet.")
            self.say(message, "Use `{pre}item {} add <name> <equation>` to give it an equation".format(
                item_obj.short_desc, pre=server.prefix))
            await self.say_message(message)
            return

        if name is None:
            equation = item_obj.equations.values()[0]
        else:
            equation = item_obj.equations.get(name.lower())
            if equation is None:
                self.say(message, "I couldn't find {}, did you spell it right".format(name.lower()))
                await self.say_message(message)
                return

        # Parse any variables in the equation first.
        try:
            _params = list()
            # Paramters can also be equations, but can't contains spaces
            for param in params:
                param = param.format(**user.stats)
                try:
                    param = util.calculator.parse_equation(param)
                except util.BadEquation as be:
                    self.say(message, str(be))
                    await self.say_message(message)
                    return
            equation = equation.format(*params, **user.stats)
        except:
            try:
                raise
            except KeyError as ke:
                self.say(message, "Missing variable " + str(ke))
            except IndexError:
                self.say(message, "Not enough parameters")
            finally:
                await self.say_message(message)
                return

        try:
            util.dice.logging_enabled = True
            value = util.calculator.parse_equation(equation)
            util.dice.logging_enabled = False
        except util.BadEquation as be:
            self.say(message, "Couldn't parse the equation: " + str(be))
            await self.say_message(message)
            return

        dice = util.dice.rolled_dice
        if len(dice) > 0:
            from .dice import Dice 
            self.say(message, Dice.print_dice(dice))
            one_liner = Dice.print_dice_one_liner(dice + [(value, "sum")])
            if one_liner is not None:
                self.say(message, one_liner)
        
        self.say(message, "You got a **{}**".format(value))
        
        await self.say_message(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @commands.command(pass_context=True)
    async def stats(self, ctx: commands.Context, *params):
        """
        manipulate the your stats.  say `help stats` for more details

        - stats                     (List all of your stats)
        - stats set <stat> <value>  (set a specific stat)
        - stats del <stat>          (delete a stat)
        - stats <stat>              (show a single stat)
        """

        message = list()

        params = [p.lower() for p in params]

        server = db.database[ctx.message.server.id]
        user = server.get_user(ctx.message.author.id)

        def usage():
            self.say(message, "Usage:\n```")
            self.say(message, server.prefix + "stats")
            self.say(message, server.prefix + "stats set <stat> <value>")
            self.say(message, server.prefix + "stats del <stat>")
            self.say(message, server.prefix + "stats <stat>\n```")

        if len(params) is 0:  # Print all stats
            if len(user.stats) is 0:
                self.say(message, "You don't have any stats")
                self.say(message, "Use `{pre}stats set <stat> <value>` to add stats".format(pre=server.prefix))
            else:
                self.say(message, '```')
                self.say(message, user.description)
                self.say(message, '```')
            await self.say_message(message)
            return
        
        if len(params) is 1:
            # Check for too few params
            if params[0] in ["set", 'del']:
                self.say(message, "Usage: `{pre}stats {} <stat>{}`".format(
                    params[0], ' <value>' if params[0] == 'set' else '', pre=server.prefix))
            else:
                # Show Single Stat
                stat = user.stats.get(params[0])
                if stat is None:
                    self.say(message, "Couldn't find `{}` stat".format(params[0]))
                    await self.say_message(message)
                    return
                
                self.say(message, "```\n{}: {}\n```".format(params[0], stat))
            await self.say_message(message)
            return
        
        if len(params) is 2:
            # Check for too few params
            if params[0] == "set":
                self.say(message, "Usage: `{pre}stats set <stat> <value>`".format(pre=server.prefix))
            else:
                if params[0] == "del":  # Delete a stat
                    if params[1] in user.stats:
                        self.say(message, "Deleted " + params[1])
                        del user.stats[params[1]]
                        server.save()
                    else:
                        self.say(message, "Could not find " + params[1])
                else:
                    usage()
            await self.say_message(message)
            return
        
        # Set a stat
        if params[0] == "set":
            user.stats[params[1]] = '(' + " ".join(params[2:]) + ')'
            self.say(message, "Set {} to `{}`".format(params[1], ' '.join(params[2:])))
            server.save()
        else:
            usage()
        await self.say_message(message)