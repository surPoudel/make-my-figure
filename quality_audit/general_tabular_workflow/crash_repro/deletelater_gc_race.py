"""Deterministic-as-possible: widen the gap between slot return and DeferredDelete processing
(C++-only posted events ahead of deleteLater), with a worker waiting to run a full GC in that gap."""
import faulthandler, gc, sys, threading
faulthandler.enable()
from PySide6.QtCore import QThread, QTimer, QObject, QEvent, QCoreApplication
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from shiboken6 import Shiboken as S
app = QApplication(sys.argv); host = QWidget(); lay = QVBoxLayout(host); host.show()
MAIN = threading.get_ident(); stats = {"worker": 0, "armed": 0}
sink = QObject()                       # plain C++ QObject: its events run no Python
class Canvas(QWidget):
    def __init__(self): super().__init__(); self.cycle = self
    def __del__(self):
        if threading.get_ident() != MAIN:
            stats["worker"] += 1
            if S.isValid(self) and S.ownedByPython(self): stats["armed"] += 1
go = threading.Event()
class Worker(QThread):
    def run(self):
        go.wait(); gc.collect()
gc.disable()
st = {"c": None, "n": 0}
def step():
    c = st.pop("c", None)
    w = Worker(); st["w"] = w; w.start()
    if c is not None:
        lay.removeWidget(c)
        for _ in range(int(sys.argv[2])): QCoreApplication.postEvent(sink, QEvent(QEvent.User))
        c.setParent(None); c.deleteLater()
    del c
    st["c"] = Canvas(); lay.addWidget(st["c"])
    st["n"] += 1
    go.set()                            # worker collects as soon as this slot returns
    if st["n"] >= int(sys.argv[1]):
        print(stats, flush=True); app.quit()
def rearm(): go.clear()
t = QTimer(); t.timeout.connect(lambda: (st.get("w") and st["w"].wait(), rearm(), step())); t.start(0)
app.exec()
