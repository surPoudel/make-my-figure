"""The studentized range distribution as R computes it (``ptukey`` / ``qtukey``).

A port of R's nmath ``ptukey.c`` and ``qtukey.c`` (Copenhaver & Holland 1988,
Gauss-Legendre quadrature; ``qtukey`` by secant iteration to 1e-4), vectorised
over ``q`` with numpy. ``TukeyHSD`` prints its intervals to 7-10 significant
digits, and they depend on how the quantile was found: scipy's
``studentized_range`` integrates to a different precision, so a 48-mean
interval differed from R's in the 8th digit (5.35832056 against 5.35832051), and
1128 scipy tail integrals took 6 s where this takes a fraction of a second.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.special import gammaln, ndtr

_XLEG = np.array([0.981560634246719250690549090149, 0.904117256370474856678465866119,
                  0.769902674194304687036893833213, 0.587317954286617447296702418941,
                  0.367831498998180193752691536644, 0.125233408511468915472441369464])
_ALEG = np.array([0.047175336386511827194615961485, 0.106939325995318430960254718194,
                  0.160078328543346226334652529543, 0.203167426723065921749064455810,
                  0.233492536538354808760849898925, 0.249147045813402785000562436043])
_XLEGQ = np.array([0.989400934991649932596154173450, 0.944575023073232576077988415535,
                   0.865631202387831743880467897712, 0.755404408355003033895101194847,
                   0.617876244402643748446671764049, 0.458016777657227386342419442984,
                   0.281603550779258913230460501460, 0.950125098376374401853193354250e-1])
_ALEGQ = np.array([0.271524594117540948517805724560e-1, 0.622535239386478928628438369944e-1,
                   0.951585116824927848099251076022e-1, 0.124628971255533872052476282192,
                   0.149595988816576732081501730547, 0.169156519395002538189312079030,
                   0.182603415044923588866763667969, 0.189450610455068496285396723208])
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _wprob(w: np.ndarray, rr: float, cc: float) -> np.ndarray:
    """P(range of cc normal means < w), per element of ``w`` (R's wprob)."""
    nleg, ihalf = 12, 6
    C1, C2, C3, bb, wlar, wincr1, wincr2 = -30.0, -50.0, 60.0, 8.0, 3.0, 2, 3
    w = np.asarray(w, float)
    qsqz = w * 0.5
    out = np.ones_like(w)
    live = qsqz < bb
    if not live.any():
        return out
    w_, q_ = w[live], qsqz[live]
    pr_w = 2.0 * ndtr(q_) - 1.0
    pr_w = np.where(pr_w >= math.exp(C2 / cc), pr_w ** cc, 0.0)
    wincr = np.where(w_ > wlar, wincr1, wincr2)
    blb = q_.copy()
    binc = (bb - q_) / wincr
    bub = blb + binc
    einsum = np.zeros_like(w_)
    cc1 = cc - 1.0
    for wi in range(1, wincr2 + 1):
        on = wi <= wincr
        elsum = np.zeros_like(w_)
        a = 0.5 * (bub + blb)
        b = 0.5 * (bub - blb)
        going = on.copy()
        for jj in range(1, nleg + 1):
            if ihalf < jj:
                j = (nleg - jj) + 1
                xx = _XLEG[j - 1]
            else:
                j = jj
                xx = -_XLEG[j - 1]
            ac = a + b * xx
            qexpo = ac * ac
            going &= qexpo <= C3            # R breaks out of the loop; ac grows with jj
            pplus = 2.0 * ndtr(ac)
            pminus = 2.0 * ndtr(ac - w_)
            rinsum = pplus * 0.5 - pminus * 0.5
            ok = going & (rinsum >= math.exp(C1 / cc1))
            with np.errstate(invalid="ignore", over="ignore", under="ignore"):
                term = _ALEG[j - 1] * np.exp(-0.5 * qexpo) * np.power(np.where(ok, rinsum, 1.0), cc1)
            elsum += np.where(ok, term, 0.0)
        elsum *= (2.0 * b * cc) / _SQRT_2PI
        einsum += np.where(on, elsum, 0.0)
        blb = np.where(on, bub, blb)
        bub = np.where(on, bub + binc, bub)
    pr_w = pr_w + einsum
    res = np.where(pr_w <= math.exp(C1 / rr), 0.0, np.minimum(1.0, np.power(np.maximum(pr_w, 0.0), rr)))
    out[live] = res
    return out


def ptukey(q, nmeans: float, df: float, nranges: float = 1.0, lower_tail: bool = True) -> np.ndarray:
    """R's ``ptukey(q, nmeans, df, nranges, lower.tail)``, vectorised over ``q``."""
    q = np.atleast_1d(np.asarray(q, float))
    rr, cc = float(nranges), float(nmeans)
    ans = np.zeros_like(q)
    pos = np.isfinite(q) & (q > 0)
    ans[np.isinf(q) & (q > 0)] = 1.0
    if pos.any():
        qq = q[pos]
        if df > 25000.0:
            res = _wprob(qq, rr, cc)
        else:
            f2 = df * 0.5
            f2lf = (f2 * math.log(df)) - (df * math.log(2.0)) - float(gammaln(f2))
            f21 = f2 - 1.0
            ff4 = df * 0.25
            ulen = 1.0 if df <= 100 else 0.5 if df <= 800 else 0.25 if df <= 5000 else 0.125
            f2lf += math.log(ulen)
            res = np.zeros_like(qq)
            active = np.ones_like(qq, bool)
            for i in range(1, 51):
                otsum = np.zeros_like(qq)
                twa1 = (2 * i - 1) * ulen
                for jj in range(1, 17):
                    if 8 < jj:
                        j = jj - 8 - 1
                        t1 = f2lf + f21 * math.log(twa1 + _XLEGQ[j] * ulen) - (_XLEGQ[j] * ulen + twa1) * ff4
                    else:
                        j = jj - 1
                        t1 = f2lf + f21 * math.log(twa1 - _XLEGQ[j] * ulen) + (_XLEGQ[j] * ulen - twa1) * ff4
                    if t1 >= -30.0:
                        if 8 < jj:
                            qsqz = qq * math.sqrt((_XLEGQ[j] * ulen + twa1) * 0.5)
                        else:
                            qsqz = qq * math.sqrt((-(_XLEGQ[j] * ulen) + twa1) * 0.5)
                        otsum += _wprob(qsqz, rr, cc) * _ALEGQ[j] * math.exp(t1)
                stop = active & (i * ulen >= 1.0) & (otsum <= 1.0e-14)
                active &= ~stop
                res += np.where(active, otsum, 0.0)
                if not active.any():
                    break
            res = np.minimum(res, 1.0)
        ans[pos] = res
    return ans if lower_tail else (0.5 - ans) + 0.5


def _qinv(p: float, c: float, v: float) -> float:
    p0, q0 = 0.322232421088, 0.993484626060e-01
    p1, q1 = -1.0, 0.588581570495
    p2, q2 = -0.342242088547, 0.531103462366
    p3, q3 = -0.204231210125, 0.103537752850
    p4, q4 = -0.453642210148e-04, 0.38560700634e-02
    c1, c2, c3, c4, c5, vmax = 0.8832, 0.2368, 1.214, 1.208, 1.4142, 120.0
    ps = 0.5 - 0.5 * p
    yi = math.sqrt(math.log(1.0 / (ps * ps)))
    t = yi + ((((yi * p4 + p3) * yi + p2) * yi + p1) * yi + p0) / ((((yi * q4 + q3) * yi + q2) * yi + q1) * yi + q0)
    if v < vmax:
        t += (t * t * t + t) / v / 4.0
    q = c1 - c2 * t
    if v < vmax:
        q += -c3 / v + c4 * t / v
    return t * (q * math.log(c - 1.0) + c5)


def qtukey(p: float, nmeans: float, df: float, nranges: float = 1.0) -> float:
    """R's ``qtukey(p, nmeans, df)`` (lower tail): secant iteration until successive iterates differ < 1e-4."""
    eps, maxiter = 0.0001, 50

    def f(x):
        return float(ptukey(x, nmeans, df, nranges)[0]) - p

    x0 = _qinv(p, nmeans, df)
    valx0 = f(x0)
    x1 = max(0.0, x0 - 1.0) if valx0 > 0.0 else x0 + 1.0
    valx1 = f(x1)
    ans = x1
    for _ in range(1, maxiter):
        ans = x1 - ((valx1 * (x1 - x0)) / (valx1 - valx0))
        valx0 = valx1
        x0 = x1
        if ans < 0.0:
            ans = 0.0
            valx1 = -p
        valx1 = f(ans)
        x1 = ans
        if abs(x1 - x0) < eps:
            return ans
    return ans
