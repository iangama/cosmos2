"""Second-order forward differentiation for a scalar Helmholtz free energy."""
import math
import numpy as np


class Jet:
    __array_priority__ = 1000

    def __init__(self, value, gradient, hessian):
        self.v = float(value)
        self.g = np.asarray(gradient, dtype=float)
        self.h = np.asarray(hessian, dtype=float)

    @classmethod
    def variable(cls, value, index, dimension):
        g = np.zeros(dimension)
        g[index] = 1.
        return cls(value, g, np.zeros((dimension, dimension)))

    def unary(self, value, first, second):
        return Jet(value, first*self.g, first*self.h+second*np.outer(self.g, self.g))

    def __add__(self, other):
        if isinstance(other, Jet):
            return Jet(self.v+other.v, self.g+other.g, self.h+other.h)
        return Jet(self.v+other, self.g, self.h)

    __radd__ = __add__

    def __neg__(self):
        return Jet(-self.v, -self.g, -self.h)

    def __sub__(self, other):
        return self+-other

    def __rsub__(self, other):
        return other+-self

    def __mul__(self, other):
        if isinstance(other, Jet):
            return Jet(self.v*other.v, self.g*other.v+other.g*self.v,
                       self.h*other.v+other.h*self.v+np.outer(self.g, other.g)+np.outer(other.g, self.g))
        return Jet(self.v*other, self.g*other, self.h*other)

    __rmul__ = __mul__

    def __pow__(self, power):
        if isinstance(power, Jet):
            return exp(power*log(self))
        if power == 0:
            return self.unary(1., 0., 0.)
        if power == 1:
            return self
        return self.unary(self.v**power, power*self.v**(power-1), power*(power-1)*self.v**(power-2))

    def __rpow__(self, base):
        return exp(self*math.log(base))

    def __truediv__(self, other):
        return self*(other**-1 if isinstance(other, Jet) else 1/other)

    def __rtruediv__(self, other):
        return other*self**-1


def exp(x):
    if not isinstance(x, Jet):
        return math.exp(x)
    v = math.exp(x.v)
    return x.unary(v, v, v)


def log(x):
    return x.unary(math.log(x.v), 1/x.v, -1/x.v**2) if isinstance(x, Jet) else math.log(x)


def log1p(x):
    return x.unary(math.log1p(x.v), 1/(1+x.v), -1/(1+x.v)**2) if isinstance(x, Jet) else math.log1p(x)


def sqrt(x):
    return x**.5


def atan(x):
    return x.unary(math.atan(x.v), 1/(1+x.v*x.v), -2*x.v/(1+x.v*x.v)**2) if isinstance(x, Jet) else math.atan(x)


def asinh(x):
    return x.unary(math.asinh(x.v), 1/math.sqrt(1+x.v*x.v), -x.v/(1+x.v*x.v)**1.5) if isinstance(x, Jet) else math.asinh(x)


def tanh(x):
    if not isinstance(x, Jet):
        return math.tanh(x)
    v = math.tanh(x.v)
    return x.unary(v, 1-v*v, -2*v*(1-v*v))
