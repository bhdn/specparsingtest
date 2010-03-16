import glob

import parser
import parser_types

default_files = ["/usr/lib/rpm/macros",
        "/etc/rpm/macros", "/etc/rpm/macros.d/*.macros"]

class LoadError(Exception):
    pass

def load():
    ctx = parser_types.Context()
    for pat in default_files:
        files = glob.glob(pat)
        for file in files:
            try:
                mf = parser.parse_macro_file(open(file).read())
                mf.eval(ctx)
            except parser.ParserError, e:
                raise LoadError, "failed to parse %s" % file
    return ctx
