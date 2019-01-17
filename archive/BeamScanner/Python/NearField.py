# NearField.py
#
# Class holding and processing near-field measurement data
#
#
# Based on the Python version of NF2FF script.
# Translated by Paul Grimes from Matlab NF2FF script written by the following people.
#
# Original header:
#
# Near-Field to Far-Field Transformation for Antenna Measurements (NF2FF)
# J. Logan (john_logan@mail.uri.edu)
# A. P. Mynster (andersmynster@hotmail.com)
# M. J. Pelk (m.j.pelk@tudelft.nl)
# C. Ponder (chris.ponder@sli-institute.ac.uk)
# K. Van Caekenberghe (vcaeken@umich.edu) 
# 
# Bug fixes:
# 1. Aspect ratio maintained during zero padding
#
# New extensions include:
# 1. Holographic back projection. Hologram analysis can also be used to study near field communication (NFC) antennas. 
# 2. Cross polarization (Ludwig 1 and 3)
# 3. Probe compensation (EXPERIMENTAL)
#
# The script assumes:
# 1. Rectangular coordinate system with z axis normal to planar aperture
# 2. exp(j*omega*t) time dependence convention. Please, substitute i with -j
#    whenever implementing exp(-i*omega*t) time dependence convention based
#    algorithms.
#
# The script uses:
# 1. Near field datasets of a 94 GHz slotted waveguide (U.S. Patent No.: 7,994,969)
#    can be downloaded from: http://www-personal.umich.edu/~vcaeken/DATASETS.zip.
# 2. GoldsteinUnwrap2D.m, posted on the fileexchangewebsite by B. Spottiswoode on 
#    22 December 2008
# 3. Sphere3D.m, posted on the fileexchange website by J. M. De Freitas on 
#    15 September 2005
# 
# Sought-after extensions are listed below. Please post them on the 
# website, if you are willing to contribute:
# 1. Cylindrical and spherical near field to far field transformation
# 2. Graphical user interface
#
# References:
# 1. C. A. Balanis, "Antenna Theory, Analysis and Design, 2nd Ed.", Wiley, 1997. [exp(j*omega*t) time dependence convention]
# 2. D. Paris, W. Leach, Jr., E. Joy, "Basic Theory of Probe-Compensated Near-Field Measurements", IEEE Transactions on Antennas and Propagation, Vol. 26, No. 3, May 1978. [exp(-i*omega*t) time dependence convention]
# 3. A. D. Yaghjian, "Approximate Formulas for the Far Field and Gain of Open-Ended Rectangular Waveguide", IEEE Transactions on Antennas and Propagation, Vol. 32, No. 4, April 1984. [exp(-i*omega*t) time dependence convention]
# 4. A. D. Yaghjian, "An Overview of Near-Field Antenna Measurements", IEEE Transactions on Antennas and Propagation, Vol. 34, No. 1, June 1986. [exp(-i*omega*t) time dependence convention]
# 5. G. F. Masters, "Probe-Correction Coefficients Derived From Near-Field Measurements", AMTA Conference, October 7-11, 1991.
# 6. J. J. Lee, E. M. Ferren, D. P. Woollen, and K. M. Lee, "Near-Field Probe Used as a Diagnostic Tool to Locate Defective Elements in an Array Antenna", IEEE Transactions on Antennas and Propagation, Vol. 36, No. 6, June 1988. [exp(-i*omega*t) time dependence convention]
# 7. http://www.fftw.org/
# 8. R. M. Goldstein, H. A. Zebken, and C. L. Werner, "Satellite Radar Interferometry: Two-Dimensional Phase Unwrapping", Radio Sci., Vol. 23, No. 4, pp. 713-720, 1988.
# 9. D. C. Ghiglia and M. D. Pritt, "Two-Dimensional Phase Unwrapping: Theory, Algorithms and Software". Wiley-Interscience, 1998.
# 10. J. M. De Freitas. "SPHERE3D: A Matlab Function to Plot 3-Dimensional Data on a Spherical Surface".
#    QinetiQ Ltd, Winfrith Technology Centre, Winfrith,
#    Dorchester DT2 8XJ. UK. 15 September 2005.

import numpy as np
from numpy.lib.scimath import sqrt as csqrt
from numpy import random
import scipy as sp
import scipy.constants as constants
import scipy.io as io
import scipy.fftpack as fft

import matplotlib as mpl
import matplotlib.pyplot as pp
import matplotlib.colors as colors
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from skimage import restoration
from scipy.interpolate import RectBivariateSpline
from Probe import Probe

from cmath import rect
nprect = np.vectorize(rect)

# Set up some constants
c = constants.c
pi = constants.pi
j = csqrt(-1)

# A helpful class to build a struct for holding SAO Sdata
class Sdata:
    pass
    

def spherical_to_cartesian(r, theta , phi):
    """
    Convert spherical coordinates to cartesian coordinates.
    
    :param r: norm
    :param theta: angle :math:`\\theta`
    :param phi: angle :math:`\\phi`
    
    .. math:: x = r \\sin{\\theta}\\cos{\\phi}
    .. math:: y = r \\sin{\\theta}\\sin{\\phi}
    .. math:: z = r \\cos{\\theta}
    """
    return (
        r * np.sin(theta) * np.cos(phi),
        r * np.sin(theta) * np.sin(phi),
        r * np.cos(theta)
        )

def smooth(x,beta, window_len):
    """ kaiser window smoothing """
    window_len=int(window_len)
    # extending the data at beginning and at the end
    # to apply the window at the borders
    s = np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    w = np.kaiser(window_len,beta)
    y = np.convolve(w/w.sum(),s,mode='valid')
    return y[np.floor(window_len/2.):len(y)-np.floor(window_len/2.)]
        
class NearField:
    """Class for holding and processing near-field measurement data"""
    def __init__(self):
        """Creates a new NearField object"""
        
    def loadFromMat(self, filename_Pol1, filename_Pol2):
        """Load data from matlab file matching the struct of the example
        file from NF2FF.m"""
        
        # Load data for both polarizations
        self.sdata_cp = io.loadmat(filename_Pol1, struct_as_record=False, squeeze_me=True)["sdata"]
        self.sdata_xp = io.loadmat(filename_Pol2, struct_as_record=False, squeeze_me=True)["sdata"]

        # Get the frequency points (in Hz)
        self.freq = self.sdata_cp.freq

        # Get the number of spatial samples and spacings
        # % See equations (16-10a) and (16-10b) in Balanis
        self.xpoints = self.sdata_cp.xpoints
        self.ypoints = self.sdata_cp.ypoints
        self.dx = self.sdata_cp.x_step/1000.
        self.dy = self.sdata_cp.y_step/1000.

    def getFPointFromNF2FF(self, f):
        """Pick a frequency point out of Matlab struct data like that
        provided by NF2FF"""
        
        # Look for the nearest frequency value to the requested frequency
        f = min(self.freq, key=lambda x:abs(x-f))
        f_Index = np.where(self.freq == f)[0][0]
        
        self.NF_X_Complex = np.zeros((self.xpoints, self.ypoints), dtype=np.complex64)
        self.NF_Y_Complex = np.zeros((self.xpoints, self.ypoints), dtype=np.complex64)
        for iy in range(0,self.ypoints):
            for ix in range(0,self.xpoints): 
                self.NF_X_Complex[ix,iy]=self.sdata_cp.s21[ix,iy][f_Index]
                self.NF_Y_Complex[ix,iy]=self.sdata_xp.s21[ix,iy][f_Index]
        
        lambda0=c/f
        self.f = f
        self.k0=2*pi/lambda0


    def loadFromSAO(self, filename_Pol1, filename_Pol2, f, tblname_Pol1=None, tblname_Pol2=None, tblsmooth=None):
        """Load data from SAO Receiver Lab near field scanner files"""
        
        # Load data for both polarizations
        self.sdata_cp = self.loadSAOdata(filename_Pol1, tblname=tblname_Pol1, tblsmooth=tblsmooth)
        self.sdata_xp = self.loadSAOdata(filename_Pol2, tblname=tblname_Pol2, tblsmooth=tblsmooth)
        
        # Get the frequency of the data
        lambda0=c/f
        self.f = f
        self.k0=2*pi/lambda0        

        # Get the number of spatial samples and spacings
        # % See equations (16-10a) and (16-10b) in Balanis
        self.xpoints = self.sdata_cp.xpoints
        self.ypoints = self.sdata_cp.ypoints
        self.dx = self.sdata_cp.x_step/1000.
        self.dy = self.sdata_cp.y_step/1000.
        
        self.NF_X_Complex = self.sdata_cp.s21
        self.NF_Y_Complex = self.sdata_xp.s21
        
        
    def loadSAOdata(self, filename, tblname=None, tblsmooth=None):
        """Load the SAO data for one polarization, and correct it with the
        calibration data in tblname.  Smooth the calibration data by a Kaiser window
        with beta 1 and width = tblsmooth."""
        sdata = Sdata()
        
        # Load the data
        data = np.loadtxt(filename)
        
        sdata.xpoints = int(np.max(data[:,0])+1) # Horizontal dimension = BeamScanner "v" = Unidex "u"
        sdata.ypoints = int(np.max(data[:,1])+1) # Vertical dimension = BeamScanner "u" = Unidex "v"
        
        sdata.x_step = np.ptp(data[:,2])/np.max(data[:,0])
        sdata.y_step = np.ptp(data[:,3])/np.max(data[:,1])
        
        # Read the data from the table
        #   Note that the data is in a raster scan pattern, so that the x and y indices
        #   are not in an expected order.  We use the indices explicitly given in the
        #   data to make sure that the correct element of the array is set
        sdata.s21 = np.zeros((sdata.xpoints, sdata.ypoints), dtype=np.complex64)
        
        for d in data:
            sdata.s21[d[0],d[1]] = nprect(np.power(10, d[4]/20), -np.deg2rad(d[5]))
            
        if tblname != None:
            # Read the table file
            tbl = np.loadtxt(tblname)
            
            sdata.calTable = np.zeros((sdata.ypoints), dtype = np.complex64)
            
            if tblsmooth != None:
                tbl[:,1] = smooth(tbl[:,1], 1.0, tblsmooth)
                tbl[:,2] = smooth(tbl[:,2], 1.0, tblsmooth)
            
            for t in tbl:
                sdata.calTable[t[0]] = nprect(np.power(10, t[1]/20), -np.deg2rad(t[2]))
                
            # Calibrate the s21 data
            sdata.s21 = sdata.s21*sdata.calTable
            
        return sdata
        

    def addPhaseNoise(self, phaseNoise):
        """Adds Gaussian phase noise to the nearfield data to test the 
        performance of the algorithm under more realistic conditions.  
        
        phaseNoise = std dev of phase noise in degrees"""
        randomPhase = random.normal(scale = phaseNoise, size = (self.xpoints, self.ypoints))
        uniformAmp = np.ones((self.xpoints, self.ypoints))
        
        self.NF_X_Complex = self.NF_X_Complex*nprect(uniformAmp, np.deg2rad(randomPhase))
        randomPhase = random.normal(scale = phaseNoise, size = (self.xpoints, self.ypoints))
        self.NF_Y_Complex = self.NF_Y_Complex*nprect(uniformAmp, np.deg2rad(randomPhase))
        
    def addPhaseDrift(self, phaseDrift, pattern="raster"):
        """Adds linear phase drift to the nearfield data to test the 
        performance of the algorithm under more realistic conditions.  
        
        phaseDrift = total drift across scan in degrees
        pattern = "raster" (row by row in same direction) or "bdon" (reversing each row)"""
        phaseDrift = np.linspace(0, phaseDrift, self.xpoints*self.ypoints)
        if pattern == "raster":
            phaseDrift = phaseDrift.reshape((self.xpoints, self.ypoints))
        uniformAmp = np.ones((self.xpoints, self.ypoints))
        
        self.NF_X_Complex = self.NF_X_Complex*nprect(uniformAmp, np.deg2rad(phaseDrift))
        self.NF_Y_Complex = self.NF_Y_Complex*nprect(uniformAmp, np.deg2rad(phaseDrift))
        
    def addGainNoise(self, gainNoise):
        """Adds Gaussian amplitude gain noise to the nearfield data to test the 
        performance of the algorithm under more realistic conditions.  Multiplies
        complex magnitude by value.
        
        ampNoise = std dev of amplitude noise in absolute units"""
        randomAmp = random.normal(loc = 1.0, scale = gainNoise, size = (self.xpoints, self.ypoints))
        uniformPhase = np.zeros((self.xpoints, self.ypoints))
        
        self.NF_X_Complex = self.NF_X_Complex*nprect(randomAmp, uniformPhase)
        randomAmp = random.normal(loc = 1.0, scale = gainNoise, size = (self.xpoints, self.ypoints))
        self.NF_Y_Complex = self.NF_Y_Complex*nprect(randomAmp, uniformPhase)
        
    def delCrossPol(self):
        """Sets the crosspolar fields to (near) zero, as though they hadn't been measured"""
        self.NF_Y_Complex = 1e-15*np.ones((self.xpoints, self.ypoints), dtype=np.complex64)
        

    def setUpScan(self, z0):
        """Set up the grids and other details of the scan region"""
        # % See equations (16-10a) and (16-10b) in Balanis
        a=self.dx*(self.xpoints-1) # The length of the scanned area in the x direction [m]
        b=self.dy*(self.ypoints-1) # The length of the scanned area in the y direction [m]
        # Create arrays of x and y points
        self.x=np.linspace(-a/2, a/2, self.xpoints)
        self.y=np.linspace(-b/2, b/2, self.ypoints)
        self.z0=z0;

        # Create matrices of x and y values for plotting
        self.X, self.Y = np.meshgrid(self.x*1000, self.y*1000)


    def setUpGrids(self, zero_padding=4, dtheta=0.01, dphi=0.01):
        """Set up the grids for the output data"""
        
        # % See equations (16-13a) and (16-13b) in Balanis
        # % Zero padding is used to increase the resolution of the plane wave spectral domain.
        zp = zero_padding  # amount to zero pad by
        self.MI=zp*self.xpoints # 2^(ceil(log2(M))+1);
        self.NI=zp*self.ypoints # 2^(ceil(log2(N))+1);
        m=np.linspace(-self.MI/2, self.MI/2, self.MI)
        n=np.linspace(-self.NI/2, self.NI/2, self.NI)
        self.k_X_Rectangular=2*pi*m/(self.MI*self.dx) # k_X vector
        self.k_Y_Rectangular=2*pi*n/(self.NI*self.dy) # k_Y vector
        
        # Create matrices of k_X and k_Y values
        self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid = np.meshgrid(self.k_X_Rectangular,self.k_Y_Rectangular)
        with np.errstate(invalid='ignore'):
            self.k_Z_Rectangular_Grid = csqrt(self.k0**2-self.k_X_Rectangular_Grid**2-self.k_Y_Rectangular_Grid**2)

        # Create spherical coordinates for far-field output
        theta=np.linspace(-pi/2, pi/2, 2*np.floor(1/dtheta/2)+1) # Need to guarantee odd number of theta and phi points
        phi=np.linspace(0, 2*pi, 2*np.floor(1/dphi/2)+1)
        self.theta, self.phi = np.meshgrid(theta,phi)
        self.dtheta, self.dphi = dtheta*pi, dphi*pi


    def calcFarFieldRect(self):
        """Calculate the Farfield Rectangular radiation pattern by inverse Fourier Transform"""
    
        # See equations (16-7a) and (16-7b) in Balanis
        self.f_X_Rectangular=fft.ifftshift(fft.ifft2(self.NF_X_Complex, shape=(self.MI,self.NI)))
        self.f_Y_Rectangular=fft.ifftshift(fft.ifft2(self.NF_Y_Complex, shape=(self.MI,self.NI)))
        with np.errstate(invalid='ignore'):
            self.f_Z_Rectangular=-(self.f_X_Rectangular*self.k_X_Rectangular_Grid+self.f_Y_Rectangular*self.k_Y_Rectangular_Grid)/(self.k_Z_Rectangular_Grid)
            

    def calcFarFieldCartSpherical(self):
        """Calculate the Cartesian components of the far field pattern on a polar grid"""
        f_X_Spherical_ip=RectBivariateSpline(self.k_X_Rectangular, self.k_Y_Rectangular, np.abs(self.f_X_Rectangular))
        self.f_X_Spherical = f_X_Spherical_ip.ev(self.k0*np.sin(self.theta)*np.cos(self.phi), self.k0*np.sin(self.theta)*np.sin(self.phi))
        f_Y_Spherical_ip=RectBivariateSpline(self.k_X_Rectangular, self.k_Y_Rectangular, np.abs(self.f_Y_Rectangular))
        self.f_Y_Spherical = f_Y_Spherical_ip.ev(self.k0*np.sin(self.theta)*np.cos(self.phi), self.k0*np.sin(self.theta)*np.sin(self.phi))
        f_Z_Spherical_ip=RectBivariateSpline(self.k_X_Rectangular, self.k_Y_Rectangular, np.abs(self.f_Z_Rectangular))
        self.f_Z_Spherical = f_Z_Spherical_ip.ev(self.k0*np.sin(self.theta)*np.cos(self.phi), self.k0*np.sin(self.theta)*np.sin(self.phi))
    
    def calcEthetaphi(self):
        """Calculate the E_theta and E_phi components of the far field pattern"""
        r=10000
        C=j*(self.k0*np.exp(-j*self.k0*r))/(2*pi*r)
        self.Etheta=C*(self.f_X_Spherical*np.cos(self.phi)+self.f_Y_Spherical*np.sin(self.phi))
        self.Ephi=C*np.cos(self.theta)*(-self.f_X_Spherical*np.sin(self.phi)+self.f_Y_Spherical*np.cos(self.phi))
        
    def setUpProbe(self, a, b, z0):
        """Set the probe to be used for compensating the near field pattern"""
        self.probe = Probe(a, b, z0)
        
    def probeCompensation(self):
        """Compensate the calculated E_theta and E_phi components for the effects of
        the probe"""
        self.Etheta, self.phi = self.probe.Compensate(self.Etheta, self.Ephi, self.theta, self.phi, self.f)
        
        
    def calcDirectivity(self):
        """Calculate the radiation patterns"""
        self.W=1.0/(2*120*pi)*(self.Etheta*np.conj(self.Etheta)+self.Ephi*np.conj(self.Ephi))
        self.U = (np.abs(self.Etheta)**2 + np.abs(self.Ephi)**2)
        
        # Calculation of radiated power through numerical integration
        e_theta = np.matrix(np.concatenate((np.array([1, 4]), np.tile([2, 4], np.floor(len(self.theta)/2) - 1), np.array([1]))))
        e_phi = np.matrix(np.concatenate((np.array([1, 4]), np.tile([2, 4], np.floor(len(self.phi)/2) - 1), np.array([1]))))
        
        self.P = self.dphi*self.dtheta*np.sum(np.sum(self.U*np.array(e_theta.T*e_phi)*np.abs(np.sin(self.theta))))/9
    
        # Rescale
        self.D = 4*pi*self.U/self.P
        
        # Calculate co and cross-polar patterns under Ludwig's 3rd definition
        self.U_Co = (np.abs(self.Etheta*np.cos(self.phi)-self.Ephi*np.sin(self.phi)))**2
        self.U_Cross = (np.abs(self.Etheta*np.sin(self.phi)+self.Ephi*np.cos(self.phi)))**2
        self.D_Co = 4*pi*self.U_Co/self.P
        self.D_Cross = 4*pi*self.U_Cross/self.P
        
        # Calculate E- X- and H-plane patterns
        D_Size=self.D.shape
        self.Eplane_Co=10*np.log10(self.D_Co[np.floor(D_Size[1]/4),:])-np.max(10*np.log10(self.D_Co[np.floor(D_Size[1]/4),:]))
        self.Hplane_Co=10*np.log10(self.D_Co[0,:])-max(10*np.log10(self.D_Co[0,:]))
        self.Xplane_Co=10*np.log10(self.D_Co[np.floor(D_Size[1]/8),:])-np.max(10*np.log10(self.D_Co[np.floor(D_Size[1]/8),:]))
        
        self.Eplane_Cross=10*np.log10(self.D_Cross[np.floor(D_Size[1]/4),:])-np.max(10*np.log10(self.D_Co[np.floor(D_Size[1]/4),:]))
        self.Hplane_Cross=10*np.log10(self.D_Cross[0,:])-max(10*np.log10(self.D_Co[0,:]))
        self.Xplane_Cross=10*np.log10(self.D_Cross[np.floor(D_Size[1]/8),:])-np.max(10*np.log10(self.D_Co[np.floor(D_Size[1]/8),:]))
        
        
        
    def plotNFData2d(self):
        """Plot the near field data read from the file as contour plots"""
        NF_X_Magnitude = 20*np.log10(np.abs(self.NF_X_Complex)+1e-10)
        NF_Y_Magnitude = 20*np.log10(np.abs(self.NF_Y_Complex)+1e-10)
        
        # plot Magnitude of measured data.
        fig = pp.figure(figsize=pp.figaspect(0.3))
        ax = fig.add_subplot(1,2,1, aspect='equal')
        fig.suptitle('Rectangular Near Field: f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax.set_ylim(min(self.y)*1000, max(self.y)*1000)

        norm = colors.Normalize(vmin = np.max(NF_X_Magnitude)-70, vmax=np.max(NF_X_Magnitude), clip=False)
        im = pp.pcolormesh(self.X, self.Y, NF_X_Magnitude.T, cmap=cm.jet, norm=norm)
        pp.colorbar(im, fraction=0.046, pad=0.04)
        
        ax2 = fig.add_subplot(1,2,2, aspect='equal')
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax2.set_ylim(min(self.y)*1000, max(self.y)*1000)
        im2 = pp.pcolormesh(self.X, self.Y, NF_Y_Magnitude.T, cmap=cm.jet, norm=norm)
        pp.colorbar(im2, fraction=0.046, pad=0.04)
        pp.show()
        
        NF_X_Phase = restoration.unwrap_phase(np.angle(self.NF_X_Complex))
        NF_Y_Phase = restoration.unwrap_phase(np.angle(self.NF_Y_Complex))
        
        # plot Phase of measured data.
        fig = pp.figure(figsize=pp.figaspect(0.3))
        ax = fig.add_subplot(1,2,1)
        fig.suptitle('f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax.set_ylim(min(self.y)*1000, max(self.y)*1000)
        ax.set_aspect('equal')
        im = pp.pcolormesh(self.X, self.Y, NF_X_Phase.T, cmap=cm.jet)
        pp.colorbar(im, fraction=0.046, pad=0.04)
        
        ax2 = fig.add_subplot(1,2,2)
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax2.set_ylim(min(self.y)*1000, max(self.y)*1000)
        ax2.set_aspect('equal')
        im2 = pp.pcolormesh(self.X, self.Y, NF_Y_Phase.T, cmap=cm.jet)
        pp.colorbar(im2, fraction=0.046, pad=0.04)
        pp.show()
        
    def plotNFData(self):
        """Plot the near field data read from the file"""
        NF_X_Magnitude = 20*np.log10(np.abs(self.NF_X_Complex)+1e-10)
        NF_Y_Magnitude = 20*np.log10(np.abs(self.NF_Y_Complex)+1e-10)
        
        # plot Magnitude of measured data.
        fig = pp.figure(figsize=pp.figaspect(0.4))
        ax = fig.add_subplot(1,2,1, projection='3d')
        fig.suptitle('Rectangular Near Field: f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_zlabel(r'$|E_{x}|$ (dB)')
        ax.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax.set_ylim(min(self.y)*1000, max(self.y)*1000)
        
        #ax.set_zlim(-70, -30)
        norm = colors.Normalize(vmin = -70, vmax=0, clip=False)
        surf = ax.plot_surface(self.X, self.Y, NF_X_Magnitude, rstride=1, cstride=1, cmap=cm.jet, norm=norm, linewidth=0, antialiased=False)
        ax2 = fig.add_subplot(1,2,2 , projection='3d')
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_zlabel(r'$|E_{y}|$ (rad)')
        ax2.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax2.set_ylim(min(self.y)*1000, max(self.y)*1000)
        ax2.set_zlim(ax.get_zlim())
        
        surf2 = ax2.plot_surface(self.X, self.Y, NF_Y_Magnitude, rstride=1, cstride=1, cmap=cm.jet, norm=norm, linewidth=0, antialiased=False)
        pp.show()
        
        NF_X_Phase = restoration.unwrap_phase(np.angle(self.NF_X_Complex))
        NF_Y_Phase = restoration.unwrap_phase(np.angle(self.NF_Y_Complex))
        
        # plot Phase of measured data.
        fig = pp.figure(figsize=pp.figaspect(0.4))
        ax = fig.add_subplot(1,2,1, projection='3d')
        fig.suptitle('f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_zlabel(r'$\angle E_{x}$ (rad)')
        ax.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax.set_ylim(min(self.y)*1000, max(self.y)*1000)
        surf = ax.plot_surface(self.X, self.Y, NF_X_Phase, rstride=1, cstride=1, cmap=cm.jet, linewidth=0, antialiased=False)
        ax2 = fig.add_subplot(1,2,2 , projection='3d')
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_zlabel(r'$\angle E_{y}$ (rad)')
        ax2.set_xlim(min(self.x)*1000, max(self.x)*1000)
        ax2.set_ylim(min(self.y)*1000, max(self.y)*1000)
        surf2 = ax2.plot_surface(self.X, self.Y, NF_Y_Phase, rstride=1, cstride=1, cmap=cm.jet, linewidth=0, antialiased=False)
        pp.show()
        
    def plotCalTable(self):
        """Plot the calibration table data"""
        fig = pp.figure(figsize=pp.figaspect(0.4))
        ax = fig.add_subplot(1,2,1)
        ax.plot(self.y*1000, 10*np.log10(np.abs(self.sdata_cp.calTable)))
        ax.set_title('Cal Magnitude')
        ax.set_xlabel(r'Row')
        ax.set_ylabel(r'Magnitude (dB)')
        ax.set_xlim(min(self.y*1000), max(self.y*1000))
        x0,x1 = ax.get_xlim()
        y0,y1 = ax.get_ylim()
        ax.set_aspect(abs((x1-x0)/(y1-y0)))
        ax.grid()

        ax2 = fig.add_subplot(1,2,2)
        ax2.plot(self.y*1000, np.angle(self.sdata_cp.calTable)*180./pi)
        ax2.set_title('Cal Angle')
        ax2.set_xlabel(r'Row')
        ax2.set_ylabel(r'Angle (deg)')
        ax2.set_xlim(min(self.y*1000), max(self.y*1000))
        x0,x1 = ax2.get_xlim()
        y0,y1 = ax2.get_ylim()
        ax2.set_aspect(abs((x1-x0)/(y1-y0)))
        ax2.grid()
        
        pp.show()

    def plotFFRectData(self):
        """Plot the rectangular far-field data"""
        f_X_Rectangular_Magnitude=20*np.log10(abs(self.f_X_Rectangular))
        f_Y_Rectangular_Magnitude=20*np.log10(abs(self.f_Y_Rectangular))
        f_Z_Rectangular_Magnitude=20*np.log10(abs(self.f_Z_Rectangular)+1e-10)
    
        fig = pp.figure(figsize=pp.figaspect(1/3.0))
        fig.suptitle('Rectangular Far Field: f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        
        ax = fig.add_subplot(1,3,1, projection='3d')
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_zlabel(r'$|E_{x}|$ (dB)')
        norm = colors.Normalize(vmin = np.max(f_X_Rectangular_Magnitude)-70, vmax= np.max(f_X_Rectangular_Magnitude), clip=False)
        surf = ax.plot_surface(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_X_Rectangular_Magnitude, rstride=5, cstride=5, cmap=cm.jet, norm=norm, linewidth=0, antialiased=False)
        
        ax2 = fig.add_subplot(1,3,2 , projection='3d')
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_zlabel(r'$|E_{y}|$ (dB)')
        surf2 = ax2.plot_surface(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_Y_Rectangular_Magnitude, rstride=5, cstride=5, cmap=cm.jet, norm=norm, linewidth=0, antialiased=False)
        
        ax3 = fig.add_subplot(1,3,3 , projection='3d')
        ax3.set_xlabel(r'x (mm)')
        ax3.set_ylabel(r'y (mm)')
        ax3.set_zlabel(r'$|E_{z}|$ (dB)')
        surf3 = ax3.plot_surface(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_Z_Rectangular_Magnitude, rstride=5, cstride=5, cmap=cm.jet, norm=norm, linewidth=0, antialiased=False)
        
        pp.show()
    
    def plotFFRectData2d(self):
        """Plot the rectangular far-field data"""
        f_X_Rectangular_Magnitude=20*np.log10(abs(self.f_X_Rectangular))
        f_Y_Rectangular_Magnitude=20*np.log10(abs(self.f_Y_Rectangular))
        f_Z_Rectangular_Magnitude=20*np.log10(abs(self.f_Z_Rectangular)+1e-10)
    
        fig = pp.figure(figsize=pp.figaspect(1/4.))
        fig.suptitle('Rectangular Far Field: f = %f GHz (z = %i mm)' % (self.f/1000000000,self.z0*1000))
        
        ax = fig.add_subplot(1,3,1)
        ax.set_xlabel(r'x (mm)')
        ax.set_ylabel(r'y (mm)')
        ax.set_aspect('equal')
        norm = colors.Normalize(vmin = np.max(f_X_Rectangular_Magnitude)-70, vmax= np.max(f_X_Rectangular_Magnitude), clip=False)
        im = pp.pcolormesh(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_X_Rectangular_Magnitude, cmap=cm.jet, norm=norm)
        
        ax2 = fig.add_subplot(1,3,2)
        ax2.set_xlabel(r'x (mm)')
        ax2.set_ylabel(r'y (mm)')
        ax2.set_aspect('equal')
        im2 = pp.pcolormesh(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_Y_Rectangular_Magnitude, cmap=cm.jet, norm=norm)
        
        ax3 = fig.add_subplot(1,3,3)
        ax3.set_xlabel(r'x (mm)')
        ax3.set_ylabel(r'y (mm)')
        ax3.set_aspect('equal')
        im3 = pp.pcolormesh(self.k_X_Rectangular_Grid, self.k_Y_Rectangular_Grid, f_Z_Rectangular_Magnitude, cmap=cm.jet, norm=norm)
        
        pp.show()


    def plotFFSphere3d(self):
        """Plot 3d far field radiation patterns"""
        norm = colors.Normalize()
    
        D_Co_x, D_Co_y, D_Co_z = spherical_to_cartesian( self.D_Co, self.theta, self.phi )
    
        fig = pp.figure(figsize=pp.figaspect(0.5))
        fig.suptitle('Spherical Far Field: f = %.2f GHz' % (self.f/1e9))
        ax = fig.add_subplot(1,2,1, projection='3d')
        ax.set_title('Ludwig-3 Co-Pol. Dir. [dB]')
    
        surf = ax.plot_surface(D_Co_x, D_Co_y, D_Co_z, rstride=1, cstride=1, facecolors=cm.jet(norm(self.D_Co)), cmap=cm.jet, linewidth=0, antialiased=False)
    
        D_Cross_x, D_Cross_y, D_Cross_z = spherical_to_cartesian( self.D_Cross, self.theta, self.phi )
            
        ax2 = fig.add_subplot(1,2,2 , projection='3d')
        ax2.set_xlim(ax.get_xlim())
        ax2.set_ylim(ax.get_ylim())
        ax2.set_zlim(ax.get_zlim())
        ax2.set_title('Ludwig-3 X-Pol. Dir. [dB]')
        
        surf2 = ax2.plot_surface(D_Cross_x, D_Cross_y, D_Cross_z, rstride=1, cstride=1, facecolors=cm.jet(norm(self.D_Cross)), cmap=cm.jet, linewidth=0, antialiased=False)
    
        pp.show()
        
    def plotDirectivity2d(self, polar=True):
        """Plot 2d far field radiation patterns"""
        norm = colors.Normalize(vmin = np.max(10*np.log10(np.abs(self.D_Co)))-50, vmax= np.max(10*np.log10(np.abs(self.D_Co))), clip=False)
        
        fig = pp.figure(figsize=pp.figaspect(0.4))
        fig.suptitle('Spherical Far Field: f = %.2f GHz' % (self.f/1e9))
        ax = fig.add_subplot(1,2,1, polar=polar)
        ax.set_title('Ludwig-3 Co-Pol. Dir. [dB]')
        ax.set_ylim(0, 80)
        im = pp.pcolormesh(self.phi, 180/pi*self.theta, 10*np.log10(np.abs(self.D_Co)), cmap=cm.jet, norm=norm)
        pp.colorbar(im, fraction=0.046, pad=0.04)
        ax.grid()
            
        ax2 = fig.add_subplot(1,2,2, polar=polar)
        ax2.set_title('Ludwig-3 X-Pol. Dir. [dB]')
    
        ax2.set_ylim(0, 80)
        im2 = pp.pcolormesh(self.phi, 180/pi*self.theta, 10*np.log10(np.abs(self.D_Cross)), cmap=cm.jet, norm=norm)
        pp.colorbar(im2, fraction=0.046, pad=0.04)
        ax2.grid()
        
        pp.show()
    
    def plotEHXPlanes(self):
        """Plot E- and H-plane patterns"""
    
        fig = pp.figure(figsize=pp.figaspect(0.4))
        ax = fig.add_subplot(1,2,1)
        ax.plot(180/pi*self.theta[0,:], self.Eplane_Co, label="E-plane")
        ax.plot(180/pi*self.theta[0,:], self.Xplane_Co, label="X-plane")
        ax.plot(180/pi*self.theta[0,:], self.Hplane_Co, label="H-plane")
        ax.set_title('Co-polar')
        ax.set_xlabel(r'$\theta$ (Deg)')
        ax.set_ylabel(r'Directivity (dBi)')
        ax.set_xlim(-90, 90)
        ax.set_ylim(-70, 0)
        x0,x1 = ax.get_xlim()
        y0,y1 = ax.get_ylim()
        ax.set_aspect(abs((x1-x0)/(y1-y0)))
        ax.grid()
        ax2 = fig.add_subplot(1,2,2)
        ax2.plot(180/pi*self.theta[0,:], self.Eplane_Cross, label="E-plane")
        ax2.plot(180/pi*self.theta[0,:], self.Xplane_Cross, label="X-plane")
        ax2.plot(180/pi*self.theta[0,:], self.Hplane_Cross, label="H-plane")
        ax2.set_title('Cross-polar')
        ax2.set_xlabel(r'$\theta$ (Deg)')
        ax2.set_ylabel(r'Directivity (dBi)')
        ax2.set_xlim(-90, 90)
        ax2.set_ylim(-70, 0)
        x0,x1 = ax2.get_xlim()
        y0,y1 = ax2.get_ylim()
        ax2.set_aspect(abs((x1-x0)/(y1-y0)))
        ax2.grid()

        pp.show()



# Test/example code for the module
if __name__ == "__main__":
    # Create NearField object
    nf = NearField()
    
    ## Load the NF2FF test data
    #nf.loadFromMat("scanarray_pol1_h6mm-10_2_2009.mat", "scanarray_pol2_h6mm-10_2_2009.mat")
    #nf.getFPointFromNF2FF(nf.freq[0])
    
    # Load the SAO test data
    nf.loadFromSAO("MBRx_H1_345GHz_3.dat", "MBRx_H1_345GHz_3.dat", 345e9, tblname_Pol1="MBRx_H1_345GHz_3.tbl", tblname_Pol2="MBRx_H1_345GHz_3.tbl")
     
    # Set up the scan.  Set the Z distance for the measurement
    nf.setUpScan(0.0242)
    
    # Set up the output grids
    nf.setUpGrids(dtheta=0.002, dphi= 0.002)
    
    nf.delCrossPol()
    
    # Plot data from the measurements
    nf.plotNFData()
    
    # Calculate the far field transform
    nf.calcFarFieldRect()
    
    # Plot the far field transform
    #nf.plotFFRectData()

    # Calculate the far field on a sphere and the directivity
    nf.calcFarFieldCartSpherical()
    nf.calcEthetaphi()
    nf.calcDirectivity()
    
    print len(nf.theta), len(nf.phi)
    print "Total Power in Farfield pattern = {:.4g} dB".format(10*np.log10(nf.P))
    
    # Plot the directivity
    #nf.plotFFSphere3d()
    nf.plotEHPlanes()

    ## Test Probe Compensation
    #a_probe = 0.034*0.0254  # probe's x-dimension (m)
    #b_probe = 0.017*0.0254 # probe's y-dimension (m)
    
    #nf.setUpProbe(a_probe, b_probe, nf.z0)
    #nf.probeCompensation()
    
    #nf.calcDirectivity()
    
    ## Plot the directivity
    #nf.plotFFSphere3d()
    #nf.plotEHPlanes()
