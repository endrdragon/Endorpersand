import discord
from discord.ext import commands
from copy import deepcopy
from scripts.util import ANSI, override_signature, guild_or_dm
import json
from math import inf
from asyncio import sleep
ai = 'AI' # there's really no reason to do this but w/e

# what am i doing
# check makers
def in_game_chk(game):
    def ig_chk(ctx):
        b = ctx.bot.cogs['Games'].in_game(guild_or_dm(ctx), ctx.author, game)
        if not b: raise commands.CheckFailure('You are not in a game!')
        return True
    return ig_chk

def not_in_game_chk(game):
    def fig_chk(ctx):
        b = not ctx.bot.cogs['Games'].in_game(guild_or_dm(ctx), ctx.author, game)
        if not b: raise commands.CheckFailure('You are already in a game!')
        return True
    return fig_chk

def running_chk(game):
    def run_chk(ctx):
        b = ctx.bot.cogs['Games'].curr_game(guild_or_dm(ctx), ctx.author, game).running
        if not b: raise commands.CheckFailure('Game is not currently running!')
        return True
    return run_chk

def paused_chk(game):
    def psd_chk(ctx):
        b = not ctx.bot.cogs['Games'].curr_game(guild_or_dm(ctx), ctx.author, game).running
        if not b: raise commands.CheckFailure('Game must be paused to use this command!')
        return True
    return psd_chk

class Board:
    def __init__(self, **kwargs):

        self.players = kwargs.pop('players', [])
        self.turn = kwargs.pop('turn', 0)
        self.board = kwargs.pop('board', [])
        self.running = kwargs.pop('running', False)
        self.bot = kwargs.pop('bot')

        if not isinstance(self.players, list):
            raise TypeError('Arg players is not a list')
        if not isinstance(self.board, list):
            raise TypeError('Arg board is not a board')
    #def __eq__(self, other):
    #    return (type(self), self.players, self.board) == (type(other), other.players, other.board)
    
    def serial(self):
        return {"players": self.players, "board": self.board}

    def replace(self, new):
        if type(self) != type(new): raise TypeError('Cannot replace Board of different types')
        for attr, val in new.__dict__.items():
            setattr(self, attr, val)

    def copy(self, **kwargs):
        '''
        Shallow copies a board and then replaces specified properties with kwargs
        '''
        clone = self.__class__(**self.__dict__)
        for attr, val in kwargs.items():
            setattr(clone, attr, val)
        return clone

    def player_names(self, i = None):
        pn = [discord.utils.escape_mentions(discord.utils.escape_markdown(self.bot.get_user(player).name)) if player != ai else ai for player in self.players]
        return pn if i == None else pn[i]

class Mancala(Board):
    '''
    Board type
    pl0: [[0,0,0,0,0,0,1],
    pl1: [0,0,0,0,0,0,1]]

    Board[-1] = store
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mobile = kwargs.pop('mobile', False)
        self.special = kwargs.pop('special', None)
        self.total = sum(j for i in self.board for j in i)
        self.size = len(self.board[0]) - 1

    def serial(self):
        return {"players": self.players, "board": self.board, "turn": self.turn, "mobile": self.mobile}
    
    def abbrs(self, i = None):
        pn = [name.upper() for name in self.player_names()]
        if len(pn) == 1:
            a = [pn[0][:3], ''] # Waiting for player => ??? v. 
            return a if i == None else a[i]

        if pn[0] == pn[1]: 
            a = [name[:2] + str(i) for i, name in enumerate(pn)] # wyatt v. wyatt => WY0 v. WY1
            return a if i == None else a[i]

        a = [name[:3] for name in pn] # Balloon_Project v. Bammmyouuu => BAL v. BAM
        if a[0] == a[1]:
            # alex111 v. AlexToucanYT => AL1 v. ALT
            pnset = [list(dict.fromkeys(name)) for name in pn] # remove duplicates from list but keep order
            for i in range(3, min(len(lst) for lst in pnset)):
                if pnset[0][i] == pnset[1][i]: continue
                a = [name[:2] + pnset[j][i] for j, name in enumerate(pnset)]
            else:
                a = [pn[0][:3], pn[1][:2] + pnset[1][i + 1]] # ame vs. Americatress => AME v. AMR
        
        return a if i == None else a[i]

    def display(self, end=False): # this abbrs is a disgusting bodge
        '''
        Displays board.
        ┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼

        game running screen
               ┌──┬──┬──┬──┬──┬──┬──┬──┐
               │  │5 │4 │3 │2 │1 │0 │  │ <- opp
               │6 ├──┼──┼──┼──┼──┼──┤ 6│
        you -> │  │ 0│ 1│ 2│ 3│ 4│ 5│  │
               └──┴──┴──┴──┴──┴──┴──┴──┘
                 >  0  1  2  3  4  5 <
        paused screen
               ┌──┬──┬──┬──┬──┬──┬──┬──┐
               │  │5 │4 │3 │2 │1 │0 │  │ <- opp
               │6 ├──┼──┼──┼──┼──┼──┤ 6│
        you -> │  │ 0│ 1│ 2│ 3│ 4│ 5│  │
               └──┴──┴──┴──┴──┴──┴──┴──┘
               ### PAUSED ###
        end screen
               ┌──┬──┬──┬──┬──┬──┬──┬──┐
               │  │5 │4 │3 │2 │1 │0 │  │
        PL1 -> │6 ├──┼──┼──┼──┼──┼──┤ 6│ <- PL1
               │  │ 0│ 1│ 2│ 3│ 4│ 5│  │
               └──┴──┴──┴──┴──┴──┴──┴──┘
        '''
        c = len(str(self.total)) + 1 # cell size
        [s,b,t,p] = [self.size, self.board, self.turn, self.players]

        if not self.mobile:
            sl =  [ # board w/ no player markers
                '┌' + ('─' * c + '┬') * (s + 1) + ('─' * c) + '┐',
                '│' + (' '  * c) + ''.join('|' + str(slot).ljust(c, ' ') for slot in b[1 - t][-2::-1]) + '│' + (' ' * c) + '│',
                '│' + str(b[1 - t][-1]).ljust(c, ' ') + '├' + ('─' * c + '┼') * (s - 1) + ('─' * c) + '┤' + str(b[t][-1]).rjust(c, ' ') + '│',
                '│' + (' '  * c) + ''.join('|' + str(slot).rjust(c, ' ') for slot in b[t][:-1]) + '│' + (' ' * c) + '│',
                '└' + ('─' * c + '┴') * (s + 1) + ('─' * c) + '┘',
            ]
            # move marker / paused / AI is thinking
            if not end:
                if self.running:
                    if p[t] == ai:
                        aistr = 'AI is making a move...'
                        if (c + 1) * s - 1 >= len(aistr): # add arrows if it fits between the length
                            sl.append(' ' * c + '> ' + aistr.rjust((c + 1) * s - 1, ' ') + ' <')
                        else:
                            sl.append(aistr)
                    else: 
                        va = self.actions(False)
                        movestr = (' ').join((str(i) if i in va else ' ').rjust(c, ' ') for i in range(s))
                        sl.append(' ' * c + '> ' + movestr + ' <')
                else:
                    sl.append('### PAUSED ###')
            # abbrs and arrow markers
            for i in range(len(sl)):
                left = ' ' * 7
                right = ''
                # left-side arrow
                if end and i == 2:
                    left = self.abbrs(1).rjust(c, ' ') + ' -> '
                if not end and i == 3:
                    left = self.abbrs(t).rjust(c, ' ') + ' -> '
                # right-side arrow
                if end and i == 2:
                    right = ' <- ' + self.abbrs(0).ljust(c, ' ')
                if not end and i == 1:
                    right = ' <- ' + self.abbrs(1 - t).ljust(c, ' ')
                
                sl[i] = left + sl[i] + right

            # wrap in ```s
            return '```' + '\n'.join(sl) + '```'
        '''
            Mobile configuration
              YOU
            ┌───────────┐
         V  │     3     │
            ├─────┬─────┤
         0  │  1  │  2  │
            ├─────┼─────┤
         1  │  4  │  5  │
            ├─────┼─────┤
         2  │  7  │  6  │
            ├─────┼─────┤
         3  │  9  │  8  │
            ├─────┼─────┤
         4  │  2  │  1  │
            ├─────┼─────┤
         5  │  3  │  4  │
            ├─────┴─────┤
         Λ  │     5     │
            └───────────┘
                    OPP
        '''
        mc = 2 * c + 1 # mobile cell size
        sl = [
            # top
            '┌' + '─' * (2 * mc + 1) + '┐',
            '│' + str(b[1 - t][-1]).center(2 * mc + 1, ' ') + '│',
            '├' + '─' * mc + '┬' + '─' * mc + '┤'
        ]
        # draw all slots
        for i in range(s):
            sl.append('│' + str(b[t][i]).center(mc, ' ') + '│' + str(b[1-t][s - 1 - i]).center(mc, ' ') + '│')
            if i + 1 == s:
                sl.append('├' + '─' * mc + '┴' + '─' * mc + '┤')
                break
            sl.append('├' + '─' * mc + '┼' + '─' * mc + '┤')
        # bottom
        sl.append('│' + str(b[t][-1]).center(2 * mc + 1, ' ') + '│')
        sl.append('└' + '─' * (2 * mc + 1) + '┘')
        # YOU / OPP
        sl.insert(0, ' ' + self.abbrs(t).center(mc, ' ')) #YOU
        sl.append(' ' * (2 + mc) + self.abbrs(1-t).center(mc, ' ')) #OPP
        
        # move marker / AI marker / paused
        for i in range(1, len(sl), 2):
                sl[i] = ' ' * (c + 1) + sl[i]

        if end or not self.running or p[t] == ai:
            for i in range(0, len(sl), 2):
                sl[i] = ' ' * (c + 1) + sl[i]
        else:
            va = self.actions(False)
            movearr = [' ', 'V', *(str(i) if i in va else ' ' for i in range(s)), 'Λ', ' ']
            movearr = [text.rjust(c - 1, ' ') for text in movearr]
            for i in range(0, len(sl), 2):
                sl[i] = movearr[i // 2] + '  ' + sl[i]

        if not end:
            if self.running:
                if p[t] == ai:
                    sl.extend(['', 'AI is making a move...'])
            else:
                sl.extend(['', '### PAUSED ###'])

        # wrap in ```s
        return '```' + '\n'.join(sl) + '```'


    def path(self, slot):
        """
        Returns path the pebbles go through when distributing
        """
        path = [(self.turn, i) for i in range(self.size + 1)]  # the path through your bank
        path += [(1 - self.turn, i) for i in range(self.size)] # the path through opp bank
        slot += 1
        return path[slot:] + path[:slot] # start path right after the action

    @staticmethod
    def pop(board: list, turn: int, action: int):
        """
        Clears slot as well as returns value of a board
        """
        [v, board[turn][action]] = [board[turn][action], 0]
        return v

    def result(self, actions: list):
        """
        Returns the board that results from making the list of moves specified on the board.
        it's a list of actions, rather than one action to allow the minimax AI to make one whole move
        """
        if len(actions) == 0: return self
        bcopy = deepcopy(self.board)
        for action in actions:
            value = Mancala.pop(bcopy, self.turn, action) # take out the pebbles on the selected slot
            path = self.path(action) # move pebbles around the board

            for i in range(0, value):
                [bank, slot] = path[i % len(path)]
                bcopy[bank][slot] += 1
        
        if bank == self.turn and slot == self.size: return self.copy(board=bcopy, special='again') # if it lands in store, then the player gets to play again
        # if the slot that the pebbles land on was empty and the slot on the opposite side is not empty, then take out the pebble and the pebbles across the slot and add them to the correct store
        if bank == self.turn and bcopy[bank][slot] == 1 and bcopy[1 - bank][(self.size - 1) - slot] > 0:
            store  = Mancala.pop(bcopy, bank, slot)
            store += Mancala.pop(bcopy, 1 - bank, (self.size - 1) - slot)
            bcopy[bank][-1] += store
            return self.copy(board=bcopy, turn = 1 - self.turn, special='capture')
        return self.copy(board=bcopy, turn = 1 - self.turn, special=None) # otherwise, it's the other person's move
            
    def terminal(self):
        """
        Returns True if game is over, False otherwise.
        """
        for side in self.board:
            if all([slot == 0 for slot in side[:-1]]): # if a side is empty, then game over
                return True
            if side[-1] > self.total / 2: # if one player has more than half of the pebbles stored, then game over
                return True
        return False

    def end(self):
        """
        Returns ending board
        """
        if all([slot == 0 for slot in self.board[0][:-1]]) or all([slot == 0 for slot in self.board[1][:-1]]):
            self.board = [[0] * self.size + [sum(side)] for side in self.board]
        # else: just leave the board as is
        self.turn = 0
        return self

    def winner(self):
        """
        Returns the winner of the game, if there is one.
        """
        if self.terminal():
            for side in range(2):
                if self.board[side][-1] > self.board[1 - side][-1]:
                    return side
            return None
        raise Exception('Game has not ended')

    ### AI ###
    def actions(self, iter = True):
        """
        Returns set of all possible indexes available on the board.
        If iter is false, this is a player move and therefore don't recurse
        """
        acts = [index for index, elem in enumerate(self.board[self.turn][:-1]) if elem != 0] # each non-empty slot
        if not iter: return acts
        ras = [[slot] for slot in acts if (slot + self.board[self.turn][slot]) % (self.size * 2 + 1) == self.size] # actions that land in store
        
        acts = [[elem] for elem in acts]
        if len(ras) == 0: return acts
        acts = [elem for elem in acts if elem not in ras] # remove duplicates

        for ra in ras:
            nacts  = self.result(ra).actions() # get possible actions of the next state
            if len(nacts) == 0: # we have an empty side
                acts.append(ra)
            else:
                acts.extend(ra + nact for nact in nacts)
        return acts

    def utility(self):
        """
        Returns the value of a board.
        2 pts per stored pebble
        1 pt for pebble in play
        score: your pts - opp pts
        """
        if self.terminal():
            sums = [sum(side) for side in self.board]
            return 2 * (sums[0] - sums[1]) # since game ended, all pebbles in play are considered stored
        
        bcopy = deepcopy(self.board)
        for side in bcopy: side[-1] *= 2
        sums = [sum(side) for side in bcopy]
        return sums[0] - sums[1]

    def minimax(self, depth):
        """
        Returns the optimal action for the current player on the board.
        """
        if self.turn == 0:
            return self.maxp_score(depth)
        if self.turn == 1:
            return self.minp_score(depth)

    def maxp_score(self, depth = 0, alpha = -inf, beta = inf):
        """
        Given board, returns (value of action, action) of best action on board if player Max
        """
        if self.terminal() or depth == 0:
            return (self.utility(),)

        bact, maxev = [], -inf
        for act in self.actions():
            act_value = self.result(act).minp_score(depth - 1, alpha, beta)[0]
            if maxev < act_value:
                maxev = act_value
                bact = act
            
            alpha = max(alpha, maxev)  #alpha = min score player Max can get
            if alpha >= beta: break # if min Max can get (ɑ) > min Min can get (β), then the rest can be ignored cause Max will choose ɑ
        return (maxev, bact)

    def minp_score(self, depth = 0, alpha = -inf, beta = inf):
        """
        Given board, returns (value of action, action) of best action on board if player Min
        """
        if self.terminal() or depth == 0: 
            return (self.utility(),)
        
        bact, minev = [], inf
        for act in self.actions():
            act_value = self.result(act).maxp_score(depth - 1, alpha, beta)[0]
            if minev > act_value: 
                minev = act_value
                bact = act

            beta = min(beta, minev) # beta = min score player Min can get
            if alpha >= beta: break
        return (minev, bact)

class Uno(Board):
    '''
    Board type: Queue of cards.
    last played -> [1R, 2R, 2B, 4B, ...] <- first played
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.draw_stack = kwargs.pop("draw_stack", True)
        self.jump_in = kwargs.pop("jump_in", False)
        self.seven_o = kwargs.pop("seven_o", False)
        self.color_stack = kwargs.pop("color_stack", False)
        self.rank_stack = kwargs.pop("rank_stack", False)
        self.hand_size = kwargs.pop("hand_size", 7)

class Games(commands.Cog):
    '''
    Bot games
    '''
    def __init__(self, bot):
        self.bot = bot
        self.mancalas = {
            #guild_id: [
            #   Mancala(players, board), ...
            # ]

        }
        self.unos = {

        }
        self.dirs = {
            'mancalas': {'dict': self.mancalas, 'type': Mancala},
            'unos': {'dict': self.unos, 'type': Uno},
        }
        self.load()

    def save(self):
        '''
        Saves data in Cog to disk
        '''
        for dirc, data in self.dirs.items():
            serial_data = {key: [game.serial() for game in guild_glist] for key, guild_glist in data['dict'].items()}
            with open(f"./data/{dirc}.json", "w") as file:
                json.dump(serial_data, file)

    def load(self):
        # load mancala data
        for dirc, data in self.dirs.items():
            try:
                with open(f'./data/{dirc}.json', 'r') as file:
                    serial_data = json.load(file)

                if serial_data != '':
                    for guild_id in serial_data.keys():
                        guild_list = serial_data[guild_id]
                        for gamedict in guild_list:
                            gamedict['bot'] = self.bot
                        data['dict'][int(guild_id)] = [data['type'](**gamedict) for gamedict in guild_list]
            except FileNotFoundError as e:
                ANSI.print('yellow', 'Warning: ' + str(e) + f'\nA new {dirc}.json file will be generated.')
    
    def in_game(self, guild, player, game):
        '''
        Checks if a player is in some game of type [game] in guild [guild]
        '''
        dct = getattr(self, game)
        game_ids = sum((game.players for game in dct[guild.id]), start=[])
        if player.id in game_ids:
            return True
        return False

    def curr_game(self, guild, player, game):
        '''
        Returns game of type [game] player is currently playing in a guild
        '''
        dct = getattr(self, game)
        return next((game for game in dct[guild.id] if player.id in game.players), None)
    ### MANCALA ###
    # Function prefix: mc_, mcf_, mch_

    @commands.group(aliases=['man'])
    async def mancala(self, ctx):
        '''
        Play a Mancala game.

        __How to play Mancala:__
            - On both sides of the board, you have slots with a certain set of pebbles.
            - When playing, you pick up the pebbles in your slot, move counter-clockwise through each of the slots, dropping one pebble in each of the slots (this includes the opponent slots and your store (the large hole after slot 5), but not the opponent's store) until you run out of pebbles.
            - The winner is whoever has the most pebbles in their store by the end of the game.

            __Additional rules:__
                - If your last pebble lands on your store, you get another move.
                - If your last pebble lands on an empty slot on your side of the board, you "capture" the opponent's slot. (This means the pebble you just placed and all of the pebbles on the opposing side are taken and added to your store.)
        '''

        if guild_or_dm(ctx).id not in self.mancalas: 
            self.mancalas[guild_or_dm(ctx).id] = []
        if ctx.invoked_subcommand == None:
            await ctx.send_help('mancala')

    async def mc_finish(self, ctx, additional_message = None):
        """
        Completes game. Triggerable via e&mancala end or by a terminal condition in e&mancala board
        """
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        msg = f'Final board: ' + mancala.display(True)
        if additional_message != None: msg = additional_message + '\n' + msg

        await ctx.send(msg)
        self.mancalas[guild_or_dm(ctx).id].remove(mancala)

    @mancala.command(name='new', aliases=['create', 'make'])
    @commands.check(not_in_game_chk("mancalas"))
    async def mc_new(self, ctx, gametype, size: int = 6):
        '''
        Create a new Mancala game.
        Args:
            Select gametype: player vs. player, player vs. AI, or AI vs. player
            Select board size: The total number of slots on one side of the board
        '''
        # gametype check
        if gametype == 'pvp': 
            if ctx.guild == None:
                raise commands.NoPrivateMessage('PVP mode cannot be played in DMs.')
            players = [ctx.author.id, ]
        elif gametype == 'avp': 
            players = [ai, ctx.author.id]
        elif gametype == 'pva': 
            players = [ctx.author.id, ai]
        else: 
            raise commands.BadArgument('Invalid gametype.')
        # size check
        if size < 1:
            raise commands.BadArgument('Board should at least 1 slot.')
        board = [[4] * size, [4] * size]
        for side in board: side.append(0)
        # display start
        mancala = Mancala(players=players, board=board, bot=self.bot)
        self.mancalas[guild_or_dm(ctx).id].append(mancala)
        await self.mc_board(ctx)

    @mancala.command(name='start',aliases=['unpause'])
    @commands.check(in_game_chk("mancalas"))
    @commands.check(paused_chk("mancalas"))
    async def mc_start(self, ctx):
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        if len(mancala.players) == 1:
            await ctx.send(f'Game cannot start without two players. Type `{ctx.prefix}{self.mcf_ai} true` to add an AI player.')
            return
        mancala.running = True
        await ctx.send(f'Game started! Type `{ctx.prefix}{self.mc_play} [0-{mancala.size - 1}]` to play.')
        await self.mc_board(ctx)
    
    @mancala.command(name='pause')
    @commands.check(in_game_chk("mancalas"))
    @commands.check(running_chk("mancalas"))
    async def mc_pause(self, ctx):
        '''
        Pause the game.
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        mancala.running = False
        await ctx.send('Game paused!')
        await self.mc_board(ctx)

    @mancala.command(name='board')
    @commands.check(in_game_chk("mancalas"))
    async def mc_board(self, ctx):
        '''
        Load board.
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        def gen_player_disp():
            str = ''
            if len(mancala.players) == 1:
                str += 'Waiting for second player...'
            elif mancala.turn == 0:
                str += f'**{mancala.player_names(0)}** vs. {mancala.player_names(1)}'
            else:
                str += f'{mancala.player_names(0)} vs. **{mancala.player_names(1)}**'
            
            if mancala.special == 'capture':
                str += '\nCapture!'
            elif mancala.special == 'again':
                str += '\nFree move!'
            
            return str

        if not mancala.running:
            if len(mancala.players) == 1:
                await ctx.send(gen_player_disp() + mancala.display() + f'\nType `{ctx.prefix}{self.mc_join} [user]` to join!')
                return
            await ctx.send(gen_player_disp() + mancala.display() + f'\nType `{ctx.prefix}{self.mc_start}` to begin!')
            return
        
        await ctx.send(gen_player_disp() + mancala.display())

        if mancala.players[mancala.turn] == ai:
            best_move = mancala.minimax(5)[1]
            await ctx.send(str(best_move))
            await sleep(1)
            for move in best_move:
                mancala.replace(mancala.result([move]))
                await ctx.send(gen_player_disp() + mancala.display())
                await sleep(1)
    
        if mancala.terminal(): # let normal display play but then play the end screen
            mancala.end()
            if winner := mancala.player_names(mancala.winner()):
                await self.mc_finish(ctx, f'**Winner: {winner}**')
            else:
                await self.mc_finish(ctx, 'Tie!')
            return

    @mancala.command(name='play')
    @commands.check(in_game_chk("mancalas"))
    @commands.check(running_chk("mancalas"))
    async def mc_play(self, ctx, slot: int):
        '''
        Select a slot to play.
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        if mancala.players[mancala.turn] != ctx.author.id:
            await ctx.send("It's not your turn!")
            return
        
        if slot < 0 or slot >= mancala.size or mancala.board[mancala.turn][slot] == 0:
            raise commands.BadArgument("You can't play that slot!")
        mancala.replace(mancala.result([slot]))
        await self.mc_board(ctx)

    @mancala.command(name='join')
    @commands.check(not_in_game_chk("mancalas"))
    @commands.guild_only()
    async def mc_join(self, ctx, user: discord.User):
        '''
        Join someone's Mancala game
        '''
        mancala = self.curr_game(guild_or_dm(ctx), user, "mancalas")
        # arg in game check
        if not self.in_game(guild_or_dm(ctx), user, "mancalas") or mancala.running or len(mancala.players) > 1:
            await ctx.send('User is not starting a game!')
            return
        mancala.players.append(ctx.author.id)
        await ctx.send(f"Joined {discord.utils.escape_mentions(user.name)}'s game!")

    @mancala.command(name='leave')
    @commands.check(in_game_chk("mancalas"))
    async def mc_leave(self, ctx):
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        if ai in mancala.players:
            await self.mc_end(ctx)
            return
            
        mancala.running = False
        mancala.players.remove(ctx.author.id)
        await ctx.send('You have left the game.')

    @mancala.command(name='end')
    @commands.check(in_game_chk("mancalas"))
    async def mc_end(self, ctx):
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        if ai not in mancala.players and ctx.author.id != mancala.players[0]:
            await ctx.send('You are not the owner of this game! Leaving game...')
            await self.mc_leave(ctx)
            return
        await self.mc_finish(ctx)

    @mancala.command(name='next')
    @commands.is_owner()
    @commands.check(in_game_chk("mancalas"))
    @commands.check(running_chk("mancalas"))
    async def mc_next(self, ctx):
        """
        Owner only: Skips the current player's move
        """
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        mancala.turn = 1 - mancala.turn
        await self.mc_board(ctx)

    @mancala.group(name='config')
    @commands.check(in_game_chk("mancalas"))
    @commands.check(paused_chk("mancalas"))
    async def mc_config(self, ctx):
        '''
        Change the configuration of the board.
        '''
        if ctx.invoked_subcommand == None:
            mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
            configs = {
                "board": mancala.board,
                "turn": mancala.turn,
                "ai": ai in mancala.players,
                "mobile": mancala.mobile,
            }
            config_str = '```py\n' + '\n'.join([f'{key}: {str(val)}' for key, val in configs.items()]) + '```'
            config_str += f'Type `{ctx.prefix}{ctx.command} <setting> <new value>` to change the desired setting.'
            await ctx.send(config_str)

    @mc_config.command(name='board')
    async def mcf_board(self, ctx, *, board = None):
        '''
        Edit the board.
        Board is of form [[slot 0, slot 1, slot 2, ..., slot n, store], [slot 0, slot 1, slot 2, ..., slot n, store]].
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        if board == None:
            await ctx.send_help('mancala config board')
            return
        board_arr = json.loads(board)
        if len(board_arr) != 2: raise commands.BadArgument('Board can only have two sides.')
        if len(board_arr[0]) != len(board_arr[1]): raise commands.BadArgument('Each side should have the same number of slots.')
        if len(board_arr[0]) < 2: raise commands.BadArgument('Board should at least 1 slot.')
        if not all(isinstance(elem, int) for side in board_arr for elem in side): raise commands.BadArgument('Board should only consist of integer numbers of pebbles.')
        board_arr = [[int(elem) for elem in side] for side in board_arr] # remove booleans

        mancala.board = board_arr
        mancala.total = sum(j for i in mancala.board for j in i)
        mancala.size = len(mancala.board[0]) - 1
        await self.mc_board(ctx)

    @mc_config.command(name='turn')
    async def mcf_turn(self, ctx, turn: int):
        '''
        Change the game's turn.
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        if turn not in (0, 1):
            raise commands.BadArgument('Turn number can only be set to 0 or 1.')
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        mancala.turn = turn
        await ctx.send(f"Set game's turn to **{mancala.player_names(turn)}**")

    @mc_config.command(name='ai')
    async def mcf_ai(self, ctx, ai_player: bool):
        '''
        Add or remove AI player from game
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")

        if ai_player:
            # two players in game
            if len(mancala.players) != 1:
                await ctx.send('There are currently two players in game. A player must leave before adding an AI player.')
                return
            mancala.players.append(ai)
            await self.mc_board(ctx)
            return
        # ai isn't in game
        if ai not in mancala.players:
            await ctx.send('AI is not in game.')
            return
        mancala.players.remove(ai)
        await self.mc_board(ctx)

    @mc_config.command(name='mobile')
    async def mcf_mobile(self, ctx, arg: bool):
        '''
        If toggled on, the board is rotated for better viewing on mobile.
        '''
        mancala = self.curr_game(guild_or_dm(ctx), ctx.author, "mancalas")
        mancala.mobile = arg
        await self.mc_board(ctx)

    ### UNO ###
    # Function prefix: uno_, unoc_
    @commands.group()
    @commands.guild_only() # this game does not have an ai setting so is guild_only
    async def uno(self, ctx):
        '''
        Play an Uno game.
        EVERYTHING HERE IS WIP!

        __How to play Uno:__
            - 
        '''
        '''
        uno new
        uno start
        uno join
        uno leave
        uno end
        uno play [card / cards (if stacking same color cards is allowed)]
        uno draw
        uno kick
        uno board
        uno config
        '''

        if guild_or_dm(ctx).id not in self.unos: 
            self.unos[guild_or_dm(ctx).id] = []
        if ctx.invoked_subcommand == None:
            await ctx.send_help('uno')

    @uno.command(name='new')
    @commands.check(not_in_game_chk("unos"))
    async def uno_new(self, ctx, hand_size: int = 7):
        '''
        Make a new Uno game.
        Use `e&uno config` to configurate game.
        '''
        if hand_size < 1:
            raise commands.BadArgument('Size of hand at start must be greater than 0.')
        uno = Uno(players=[ctx.author.id], hand_size=hand_size, bot=self.bot)
        self.unos[guild_or_dm(ctx).id].append(uno)
        await ctx.send(f'New Uno game created!\nType `{ctx.prefix}{self.uno_config}` to configurate game.\nType `{ctx.prefix}{self.uno_join} @{ctx.author}` to join this game.\nType `{ctx.prefix}{self.uno_start}` to start.')

    @uno.command(name='start')
    @commands.check(in_game_chk("unos"))
    @commands.check(paused_chk("unos"))
    async def uno_start(self, ctx):
        '''
        Start an Uno game after it's been created. At least two people are necessary for a game to start.
        '''

    @uno.command(name='join')
    @commands.check(not_in_game_chk("unos"))
    async def uno_join(self, ctx):
        '''
        Join an Uno game.
        '''

    @uno.command(name='leave')
    @commands.check(in_game_chk("unos"))
    async def uno_leave(self, ctx):
        '''
        Leave an Uno game. Cards are returned to the Draw pile.
        '''

    @uno.command(name='end')
    @commands.check(in_game_chk("unos"))
    async def uno_end(self, ctx):
        '''
        Ends an unfinished game.
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        if ctx.author.id != uno.players[0]:
            await ctx.send('You are not the owner of this game! Leaving game...')
            await self.uno_leave(ctx)
            return

        self.unos[guild_or_dm(ctx).id].remove(uno)
        await ctx.send('Game ended.')

    @uno.command(name='play')
    @commands.check(in_game_chk("unos"))
    @commands.check(running_chk("unos"))
    async def uno_play(self, ctx):
        '''
        Play a card.
        If rank or color stacking is enabled, multiple cards can be played at once.
        '''

    @uno.command(name='draw')
    @commands.check(in_game_chk("unos"))
    @commands.check(running_chk("unos"))
    async def uno_draw(self, ctx):
        '''
        Draw a card from the draw pile.
        '''

    @uno.command(name='kick')
    @commands.check(in_game_chk("unos"))
    async def uno_kick(self, ctx):
        '''
        Kick someone from the game. Though I have no idea how I'm setting this up but ok.
        '''

    @uno.command(name='board', aliases=['pile'])
    @commands.check(in_game_chk("unos"))
    async def uno_board(self, ctx):
        '''
        Show current discard pile.
        '''

    @uno.group(name='config', aliases=['rules'])
    @commands.check(in_game_chk("unos"))
    @commands.check(paused_chk("unos"))
    async def uno_config(self, ctx):
        '''
        Enable/disable house rules before starting.
        '''
        if ctx.invoked_subcommand == None:
            uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
            configs = {
                "hand": uno.hand_size,
                "draw_stack": uno.draw_stack,
                "jump_in": uno.jump_in,
                "seven-o": uno.seven_o,
                "color_stack": uno.color_stack,
                "rank_stack": uno.rank_stack,
            }
            config_str = '```py\n' + '\n'.join([f'{key}: {str(val)}' for key, val in configs.items()]) + '```'
            config_str += f'Type `{ctx.prefix}{ctx.command} <setting> <new value>` to change the desired setting.'
            await ctx.send(config_str)

    @uno_config.command(name='hand')
    async def unoc_hand(self, ctx, hand_size: int):
        '''
        Change the initial size of the hands.
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.hand_size = hand_size
        await self.uno_config(ctx)

    @uno_config.command(name='draw_stack')
    async def unoc_draw_stack(self, ctx, opt: bool):
        '''
        Enable/disable draw stacking. Enabled by default.
            - When forced to draw cards due to a +2 or +4 card, you can place a +2 or +4 to avoid drawing and pass the burden onto the next player.

        - Considered a house rule by Hasbro
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.draw_stack = opt
        await self.uno_config(ctx)

    @uno_config.command(name='jump_in', aliases=['cut'])
    async def unoc_jump_in(self, ctx, opt: bool):
        '''
        Enable/disable jump ins. Disabled by default.
            - If the card on the top of the discard pile matches the rank and color of a card in your hand, that card can be played, skipping all players before you.

        - Considered a house rule by Hasbro
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.jump_in = opt
        await self.uno_config(ctx)

    @uno_config.command(name='seven-o', aliases=['seven_o'])
    async def unoc_seven_o(self, ctx, opt: bool):
        '''
        Enable/disable special abilities of rank 0 and 7. Disabled by default.
            - Every time a 0 is played, all players pass their hands to the next player in direction of play.
            - Every time a 7 is played, the player who played the 7 card must trade their hand with another player of their choice. 

        - Considered a house rule by Hasbro
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.seven_o = opt
        await self.uno_config(ctx)

    @uno_config.command(name='color_stack')
    async def unoc_color_stack(self, ctx, opt: bool):
        '''
        Enable/disable color stacking. Disabled by default.
            - If enabled, cards of the same color can be played at once. (e&uno play card1 card2 card3...)
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.color_stack = opt
        await self.uno_config(ctx)

    @uno_config.command(name='rank_stack')
    async def unoc_rank_stack(self, ctx, opt: bool):
        '''
        Enable/disable rank stacking. Disabled by default.
            - If enabled, cards of the same rank can be played at once. (e&uno play card1 card2 card3...)
        '''
        uno = self.curr_game(guild_or_dm(ctx), ctx.author, "unos")
        uno.rank_stack = opt
        await self.uno_config(ctx)


def setup(bot):
    cog = Games(bot)
    bot.add_cog(cog)
    # signature overrides
    override_signature(cog.mancala, '<subcmd> [...]')
    override_signature(cog.mc_config, '<setting> <...>')
    override_signature(cog.mc_new, '<pvp|pva|avp> [size=6]')
    override_signature(cog.mcf_ai, '<true|false>')
    override_signature(cog.mcf_mobile, '<true|false>')
    override_signature(cog.mcf_turn, '<0|1>')

    override_signature(cog.uno, '<subcmd> [...]')
    override_signature(cog.unoc_draw_stack, '<true|false>')
    override_signature(cog.unoc_jump_in, '<true|false>')
    override_signature(cog.unoc_seven_o, '<true|false>')
    override_signature(cog.unoc_color_stack, '<true|false>')
    override_signature(cog.unoc_rank_stack, '<true|false>')
