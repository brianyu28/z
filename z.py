"""
Z
Brian Yu
v0.0.0

An implementation of the Z programming language.
"""

import sys

from arpeggio import Optional, ZeroOrMore, OneOrMore, EOF
from arpeggio import ParserPython, PTNodeVisitor, visit_parse_tree, ArpeggioError
from arpeggio import RegExMatch as _
from termcolor import cprint

WORD = r"[A-z][\w]*"
VARIABLE = r"\$" + WORD

# Terminals
def comment():          return r"//", _(r".*")
def number():           return _(r"\-?\d+\.\d*|\-?\.\d+|\-?\d+")
def identifier():       return _(VARIABLE)
def string():           return _(r'"[^"]*"')

# Non-terminals
def atom():             return [number, identifier, string, function_call]
def arglist():          return expression, ZeroOrMore(",", expression)
def paramlist():        return _(VARIABLE), ZeroOrMore(",", _(VARIABLE))
def function_call():    return _(WORD), "(", Optional(arglist), ")"
def expression():       return atom, Optional("<", atom)
def function():         return "function", _(WORD), "(", Optional(paramlist), ")", "{", ZeroOrMore(statement), "}"
def statement():        return [assignment, condition, expression]
def assignment():       return identifier, "<-", expression
def condition():        return "if", "(", expression, ")", "{", ZeroOrMore(statement), "}"
def program():          return ZeroOrMore(function)

# Classes to store information about program.
class Identifier():
    def __init__(self, name):
        self.name = name

class Assignment():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Comparison():
    def __init__(self, left, right):
        self.left = left
        self.right = right

class Condition():
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class Function():
    def __init__(self, name, params, statements):
        self.name = name
        self.params = params
        self.statements = statements

class FunctionCall():
    def __init__(self, name, params):
        self.name = name
        self.params = params

class ArgList():
    def __init__(self, params):
        self.params = params

class ParamList():
    def __init__(self, params):
        self.params = params

class ZVisitor(PTNodeVisitor):

    def __init__(self, functions):
        super().__init__()
        self.functions = functions

    def visit_number(self, node, children):
        return (float if "." in node.value else int)(node.value)

    def visit_identifier(self, node, children):
        return Identifier(node.value)

    def visit_string(self, node, children):
        # Strip away quotation marks, unescape backslashes.
        return node.value[1:-1].encode('latin1').decode('unicode_escape')

    def visit_atom(self, node, children):
        return children[0]

    def visit_arglist(self, node, children):
        return ArgList(children)

    def visit_paramlist(self, node, children):
        return ParamList(children)

    def visit_function_call(self, node, children):
        if len(children) == 1:
            return FunctionCall(children[0], None)
        else:
            return FunctionCall(children[0], children[1])

    def visit_expression(self, node, children):

        if len(children) == 1:  # Atom
            return children[0]
        else:  # Comparison
            return Comparison(children[0], children[1])

    def visit_function(self, node, children):
        if len(children) > 2 and type(children[1]) == ParamList:
            return Function(children[0], children[1], children[2:])
        return Function(children[0], None, children[1:])

    def visit_statement(self, node, children):
        return children

    def visit_assignment(self, node, children):
        return Assignment(children[0], children[1])

    def visit_condition(self, node, children):
        return Condition(children[0], children[1:])

    def visit_program(self, node, children):
        main = None
        for fn in children:
            if fn.name == "main":
                main = fn
            self.functions[fn.name] = fn
        if main is None:
            err("Program needs a main function.")
        try:
            run(main, self.functions)
        except Exception as e:
            raise e
            err("An unknown error occurred.")

def err(msg):
    cprint(msg, "red")
    sys.exit(1)

def run(function, functions, *args):
    args = args[0] if args and args[0] != None else []
    return_value = None  # no return value to begin with

    # If it's callable, just return the result.
    if callable(function):
        return function(*args)

    # Store local variables, starting with params.
    local = dict()
    if args:
        if len(args) != len(function.params.params):
            err("Incorrect number of arguments to function {}".format(function.name))
            sys.exit(1)
        for name, value in zip(function.params.params, args):
            local[name] = value

    def evaluate(statement):
        nonlocal return_value
        if return_value:
            return

        if type(statement) == Assignment:
            local[statement.name.name] = evaluate(statement.value)
            return None

        if type(statement) == Comparison:
            return evaluate(statement.left) < evaluate(statement.right)

        if type(statement) == Condition:
            if not evaluate(statement.condition):
                return
            for child in statement.body:
                evaluate(child[0])

        if type(statement) == FunctionCall:
            if statement.name == "return":
                return_value = evaluate(statement.params)[0]
                return

            if statement.name not in functions:
                err("Undefined function {}".format(statement.name))
            return run(functions[statement.name], functions, evaluate(statement.params))

        if type(statement) == Identifier:
            if statement.name in local:
                return local[statement.name]
            err("Undefined variable {}".format(statement.name))

        if type(statement) == ArgList:
            args = map(evaluate, statement.params)
            return list(args)
        
        return statement
    
    # Evaluate every statement in the function.
    for statement in function.statements:
        statement = statement[0]
        evaluate(statement)
        if return_value:
            break
        continue

    return return_value

# Functions in the Z language
def zget(*args):
    content = input()
    try:
        return (float if "." in content else int)(content)
    except Exception:
        return content

def zprint(*args):
    if not args:
        print()
        return
    output = args[0]
    if type(output) == bool:
        print("true" if output else "false", end="")
        return
    print(output, end="")

def znot(*args):
    if not args:
        err("No arguments provided to function not.")
    args = args[0]
    return not args

def zadd(*args):
    if not args:
        err("No arguments provided to function add.")
    return args[0] + args[1]

def main():
    functions = {
        "add": zadd,
        "get": zget,
        "not": znot,
        "print": zprint
    }
    visitor = ZVisitor(functions)
    parser = ParserPython(program, comment)
    prog = sys.stdin.read() if len(sys.argv) == 1 else open(sys.argv[1]).read()
    parse_tree = parser.parse(prog)
    visit_parse_tree(parse_tree, visitor)

if __name__ == "__main__":
    main()
