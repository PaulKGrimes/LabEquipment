# Probe.py
#
# Provides functions to compensate near-field measurements for the effects
# of a waveguide near-field probe.
# 
#
import numpy as np
from scipy.constants import c, pi
from numpy.lib.scimath import sqrt as csqrt

j = csqrt(-1)


class Probe:
    """Object defining a near-field single moded waveguide probe that
    is used to probe the radiation pattern of an antenna under test.
    
    This object provides methods for compensating the measured radiation
    patterns for the effects of the probe.
    """
    def __init__(self, a, b, z0):
        """Sets up a probe with waveguide dimensions a x b at a distance
        z0 from the antenna under test"""
        self.a = a
        self.b = b
        self.z0 = z0
        
        self.s11short_V = 1.0
        self.s11short_H = 1.0
        self.K = 1.0
        
    def setGains(self, s11short_V, s11short_H):
        """Set gains to correct for different gains in differing polarizations
        """
        self.s11short_V = s11short_V
        self.s11short_H = s11short_H
        
        self.K = np.sqrt(S11short_V/S11short_H)

    def Eprobe_Ex(self, theta, phi, f):
        """Calculate the compensation for the probe in the Horizontal 
        polarization (probe E-field oriented along x-direction) at
        direction (theta, phi) and frequency f."""
        w=c/f
        k = 2*pi/w
        
        X=k*self.a/2*np.sin(theta)*np.sin(phi)
        Y=k*self.b/2*np.sin(theta)*np.cos(phi)+1e-15
        
        Eprobe_theta_H=np.cos(phi)*np.cos(X)/(X**2-(pi/2)**2)*np.sin(Y)/Y
        Eprobe_phi_H=-np.cos(theta)*np.sin(phi)*np.cos(X)/(X**2-(pi/2)**2)*np.sin(Y)/Y
        
        return Eprobe_theta_H, Eprobe_phi_H
        
    def Eprobe_Ey(self, theta, phi, f):
        """Calculate the compensation for the probe in the Vertical 
        polarization (probe E-field oriented along y-direction) at
        direction (theta, phi) and frequency f."""
        w=c/f
        k = 2*pi/w
        
        X=k*self.a/2*np.sin(theta)*np.cos(phi)
        Y=k*self.b/2*np.sin(theta)*np.sin(phi)+1e-15
        
        Eprobe_theta_V=np.sin(phi)*np.cos(X)/(X**2-(pi/2)**2)*np.sin(Y)/Y
        Eprobe_phi_V=np.cos(theta)*np.cos(phi)*np.cos(X)/(X**2-(pi/2)**2)*np.sin(Y)/Y
        
        return Eprobe_theta_V, Eprobe_phi_V
        
    def Compensate(self, Etheta, Ephi, theta, phi, f):
        
        """Compensate data in Etheta, Ephi for the effects of the probe
        at frequency f."""
        w=c/f
        k = 2*pi/w
        
        # Vertical polarization, probe E-field is oriented along y-direction
        Eprobe_theta_V, Eprobe_phi_V = self.Eprobe_Ey(theta,-phi, f)
        Mv = np.cos(theta)*np.exp(j*k*np.cos(theta)*self.z0)*Etheta
    
        # Horizontal polarization, probe E-field is oriented along x-direction
        Eprobe_theta_H, Eprobe_phi_H = self.Eprobe_Ex(theta,-phi, f)
        Mh = np.cos(theta)*np.exp(j*k*np.cos(theta)*self.z0)*Ephi

        # Compensate for different polarization measurement gain
        Mv = Mv/self.K
        
        #Calculate compensated Etheta and Ephi
        Etheta_compensated = (Mv*Eprobe_phi_H-Mh*Eprobe_phi_V)/(Eprobe_theta_V*Eprobe_phi_H-Eprobe_phi_V*Eprobe_theta_H)
        Ephi_compensated = (Mh*Eprobe_theta_V-Mv*Eprobe_theta_H )/(Eprobe_theta_V*Eprobe_phi_H-Eprobe_phi_V*Eprobe_theta_H)

        
        return Etheta_compensated, Ephi_compensated
        
    
