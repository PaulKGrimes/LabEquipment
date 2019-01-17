'''
Source code for analyzing data obtained by Vamp_sweep

Created on March 7, 2012 ET

'''

from math import *
import numpy as np
import pylab

ifile = open('PVamp_data.txt', 'r')
lines = ifile.readlines()
Vlist = []
Ilist = []
Flist = []
Plist = []
Pdata = []
Idata = []
for i, xx in enumerate(lines[0].split()):
    if i>0:
        Vlist.append(float(xx))
for i, xx in enumerate(lines[1].split()):
    if i>0:
        Ilist.append(float(xx))  


a = np.vstack([Vlist,np.ones(len(Vlist))]).T
m_vi, c_vi = np.linalg.lstsq(a,Ilist)[0]
Vcross = -c_vi/m_vi
print Vcross


for i, xx in enumerate(lines[4].split()):
    print i, xx
    if i==0:
        Flist.append(float(xx))
    else:
        Plist.append(float(xx))
      
a = np.vstack([Vlist,np.ones(len(Vlist))]).T
m_pv, c_pv = np.linalg.lstsq(a,Plist)[0]
for i, xx in enumerate(Vlist):
    Pdata.append(m_pv*float(xx)+c_pv)
    Idata.append(m_vi*float(xx)+c_vi)

print Vlist
print Ilist
print Idata

#Plot data
print 'plotting data'
pylab.xlabel('Voltage/mV')
pylab.plot(np.array(Vlist),np.array(Idata), 'b-', label='I-V')
pylab.grid()
pylab.ylabel('Current/mA')
pylab.scatter(np.array(Vlist),np.array(Ilist),s=20,c='r',marker='x')
pylab.show()
