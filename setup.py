import os
from setuptools import setup, find_packages


with open('README.md', 'r') as fh:
    LONG_DESCRIPTION = fh.read()


# All the pip dependencies required for installation.
INSTALL_REQUIRES = [
    'alembic==1.4.2',
    'discord.py==1.3.3',
    'marshmallow==3.6.0',
    'ruamel.yaml==0.16.10',
    'SQLAlchemy==1.3.17'
]


setup(
    name="Dice Roller",
    version="0.4.0",
    description="A Discord Dice Rolling bot.",

    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",

    install_requires=INSTALL_REQUIRES,

    # https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Other Audience",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Communications :: Chat",
        "Topic :: Games/Entertainment :: Role-Playing"
    ],
    author='Noobot9k, TheVoiceInsideYourHead, Benjamin Jacobs',
    url='https://github.com/ttocsneb/discordDiceBot',
    packages=['dice_roller'],

    entry_points={
        'console_scripts': [
            'dice_roller = dice_roller:serve'
        ]
    })
