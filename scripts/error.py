import discord
from discord.ext import commands
from scripts.util import ANSI, get_exts
import math
from asyncio import sleep

async def check(ctx, err):
    if isinstance(err, l := commands.NotOwner):
        await ctx.send('No.')
        return l

    if isinstance(err, l := commands.CheckFailure):
        await ctx.send('❌ ' + str(err))
        return l

    if isinstance(err, l := commands.BadArgument):
        err_str = str(err)
        err_str = err_str[0].lower() + err_str[1:]
        err_str = err_str[:-1] if err_str.endswith('.') else err_str
        err_str += '' if err_str.endswith('!') else '!'
        await ctx.send('Silly rabbit, ' + err_str)
        return l

    if isinstance(err, l := commands.MissingRequiredArgument) or isinstance(err, l := commands.TooManyArguments):
        await ctx.send_help(ctx.command)
        return l

    if isinstance(err, l := commands.DisabledCommand): # i don't have this
        await ctx.send(f'{ctx.prefix}{ctx.command} is disabled. Unfortunate.')
        return l
    if isinstance(err, l := commands.CommandOnCooldown): # or this
        await ctx.message.add_reaction('🛑')
        await sleep(err.retry_after)
        await ctx.message.remove_reaction('🛑', ctx.bot.user)
        return l

    if isinstance(err, l := commands.CommandInvokeError):
        await ctx.send(type(err).__name__ + ': ' + str(err))
        return l

    if isinstance(err, l := commands.UserInputError):
        await ctx.send(type(err).__name__ + ': ' + str(err))
        return l

    if isinstance(err, l := commands.CommandError):
        return l