#!/usr/bin/python

# given a picture directory and logfile directory, generates one kml
# file corresponding to each logfile, geotagging pictures using
# timestamps, and adding a placemark with each location-matched
# picture in an info bubble, at the correct place on the map. 

# note that the script currently requires you to manually move any
# pictures used in the kml files to a subdirectory called 'pictures'
# from the location where the kml files are saved. (currently also the 

# future options:
# * add prev and next buttons 
# * fix files which are started but have no content and dont get removed. 
# * specify output dir for kml files
# * automatically copy pictures to pictures subdirectory
# * support flickr api/remote photos
# * support kml as input?

import os, sys, re, libgps, datetime, dircache 

# parse command line options
try:
    LOGFILE_DIR = sys.argv[1]
    if LOGFILE_DIR[-1] != '/':
        LOGFILE_DIR += '/'
    PICS_DIR = sys.argv[2]
    if PICS_DIR[0] != '/':
        raise ValueError
    if PICS_DIR[-1] != '/':
        PICS_DIR += '/'
    utc_offset = int(sys.argv[3])

except:
    print 'argument error!'
    print 'usage: ./phototagging.py path/to/logfile(s) path/to/pictures utc_offset'
    print '\teg. ./phototagging.py gps/logfiles/june27/ /home/username/pictures/mytrip/ -6'
    print '\tnote: pictures path must be absolute (weird, i know)'
    sys.exit()

# extract information from the pictures. will also parse
# subdirectories for pictures if they exist.
pic_files = libgps.files_in_subdirs(PICS_DIR, 'jpg', 'avi')
print 'Found %d pictures.' % len(pic_files)
print 'Extracting dates and converting timestamps to UTC...'
# pictures is a time-sorted list of picture objects with datetime
# stamps converted to UTC
pictures = libgps.get_pic_info(pic_files)
print 'Pictures date range (UTC): %s - %s\n' % (pictures[0].datetime.ctime(), pictures[-1].datetime.ctime())

# process each gps data file and match photos to locations using
# timestamps. outputs a kml file with one placemark per photo. output
# is to the logfile directory. 
for filename in dircache.listdir(LOGFILE_DIR):
    if os.path.isdir(LOGFILE_DIR+filename):
        continue
    print 'now processing:', filename
    logfile = open(LOGFILE_DIR+filename)
    outfile = os.path.join(LOGFILE_DIR,filename[:filename.rfind('.')]+'_photos.kml')
    if os.path.exists(outfile):
        print >> sys.stderr, '\tFile exist: %s. skipping.\n' % outfile
        continue
    out = open(outfile, 'w')

    print >> out, libgps.kml_preamble() 

    # pass the raw data file, format, and desired metadata items to
    # the data extraction function.
    points = libgps.points_from_file(logfile, 'NMEA', 'date', 'time')

    if not points:
        print '\tLogfile %s was empty. Continuing.\n' % filename
        out.close()
        os.remove(outfile)
        continue

    print '\tGPS data date range for %s: %s - %s' % (filename, str(points[0].datetime), str(points[-1].datetime))    
    
    # both the pictures and the points arrays are sorted by time. for
    # each picture, iterate over the points array until a point is
    # found that (roughly) matches the timestamp on the picture. when
    # the match is found, create a kml placemark at that location with
    # the image. for each subsequent picture, iterate over the gps
    # points starting from the *same spot* (without starting over
    # again).
    index = 0 # keep track of our position in the points array
    num_matched = 0
    for picture in pictures: 
        picture_found = True        
        # make sure this picture wasnt taken before any of the points
        # in this logfile.
        if picture.datetime < points[index].datetime:
            out.close()
            os.remove(outfile)
            continue
        while picture.datetime > points[index].datetime:
            if index < len(points)-1:
                index += 1                            
            else: 
                picture_found = False
                break
        if picture_found:
            base_filename = os.path.basename(picture.filename)
            num_matched += 1
            picture_location = points[index]

            print >> out, '<Placemark id="'+basename+'">'
            print '<description>'
            print >> out, picture.datetime.ctime()
            print >> out,  '''<![CDATA['''
            print >> out, '<img src="pictures/'+ base_filename + '"/>'
            print >> out, ''']]>
</description>
<Point>
<coordinates>'''
            print >> out, '%s, %s' % (picture_location.long, picture_location.lat)
            print >> out, '''</coordinates>
</Point>
</Placemark>
'''    
        else: break # if not picture_found

    print >> out, libgps.kml_postamble()
    out.flush() 
    out.close()

    if num_matched == 0:
        print '\tNo pictures matched the data in this file. Continuing.\n' 
        os.remove(outfile)
    else:
        print '\tSaved output to file %s\n' % outfile
    # remove any matched pictures from the pictures list so that we
    # dont revisit them again.
    pictures = pictures[num_matched:]

