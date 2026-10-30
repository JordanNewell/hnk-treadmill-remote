"""Dump smali of TreadMill_HNK class."""
from androguard.misc import AnalyzeDex

a, d, dx = AnalyzeDex("C:/tmp/wfx/classes.dex")
out = open("C:/tmp/hnk.smali", "w", encoding="utf-8")
count = 0
for cls in d.get_classes():
    if "TreadMill_HNK" in cls.get_name():
        count += 1
        out.write(cls.get_source())
        out.write("\n\n")
out.close()
print("dumped", count, "classes")
