import discord
from discord.ext import commands
from os import listdir

class ANSI:
    reset = '\033[0m'
    bold = '\033[1m'
    faint = '\033[2m'
    italic = '\033[3m'
    underline = '\033[4m'
    invert_colors = '\033[7m'
    # color set 1
    black = '\033[30m'
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    purple = '\033[34m'
    magenta = '\033[35m'
    cyan = '\033[36m'
    # bg color set 1
    bg_black = '\033[40m'
    bg_red = '\033[41m'
    bg_green = '\033[42m'
    bg_yellow = '\033[43m'
    bg_purple = '\033[44m'
    bg_magenta = '\033[45m'
    bg_cyan = '\033[46m'
    bg_white = '\033[47m'
    # color set 2
    lblack = '\033[90m'
    lred = '\033[91m'
    lgreen = '\033[92m'
    lyellow = '\033[93m'
    lpurple = '\033[94m'
    lmagenta = '\033[95m'
    lcyan = '\033[96m'
    # bg color set 2
    bg_lblack = '\033[100m'
    bg_lred = '\033[101m'
    bg_lgreen = '\033[102m'
    bg_lyellow = '\033[103m'
    bg_lpurple = '\033[104m'
    bg_lmagenta = '\033[105m'
    bg_lcyan = '\033[106m'

    @classmethod
    def print(cls, colors, *txt):
        if isinstance(colors, list):
            print(''.join([getattr(cls, color) for color in colors]), *txt, cls.reset, sep='')
            return
        print(getattr(cls, colors), *txt, cls.reset, sep='')

    @classmethod
    def rainbowtest(cls):
        colors = [key for key in cls.__dict__.keys() if not key.startswith('__') and key != 'print' and key != 'rainbowtest']
        for key in colors:
            ANSI.print(key, key)
            


def guild_or_dm(ctx):
    """
    If the context is in a guild, use the guild info, else use the DM info.
    """
    return ctx.guild if ctx.guild != None else ctx.channel

def override_signature(cmd, new_sig):
    """
    Overrides regular signature with user-defined one
    """
    cmd.orsig = new_sig

def get_exts():
    """
    Returns all extensions / cogs.
    """
    return ['cogs.' + ext[:-3] for ext in listdir('./cogs/') if ext[-3:] == '.py']