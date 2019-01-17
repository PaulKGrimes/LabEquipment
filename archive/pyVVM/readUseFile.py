# readUseFile.py
# 
# Paul Grimes
#
# Module to parse a usefile and return the options in it

def readUseFile(fileName):
	'''Read the use file into a dictionary of settings'''
	# The file contents
	usefile = open(fileName)
	lines = usefile.readlines()
	usefile.close()
	
	options = {}
	# Parse the file
	for line in lines:
		# Check for empty line
		if len(line) < 3:
			continue
		
		# Skip comments
		if line[0] == "#":
			continue
		
		# Parse the line
		a = line.split(": ")
		if len(a) == 2:
			# We have found a key:value pair
			key = a[0]
			value = a[1]
			
			# parse the value for any unit
			if len(value.split()) != 1:
				val = float(value.split()[0])
				unitstr = value.split()[1].rstrip()
				unit = getUnitValue(unitstr)
				value = val*unit
			else:
				value = value.rstrip()
				try:
					value = float(value)
				except ValueError:
					pass
					
			options[key] = value
		
	return options
			
def getUnitValue(unitstr):
	'''Return the value corresponding to a unit'''
	units = {
		"MHz" : 1.0e6,
		"GHz" : 1.0e9,
		"dBm" : 1.0,
		"ms"  : 1.0e-3
		}
		
	return units[unitstr]
