#!/usr/bin/python

##########################################################
# uses a basic markov assumption to identify and build paths and
# locations on the fly from gps coordinates.
##########################################################

import os, sys, dircache
import lib.libgps as libgps

try:
    LOGFILE_DIR = sys.argv[1]
    if LOGFILE_DIR[-1] != '/':
        LOGFILE_DIR += '/'
except:
    print 'argument error!'
    print 'usage: ./nmea_to_arff.py path/to/logfile(s)'
    print '\teg. ./nmea_to_arff.py gps/logfiles/june27/'
    sys.exit()

# keep stats across all points in all files. 
mean_lat = 0
mean_long = 0
count = 0
previous_point_1 = None
previous_point_2 = None
for filename in dircache.listdir(LOGFILE_DIR):
    if os.path.isdir(LOGFILE_DIR+filename):
        continue
    if filename[filename.rfind('.')+1:].lower() != 'txt':
        continue
    print 'now processing:', filename
    logfile = open(LOGFILE_DIR+filename)

    # returned points are cleaned for basic validity
    points.extend(libgps.points_from_file(logfile, 'NMEA', 'date', 'time'))

    if not points:
        continue

    for point in points:
        count += 1

        mean = ((mean.lat + point.lat), (mean.long+point.long)/count        

out.flush() 
out.close()



    
