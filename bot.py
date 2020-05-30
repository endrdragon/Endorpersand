import discord
from discord.ext import commands
from scripts.util import ANSI, get_exts
import scripts.error as error
from importlib import reload

bot = commands.Bot(command_prefix='e&', owner_ids={141294044671246337}) # for help_command=..., see bottom of ./cogs/misc.py
# allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False)
try:
    with open("./assets/token.txt", "r") as f:
    	token = f.read()
except FileNotFoundError as e:
    ANSI.print('red', 'Token not found. Add token at ./assets/token.txt')
    raise e

@bot.event
async def on_ready():
    ANSI.print('lgreen', f'Boop! {bot.user} is awake!')

@bot.event
async def on_message(message):
    if not message.author.bot:
        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, err):
    l = await error.check(ctx, err) # send err through discord
    # signify start of error
    if type(err).__name__ == l.__name__:
        ANSI.print('red', type(err).__name__) 
    else:
        ANSI.print('lred', type(err).__name__ + ', halted on ' + l.__name__)
    # print error
    raise err

def reload_errors():
    reload(error)

if __name__ == '__main__':
    for ext in get_exts():
        bot.load_extension(ext)

    bot.run(token)
