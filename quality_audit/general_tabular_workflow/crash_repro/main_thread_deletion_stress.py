"""The path named in the crash: a Python-owned QWidget subclass whose last reference dies on a QThread,
so shiboken queues its C++ destructor and runs it from mainThreadDeletionHandler under a Python callback."""
import faulthandler, sys, queue
faulthandler.enable()
from PySide6.QtCore import QThread, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
app = QApplication(sys.argv)
class Canvas(QWidget):
    def __init__(s):
        super().__init__(); l = QVBoxLayout(s); l.addWidget(QLabel("x", s))
        s.cycle = s
q = queue.Queue()
class Worker(QThread):
    def run(self):
        while True:
            item = q.get()
            if item is None: return
            del item                        # last Python reference dies on this thread
class Ping(QObject):
    sig = Signal(object)
p = Ping(); hits = {"slot": 0}
def slot(x): hits["slot"] += 1
p.sig.connect(slot)
w = Worker(); w.start()
n0 = sys.getrefcount(None); N = int(sys.argv[1]); st = {"i": 0}
def step():
    q.put([Canvas()])                      # wrapped in a list so the worker holds the only ref
    p.sig.emit(st["i"])                     # Python callback via SignalManager -> runs pending calls
    st["i"] += 1
    if st["i"] >= N:
        q.put(None); w.wait(); app.processEvents(); p.sig.emit(0)
        print("survived", N, "None refcount delta", sys.getrefcount(None) - n0, flush=True); app.quit()
t = QTimer(); t.timeout.connect(step); t.start(0); app.exec()
