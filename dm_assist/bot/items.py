import logging
import asyncio
import re

from discord.ext import commands

from ..config import config
from .. import util
from ..db import db, schemas


class Items:

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(__name__)
        self._item_regex = re.compile(r"([\S]+(?=:)|(?<=:)[\d]+|[^:\s]+|(?<!\S)(?=:))")
    
    @staticmethod
    def say(messages, string):
        if string is not None:
            messages.append(string)
    
    async def say_message(self, messages):
        message = '\n'.join(messages)
        if message:
            await self.bot.say(message)

    def get_item(self, message, server, name: str) -> schemas.Item:
        # Seperate the name from the id with support for emojis
        item_name = re.findall(self._item_regex, name)

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


    def check_permissions(self, ctx: commands.Context, item: schemas.Item):
        author = ctx.message.author

        if author.id == item.creator.id:
            return True
        
        if author.id in config.config.mods:
            return True
        
        try:
            if author.server_permissions.manage_server:
                return True
        except:
            pass

        return False

    async def items_manipulate(self, ctx: commands.Context, server: schemas.Server, command: str, item_name: str, item_desc: str = None) -> list:
        message = list()

        if command == "add":
            item = schemas.Item(item_name, creator=server.get_user(ctx.message.author.id))
            server.add_item(item)
            server.save()
            self.say(message, "Added " + item.short_desc)
            self.say(message, "Use `{pre}item {} add <name> <equation>` to give it an equation".format(
                item.short_desc, pre=server.prefix))
        elif command == "del":
            item = self.get_item(message, server, item_name)
            if item is not None:
                if self.check_permissions(ctx, item):
                    self.say(message, "Deleted " + item.short_desc)
                    server.items.remove(item)
                    server.save()
                else:
                    self.say(message, "You don't have permissions to delete that item.")
        elif command == "desc":
            item = self.get_item(message, server, item_name)
            if item is not None:
                if self.check_permissions(ctx, item):
                    item.desc = item_desc
                    server.save()
                    self.say(message, "Changed {}'s description".format(item.short_desc))
                else:
                    self.say(message, "You don't have the permission to set this item's description")
        return message
    
    async def items_edit(self, ctx: commands.Context, server: schemas.Server, command: str, item_name: str, equation_name: str, equation: str = None):
        message = list()

        if command == 'del':
            item = self.get_item(message, server, item_name)
            if item is not None:
                equation = item.equations.get(equation_name)
                if equation is not None:
                    if self.check_permissions(ctx, item):
                        self.say(message, "Deleted {} from {}".format(equation_name.capitalize(), item.short_desc))
                        del item.equations[equation_name]
                        server.save()
                    else:
                        self.say(message, "You don't have the permissions to change that item")
                else:
                    self.say(message, "Could not find {} in {}".format(equation_name.capitalize(), item.short_desc))
        else:
            item = self.get_item(message, server, item_name)
            if item is not None:
                if self.check_permissions(ctx, item):
                    eq = item.equations.get(equation_name)
                    if command == 'add':  # Add Equation
                        if eq is not None:
                            self.say(message, "{} already exists, use `{pre}items {} edit {} {}` to change its equation".format(
                                equation_name.capitalize(), item_name, equation_name, equation, pre=server.prefix))
                        else:
                            item.equations[equation_name] = equation
                            server.save()
                            self.say(message, "added equation {} for {}".format(equation_name.capitalize(), item.short_desc))
                    elif command == 'edit':  # Edit Equation
                        if eq is None:
                            self.say(message, "{} doesn't exists, use `{pre}items {} add {} {}` to add that equation".format(
                                equation_name.capitalize(), item_name, equation_name, equation, pre=server.prefix))
                        else:
                            item.equations[equation_name] = equation
                            self.say(message, "edited equation {} in {}".format(equation_name.capitalize(), item.short_desc))
                            server.save()
                    elif command == 'desc':  # CHange Description
                        if eq is None:
                            self.say(message, "{} doesn't exists, use `{pre}item {} add {} {}` to add that equation".format(
                                equation_name.capitalize(), item_name, equation_name, equation, pre=server.prefix))
                        else:
                            item.eq_desc[equation_name] = equation
                            self.say(message, "Changed {}'s description for {}".format(item.short_desc, equation_name))
                            server.save()

                else:
                    self.say(message, "You don't have permission to change that item.")
            else:
                self.say(message, "I couldn't find `{}` did you spell it right?".format(item_name))
        
        return message

    async def roll(self, ctx: commands.Context, server: schemas.Server, item: str, name=None, *params):
        """
        Roll an item's equation

        Usage: <item> [name] [param0] [param1] ...

        If you don't specify an equation name, then the top equation will be used.

        Note: you cannot add paramters if you don't specify the name

        Parameters are manditory if the equation uses them.  a paramter is specified by {0}, {1}, etc.
        """

        message = list()

        user = server.get_user(ctx.message.author.id)
        
        item_obj = self.get_item(message, server, item)
        if item_obj is None:
            await self.say_message(message)
            return
        
        if len(item_obj.equations) is 0:
            self.say(message, "{} doesn't have any equations yet.")
            self.say(message, "Use `{pre}items {} add <name> <equation>` to give it an equation".format(
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

        check_vars = re.compile(r"{(.*?)}")

        # Parse any variables in the equation first.
        loop = 0
        while len(re.findall(check_vars, ''.join(params) + equation)) > 0:
            loop += 1
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
            
            if loop >= 20:
                self.say(message, "Detected a circular dependancy in your variables.")
                self.say(message, "I can't calculate your equation because of this, you will need to fix the issue before you try again.")
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
        
        self.say(message, "**{}**".format(value))
        
        await self.say_message(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @commands.command(pass_context=True)
    async def items(self, ctx: commands.Context, *params):
        """
        manipulate or roll the server's items.  say `help items` for more details

        - items:                                 lists all the items
        - items add <item>:                      adds a new item
        - items del <item>:                      deletes an item
        - items desc <item> <desc>:              Sets a description to an item

        - items <item>:                          lists item equations
        - items <item> add <name> <equation>:    adds a new equation
        - items <item> del <name>:               deletes an equation
        - items <item> edit <name> <equation>:   edits an item equation
        - items <item> desc <name> <desc>:       Sets a description to an equation
        - items <item> <name> [0] [1] ...        calculates an item equation

        item can either be the item's name (`sword`), name and id (`sword:5`), or just id (`:5`)

        When creating an equation, you can use variables denoted by {} variables can be set either
        through the `stats` command or through parameters.  If you had a stat called level; You could
        get that stat by using {level} in your equation.  If you wanted to use a parameter in your equation,
        use the parameter number starting at 0 ie. the first parameter is {0}, the second is {1}, and so on.

        Here is an example equation for magic missile:

        ceil({level} / 2)d4 + ceil({level} / 2)

        magic missile gets 1 missile at 1st level that does 1d4 + 1, and an extra missile for every other
        level beyond first (1 at 1st level, 2 at 3rd, 3 at 5th, etc.)

        If I wanted to do a number of magic missiles, I could use a parameter instead of levels:

        {0}d4 + {0}

        When I call the equation `items magic_missile num 5`, `5` is the first argument which is the variable {0},
        so this will equate to 5d4 + 5.
        """

        message = []

        server = db.database[ctx.message.server.id]

        params = [p.lower() for p in params]

        usages = dict(
            add_item=(server.prefix + 'items add <item>'),
            del_item=(server.prefix + 'items del <item>'),
            desc_item=(server.prefix + 'items desc <item> <description>'),
            item_add=(server.prefix + 'items <item> add <name> <equation>'),
            item_del=(server.prefix + 'items <item> del <name>'),
            item_edit=(server.prefix + 'items <item> edit <name> <equation>'),
            item_desc=(server.prefix + 'items <item> desc <name> <desc>'),
            item_name=(server.prefix + 'items <item> <name> [0] [1] ...')
        )

        def usage():
            self.say(message, 'Usage:\n```\n')
            for usage in usages.values():
                self.say(message, usage)
            self.say(message, '```')

        if len(params) is 0:  # List Items
            if len(server.items) is 0:
                self.say(message, 'There are no items.')
                await self.say_message(message)
                return

            all_items = server.items
            your_items = [item for item in all_items if item.creator.id == ctx.message.author.id]
            other_items = [item for item in all_items if item not in your_items]

            self.say(message, 'here is a list of all the items:')
            self.say(message, '```\nYour Items:\n' + '-' * 10)
            self.say(message, '\n'.join([i.short_desc for i in your_items]))
            self.say(message, '\nOther Items:\n' + '-' * 10)
            self.say(message, '\n'.join([i.short_desc for i in other_items]))
            self.say(message, '```')
            await self.say_message(message)
            return
        
        if len(params) is 1:  # Describe Item
            params = params[0]

            # Check for not enough arguments
            if params in ['add', 'del', 'desc']:
                self.say(message, usages[params + '_item'])
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
            if params[1] in ['add', 'del', 'edit', 'desc']:
                self.say(message, usages['item_' + params[1]])
                await self.say_message(message)
                return
            
            if params[0] in ['add', 'del', 'desc']:
                message.extend(await self.items_manipulate(ctx, server, params[0], params[1]))
            else:
                await self.roll(ctx, server, params[0], params[1])

            await self.say_message(message)
            return
        
        if len(params) is 3:

            # Check for not enough arguments
            if params[1] in ['add', 'edit', 'desc']:
                self.say(message, usages['item_' + params[1]])
                await self.say_message(message)
                return
            
        
        # Check if these commands are valid
        if params[1] in ['add', 'edit', 'del', 'desc']:
            message.extend(await self.items_edit(ctx, server, params[1], params[0], params[2], ' '.join(params[3:])))
        elif params[0] == 'desc':
            message.extend(await self.items_manipulate(ctx, server, params[0], params[1], ' '.join(params[2:])))
        else:
            await self.roll(ctx, server, params[0], params[1], *params[2:])

        await self.say_message(message)


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