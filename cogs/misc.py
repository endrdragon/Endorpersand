import discord
from discord.ext import commands
import itertools

class Misc(commands.Cog):
    '''
    Miscellaneous commands
    '''
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        '''
        Checks ping.
        '''
        file = discord.File("./assets/mrping.png")
        await ctx.send(file=file)
        await ctx.send('**{}ms**'.format(round(self.bot.latency * 1000)))

    @commands.command()
    async def copy(self, ctx, *, args):
        '''
        Copies what you say.
        '''
        await ctx.send(discord.utils.escape_mentions(args))

    @commands.command()
    @commands.cooldown(1, 3)
    async def cooldown(self, ctx):
        '''
        Command with a cooldown.
        '''
        await ctx.send('🥶')

class EndorpersandHelp(commands.MinimalHelpCommand):
    # Most of the code is taken from discord.py source code
    def __init__(self):
        super().__init__(command_attrs={
            'brief': 'Provides command information for this bot',
            'help': "HELP! SOMEBODY TRAPPED ME IN A BOT AND I CAN'T GET OUT!!! SOMEONE PLEASE HELP"
        })
        [self.get_ending_note, self.get_opening_note] = [super().get_opening_note, super().get_ending_note]

    def get_command_signature(self, command):
        fstr = '%s%s %s' % (self.clean_prefix, command.qualified_name, command.orsig if hasattr(command, 'orsig') else command.signature)
        return fstr.strip()

    def add_bot_commands_formatting(self, commands, heading):
        """Adds the minified bot heading with commands to the output.
        The formatting should be added to the :attr:`paginator`.
        The default implementation is a bold underline heading followed
        by commands separated by an EN SPACE (U+2002) in the next line.
        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            A list of commands that belong to the heading.
        heading: :class:`str`
            The heading to add to the line.
        """
        # ^ ?somewords tl;dr commands on e&help [no args]
        if commands:
            # U+00B7 Middle Dot
            joined = ' \xB7 '.join(f'`{c.name}`' for c in commands) # added interpunct and code block text
            self.paginator.add_line(f'**══ {heading} ══**') # added bars, removed underlines
            self.paginator.add_line(joined)

    def add_command_formatting(self, command):
        """A utility function to format commands and groups.
        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """

        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = f"══ {self.get_command_signature(command)} ══" # added bars
        if command.aliases:
            self.paginator.add_line(signature)
            self.add_aliases_formatting(command.aliases)
        else:
            self.paginator.add_line(signature, empty=True)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()
                    
    def add_subcommand_formatting(self, command, italicize=False):
        """Adds formatting information on a subcommand.
        The formatting should be added to the :attr:`paginator`.
        The default implementation is the prefix and the :attr:`Command.qualified_name`
        optionally followed by an En dash and the command's :attr:`Command.short_doc`.
        Parameters
        -----------
        command: :class:`Command`
            The command to show information of.
        """
        if italicize: # included italicization option
            fmt = '*`{0}`* \N{EN DASH} {1}' if command.short_doc else '*`{}`*'
        else:
            fmt = '`{0}` \N{EN DASH} {1}' if command.short_doc else '`{}`'
        self.paginator.add_line(fmt.format(self.get_command_signature(command), command.short_doc))

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        def get_category(command): # reorganize e&help so that it's in the order: [Alphabetized categories], Misc, No Category
            cog = command.cog
            if cog.qualified_name == 'Misc':
                return '\u200bMisc'
            return cog.qualified_name if cog is not None else f'\u200c{self.no_category}'

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_bot_commands_formatting(commands, category)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        self.paginator.add_line(f'**{self.commands_heading}**')
        
        filtered = await self.filter_commands(group.commands, sort=True)
        for command in sorted(filtered, key=lambda cmd: cmd.name):
            self.add_subcommand_formatting(command)

        # don't hide filtered out commands, but rather, italicize them
        for command in sorted((cmd for cmd in group.commands if cmd not in filtered), key=lambda cmd: cmd.name):
            self.add_subcommand_formatting(command, True)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    async def send_cog_help(self, cog):
        bot = self.context.bot
        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        if cog.description:
            self.paginator.add_line(cog.description, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        if filtered:
            self.paginator.add_line('**%s %s**' % (cog.qualified_name, self.commands_heading))
            for command in filtered:
                self.add_subcommand_formatting(command)
            # don't hide filtered out commands, but rather, italicize them
            for command in sorted(cog.get_commands(), key=lambda cmd: cmd.name):
                if command in filtered: continue
                self.add_subcommand_formatting(command, True)

        else: # the entire cog failed the check, so italicize everything
            self.paginator.add_line('**_%s %s_**' % (cog.qualified_name, self.commands_heading))
            for command in cog.get_commands():
                self.add_subcommand_formatting(command, True)
        
        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

def setup(bot):
    cog = Misc(bot)
    bot.add_cog(cog)
    bot.help_command = EndorpersandHelp()
    bot.help_command.cog = cog
