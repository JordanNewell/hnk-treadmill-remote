"""Locate FFB0 usage in FITIME dex via androguard, dump smali of relevant methods."""
import sys
from androguard.misc import AnalyzeDex

DEX = sys.argv[1] if len(sys.argv) > 1 else "C:/tmp/wfx/classes.dex"

print("analyzing (slow first load) ...")
a, d, dx = AnalyzeDex(DEX)

targets = []
for s in dx.find_strings(".*"):
    v = s.get_value()
    if isinstance(v, str) and ("ffb0" in v.lower() or "faef" in v.lower() or
                               "ffb1" in v.lower() or "ffb2" in v.lower()):
        targets.append(v)
        print("STRING:", v[:120])

seen = set()
for s in dx.find_strings(".*"):
    v = s.get_value()
    if isinstance(v, str) and ("ffb" in v.lower() or "faef" in v.lower()):
        for cls, meth in s.get_xref_from():
            key = (cls.name if hasattr(cls, 'name') else str(cls),
                   meth.name if hasattr(meth, 'name') else str(meth))
            if key not in seen:
                seen.add(key)
                print("XREF:", key)
print(f"\n{len(targets)} strings, {len(seen)} methods")
