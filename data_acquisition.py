####################################################################################################

# Script to acquire a fixed amount of bytes of data and then convert it to a csv file that can 
# then be read into Matlab for EEGLab and BCILab. We can change this to an amount of time of 
# time of data collection once we know the sampling rate for the chip. The current sample rate 
# (as of October 10, 2014) looks like about 2 Hz. 

####################################################################################################


import sys 
import numpy as np
import time
import serial
start_time = time.time()

####################################################################################################
# Input variables 
####################################################################################################

time_points = 30  # number of time points to sample 
read_blocks = 15   # number of time points to read at a time in calls to read function 
port_string = "/dev/tty.sichiray-SPPDev"
#port_string = "/dev/tty.SLAB_USBtoUART"
#"/dev/tty.sichiray-SPPDev"
####################################################################################################


bytes = time_points*56

# Define parameters for serial port 

s = serial.Serial()
s.baudrate = 57600
s.port = port_string
s.timeout = 5 
s.open() 

# Now define a function read_in_blocks to help with data acquisition.  
# This function will call the s.read(560) function with 560 bytes, 
# so it will continuously empty the buffer, taking 10 time points at a time. 
# The parameter time_points is total number of time points to read


"""def read_in_blocks(socket, time_points, read_blocks):
	data = ''
	number_of_whole_reads = time_points/read_blocks
	extra_read_time_points = (time_points - read_blocks*number_of_whole_reads) 
	whole_read_bytes = read_blocks*56
	extra_read_bytes = extra_read_time_points*56 
	i = 1
	while i <= number_of_whole_reads: 
		packet = socket.read(whole_read_bytes)
		data += packet
		i += 1
	data += s.read(extra_read_bytes) 
	return data"""

# Use read_in_blocks call to receive data we want; data is one long 
# delimited hex string. 

time_start_collect = time.time()
data_in_bytes = s.read(bytes)
time_end_collect = time.time()
time_to_collect = time_end_collect - time_start_collect

#data_in_bytes = recvall(s,bytes) 
#data_in_bytes = s.read(bytes)
#data_in_bytes = read_in_blocks(s,time_points,read_blocks)
#datan = data_in_bytes.encode('hex')

print "Took", time_to_collect, "seconds to collect data"
print "number of bytes =", len(data_in_bytes)

# Close the serial port 

s.close

# We now convert string to a 1-D numpy array. This allows us to do vectorized operations on 
# entire array (much faster than looping over entries). The uint8 means the data type in string 
# is a byte. 

# Before converting to array we clip front of data so that it starts with the expected "\xaa" 
# character; we'll then clip the back of data after it has been converted to an array. 

start = data_in_bytes.index("\xaa")
data_in_bytes = data_in_bytes[start:]
data_array = np.fromstring(data_in_bytes,dtype=np.uint8)

####################################################################################################

# Next step is to massage data to desired L x 16 array. For now this script just chops off the 
# beginning data at each line and assumes the single-time-point line will be the same length every 
# time. Each line has length 56 in the hex string, so each data line in array also has length 56. 

# Besides making this general, would also be a good idea to make it robust against packet loss or 
# general data issues. (E.g., a single packet loss shouldn't ruin entire resulting array.) 
# Christian implements this in his code with byte counter, see examples he sent in email. 

####################################################################################################

# Clip data_array so it has an even number of time point strings (each time point string has length 56)

collected_time_points = len(data_array)/56
data_array = data_array[0:collected_time_points*56]

print "time_points =", time_points
print "collected_time_points =", collected_time_points
print "approximate collection rate:", collected_time_points/time_to_collect, "Hz"

# Reshape to prepare removal of metadata. This produces array of time points, where each element is 
# the 56-element array corresponding to that time point. 

data_m = np.reshape(data_array,(collected_time_points,56))

# Remove the first 8 entries from each time point (this is just metadata) and convert to integer 
# data type (to make computing possibly faster than floats)

data_m_clipped = data_m[:,8:]
data_m_cl_int = data_m_clipped.astype(int)

####################################################################################################
# The data appear to be ordered with most significant hex digits listed first in array, though 
# this deserves double checking with input voltage.  
####################################################################################################

# Convert each list of sensors values to integers: the first three entries in time point 
# correspond to first sensor value, next three to second sensor value, etc. The original data 
# was in hex, so to convert to proper total integer value for entries (240 190 187) need to do 
#
# value = 240*16^4 + 190*16^2 + 187 
#
# This can be accomplished with dot product, which hopefully is sufficiently vectorized to 
# be faster than just looping over array. Note that 16^4 = 65536, 16^2 = 256.  

hex_c = np.array([65536, 256, 1], dtype=int)
#hex_convert = np.tile(hex_c,16)
#hex_to_dot = np.reshape(hex_convert,(16,3))

# Split colums of data_m_cl_int into 3-member arrays that can be dotted with the hex_to_dot
# vector to get an array of numbers that correspond to integer values of electrode readouts. 
# At end of operation data_m_cl_int should be transformed to a data structures that is L x 16

print "number of time points in array =", data_m_cl_int.shape[0]

data_pr = np.reshape(data_m_cl_int,(data_m_cl_int.shape[0],16,3))

# Do dot product between each element of hex_to_dot and each element of the time points 
# (these elements are now vectors of 3 elements each that correspond to a single sensor readout)

data_int = np.dot(data_pr,hex_c)

# Recenter data on 0 and scale to get microvolts; this is assuming the data, which go from 0 to max, can be recentered 
# by subtracting max/2, where max = "ffffff" in hex. The conversion factor from the Chinese team is we 
# take our number and multiply by 5*(10^6)/(2^24) to get microvolts

data_int = (data_int - 8388608)*0.2980232238769531

# Then we can convert this L x 16 array to a csv with this command: 

final_data_csv = np.savetxt("data.csv",data_int,delimiter=",")

# it may also be possible to convert directly to matlab format with routine from scipy, will have to 
# check that; I have confirmed that EEGLab can read csv created by above script (in EEGLab need to 
# enter that it is ASCII)

print "data.csv saved to current directory"

print "data_acquisition.py took", time.time() - start_time, " seconds to run"
