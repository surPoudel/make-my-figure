import gc, sys, weakref
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from shiboken6 import Shiboken as S
app=QApplication(sys.argv); h=QWidget(); l=QVBoxLayout(h)
class C(QWidget):
    def __init__(s): super().__init__(); s.cycle=s
for label, ops in [("plain owned, no deleteLater", "o"), ("setParent(None) only", "p"), ("setParent(None)+deleteLater", "pd"), ("in layout, removeWidget only", "r")]:
    c=C(); l.addWidget(c) if ops!="o" else None
    if "r" in ops or "p" in ops: l.removeWidget(c)
    if "p" in ops: c.setParent(None)
    if "d" in ops: c.deleteLater()
    print(label, "refcount", sys.getrefcount(c)-1, "owned", S.ownedByPython(c), "gc-tracked", gc.is_tracked(c))
    r=weakref.ref(c); del c; gc.collect(); print("   alive after collect:", r() is not None)
