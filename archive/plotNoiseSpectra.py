# plotNoiseSpectra.py - Plots noise spectra taken as .mat files in .png files
#			using matplotlib
# -----------------------------------------------------------------------------
# P. Grimes, 17th Nov 2008
# ========================
# This script loops over all .mat files in a directory to provide a quick
# plotting method for large amounts of data
#
# Assumes that .mat file contains following arrays:
#	fs 	= Array of frequencies in FFTs
#	sfft	= Smoother FFT data
#	Vdens	= Raw FFT data
#
# Plots Raw and Smooth FFT data on loglog scales

import matplotlib.pyplot as plt
import scipy.io
loadmat = scipy.io.loadmat
import os


# Edit these for different plots or applications
ylabel = r'Voltage Density ($\mathrm{nV/\sqrt{Hz}}$)'
xlabel = r'Frequency ($\mathrm{Hz}$)'
axis = [1e-2, 1e4, 1e-3, 1e2]
xstring = 'fs'
ystring1 = 'Vdens'
ystring2 = 'sfft'
legend = ('Raw FFT', 'Smoothed FFT')
legendpos = 'upper right'


def plotNoiseSpectrum(matdata, filename, title="Noise Spectrum", fileformat='png'):
	"""Plot individual noise spectrum to png file

	Takes matlab data structure returned by loadmat and a filename
	to plot to and an optional title and format to plot to"""

	# Create the plot
	plt.loglog(matdata[xstring], matdata[ystring1], 'b-',
		matdata[xstring], matdata[ystring2], 'r-')
	plt.axis(axis)
	plt.title(title)
	plt.grid(True)
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.legend(legend, legendpos, shadow=True)

	# Save the plot
	plt.savefig(filename + '.' + fileformat, format=fileformat)

	# Clear the plot
	plt.clf()



def getFileNames(directory=os.getcwd()):
	"""Iterate over current directory to find filenames of .mat files

	By default operates on current directory.  Returns list of filenames
	with extension removed
	"""
	dirlist = os.listdir(directory)

	matlist = []
	for filename in dirlist:
		if filename[-4:] == '.mat':
			matlist.append(filename[:-4])

	if len(matlist) == 0:
		raise ValueError, "No .mat files to work on in current directory"

	return matlist


# Code that loops over files in current directory and plots spectra to .png files
#
# For some reason, os.getcwd() has to be prepended to each filename in the script
#
if __name__=="__main__":
	print os.getcwd()
	filelist = getFileNames()
#	print filelist
	for fname in filelist:
#		print os.getcwd()+'/'+fname+'.mat'
		mdata = loadmat(os.getcwd()+'/'+fname+'.mat')
		plotNoiseSpectrum(mdata, fname, title=fname)
