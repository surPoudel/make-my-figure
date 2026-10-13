"""Per-operation refcount drift of None/True/False on the singletons, for each PySide operation in isolation."""
import sys, queue
from PySide6.QtCore import QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget
app = QApplication(sys.argv); mode = sys.argv[1]; N = int(sys.argv[2])
class Ping(QObject): sig = Signal(object)
p = Ping(); p.sig.connect(lambda x: None)
class C(QWidget): pass
q = queue.Queue()
class W(QThread):
    def run(self):
        while (it := q.get()) is not None: del it
w = W(); w.start()
def snap(): return {k: sys.getrefcount(v) for k, v in (("None", None), ("True", True), ("False", False))}
a = snap()
for i in range(N):
    if mode == "emit": p.sig.emit(i)
    elif mode == "widget_main": C()
    elif mode == "widget_worker": q.put([C()])
    elif mode == "timer": QTimer.singleShot(0, lambda: None)
q.put(None); w.wait(); app.processEvents(); p.sig.emit(0); app.processEvents()
b = snap(); print(mode, {k: round((b[k] - a[k]) / N, 3) for k in a})
