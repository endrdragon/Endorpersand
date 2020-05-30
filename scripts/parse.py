import re
import math
import cmath
import statistics
import random
import functools
from fractions import Fraction

class Token:
    '''
    In tokenization phase, tokens are used to mark separate objects.
    '''
    def __init__(self, type, value):
        self.type = type # numeric/constant, operator, function, lparen, rparen, sep
        self.value = value
    
    def __eq__(self, other):
        return (self.type, self.value) == (self.type, self.value)

    def __repr__(self):
        if self.type == 'numeric':
            return f'Token("{self.type}", {str(self.value)})'
        return f'Token("{self.type}", "{str(self.value)}")'

class Operator(Token):
    '''
    In tokenization phase, operator fix is used to determine implicit *'s and invalid positions.
    In RPNizing phase, operator position is determined by their precedence.
    In parsing phase, operators are used to calculate their results.
    '''
    def __init__(self, type, value, **kwargs):
        super().__init__('operator', value)
        self.fix = kwargs.pop('fix', 'infix') # prefix, infix, postfix

        self.prec = kwargs.pop('prec', 6)                                                   # higher precedence means it's more prioritized in order of operations
        self.left_assoc = kwargs.pop('left_assoc', False if self.fix == 'prefix' else True) # left assoc means 2 @ 2 @ 2 = (2 @ 2) @ 2, right assoc means 2 @ 2 @ 2 = 2 @ (2 @ 2)
        self.arglen = kwargs.pop('arglen', (2, ))                                           # Number of args it allows. If this is a tuple (accepting one of those choices) or None (any amount of args >= 0), it will be replaced during RPN phase.
        self.func = kwargs.pop('func')                                                      # accepts Numbers, returns a Number

        if self.fix == 'infix' and self.arglen != (2, ): raise SyntaxError('Infix operators can only have two arguments.')

    def __repr__(self):
        return f'Operator("{self.type}", "{str(self.value)}", arglen={str(self.arglen)})'

    def set_arglen(self, arglen):
        '''
        Changes tuple / None to the actual number of args this operator will accept if the arglen specified is an accepted value of args.
        '''
        if self.arglen == None or arglen in self.arglen: 
            self.arglen = arglen
            return
        raise SyntaxError(f'Operator {self.value} does not accept {arglen} argument{"" if arglen == 1 else "s"}')

    def run(self, *args):
        vals = [arg.value for arg in args]
        result = self.func(*vals)
        return Token('numeric', result)

def alias(map, alias_of: str, aliases: list):
    for alias in aliases:
        if not isinstance(map[alias_of], dict):
            map[alias] = map[alias_of]
            return
        map[alias] = map[alias_of].copy()

def func_type(*args):
    '''
    Returns the type of number the number should deal with, given args. (int, Fraction, float, complex)
    '''
    if any(isinstance(arg, complex) for arg in args): return 'complex'
    if any(isinstance(arg, float) for arg in args): return 'float'
    if any(isinstance(arg, Fraction) for arg in args): return 'fraction'
    return 'int'

# rewritten functions #
# Fast growing functions are clamped to:
#     maximums:
#     floats & complex    ~10^308, ~170!
#     fractions            numerators & denoms are capped by int cap
#     ints                 10^500,  253!
def divide(x, y):
    if func_type(x, y) in ('fraction', 'int'):
        return Fraction(x, y)
    else:
        return x / y

def factorial(x):
    if func_type(x) == 'int':
        if (x > 253): raise OverflowError('Result too large')
        return math.factorial(x) #note there's a valueerror here for neg ints
    else:
        return math.gamma(x + 1)

def powa(x, y):
    if func_type(x, y) in ('fraction', 'int'):
        if y * math.log10(abs(x)) > 500: raise OverflowError('Result too large')
        if isinstance(x, Fraction):
            if abs(y) * math.log10(abs(x.numerator)) > 500: raise OverflowError('Numerator too large')
            if abs(y) * math.log10(abs(x.denominator)) > 500: raise OverflowError('Denominator too large')
    return x ** y

def real(x):
    if func_type(x) == 'complex':
        return x.real
    return x
def imag(x):
    if func_type(x) == 'complex':
        return x.imag
    return 0
def conj(x):
    if func_type(x) == 'complex':
        return x.conjugate()
    return x

def log(x, b=None):
    if b == None: return cmath.log(x)
    if b == 10: return cmath.log10(x)
    if func_type(x) == 'float' and b == 2: math.log2(x)
    return cmath.log(x, b)

# when py 3.9 comes, delete iter_gcd and iter_lcm and replace with new math.gcd and math.lcm
lcm = lambda a, b: a * b / math.gcd(a, b) 
def iter_gcd(*args):
    return functools.reduce(lambda acc, cv: math.gcd(acc, cv), args)
def iter_lcm(*args):
    return functools.reduce(lambda acc, cv: lcm(acc, cv), args)

def concat(*args):
    return float(''.join(str(n) for n in args))

def comb(x, y):
    if x > 253 or y > 253: raise OverflowError('Result too large')
    return math.comb(x, y)

def perm(x, y):
    if x > 253 or y > 253: raise OverflowError('Result too large')
    return math.perm(x, y)

def _sum(*args):
    if func_type(*args) == 'float':
        return math.fsum(args)
    else:
        return sum(args)

def prod(*args):
    return math.prod(args)

def lshift(x, y):
    if y * math.log2(abs(x)) > 500 * math.log2(10): raise OverflowError('Result too large')
    return x << y

def atan(y, x = None):
    if x == None:
        return cmath.atan(y)
    else:
        return math.atan2(y, x)

operators = {
    # "func": {props}
    # complex numbers in the form (a + 0i) are converted to floats later on

    # operators
    '|':  {"fix": "infix", "prec": 0,  "left_assoc": True,  "func": lambda x, y: x | y},
    '&':  {"fix": "infix", "prec": 0,  "left_assoc": True,  "func": lambda x, y: x & y},
    '<<': {"fix": "infix", "prec": 1,  "left_assoc": True,  "func": lshift},
    '>>': {"fix": "infix", "prec": 1,  "left_assoc": True,  "func": lambda x, y: x >> y},
    '+':  {"fix": "infix", "prec": 2,  "left_assoc": True,  "func": lambda x, y: x + y},
    '*':  {"fix": "infix", "prec": 3,  "left_assoc": True,  "func": lambda x, y: x * y},
    '/':  {"fix": "infix", "prec": 3,  "left_assoc": True,  "func": divide},
    '%':  {"fix": "infix", "prec": 3,  "left_assoc": True,  "func": lambda x, y: x % y},
    '^':  {"fix": "infix", "prec": 4,  "left_assoc": False, "func": powa},
    '==': {"fix": "infix", "prec": -1, "left_assoc": True,  "func": lambda x, y: x == y},
    '>':  {"fix": "infix", "prec": -1, "left_assoc": True,  "func": lambda x, y: x > y},
    '<':  {"fix": "infix", "prec": -1, "left_assoc": True,  "func": lambda x, y: x < y},
    '>=': {"fix": "infix", "prec": -1, "left_assoc": True,  "func": lambda x, y: x >= y},
    '<=': {"fix": "infix", "prec": -1, "left_assoc": True,  "func": lambda x, y: x <= y},

    # unary and binary operator -
    '-':  [{'fix': 'prefix',  "prec": 5, "arglen": (1,), "func": lambda x: -x}, {"prec": 2, "left_assoc": True,  "func": lambda x, y: x - y}],
    
    # postfix operators
    '!':     {'fix': 'postfix', "prec": 5, "arglen": (1,), "func": factorial},
    'deg':   {'fix': 'postfix', "prec": 5, "arglen": (1,), "func": lambda x: x * math.pi / 180},

    # complex
    'arg':   {'fix': 'prefix', 'arglen': (1,), 'func': cmath.phase},
    'rect':  {'fix': 'prefix', 'arglen': (2,), 'func': cmath.rect},
    'real':  {'fix': 'prefix', 'arglen': (1,), 'func': real},
    'imag':  {'fix': 'prefix', 'arglen': (1,), 'func': imag},
    'conj':  {'fix': 'prefix', 'arglen': (1,), 'func': conj},
    
    # exponents and logs
    'exp':   {'fix': 'prefix', 'arglen': (1,), 'func': cmath.exp},
    'ln':    {'fix': 'prefix', 'arglen': (1,), 'func': cmath.log},
    'log':   {'fix': 'prefix', 'arglen': (1, 2), 'func': log},
    'sqrt':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.sqrt},
    
    # trig
    'hypot': {'fix': 'prefix', 'arglen': None, 'func': math.hypot},
    
    'sin':   {'fix': 'prefix', 'arglen': (1,), 'func': cmath.sin},
    'cos':   {'fix': 'prefix', 'arglen': (1,), 'func': cmath.cos},
    'tan':   {'fix': 'prefix', 'arglen': (1,), 'func': cmath.tan},
    'csc':   {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: 1 / cmath.sin(x)},
    'sec':   {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: 1 / cmath.cos(x)},
    'cot':   {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: 1 / cmath.tan(x)},
    
    'sinh':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.sinh},
    'cosh':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.cosh},
    'tanh':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.tanh},
    
    'asin':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.asin},
    'acos':  {'fix': 'prefix', 'arglen': (1,), 'func': cmath.acos},
    'atan':  {'fix': 'prefix', 'arglen': (1, 2), 'func': atan},
    'acsc':  {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: cmath.asin(1 / x) if x != 0 else cmath.asin(math.inf)},
    'asec':  {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: cmath.acos(1 / x) if x != 0 else cmath.acos(math.inf)},
    'acot':  {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: cmath.asin(1 / x) if x != 0 else cmath.atan(math.inf)},
    
    'asinh': {'fix': 'prefix', 'arglen': (1,), 'func': cmath.asinh},
    'acosh': {'fix': 'prefix', 'arglen': (1,), 'func': cmath.acosh},
    'atanh': {'fix': 'prefix', 'arglen': (1,), 'func': cmath.atanh},
    
    # statistics
    'mean':          {'fix': 'prefix', 'arglen': None, 'func': statistics.mean},
    'harmonic_mean': {'fix': 'prefix', 'arglen': None, 'func': statistics.harmonic_mean},
    'median':        {'fix': 'prefix', 'arglen': None, 'func': statistics.median},
    'mode':          {'fix': 'prefix', 'arglen': None, 'func': statistics.mode},
    'pstdev':        {'fix': 'prefix', 'arglen': None, 'func': statistics.pstdev},
    'pvariance':     {'fix': 'prefix', 'arglen': None, 'func': statistics.pvariance},
    'stdev':         {'fix': 'prefix', 'arglen': None, 'func': statistics.stdev},
    'variance':      {'fix': 'prefix', 'arglen': None, 'func': statistics.variance},

    # rand
    'rand':        {'fix': 'prefix', 'arglen': (0,), 'func': random.random},
    'randuniform': {'fix': 'prefix', 'arglen': (2,), 'func': random.uniform},
    'randint':     {'fix': 'prefix', 'arglen': (2,), 'func': random.randint},
    
    # misc
    'abs':       {'fix': 'prefix', 'arglen': (1,), 'func': abs},
    'ceil':      {'fix': 'prefix', 'arglen': (1,), 'func': math.ceil},
    'clamp':     {'fix': 'prefix', 'arglen': (3,), 'func': lambda x, minv, maxv: min(max(x, minv), maxv)},
    'concat':    {'fix': 'prefix', 'arglen': None, 'func': concat},
    'erf':       {'fix': 'prefix', 'arglen': (1,), 'func': math.erf},
    'floor':     {'fix': 'prefix', 'arglen': (1,), 'func': math.floor},
    'factorial': {'fix': 'prefix', 'arglen': (1,), 'func': factorial},
    'gcd':       {'fix': 'prefix', 'arglen': None, 'func': iter_gcd},
    'lcm':       {'fix': 'prefix', 'arglen': None, 'func': iter_lcm},
    'max':       {'fix': 'prefix', 'arglen': None, 'func': max},
    'min':       {'fix': 'prefix', 'arglen': None, 'func': min},
    'prod':      {'fix': 'prefix', 'arglen': None, 'func': prod},
    'remainder': {'fix': 'prefix', 'arglen': (2,), 'func': math.remainder},
    'round':     {'fix': 'prefix', 'arglen': (1,), 'func': round},
    'sign':      {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: int(math.copysign(1, x))},
    'sum':       {'fix': 'prefix', 'arglen': None, 'func': _sum},
    'trunc':     {'fix': 'prefix', 'arglen': (1,), 'func': math.trunc},
    'not':       {'fix': 'prefix', 'arglen': (1,), 'func': lambda x: ~x},
    'comb':      {'fix': 'prefix', 'arglen': (2,), 'func': comb},
    'perm':      {'fix': 'prefix', 'arglen': (2,), 'func': perm}
}
alias(operators, '^', ['**'])
alias(operators, '-', ['−'])
alias(operators, '/', ['÷'])
alias(operators, '*', ['×'])
alias(operators, 'deg', ['°'])
alias(operators, 'gcd', ['gcf'])
alias(operators, 'lcm', ['lcd'])
alias(operators, 'mean', ['avg', 'average'])
alias(operators, 'clamp', ['clip'])
alias(operators, 'asin', ['arcsin'])
alias(operators, 'acos', ['arccos'])
alias(operators, 'atan', ['arctan'])
alias(operators, 'acsc', ['arccsc'])
alias(operators, 'asec', ['arcsec'])
alias(operators, 'acot', ['arccot'])
alias(operators, 'asinh', ['arcsinh'])
alias(operators, 'acosh', ['arccosh'])
alias(operators, 'atanh', ['arctanh'])
alias(operators, 'not', ['~'])
alias(operators, 'comb', ['choose'])
alias(operators, 'conj', ['conjugate'])

constants = {
    # "const": value
    'tau': math.tau,
    'phi': (1 + math.sqrt(5)) / 2,
    'inf': math.inf,
    'pi': math.pi,
    'i': 1j,
    'e': math.e,
}
alias(constants, 'inf', ['∞', 'infinity'])
alias(constants, 'pi',  ['π'])
alias(constants, 'tau', ['τ'])
alias(constants, 'i',   ['j'])

regex = {
    "numeric": r'\d+(?:\.\d)?',
    "sep":     r',',
    "lparen":  r"\(",
    "rparen":  r"\)",
}
regex["string"] = '|'.join(sorted((re.escape(v) for v in [*operators.keys(), *constants.keys()]), key=len, reverse=True)) # puts all string ops/consts from longest to shortest in length
regex["invalid"] = r'.'
check_reg = '|'.join(r'(?P<{0}>{1})'.format(name, reg) for name, reg in regex.items())

def get_operator(op):
    '''
    Converts op to Operator class and returns
    '''
    if isinstance(operators[op], list):
        return [Operator('operator', op, **oper) for oper in operators[op]]
    return Operator('operator', op, **operators[op])

def get_help(): # for d.py
    s =  f'**Constants**: `{"` `".join(constants.keys())}`\n' 
    prefix = [key for key, op in operators.items() if isinstance(op, list) or op["fix"] == "prefix"]
    infix = [key for key, op in operators.items() if isinstance(op, list) or op["fix"] == "infix"]
    postfix = [key for key, op in operators.items() if not isinstance(op, list) and op["fix"] == "postfix"]
    s += f'**Prefix operators**: `{"` `".join(prefix)}`\n'
    s += f'**Infix operators**: `{"` `".join(infix)}`\n'
    s += f'**Postfix operators**: `{"` `".join(postfix)}`\n'
    return s

def parse(expr, halt=''): # halt signifies an early return, can be set to ('token', 'rpn', '')
    expr = re.sub(r'\s+', '', expr).lower()

    ### tokenization ###
    tokens = []

    def peek_token():
        if len(tokens) == 0: return Token('BOL', None)
        return tokens[-1]

    # adds * token if (numeric, constant, prefix operator, lparen) follows a (numeric, rparen, postfix operator)
    def add_needed_star():
        t = peek_token()
        if t.type in ('numeric', 'rparen') or t.type == 'function' and t.fix == 'postfix': 
            tokens.append(get_operator('*'))

    for match in re.finditer(check_reg, expr):
        ttype = match.lastgroup
        value = match.group()
        if ttype == 'numeric':
            add_needed_star()
            if '.' in value:
                tokens.append( Token(ttype, float(value)) )
                continue
            tokens.append( Token(ttype, int(value)) )
            continue
        
        if ttype == 'string':
            if value in constants.keys():
                add_needed_star()
                tokens.append( Token('numeric', constants[value]) )
                continue
            op = get_operator(value)
            t = peek_token()

            if isinstance(op, list): 
                # if op is both (prefix) unary and (infix) binary
                # op is binary after numerics, rparens, and postfixes
                fix = ''
                if t.type in ('numeric', 'rparen') or t.type == 'function' and t.fix == 'postfix':
                    fix = 'infix'
                else: fix = 'prefix'
                op = next(oper for oper in op if oper.fix == fix)

            if op.fix == 'prefix':
                add_needed_star()
                tokens.append(op)
                continue
            
            t = peek_token()
            if op.fix == 'infix':
                if t.type == 'BOL': raise SyntaxError('Infix operator begins expression')
                if t.type == 'operator' and t.fix == 'prefix': raise SyntaxError('Infix operator follows prefix operator')
                if t.type == 'operator' and t.fix == 'infix': raise SyntaxError('Infix operator follows another infix operator')
                if t.type == 'lparen': raise SyntaxError('Infix operator follows left parenthesis')
                if t.type == 'sep': raise SyntaxError('Infix operator follows comma')
                tokens.append(op)
                continue

            if op.fix == 'postfix':
                if t.type == 'BOL': raise SyntaxError('Postfix operator begins expression')
                if t.type == 'operator' and t.fix == 'prefix': raise SyntaxError('Postfix operator follows prefix operator')
                if t.type == 'operator' and t.fix == 'infix': raise SyntaxError('Postfix operator follows infix operator')
                if t.type == 'lparen': raise SyntaxError('Postfix operator follows left parenthesis')
                if t.type == 'sep': raise SyntaxError('Postfix operator follows comma')
                add_needed_star()
                tokens.append(op)
                continue

        if ttype == 'lparen':
            add_needed_star()
            tokens.append( Token(ttype, value) )
            continue

        if ttype == 'rparen':
            t = peek_token()
            if t.type == 'BOL': raise SyntaxError('Right parenthesis begins expression')
            if t.type == 'operator' and t.fix == 'prefix': raise SyntaxError('Right parenthesis follows prefix operator')
            if t.type == 'operator' and t.fix == 'infix': raise SyntaxError('Right parenthesis follows infix operator')
            #if t.type == 'lparen': raise SyntaxError('Right parenthesis follows left parenthesis')
            if t.type == 'sep': raise SyntaxError('Right parenthesis follows comma')
            tokens.append( Token(ttype, value) )
            continue

        if ttype == 'sep':
            t = peek_token()
            if t.type == 'BOL': raise SyntaxError('Comma begins expression')
            if t.type == 'operator' and t.fix == 'prefix': raise SyntaxError('Comma follows prefix operator')
            if t.type == 'operator' and t.fix == 'infix': raise SyntaxError('Comma follows infix operator')
            if t.type == 'lparen': raise SyntaxError('Comma follows left parenthesis')
            if t.type == 'sep': raise SyntaxError('Comma follows another comma')
            tokens.append( Token(ttype, value) )
            continue

        if ttype == 'invalid':
            raise NameError('Invalid operator or constant')

    if halt == 'token': return tokens

    ### RPNization ###  
    # shunting yard algorithm, but modified (see comments below)
    stack = []
    output = []
    counter = [0]

    # counter system to count arg lens
    # 1. if number is pushed to output: counter[-1] += 1
    # 2. if (left paren) or (right assoc op that precedes an equal prec op)* or (an op that precedes a higher prec op)* is pushed to stack: counter.push(0)
    # 3. if (left paren) or (right assoc op that preceded an equal prec op)* or (an op that preceded a higher prec op)* is popped from stack: counter.pop(), add to counter[-1]
        #* before an lparen, it doesn't actually matter
    # 4. if operator is pushed to output: op inherits counter[-1] # of args, and counter[-1] = 1
    # 5. when separator reaches lparen, counter[-2] inherits counter[-1] and counter[-1] is cleared to 0


    def combine_counter(): # 3
        '''
        Combines last two counters into one.
        '''
        c = counter.pop()
        counter[-1] += c
    
    # assign a 'invis_paren' property to figure out which operators follow the property of 2 and 3. ex. 2 + 3 * 1 => 2 + (3 * 1), 2 ^ 3 ^ 1 => 2 ^ (3 ^ 1)
    stack_tokens = [token for token in tokens if token.type != 'numeric']
    for (i, token) in enumerate(stack_tokens):
        if token.type != 'operator': continue
        token.invis_paren = False
        if i + 1 == len(stack_tokens): continue

        nt = stack_tokens[i + 1]
        if nt.type != 'operator': continue # 2 + 2, 2 =/> 2 + (2, 2)
        if token.prec < nt.prec:
            token.invis_paren = True
            continue
        if not token.left_assoc and token.prec == nt.prec:
            token.invis_paren = True
            continue

    for token in tokens:
        if token.type == 'numeric':
            output.append(token)
            counter[-1] += 1 # 1
            continue
        
        # pop ops from op stack until lparen is reached
        if token.type == 'sep':
            if len(stack) == 0: continue
            while stack[-1].type != 'lparen':
                op = stack.pop()
                if op.invis_paren: combine_counter() # 3
                op.set_arglen(counter[-1]) # 4
                counter[-1] = 1
                output.append(op)
                if len(stack) == 0: break
            if len(stack) == 0: continue
            counter[-2] += counter[-1]
            counter[-1] = 0
            continue

        if token.type == 'operator':
            while len(stack) > 0 and stack[-1].type != 'lparen' and ( stack[-1].prec > token.prec or (stack[-1].prec == token.prec and token.left_assoc) ):
                op = stack.pop()
                if op.invis_paren: combine_counter() # 3
                op.set_arglen(counter[-1]) # 4
                counter[-1] = 1 # 4
                output.append(op)
            stack.append(token)
            if token.invis_paren: counter.append(0) # 2
            continue

        if token.type == 'lparen':
            stack.append(token)
            counter.append(0) # 2
            continue

        if token.type == 'rparen':
            if len(stack) == 0: raise SyntaxError('Mismatched parentheses')
            while stack[-1].type != 'lparen':
                op = stack.pop()
                if op.invis_paren: combine_counter() # 3
                op.set_arglen(counter[-1]) # 4
                counter[-1] = 1 # 4
                output.append(op)
                if len(stack) == 0: raise SyntaxError('Mismatched parentheses')
            stack.pop()
            combine_counter() # 3
            continue
    
    if len(stack) != 0:
        if 'lparen' in [op.type for op in stack]: raise SyntaxError('Mismatched parentheses')
        for op in stack[::-1]:
            if op.invis_paren: combine_counter() # 3
            op.set_arglen(counter[-1]) # 4
            counter[-1] = 1 # 4
            output.append(op)

    if halt == 'rpn': return output

    # parsing

    while any(token.type == 'operator' for token in output):
        [i,o] = next(pair for pair in enumerate(output) if pair[1].type == 'operator')
        args = output[i - o.arglen : i]
        result = o.run(*args)
        output = output[:i - o.arglen] + [result] + output[i + 1:]

    output = [token.value if imag(token.value) != 0 else token.value.real for token in output]
    return output
