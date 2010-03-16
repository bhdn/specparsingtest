# vim:tw=0
import parser

A = 1

def t(s, a=None):
    o = parser.parse(s)
    r = repr(o)
    print "%r => %s" % (s, r)
    if A and a:
        assert r == a, "%s ==> NEW: \n%s\n!= OLD:\n%s\n" % (s, r, a)
    return o

def t2(s, a=None):
    o = parser.parse_macro_file(s)
    r = repr(o)
    print "%r => %s" % (s, r)
    if A and a:
        assert r == a, "\n%s\n!=\n%s\n" % (r, a)
    return o

t("foo", r"Spec([Text('foo')])")
t("foo\nbar", r"Spec([Text('foo\nbar')])")
t("foo%%", r"Spec([Text('foo'), Text('%')])")
t("foo%bar", r"Spec([Text('foo'), MacroNameExpand([MacroName('bar')])])")
t("foo%bar%bling", r"Spec([Text('foo'), MacroNameExpand([MacroName('bar')]), MacroNameExpand([MacroName('bling')])])")
t("foo%bling\n", r"Spec([Text('foo'), MacroNameExpand([MacroName('bling')]), Text('\n')])")

o = t("foo%{bar%{baran%{barov%{barev}}}}baz", r"Spec([Text('foo'), MacroNameExpand([MacroName('bar')]), Text('baz')])")
assert o.value[1].args

t("%define simple_macro simple_value", r"Spec([MacroDefine(name=MacroName('simple_macro'),body=MacroBody([Text('simple_value')]))])")

t("%define simple_macro simple_value\nanother non-related line", r"Spec([MacroDefine(name=MacroName('simple_macro'),body=MacroBody([Text('simple_value')])), Text('\nanother non-related line')])")

t("%define simple_macro one line\\\nanother line\n", r"Spec([MacroDefine(name=MacroName('simple_macro'),body=MacroBody([Text('one line\nanother line')])), Text('\n')])")

t("%define simple_macro one line\\\nanother %line\n", r"Spec([MacroDefine(name=MacroName('simple_macro'),body=MacroBody([Text('one line\nanother '), MacroNameExpand([MacroName('line')])])), Text('\n')])")

t("%define .simple_ro_macro %{bar} line\\\nanother %line\n", r"Spec([MacroDefine(name=MacroName('simple_ro_macro'),body=MacroBody([MacroNameExpand([MacroName('bar')]), Text(' line\nanother '), MacroNameExpand([MacroName('line')])])), Text('\n')])")

t("%define parametrized(p) foo bar baz\\\n%define blarg legal\\\nRelease: %blarg", r"Spec([MacroDefine(name=MacroName('parametrized'),body=MacroBody([Text('foo bar baz\n'), MacroDefine(name=MacroName('blarg'),body=MacroBody([Text('legal')])), Text('\nRelease: '), MacroNameExpand([MacroName('blarg')])]))])")

t("%define parametrized(p) foo bar baz\\\n%define blarg legal\\\nRelease: %blarg\nName: %parametrized", r"Spec([MacroDefine(name=MacroName('parametrized'),body=MacroBody([Text('foo bar baz\n'), MacroDefine(name=MacroName('blarg'),body=MacroBody([Text('legal')])), Text('\nRelease: '), MacroNameExpand([MacroName('blarg')])])), Text('\nName: '), MacroNameExpand([MacroName('parametrized')])])")

t("%define mkrel() something\n", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([Text('something')])), Text('\n')])")

o = t("%define mkrel() something\nFoo: %mkrel 666.0 888.0 999.0\n\n", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([Text('something')])), Text('\nFoo: '), MacroNameExpand([MacroName('mkrel')]), Text('\n\n')])")
assert len(o.value[2].args.value) == 3 and o.value[2].body

o = t("%define mkrel() something\nFoo: %{mkrel 666.0 888.0 / 999.0}\n\n", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([Text('something')])), Text('\nFoo: '), MacroNameExpand([MacroName('mkrel')]), Text('\n\n')])")
assert len(o.value[2].args.value) == 4 and o.value[2].body

o = t("%define mkrel(c:) %{-c:HAZ CEESBURGER}", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([MacroOptExpand(neg=False,arg=False,body=[MacroName('-c')])]))])")

t("%define mkrel(c:) %{!-c*:HAZ CEESBURGER}", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([MacroOptExpand(neg=True,arg=True,body=[MacroName('!-c*')])]))])")

o = t("%define blarg(c:) %{-c:hallo: %{-c*}}", r"Spec([MacroDefine(name=MacroName('blarg'),body=MacroBody([MacroOptExpand(neg=False,arg=False,body=[MacroName('-c')])]))])")
assert o.value[0].body.value[0].body.value[0].value == "hallo: "

t("%define blarg(c:) %{-c:hallo: %{-c*}}%{!-c:another param: %{1}}", r"Spec([MacroDefine(name=MacroName('blarg'),body=MacroBody([MacroOptExpand(neg=False,arg=False,body=[MacroName('-c')]), MacroOptExpand(neg=True,arg=False,body=[MacroName('!-c')])]))])")

# our holy grail
o = t("%define mkrel(c:) %{-c: 0.%{-c*}.}%{1}%{?subrel:.%subrel}%{?distsuffix:%distsuffix}%{?!distsuffix:mdv}%{?mandriva_release:%mandriva_release}", r"Spec([MacroDefine(name=MacroName('mkrel'),body=MacroBody([MacroOptExpand(neg=False,arg=False,body=[MacroName('-c')]), MacroNameExpand([MacroName('1')]), MacroCondExpand(neg=False,body=[MacroName('?subrel')]), MacroCondExpand(neg=False,body=[MacroName('?distsuffix')]), MacroCondExpand(neg=True,body=[MacroName('?!distsuffix')]), MacroCondExpand(neg=False,body=[MacroName('?mandriva_release')])]))])")

t("%define blarg %(ls -lh /sys/class/net)", r"Spec([MacroDefine(name=MacroName('blarg'),body=MacroBody([ShellExpand([Text('ls -lh /sys/class/net')])]))])")

t("%define blarg %(ls -lh /usr/share/doc/%pkgname/)", r"Spec([MacroDefine(name=MacroName('blarg'),body=MacroBody([ShellExpand([Text('ls -lh /usr/share/doc/'), MacroNameExpand([MacroName('pkgname')]), Text('/')])]))])")

try:
    o = t("%foo %{expand:%%blarg blirg %{zlarg:\\\nfoo\n}}")
except parser.Expected:
    pass
else:
    raise Exception, "should have raised Expected"

t2("# alo\n%foo bar\n", r"MacroFile([MacroDefine(name=MacroName('foo'),body=MacroBody([Text(' bar')]))])")

t2("%foo \\\n bar\\\\\\\n %baz\\\\\\\nblarg", r"MacroFile([MacroDefine(name=MacroName('foo'),body=MacroBody([Text(' \n bar\\\n '), MacroNameExpand([MacroName('baz')]), Text('\\\nblarg')]))])")

t2("%something %(echo one \\\\\\\n  two\\\\\\\ntree)\n\n", r"MacroFile([MacroDefine(name=MacroName('something'),body=MacroBody([Text(' '), ShellExpand([Text('echo one \\\n  two\\\ntree')])]))])")

o = t("%define foo FOO\n%ifarch noarch\nNOARCH!\n%endif\nHallo: %foo\n", r"Spec([MacroDefine(name=MacroName('foo'),body=MacroBody([Text('FOO')])), Text('\n'), IfArch(e=[Text('noarch')],then=MacroBody([Text('\nNOARCH!\n'), EndIf(e=[],then=None,else=None)]),else=None), Text('\nHallo: '), MacroNameExpand([MacroName('foo')]), Text('\n')])")

o = t("%define foo FOO\n%ifarch noarch\nNOARCH!\n%else\nHEYA\n%endif\nHallo: %foo\n", r"Spec([MacroDefine(name=MacroName('foo'),body=MacroBody([Text('FOO')])), Text('\n'), IfArch(e=[Text('noarch')],then=MacroBody([Text('\nNOARCH!\n')]),else=MacroBody([Text('\nHEYA\n')])), Text('\nHallo: '), MacroNameExpand([MacroName('foo')]), Text('\n')])")

o = t("%if %mdkversion > 200901666\nfoo\nbar\nbaz\n%else\nbaz\nbar\nfoo\n%endif\nfimm\n")

o = t("%foo %{expand:%%blarg blirg %{zlarg:\\\nfoo\\\n}}")


o = t2("""%__policy_tree\t%{expand:%%global __policy_tree %{lua:\\\nt="targeted"\\\nf = io.open("/etc/selinux/config")\\\nif f then\\\n  for l in f:lines() do\\\n    if "SELINUXTYPE=" == string.sub(l,0,12) then t=string.sub(l,13); end\\\n  end\\\n  f:close()\\\nend\\\nprint (t)\\\n}}%{__policy_tree}\n""")

o = t(r"""
%define cmake_qt4 \
  QTDIR="%qt4dir" ; export QTDIR ; \
  PATH="%qt4dir/bin:$PATH" ; export PATH ; \
  CPPFLAGS="${CPPFLAGS:-%optflags -DPIC -fPIC}" ; export CPPFLAGS ; \
  %setup_compile_flags \
  mkdir -p build \
  cd build \
  %__cmake .. \\\
  %if "%{_lib}" != "lib" \
    -DLIB_SUFFIX=64 \\\
  %endif \
  -DCMAKE_INSTALL_PREFIX=%_prefix \\\
  -DCMAKE_MODULE_LINKER_FLAGS="%(echo %ldflags|sed -e 's#-Wl,--no-undefined##')" \\\
  -DDBUS_SERVICES_DIR=%_datadir/dbus-1/services \\\
  -DDBUS_INTERFACES_DIR=%_datadir/dbus-1/interfaces
""")

o = t2(r"""
%cmake_qt4 \
  QTDIR="%qt4dir" ; export QTDIR ; \
  PATH="%qt4dir/bin:$PATH" ; export PATH ; \
  CPPFLAGS="${CPPFLAGS:-%optflags -DPIC -fPIC}" ; export CPPFLAGS ; \
  %setup_compile_flags \
  mkdir -p build \
  cd build \
  %__cmake .. \\\
  %if "%{_lib}" != "lib" \
    -DLIB_SUFFIX=64 \\\
  %endif \
  -DCMAKE_INSTALL_PREFIX=%_prefix \\\
  -DCMAKE_MODULE_LINKER_FLAGS="%(echo %ldflags|sed -e 's#-Wl,--no-undefined##')" \\\
  -DDBUS_SERVICES_DIR=%_datadir/dbus-1/services \\\
  -DDBUS_INTERFACES_DIR=%_datadir/dbus-1/interfaces
""")
import pdb; pdb.set_trace()

o  = t("%define foo() [%1]\n%foo \"this is the first \\\\\"argument\\\\\" for foo\"", r"Spec([MacroDefine(name=MacroName('foo'),body=MacroBody([Text('['), MacroNameExpand([MacroName('1')]), Text(']')])), Text('\n'), MacroNameExpand([MacroName('foo')])])")


#o = t2(open("/usr/lib/rpm/macros").read())
#o = t2(open("/etc/rpm/macros.d/qt4.macros").read())

