import discord
from discord.ext import commands
import scripts.parse as parser
from importlib import reload
from json import loads
from traceback import print_exc
import math

def Base(base):
    base = base.lower()
    if base in ('b', 'bin', 'binary'): return (2, 0)
    if base in ('o', 'oct', 'octal'): return (8, 0)
    if base in ('d', 'dec', 'decimal'): return (10, 0)
    if base in ('h', 'hex', 'hexadecimal'): return (16, 0)
    if base in ('u', 'uni', 'unicode'): return ('u', 0)
    base = int(base)
    if base < 2: raise commands.BadArgument('Base must be greater than 1.')
    # return (base, mode of display)
    if base <= 36:
        return (base, 0) # 0: case-insensitive mode
    if base <= 62:
        return (base, 1) # 1: case-sensitive mode
    return (base, 2) # 2: array mode

class STEM(commands.Cog):
    '''
    Mathematical or scientific commands
    '''
    def __init__(self, bot):
        self.bot = bot
        
    @commands.group(aliases=['math','arith'], invoke_without_command=True, help='Evaluates a math expression.\n' + parser.get_help())
    async def parse(self, ctx, *, expr):
        '''
        Evaluates a math expression.
        '''
        try:
            output = parser.parse(expr)
        except ValueError as e:
            await ctx.send("That\'s an out of domain argument, stupid")
            print_exc()
        except ZeroDivisionError as e:
            await ctx.send("You can't divide by zero, stupid")
            print_exc()
        except OverflowError as e:
            await ctx.send("Please don\'t try to kill my computer with overly large numbers, thanks.")   
            print_exc()
        except SyntaxError as e:
            await ctx.send(str(e) + ", stupid")   
            print_exc()
        except NameError as e:
            await ctx.send(f"That gibberish contains an {str(e).lower()}, stupid")   
            print_exc()
        except TypeError as e:
            await ctx.send(str(e) + ", stupid")
            print_exc()
        else:
            if len(output) > 1:
                await ctx.send("There are multiple numbers left after evaluation: \n" + str(output))
            else: await ctx.send(str(output[0]))

    @parse.command(name='token')
    async def ptoken(self, ctx, *, expr):
        '''
        Tokenizes a math expression.
        '''
        try:
            output = parser.parse(expr, halt='token')
        except SyntaxError as e:
            await ctx.send(str(e) + ", stupid")   
            print_exc()
        except NameError as e:
            await ctx.send("That gibberish contains an invalid function or constant, stupid")   
            print_exc()
        else:
            await ctx.send(str([str(token) for token in output]))

    @parse.command(name='rpn') 
    async def prpn(self, ctx, *, expr):
        '''
        Converts a math expression to RPN notation.
        '''
        try:
            output = parser.parse(expr, halt='rpn')
        except SyntaxError as e:
            await ctx.send(str(e) + ", stupid")   
            print_exc()
        except NameError as e:
            await ctx.send("That gibberish contains an invalid function or constant, stupid")   
            print_exc()
        else:
            await ctx.send(str([str(token) for token in output]))


    def splitn(self, n):
        # Takes a number and splits it into its individual digits
        return [int(d) for d in str(n)]

    def base_to_b10(self, b1: int, n: list) -> int:
        '''
        Given list of values in some base, convert to regular int 
        '''
        n = n[::-1]
        return sum(d * (b1 ** i) for i, d in enumerate(n))

    def b10_to_base(self, b2: int, n: int) -> list:
        '''
        Given int, convert to list of b2
        '''
        digits = []
        while n:
            digits.append(int(n % b2))
            n //= b2
        return digits[::-1]

    @commands.command()
    async def base(self, ctx, b1: Base, b2: Base, *values):
        '''
        Converts values (separated by spaces*) from one base to another.

        __Supported bases__
            `2` - `36` (case-insensitive), 
            `37` - `62` (0-9, A-Z, a-z), 
            `63` - (list of values are returned), 
            `unicode`
        
        *A single value in base Unicode is interpreted as one char instead of a block separated by spaces.
        *A single value in base 63+ is interpreted as one list instead of a block separated by spaces.
        '''
        if b1 == b2:
            await ctx.send(' '.join(values))
            return
        [b1, b1m, b2, b2m] = [*b1, *b2]
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' if b1m == 1 or b2m == 1 else '0123456789abcdefghijklmnopqrstuvwxyz'
        
        if b1 == 'u':
            ustr = ' '.join(values) # returns the unicode base string
            ord_lst = [ord(c) for c in ustr]

            if b2 == 10:
                await ctx.send(' '.join(str(l) for l in ord_lst))
                return
            
            newb_lst = [self.b10_to_base(b2, v) for v in ord_lst] # converts ords to list of new base

            # converts list into display format & return
            if b2m != 2:
                disp_lst = [''.join(chars[v] for v in l) for l in newb_lst]
            else:
                disp_lst = [str(l) for l in newb_lst]
            await ctx.send(' '.join(disp_lst))
            return
        
        try: # returns a list of numeric values
            if b1m == 0:
                val_lst = [int(s, base=b1) for s in values]
            if b1m == 1:
                val_lst = [[chars[:b1].index(c) for c in s] for s in values]
                val_lst = [self.base_to_b10(b1, v) for v in val_lst]
            if b1m == 2:
                # separates values by array
                values = (' '.join(values)).split('] [')
                values = [s if s.startswith('[') else f'[{s}' for s in values]
                values = [s if s.endswith(']') else f'{s}]' for s in values]

                val_lst = [loads(lst) for lst in values]
                val_lst = [self.base_to_b10(b1, v) for v in val_lst]
        except ValueError:
            print('\n\n\n')
            print_exc()
            raise commands.BadArgument('The input values are invalid.')
        
        if b2 == 'u': # convert vals to chrs and return
            chr_lst = [chr(v) for v in val_lst]
            await ctx.send(''.join(chr_lst))
            return
        
        newb_lst = [self.b10_to_base(b2, v) for v in val_lst]

        # converts list to display format & return
        if b2m != 2:
            disp_lst = [''.join(chars[v] for v in l) for l in newb_lst]
        else:
            disp_lst = [str(l) for l in newb_lst]
        await ctx.send(' '.join(disp_lst))

def setup(bot):
    bot.add_cog(STEM(bot))
    reload(parser)
        
    