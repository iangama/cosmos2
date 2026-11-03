# SPDX-License-Identifier: LGPL-3.0-or-later
"""Scalar value, full gradient and only the lnT row of a Hessian.

The parent class is used solely for the original fits' isinstance checks.
All arithmetic is overridden; this object has no full Hessian attribute.
"""
import math
import numpy as np
from is5_jet import Jet as FullJet


class Jet(FullJet):
    def __init__(self,value,gradient,thermal_row):
        self.v=float(value);self.g=np.asarray(gradient,dtype=float);self.ht=np.asarray(thermal_row,dtype=float)

    @classmethod
    def variable(cls,value,index,dimension):
        g=np.zeros(dimension);g[index]=1.
        return cls(value,g,np.zeros(dimension))

    def unary(self,value,first,second):
        return Jet(value,first*self.g,first*self.ht+second*(self.g[0]*self.g))

    def __add__(self,other):
        if isinstance(other,Jet):return Jet(self.v+other.v,self.g+other.g,self.ht+other.ht)
        if isinstance(other,FullJet):raise TypeError('Do not mix full and thermal-row jets')
        return Jet(self.v+other,self.g,self.ht)
    __radd__=__add__

    def __neg__(self):return Jet(-self.v,-self.g,-self.ht)
    def __sub__(self,other):return self+-other
    def __rsub__(self,other):return other+-self

    def __mul__(self,other):
        if isinstance(other,Jet):
            return Jet(self.v*other.v,self.g*other.v+other.g*self.v,
                       self.ht*other.v+other.ht*self.v+self.g[0]*other.g+other.g[0]*self.g)
        if isinstance(other,FullJet):raise TypeError('Do not mix full and thermal-row jets')
        return Jet(self.v*other,self.g*other,self.ht*other)
    __rmul__=__mul__

    def __pow__(self,power):
        if isinstance(power,Jet):return exp(power*log(self))
        if isinstance(power,FullJet):raise TypeError('Do not mix full and thermal-row jets')
        if power==0:return self.unary(1.,0.,0.)
        if power==1:return self
        return self.unary(self.v**power,power*self.v**(power-1),power*(power-1)*self.v**(power-2))
    def __rpow__(self,base):return exp(self*math.log(base))
    def __truediv__(self,other):return self*(other**-1 if isinstance(other,Jet) else 1/other)
    def __rtruediv__(self,other):return other*self**-1


def exp(x):
    if not isinstance(x,Jet):return math.exp(x)
    value=math.exp(x.v);return x.unary(value,value,value)


def log(x):return x.unary(math.log(x.v),1/x.v,-1/x.v**2) if isinstance(x,Jet) else math.log(x)
def log1p(x):return x.unary(math.log1p(x.v),1/(1+x.v),-1/(1+x.v)**2) if isinstance(x,Jet) else math.log1p(x)
def sqrt(x):return x**.5
def atan(x):return x.unary(math.atan(x.v),1/(1+x.v*x.v),-2*x.v/(1+x.v*x.v)**2) if isinstance(x,Jet) else math.atan(x)
def asinh(x):return x.unary(math.asinh(x.v),1/math.sqrt(1+x.v*x.v),-x.v/(1+x.v*x.v)**1.5) if isinstance(x,Jet) else math.asinh(x)
def tanh(x):
    if not isinstance(x,Jet):return math.tanh(x)
    value=math.tanh(x.v);return x.unary(value,1-value*value,-2*value*(1-value*value))
