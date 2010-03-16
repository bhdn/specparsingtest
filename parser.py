from parser_types import *

class ParserError(Exception):
    pass

class Expected(ParserError):
    pass

class InvalidIdentifier(ParserError):
    pass

class SpecParser:

    def __init__(self, rawspec, macros=None):
        self.rawspec = rawspec
        self.pos = 0
        self.prev = None
        self.macros = {}
        if macros:
            self.macros = macros
        self.wrapped = -1
        self.pending = []

    def peek(self, str, go=False):
        if self.pos + len(str) > len(self.rawspec):
            return False
        sub = self.rawspec[self.pos:self.pos + len(str)]
        res = sub == str
        if res and go:
            self.pos += len(str)
        return res

    def go(self):
        if self.pos >= len(self.rawspec):
            if self.pos == len(self.rawspec):
                # !!!
                self.pos += 1
            return ""
        c = self.rawspec[self.pos]
        self.pos += 1
        return c

    def back(self):
        if self.pos:
            self.pos -= 1

    def cur(self):
        if self.pos >= len(self.rawspec):
            return ""
        return self.rawspec[self.pos]

    def last(self):
        assert self.pos != 0
        if self.pos >= len(self.rawspec):
            return ""
        return self.rawspec[self.pos - 1]

    def expect(self, str):
        if not self.peek(str, 1):
            raise Expected(str)

    def block(self):
        line = []
        lines = []
        while True:
            c = self.go()
            if c == "\\":
                line.append(c)
                line.append(self.go())
            elif c == "\n" or not c:
                lines.append("".join(line))
                line[:] = []
                break
            else:
                line.append(c)
        self.back()
        return "".join(lines)

    def anything(self, body, split=False, except_=None, escaping=False,
            escaped_newline=True):
        def reset_text():
            str = "".join(text)
            body.append(Text(str))
            return []
        text = []
        quoted = False
        while True:
            c = self.go()
            if c == "%":
                if text:
                    text = reset_text()
                self.back()
                if self.wrapped == -1 and not self.is_cond():
                    block = self.block()
                    parser = SpecParser(block, self.macros)
                    parser.wrapped = self.wrapped + 1
                    parser.anything(body, split, except_, escaping,
                            escaped_newline)
                    continue
                else:
                    block = self.macro_related()
                body.append(block)
                if isinstance(block, (Else, EndIf)):
                    break
            elif c == "$":
                if self.peek("{"):
                    self.back()
                    if text:
                        text = reset_text()
                    body.extend(self.shell_variable())
                else:
                    text.append(c)
            elif escaping and c == "\\":
                c = self.go()
                if c == "\n" and not escaped_newline:
                    self.back()
                    self.back()
                    # \ must be fetched by the outer macro
                    break
                text.append(c)
            elif split and c == "\"":
                quoted = not quoted
            elif self.feeds_pending(c):
                self.back()
                self.pending.pop()
                break
            elif except_ and c in except_:
                self.back()
                break
            elif split and not quoted and c.isspace():
                if text:
                    text = reset_text()
            elif not c:
                #EOF
                if self.pending:
                    self.pending.pop()
                break
            else:
                text.append(c)
        if text:
            reset_text()

    def feeds_pending(self, c):
        if self.pending:
            if self.pending[-1] == c:
                return True
            for pend in reversed(self.pending):
                if pend == "\n":
                    continue
                return pend == c
        return False

    def shell_variable(self):
        self.expect("${")
        body = [Text("${")]
        self.pending.append("}")
        self.wrapped += 1
        self.anything(body)
        self.wrapped -= 1
        self.expect("}")
        body.append(Text("}"))
        return body

    def spec(self):
        # TODO spec sections (%changelog, %files, ...)
        spec = Spec()
        self.anything(spec)
        return spec

    def identifier(self):
        pos = self.pos
        # FIXME nou saide effffektz!!!
        if not (self.go().isalpha() or self.last() == "_"):
            raise InvalidIdentifier
        while self.go().isalnum() or self.last() == "_":
            pass
        self.back()
        return self.rawspec[pos:self.pos]

    def macro_line(self):
        #self.wrapped += 1
        self.expect("%")
        block = self.block()
        parser = SpecParser(block, self.macros)
        parser.wrapped = self.wrapped + 1
        m = parser.macro_define(macrofile=True)
        #self.wrapped -= 1
        return m

    def comment(self):
        self.expect("#")
        while True:
            c = self.go()
            if c == "\n" or not c:
                break

    def macrofile(self):
        mf = MacroFile()
        while True:
            c = self.go()
            if not c:
                break
            elif c.isspace():
                continue
            elif c == "#":
                self.back()
                self.comment()
            elif c == "%":
                self.back()
                block = self.macro_line()
                mf.append(block)
            else:
                raise ParserError, "unexpected: %s" % c
        return mf

    def blank(self):
        found = False
        while self.go().isspace():
            found = True
        if not found:
            raise Expected("blank")
        
    def macro_related(self):
        if self.peek("%%", 1):
            return Text("%")
        if self.peek("%define", 1):
            return self.macro_define()
        elif self.peek("%("):
            return self.shell_expand()
        else:
            return self.macro_expand(braces=self.peek("%{"))

    def shell_expand(self):
        self.expect("%(")
        body = ShellExpand()
        mb = self.macro_body(end=")")
        # cheating:
        body.extend(mb.value)
        self.expect(")")
        return body

    def macro_name(self):
        pos = self.pos
        valid = tuple("*#?-!_")
        while self.go().isalnum() or self.last() in valid:
            pass
        self.back()
        id = self.rawspec[pos:self.pos]
        return MacroName(id)

    def macro_define(self, macrofile=False):
        self.wrapped += 1
        if not macrofile:
            self.blank()
            self.back()
        ro = False
        if self.peek(".", 1):
            ro = True
        name = self.macro_name()
        if self.peek("("):
            m = self.macro_define_parameters(macrofile)
        else:
            m = self.macro_define_simple(macrofile)
        m.name = name
        m.readonly = ro
        self.macros[name.value] = m
        self.wrapped -= 1
        return m

    def macro_body(self, end=None, multiline=False):
        body = MacroBody()
        except_ = []
        if end:
            self.pending.append(end)
        elif self.wrapped > 1 and not multiline:
            self.pending.append("\n")
        escaped = bool(end) or self.wrapped == 1
        self.anything(body, except_=except_, escaping=True,
                escaped_newline=escaped)
        return body
        
    def macro_parameters(self):
        pos = self.pos
        while self.go().isalnum() or self.last() == ":":
            pass
        last = self.pos - 1
        self.back()
        return self.rawspec[pos:last]

    def macro_define_parameters(self, macrofile=False):
        self.expect("(")
        m = MacroDefine()
        m.params = self.macro_parameters()
        self.expect(")")
        self.blank()
        self.back()
        end = None
        if macrofile:
            end = "\n"
        m.body = self.macro_body(end=end)
        return m

    def macro_define_simple(self, macrofile=False):
        if not macrofile:
            self.blank()
            self.back()
        m = MacroDefine()
        end = None
        if macrofile:
            end = "\n"
        m.body = self.macro_body(end=end)
        return m

    def macro_arguments(self, expansion, braces=False, oneline=False):
        self.wrapped += 1
        except_ = []
        if braces:
            self.pending.append("}")
        else:
            self.pending.append("\n")
        escaped = not oneline and self.wrapped == 1
        self.anything(expansion, split=True, except_=except_,
                escaping=True, escaped_newline=escaped)
        self.wrapped -= 1

    def macro_type(self, name):
        typespec = name.value
        mode = MacroNameExpand
        neg = False
        text = []
        usearg = False
        for c in typespec:
            if c == ":":
                break
            elif c == "!":
                neg = not neg
            elif c == "*":
                usearg = True
            elif c == "-" and mode is MacroNameExpand:
                mode = MacroOptExpand
            elif c == "?" and mode is MacroNameExpand:
                mode = MacroCondExpand
            else:
                text.append(c)
        expand = mode()
        expand.append(name)
        expand.name = name
        expand.target = "".join(text)
        expand.negate = neg
        expand.usearg = usearg
        return expand

    conditionals = {
        "if": If,
        "ifarch": IfArch,
        "ifnarch": IfNotArch,
        "ifos": IfOs,
        "ifnos": IfNotOs,
        "endif": EndIf,
        "else": Else
    }

    def is_cond(self):
        self.go()
        found = False
        for name in self.conditionals:
            if self.peek(name):
                found = True
                break
        self.back()
        return found

    def try_cond(self, name):
        try:
            type = self.conditionals[name.value]
        except KeyError:
            return
        self.wrapped -= 1
        cond = type()
        if type not in (EndIf, Else):
            self.macro_arguments(cond, oneline=True)
            cond.then_ = MacroBody()
            self.anything(cond.then_)
            if isinstance(cond.then_.value[-1], Else):
                cond.then_.value.pop()
                cond.else_ = MacroBody()
                self.anything(cond.else_)
                cond.else_.value.pop()
        self.wrapped += 1
        return cond

    def is_builtin_macro(self, name):
        builtins = "*", "#"
        if name.value in builtins or name.value.isdigit():
            return True
        return False

    def macro_expand(self, braces=False):
        self.wrapped += 1
        multiline = False
        if braces:
            self.expect("%{")
        else:
            self.expect("%")
        name = self.macro_name()
        if name.value == "if":
            import pdb; pdb.set_trace()
        if not braces:
            cond = self.try_cond(name)
            if cond:
                self.wrapped -= 1
                return cond
        if self.cur() == ":":
            multiline = True
            self.go()
        m = self.macro_type(name)
        m.braces = braces
        md = self.macros.get(m.target)
        if braces or (self.cur() != "\n" and self.cur().isspace()):
            pos = self.pos
            m.args = MacroArguments()
            self.macro_arguments(m.args, braces=braces)
            self.pos = pos
            end = None
            if braces:
                end = "}"
            if not self.is_builtin_macro(name):
                m.body = self.macro_body(end=end, multiline=multiline)
            if braces:
                self.expect("}")
        self.wrapped -= 1
        return m

def parse(rawspec):
    sp = SpecParser(rawspec)
    return sp.spec()

def parse_macro_file(raw):
    sp = SpecParser(raw)
    return sp.macrofile()
