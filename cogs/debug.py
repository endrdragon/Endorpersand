import discord
from discord.ext import commands
from scripts.util import get_exts, ANSI, guild_or_dm
from traceback import print_exc
from bot import reload_errors

class Debug(commands.Cog):
    '''
    <@322059317689974799>'s debugging commands
    '''
    def __init__(self, bot):
        self.bot = bot

    # Owner only #
    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner('You do not own this bot.')
        return True

    def reload_exts(self):
        '''
        Reloads exts, and returns any extensions which failed to load.
        '''
        fails = []
        for ext in get_exts():
            try:
                self.bot.reload_extension(ext)
            except Exception as e:
                fails.append(ext)
                ANSI.print('red', str(e))
                print_exc()
        return fails

    @commands.command()
    async def reload(self, ctx, *exts):
        await self.save_cog_data(ctx)
        if len(exts) == 0:
            fails = self.reload_exts()
            if len(fails) == 0:
                await ctx.send(f'Successfully reloaded all extensions!')
            else:
                await ctx.send(f'Failed to reload: ' + str(fails))
            return fails
        else:
            errored = False
            for ext in exts:
                try:
                    self.bot.reload_extension(ext)
                except Exception as e:
                    ANSI.print('red', str(e))
                    errored = True
                    await ctx.send(f'Failed to reload {ext}')
            if not errored:
                await ctx.send('Successfully reloaded all specified extensions!')

    @commands.command()
    async def run(self, ctx, *, cmd = None):
        '''
        Reloads, then runs the command after it if all reloads were successful.
        '''
        fails = await self.reload(ctx)
        if cmd != '' and cmd != None:
            if len(fails) != 0:
                    await ctx.send('Command cancelled.')
                    return
            ctx.message.content = ctx.prefix + cmd
            await self.bot.process_commands(ctx.message)
        else:
            await ctx.send('No command requested.')

    @commands.command(aliases=['bye', 'fuckoff'])
    async def die(self, ctx):
        '''
        Kills bot
        '''
        await self.save_cog_data(ctx)
        await ctx.send('Bye!')
        exit()

    @commands.command(aliases=['val'])
    async def eval(self, ctx, *, args: str):
        '''
        Evaluates a Python expression. If this is not blocked, then whoops, I'm doomed!
        '''
        # shorthands
        bot = self.bot
        author = ctx.author
        channel = ctx.channel
        guild = guild_or_dm(ctx)
        cogs = bot.cogs

        try:
            await ctx.send(eval(args))
        except Exception as err:
            await ctx.send(str(err))
            ANSI.print('red', str(err))
            print_exc()

    async def save_cog_data(self, ctx):
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'save'):
                try:
                    cog.save()
                except Exception as e:
                    await ctx.send(str(e))
                    ANSI.print('red', str(e))
                    print_exc()


    async def load_cog_data(self, ctx):
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'load'):
                try:
                    cog.load()
                except Exception as e:
                    await ctx.send(str(e))
                    ANSI.print('red', str(e))
                    print_exc()

    @commands.command()
    async def chain(self, ctx, *, args: str):
        '''
        Runs a list of commands separated by semicolons
        '''
        cmds = args.split(';')
        cmds = [cmd.strip() for cmd in cmds]
        for cmd in cmds:
            ctx.message.content = ctx.prefix + cmd
            await self.bot.process_commands(ctx.message)

    @commands.command(name='save')
    async def _save(self, ctx):
        await ctx.send('Saving...')
        await self.save_cog_data(ctx)
        await ctx.send('Done.')

    @commands.command(name='load')
    async def _load(self, ctx):
        await ctx.send('Loading...')
        await self.load_cog_data(ctx)
        await ctx.send('Done.')

def setup(bot):
    bot.add_cog(Debug(bot))
    reload_errors()
    