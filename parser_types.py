import getopt
import subprocess

class EvalError(Exception):
    pass

class ExpressionError(EvalError):
    pass

class TypeError(ExpressionError):
    pass

class Context:

    def __init__(self, parent=None):
        self.macros = {}
        self.parent = parent

    def get(self, name, eval=True):
        tree = self.macros.get(name)
        if tree is None:
            if self.parent:
                tree = self.parent.get(name, eval)
                return tree
        elif eval:
            return tree.eval(self)
        return tree

    def define(self, name, value):
        macrodef = MacroDefine()
        macrodef.name = MacroName(name)
        macrodef.body = MacroBody()
        macrodef.body.append(value)
        self.set(name, MacroDefined(macrodef))

    def set(self, name, tree):
        self.macros[name] = tree

class Node(object):
 
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.value)

    def eval(self, ctx):
        raise NotImplementedError, self.__class__.__name__

class NodeList(Node):
    
    def __init__(self):
        self.value = []

    def append(self, value):
        self.value.append(value)

    def extend(self, values):
        self.value.extend(values)

    def eval(self, ctx):
        return "".join(self.eval_list(ctx))

    def eval_list(self, ctx):
        all = [value.eval(ctx) for value in self.value]
        return all

class Text(Node):

    def eval(self, ctx):
        return self.value

class MacroName(Node): pass

class MacroExpansion(NodeList):

    def __init__(self):
        super(MacroExpansion, self).__init__()
        self.args = None
        self.body = None
        self.braces = None

    def create_expand_context(self, ctx, macro):
        newctx = Context(ctx)
        newctx.define("0", Text(self.name.value))
        if self.args:
            if macro.params:
                values = [arg.eval(ctx) for arg in self.args.value]
                parsed, rest = getopt.gnu_getopt(values, macro.params)
                for arg, val in parsed:
                    newctx.define(arg, Text(val or arg))
                    if val:
                        newctx.define(arg + "*", Text(val))
                for i, arg in enumerate(rest):
                    newctx.define(str(i + 1), Text(arg))
            else:
                for i, arg in enumerate(self.args.value):
                    newctx.define(str(i + 1), arg)
            newctx.define("*", self.body)
            newctx.define("#", Text(str(len(self.args.value))))
        return newctx

    def eval(self, ctx):
        name = self.value[0]
        tree = ctx.get(name.value, False)
        if not tree:
            if self.body:
                body = self.body.eval(ctx)
            else:
                body = ""
            if self.braces:
                fmt = "%%{%s%s}"
            else:
                fmt = "%%%s%s"
            dump = fmt % (name.value, body)
            return dump
        macro = tree.value
        if macro.params is not None:
            # parametrized macro, consume args and body
            newctx = self.create_expand_context(ctx, macro)
            dump = macro.body.eval(newctx)
        else:
            # simple macro, dump body too
            value = macro.body.eval(ctx)
            bodyval = ""
            if self.body:
                bodyval = self.body.eval(ctx)
            dump = value + bodyval
        return dump

class ShellExpand(MacroExpansion):

    def eval(self, ctx):
        cmd = "".join(self.eval_list(ctx))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        out = p.stdout.read()
        return out

class Cond(MacroExpansion):
    
    def __init__(self):
        super(Cond, self).__init__()
        self.cond = None
        self.else_ = None
        self.then_ = None

    def __repr__(self):
        return "%s(e=%s,then=%s,else=%s)" % (self.__class__.__name__, self.value, self.then_, self.else_)

    def eval(self, ctx):
        values = self.eval_list(ctx)
        if self.eval_cond(ctx, values):
            return self.then_.eval(ctx)
        elif self.else_:
            return self.else_.eval(ctx)

class If(Cond):

    def eq(l, r):
        return l == r
    def dif(l, r):
        return l != r
    def lt(l, r):
        return l < r
    def lte(l, r):
        return l <= r
    def gt(l, r):
        return l > r
    def gte(l, r):
        return l >= r

    operators = {"==": eq, "!=": dif, "<": lt, "<=": lte, ">": gt,
            ">=": gte}

    def _cmp_values(self, values):
        #import pdb; pdb.set_trace()
        rl = values[0]
        op = values[1]
        rr = values[2]
        l = r = None
        try:
            try:
                l = int(rl)
                r = int(rr)
                return self.operators[op](l, r)
            except ValueError:
                if (l is not None or r is not None) and op not in ("!=", "=="):
                    raise TypeError, "incompatible types: '%s' and '%s'" % (l, r)
                return self.operators[op](rl, rr)
        except KeyError:
            raise ExpressionError, "invalid operator: %r" % op

    def eval_cond(self, ctx, values):
        neg = False
        uses_neg = False
        op = -1
        for i, operand in enumerate(values):
            if operand == "!":
                neg = not neg
                uses_neg = True
                op = i
            else:
                break
        remaining = len(values) - op - 1
        if not uses_neg and remaining == 3: # operand operator operand
            return self._cmp_values(values[op + 1:])
        elif remaining == 1: # a number
            try:
                num = int(values[op + 1])
            except ValueError:
                raise TypeError, "expected an integer"
            return bool(num) and not neg
        else:
            raise ExpressionError, "invalid expression: %s" % \
                    "".join(values)
        return False

class SysCond(Cond):

    metavar = None

    def eval_cond(self, ctx, values):
        # flatten possible values, as they may be expanded from a macro
        # (possible bug)
        options = []
        for value in values:
            options.extend(value.split())
        tree = ctx.get(self.metavar, False)
        if tree:
            arch = tree.value.body.eval(ctx)
            return arch in options
        return False

class SysCondNeg(SysCond):

    def eval_cond(self, ctx, values):
        return not super(SysCondNeg, self).eval_cond(ctx, values)

class IfArch(SysCond):
    metavar = "_arch"

class IfNotArch(IfArch, SysCondNeg): pass

class IfOs(SysCond):
    metavar = "_os"

class IfNotOs(IfOs, SysCondNeg): pass

# workarounds:
class EndIf(Cond): pass
class Else(Cond): pass

class MacroNameExpand(MacroExpansion):

    def __init__(self):
        super(MacroNameExpand, self).__init__()
        self.name = None

class MacroCond(MacroExpansion):

    def __init__(self):
        super(MacroCond, self).__init__()
        self.negate = False

    def __repr__(self):
        return "%s(neg=%s,body=%s)" % (self.__class__.__name__, self.negate, self.value)

class MacroCondExpand(MacroCond):

    def eval(self, ctx):
        md = ctx.get(self.target, False)
        if bool(md) == self.negate:
            return ""
        if self.body:
            return self.body.eval(ctx)
        return md.value.body.eval(ctx)

class MacroOptExpand(MacroCond):

    def __init__(self):
        super(MacroOptExpand, self).__init__()
        self.userarg = False

    def __repr__(self):
        return "%s(neg=%s,arg=%s,body=%s)" % (self.__class__.__name__, self.negate, self.usearg, self.value)

    def eval(self, ctx):
        tree = ctx.get(self.name.value, False)
        if tree is None:
            return ""
        if self.usearg:
            return tree.value.body.eval(ctx)
        return self.body.eval(ctx)

class Spec(NodeList): pass
class MacroFile(NodeList): pass

class MacroDefine(Node):

    def __init__(self):
        super(MacroDefine, self).__init__(None)
        self.name = None
        self.params = None
        self.body = None
        self.readonly = False

    def __repr__(self):
        return "%s(name=%s,body=%s)" % (self.__class__.__name__, self.name, self.body)

    def eval(self, ctx):
        ctx.set(self.name.value, MacroDefined(self))
        return ""

class MacroDefined(Node):

    def eval(self, ctx):
        raise NotImplementedError, "bug!"

class MacroBody(NodeList): pass
class MacroArguments(NodeList): pass
