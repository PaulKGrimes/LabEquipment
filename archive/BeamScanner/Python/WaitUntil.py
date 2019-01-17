# WaitUntil.py
#
# Python function that waits until (after) a particular time before
# continuing.  Checks the time every hour and returns after the
# given time has passed

import time
import datetime
import os

def WaitUntil(dt, pollPeriod=3600):
    """Wait until dt has passed before returning.
    
    Check the clock every pollPeriod seconds"""
    for i in range(0, 2*24*3600, pollPeriod):
        if dt<datetime.datetime.today():
            break
        else:
            time.sleep(pollPeriod)
            
def GetNextTime(hours = 0, minutes = 0, seconds = 0):
    """Return a datetime object representing the next time
    that hours:minutes:seconds will be on the clock"""
    
    now = datetime.datetime.today()
    t = datetime.datetime(now.year, now.month, now.day, hours, minutes, seconds)
    if t<now:
        t+=datetime.timedelta(days=1)
        
    return t

if __name__ == "__main__":
    # When should we wait until?
	t = GetNextTime(hours=13, minutes=30)
    
	# Wait
	print "Waiting until %s" % t
    WaitUntil(t, pollPeriod=360)
	
	# Do something
    os.system("python BeamScanner.py BeamScan330.use")
    os.system("python BeamScanner.py BeamScan345.use")
    os.system("python BeamScanner.py BeamScan357.use")
    os.system("python BeamScanner.py BeamScan372.use")
    