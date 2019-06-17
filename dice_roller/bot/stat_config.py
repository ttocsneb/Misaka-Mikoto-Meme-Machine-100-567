import logging
import asyncio

from discord.ext import commands

from .. import util, db
from ..db import config_loader
from ..config import config


class Config:

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
    def get_loader(cls, message=None):
        desc_loader = config_loader.ConfigDescLookupLoader()
        try:
            # allow files because the uri is set on the host machine
            text = util.read_uri(config.config.stat_config, allow_file=True)
            return desc_loader.load_json(text).data
        except Exception as e:
            cls._logger.debug(e)
            if message is not None:
                cls.say(message, "I can't find the list")

    @classmethod
    def get_config(cls, name, message=None, loader=None):
        if not loader:
            loader = cls.get_loader(message)
            if not loader:
                return

        conf_loader = config_loader.ConfigLoader()
        try:
            # allow files because the uri is set on the host machine
            text = util.read_uri(loader[name.lower()].uri, allow_file=True)
            return conf_loader.load_json(text).data
        except Exception as e:
            cls._logger.debug(e)
            if message is not None:
                cls.say(message, "I can't find the config `{}`".format(name))

    @classmethod
    def load_config(cls, name, message=None, loader=None):
        # Try to load the config from the default configurations
        temp_message = list()
        config = cls.get_config(name, temp_message, loader)
        if config is not None:
            if message is not None:
                message.extend(temp_message)
            return config, 'name'

        temp_message.clear()

        # Try to load the config from a url
        import traceback
        conf_loader = config_loader.ConfigLoader()
        import urllib.error
        try:
            text = util.read_uri(name)
            return conf_loader.load_json(text).data, 'url'
        except urllib.error.URLError:
            pass
        except Exception as e:
            cls._logger.debug(e)
            if message is not None:
                cls.say(message, "I can't read that url")
            return None, 'url'

        # Try to load the config as a json string

        try:
            return conf_loader.load_json(name).data, 'json'
        except Exception as e:
            cls._logger.debug(e)
            if message is not None:
                cls.say(message, "I can't understand your json")
            return None, 'json'

    @commands.group(pass_context=True, aliases=['conf', 'c'])
    async def config(self, ctx: commands.Context):
        """
        Configure the server stats

        There are several configurations already made that can be used.
        You can see them by the command `config list`

        You can implement a configuration by running the command
        `config set <config>`

        If there is another configuration that isn't available, you can use
        either a url to the config, or paste in the config directly.
        """

        if ctx.invoked_subcommand is not None:
            return

        message = list()

        desc = self.get_loader(message)
        if not desc:
            await self.send(message)
            return

        self.say(message, "```markdown")
        for name, item in desc.items():
            self.say(message, "#{}\n- {}".format(name, item.desc))
        self.say(message, "```")

        await self.send(message)

    @config.command(pass_context=True, usage="<name|url|json>",
                    aliases=['get'], name='info')
    async def c_info(self, ctx: commands.Context, *, name: str):
        """
        Get info about a configuration

        Prints information about what will be changed when you apply a
        configuration
        """

        message = list()

        config, method = self.load_config(name, message)
        if not config:
            await self.send(message)
            return

        if method == 'name':
            print_name = name
        elif method == 'url':
            print_name = 'The url'
        else:
            print_name = 'The JSON'

        stats = db.data_models.Stats(None, config.stats)
        from .stats import Stats

        self.say(message, "{} will add the following:".format(print_name))
        self.say(message, "Stats:")

        self.say(message, "```python")
        for group in stats.iter_groups():
            Stats.print_group(message, stats.get_group(group))
        self.say(message, "```")

        eq_message = list()

        self.say(eq_message, "Equations:")
        self.say(eq_message, "```python")

        config.equations.sort(key=lambda x: x.name)
        eq_names = [eq.printName() for eq in config.equations]
        max_name_width = max(map(len, eq_names))

        self.say(eq_message, '\n'.join(
            '{0:>{w}} = {1}'.format(
                name, eq.value, w=max_name_width
            ) for name, eq in zip(eq_names, config.equations)))
        self.say(eq_message, "```")

        if len('\n'.join(message + eq_message)) > 2000:
            await self.send(message)
            await self.send(eq_message)
        else:
            await self.send(message + eq_message)

    @config.command(pass_context=True, usage="<name|url|json>", name='apply')
    async def c_apply(self, ctx: commands.Context, *, name: str):
        """
        Apply a configuration to the server.

        Warning: this is not automatically reversable.  If you want to remove
        a configuration, you will have to manually remove the default
        stats/equations
        """

        message = list()
        config, method = self.load_config(name, message)
        if config is None:
            await self.send(message)
            return

        if method == 'name':
            print_name = name
        elif method == 'url':
            print_name = 'the url'
        else:
            print_name = 'the JSON'

        with db.database.session() as session:
            user = db.database.getUserFromCtx(session, ctx, True, False)[0]

            if not user.checkPermissions(ctx):
                self.say(message,
                         "You don't have permission to apply configurations")
                await self.send(message)
                return

            # Apply the equations to the server

            # Existing equation dictionary
            equations = dict(
                (e.name, e) for e in session.query(
                    db.schema.Equation).filter_by(
                        server_id=user.active_server_id
                ).all()
            )

            def apply_eq(equation):
                # Check if the equation exists in the server
                if equation.name in equations:
                    eq = equations[equation.name]
                    eq.value = equation.value
                    eq.desc = equation.desc
                    eq.params = equation.params
                    eq.creator_id = user.id
                else:
                    equation.server_id = user.active_server_id
                    user.all_equations.append(equation)

            for eq in config.equations:
                apply_eq(eq)

            # Apply the default stats

            # All the default stats as a dict
            default_stats = dict(
                (s.fullname, s) for s in session.query(
                    db.schema.RollStat).filter_by(
                        server_id=user.active_server_id
                ).all()
            )

            def apply_stat(stat):
                # Check if the stat exists in the server, and replace it
                if stat.fullname in default_stats:
                    st = default_stats[stat.fullname]
                    st.value = stat.value
                else:
                    stat.server_id = user.active_server_id
                    session.add(stat)

            for stat in config.stats:
                apply_stat(stat)

            session.commit()

            self.say(message, "Successfully applied {} to the server".format(
                print_name))

            await self.send(message)
