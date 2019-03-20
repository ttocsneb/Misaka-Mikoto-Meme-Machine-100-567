import asyncio
import math
import re
import logging

_logger = logging.getLogger(__name__)

from discord.ext import commands

from ..config import config
from .. import util

from .. import db

# Roleplay init module
class Dice:

    def __init__(self, bot):
        self.bot = bot
        self._check_vars = re.compile(r"{(.*?)}")
    
    @staticmethod
    def print_dice(dice):
        # This is my job security
        dice_string = ',\n'.join(
            [', '.join(
                ["[{}/{}]".format(x[0], x[1])
                    for x in dice[i*10:i*10+9]
                ]) 
                for i in range(min(int(math.ceil(len(dice) / 10.0)), 4))
            ])

        return "Rolled:\n```python\n{}{}\n```".format(dice_string, '...' if len(dice) > 30 else '')

    @staticmethod
    def print_dice_one_liner(dice):
        """
        Prints at most one one-liner from the rolled dice.

        One liners can be set in the lines setting of the configuration
        """
        one_liners = list()
 
        for die in dice:
            if die[0] is 1 or die[0] is die[1] \
                or die[1] is 1 \
                or str(die[0]) in config.lines.on_roll:
                one_liners.append(die)
 
        if len(one_liners) is not 0:
            one_liner = util.get_random_index(one_liners)
 
            line = "[{l[0]}/{l[1]}]: ".format(l=one_liner)
 
            if one_liner[1] is 1 or one_liner[1] is 0:
                return line + util.get_random_index(config.lines.dumb)
 
            if one_liner[0] is 1:
                return line + util.get_random_index(config.lines.critFails)

            if one_liner[0] is one_liner[1]:
                return line + util.get_random_index(config.lines.crits)

            if str(one_liner[0]) in config.lines.on_roll:
                return line + util.get_random_index(config.lines.on_roll[str(one_liner[0])])

    @staticmethod
    def say(messages, text):
        if text is not None:
            messages.append(str(text))
    
    async def send(self, messages):
        await self.bot.say('\n'.join(messages))

    def get_server(self, ctx: commands.Context, message = None) -> db.Server:
        # If the message is not part of a server, get the active server from the author

        server = db.getDbFromCtx(ctx)
        if server is None:
            if message is not None:
                self.say(message, "You don't have an active server right now :/")
                self.say(message, "Activate the server you want to use first.")
        return server

    @commands.command(pass_context=True, aliases=['calc'])
    async def roll(self, ctx:commands.Context, *, equation: str):
        """
        Calculates an equation.

        The allowed operators are as follows:

        +, -, *, /, ^, %, d

        (Note: the d operator is used for dice: 2d20 rolls 2, 20 sided dice)

        You can include all other Dice commands in your equation:

        * adv(sides)
        * dis(sides)
        * top(num, sides, top_dice)
        * bot(num, sides, bot_dice)

        Other mathematical functions are also allowed:

        * round(a)      round to the nearest whole number
        * floor(a)      round down
        * ceil(a)       round up
        * max(a, b)     return the highest number of the two
        * min(a, b)     return the lowest number of the two

        You may also use your stats as variables.  A variable
        is surrounded by {}, so if you have a stat called 'level',
        you could use it in your equation with: {level}

        Example equation:

          1d20 + floor({level} / 2)
        """

        message = list()

        # Parse any variables in the equation first
        server = self.get_server(ctx)
        if server is not None:
            session = server.createSession()
            user = server.getUser(session, ctx.message.author.id)
        else:
            session = None
            user = None

        try:
            if server is not None:
                equation = util.calculator.parse_args(equation, session, user)
            util.dice.logging_enabled = True
            value = util.calculator.parse_equation(equation, session, user)
            util.dice.logging_enabled = False
        except util.BadEquation as exception:
            self.say(message, exception)
            await self.send(message)
            return
        
        dice = util.dice.rolled_dice
        if len(dice) > 0:
            self.say(message, self.print_dice(dice))
            self.say(message, self.print_dice_one_liner(dice + [(value, "sum")]))

        self.say(message, "**{}**".format(value))
        await self.send(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @commands.command() #coinflip stuff
    async def coinflip(self):
        '''Flips a coin.'''
        HeadTails = util.dice.roll(2)

        if HeadTails == 1:
            await  self.bot.say("Tails, but you're dead either way")
        else:
            await  self.bot.say("Heads, but you're dead either way")

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())
        
    
    @commands.command()
    async def adv(self, sides='20'):
        """
        Rolls a die with advantage.
        """

        message = list()

        try:
            sides = int(sides)
        except ValueError:
            self.bot.say("That's not a number, silly.")
            return

        d1 = util.dice.roll(sides)
        d2 = util.dice.roll(sides)

        final = max(d1, d2)

        self.say(message, "You rolled a {}, and a {}.\n you got a **{}**.".format(d1, d2, final))
        if d1 is d2:
            self.say(message, "You're dead either way :)")
        
        self.say(message, self.print_dice_one_liner([(d1, sides), (d2, sides)]))
        await self.send(message)
    
        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())

    @commands.command()
    async def dis(self, sides='20'):
        """
        Rolls a die with disadvantage.
        """

        message = list()

        try:
            sides = int(sides)
        except ValueError:
            await self.bot.say("That's not a number, silly.")
            return

        d1 = util.dice.roll(sides)
        d2 = util.dice.roll(sides)

        final = min(d1, d2)

        self.say(message, "You rolled a {}, and a {}.\n you got a **{}**.".format(d1, d2, final))
        if d1 is d2:
            self.say(message, "You're dead either way :)")

        self.say(message, self.print_dice_one_liner([(d1, sides), (d2, sides)]))
        await self.send(message)

        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())
    
    @commands.command()
    async def top(self, times='4', sides='6', top_dice='3'):
        """
        Rolls a number of dice, and takes only the top dice.
        """

        message = list()

        try:
            sides = int(sides)
            times = int(times)
            top_dice = int(top_dice)
        except ValueError:
            self.bot.say("You're supposed to enter number not whatever that was")
            return

        util.dice.logging_enabled = True
        sum = util.dice.roll_top(sides, top_dice, times)
        util.dice.logging_enabled = False

        dice = util.dice.rolled_dice
        if len(dice) > 1:
            self.say(message, self.print_dice(dice))
        
        one_liner = self.print_dice_one_liner(dice + [(sum, sides * top_dice)])
        if one_liner is not None:
            self.say(message, one_liner)
        
        self.say(message, "You got **{}**".format(sum))
        await self.send(message)
        
        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())
    
    @commands.command(name='bot')
    async def _bot(self, times='4', sides='6', top_dice='3'):
        """
        Rolls a number of dice, and takes only the bottom dice.
        """

        message = list()

        try:
            sides = int(sides)
            times = int(times)
            top_dice = int(top_dice)
        except ValueError:
            self.bot.say("You're supposed to enter number not whatever that was")
            return

        util.dice.logging_enabled = True
        sum = util.dice.roll_top(sides, top_dice, times, False)
        util.dice.logging_enabled = False

        dice = util.dice.rolled_dice
        if len(dice) > 1:
            self.say(message, self.print_dice(dice))
        
        one_liner = self.print_dice_one_liner(dice + [(sum, sides * top_dice)])
        if one_liner is not None:
            self.say(message, one_liner)
        
        self.say(message, "You got **{}**".format(sum))
        await self.send(message)
        
        if util.dice.low:
            asyncio.ensure_future(util.dice.load_random_buffer())
