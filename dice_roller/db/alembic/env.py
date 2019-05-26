from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine
from logging.config import fileConfig
import logging
import re

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# fileConfig(config.config_file_name)
# logger = logging.getLogger('alembic.env')

# gather section names referring to different
# databases.  These are named "engine1", "engine2"
# in the sample .ini file.
# db_names = config.get_main_option('databases')

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from dice_roller.db.schema import Base as model
metadata = model.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

from dice_roller.config import config
db_file = config.config.db_file


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # for the --sql use case, run migrations for each URL into
    # individual files.

    is_sqlite = db_file.startswith("sqlite:")
    context.configure(
        url=db_file,
        target_metadata=metadata,
        literal_binds=True,
        render_as_batch=is_sqlite
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    
    is_sqlite = db_file.startswith("sqlite:")

    connectable = create_engine(db_file)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
            render_as_batch=is_sqlite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
