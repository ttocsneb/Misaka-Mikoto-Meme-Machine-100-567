[![Build Status](https://github.drone.home.benscraft.info/api/badges/ttocsneb/discordDiceBot/status.svg)](https://github.drone.home.benscraft.info/ttocsneb/discordDiceBot)
[![CodeFactor](https://www.codefactor.io/repository/github/ttocsneb/discorddicebot/badge)](https://www.codefactor.io/repository/github/ttocsneb/discorddicebot)

# Discord Dice Roller Bot

This bot is still in early stages of development, but you can invite it to your server [using this link](https://discordapp.com/api/oauth2/authorize?client_id=528642271885787137&permissions=0&scope=bot).  It may run on stable development builds ahead of the master branch.  If you would like to host this bot yourself, you are welcome to!

## installation

0. Make sure you have at least python 3.5.x installed!

1. Create a python virtualenv

To create a virtualenv, first install virtualenv with `python3 -m pip install virtualenv`

Next, create the venv in the project directory `python3 -m virtualenv venv`

2. Run the installer.

You can either install manually using the command `python -m pip install -r requirements.txt` after sourcing venv, or by running `install.bat`/`install.sh`

3. Start the bot

You can start the bot with start.bat or start.sh or start.py

If on linux, you can also run `source venv/bin/activate && dice_roller`
