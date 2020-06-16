FROM python:3.6

WORKDIR /usr/src/app

# Install the bot
COPY dice_roller/ dice_roller/
COPY setup.py README.md ./
RUN pip install . mysqlclient

COPY . .

CMD [ "dice_roller" ]
