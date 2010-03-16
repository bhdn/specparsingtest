# vim:ts=0
import parser

A = 1

def t(s, a=None):
    global c
    t = parser.parse(s)
    r = t.eval(c)
    print "=====\n%r\n=>\n, %r\n=====" % (s, r)
    if A and a:
        assert r == a, "\n%s ==>\nfound: %s\nexpected: %s\n" % (s, r, a)
    return r, a

c = parser.Context()

ra = t("[%foo]", r'[%foo]')

c.define("foo", parser.Text("FOOOO!"))
ra = t("[%foo] (with %%foo set)", r'[FOOOO!] (with %foo set)')
ra = t("[%foo%%bar]", r'[FOOOO!%bar]')
ra = t("%define blarg blirg\n[%blarg]", '\n[blirg]')
ra = t("%define blarg() blirg\n[%blarg]", '\n[blirg]')
ra = t("%define blarg() blirg(%0)\n[%blarg]", '\n[blirg(blarg)]')
ra = t("%define blarg() blirg(%0,%1)\n[%blarg param!] itshouldnotbevisible", '\n[blirg(blarg,param!])')
ra = t("%define blarg simple text macro\n[%blarg param] visible")

# FIXME it is eating everything and not dumping the .body
ra = t("%define blarg simple text macro\n[%invalidname param] visible", '\n[%invalidname param] visible')

ra = t("%define foo FOO\n%define uses_foo() (p=%1,f=%foo)\nx = %uses_foo someparam", '\n\nx = (p=someparam,f=FOO)')
ra = t("%define uses_foo() (p=%1,f=%foo)\n%define foo FOO2\nx = %uses_foo someparam", '\n\nx = (p=someparam,f=FOO2)')

ra = t("%define p(cd) [%1,%2,%3](%{-c:CE},%{-d:DE})\nvalor: %p -d uma mensagem legal aqui -c \nFIN", '\nvalor: [uma,mensagem,legal](CE,DE)\nFIN')

ra = t("%define p(c:d) [%1,%2,%3](%{-c:%{-c*}},%{-d:DE})\nvalor: %p -d uma mensagem legal aqui -c v\nFIN", '\nvalor: [uma,mensagem,legal](v,DE)\nFIN')
ra = t("%define p(c:d) [%1,%2,%3](%{-c:%-c*},%{-d:DE})\nvalor: %p -d uma mensagem legal aqui -c v\nFIN", '\nvalor: [uma,mensagem,legal](v,DE)\nFIN')

ra = t("%define cmd %(echo um\\\necho dois tres)\ncmd = [%cmd]", '\ncmd = [um\ndois tres\n]')

ra = t("%define foo FOO\nx: alo%?foo", '\nx: aloFOO')

ra = t("%define foo FOO\nx: alo%{?!foo:ERR}%{?!bar:BAR NON ECZISTE}", '\nx: aloBAR NON ECZISTE')

ra = t("%if 0\nERR\n%else\nZERO\n%endif\n", '\nZERO\n\n')

ra = t("%if 1\nUN!\n%else\nERR\n%endif\n", '\nUN!\n\n')

ra = t("%if ! 1\nERR!\n%else\nNOTUN!\n%endif\n", '\nNOTUN!\n\n')

ra = t("%if 1 > 0\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if 0 < 1\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if 0 < 1\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if 0 == 0\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if a == a\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if a == b\nOOPS!\n%else\nOK!\n%endif\n", '\nOK!\n\n')

ra = t("%if \"pryvit, svite\" == \"pryvit, svite\"\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if \"alo mundo\" == \"pryvit, svite\"\nOOPS!\n%else\nOK!\n%endif\n", '\nOK!\n\n')

ra = t("%if \"alo mundo\" != \"alo mundo diferente\"\nOK!\n%else\nOOPS!\n%endif\n", '\nOK!\n\n')

ra = t("%if 9 == devjat\nOOPS!\n%else\nOK!\n%endif\n", '\nOK!\n\n')

ra = t("%if \"\\\\\"quotes\\\\\"\" == nada\nOOPS!\n%else\nOK!\n%endif\n", '\nOK!\n\n')

ra = t("%if \"\\\\\"quotes\\\\\"\" == nada\nOOPS!\n%else\nOK!\n%endif\n", '\nOK!\n\n')

ra = t("%define _arch i386\n%ifarch i586\nOOPS!\n%else\nOK!\n%endif\n", '\n\nOK!\n\n')

ra = t("%define _arch i386\n%ifnarch i586 i686\nOK!\n%else\nOOPS!\n%endif\n", '\n\nOK!\n\n')

ra = t("%define _arch i586\n%ifarch i486 i586 i686\nOK!\n%else\nOOPS!\n%endif\n", '\n\nOK!\n\n')

ra = t("%define _os linux\n%ifos linux\nOK!\n%else\nOOPS!\n%endif\n", '\n\nOK!\n\n')

ra = t("%define _os linux\n%ifnos windows freebsd\nOK!\n%else\nOOPS!\n%endif\n", '\n\nOK!\n\n')

ra = t("""\
%define _os linux
%define _arch i386
%define ix86 i386 i486 i586 i686 pentium3 pentium4 athlon geode
%ifarch %ix86
  %ifos darwin linux solaris
    :-)
  %else
    :-(
  %endif
%else
  OOPS!
%endif
""", '\n\n\n\n  \n    :-)\n  \n\n')

