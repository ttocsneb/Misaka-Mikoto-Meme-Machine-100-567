import os
from setuptools import setup, find_packages


with open('README.md', 'r') as fh:
      LONG_DESCRIPTION = fh.read()


# All the pip dependencies required for installation.
INSTALL_REQUIRES = [
      'discord.py',
      'ruamel.yaml',
      'marshmallow'
]


def params():

      name = "Discord Dice Roller Bot"

      version = "0.1"

      description = "A discord bot that helps you play Dungeons & Dragons with Discord"

      long_description = LONG_DESCRIPTION
      long_description_content_type = "text/markdown"

      install_requires = INSTALL_REQUIRES

      # https://pypi.org/pypi?%3Aaction=list_classifiers
      classifiers = [
            "Development Status :: 2 - Pre-Alpha",
            "Environment :: Console",
            "Intended Audience :: Other Audience",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: Implementation :: CPython",
            "Topic :: Communications :: Chat",
            "Topic :: Games/Entertainment :: Role-Playing"
      ]
      author = 'Noobot9k, TheVoiceInsideYourHead, Benjamin Jacobs'
      url = 'https://github.com/ttocsneb/discordDiceBot'

      packages = ['dm_assist']  # TODO: Change to dice_roller

      entry_points = {
            'console_scripts': [
                  'dm_assist = dm_assist:serve'
            ]
      }

      return locals()


setup(**params())