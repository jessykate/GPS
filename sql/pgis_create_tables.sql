/* Creates tables for storing GPRMC and GPGGA NMEA sentences in a
   postgis-enabled database. points are stored as WKT in 2 dimensions
   (currently).

   Assumes you have created a spatially enabled db first. If your gis
   template name is postgistemplate, this is done as follows: 
   $ createdb new_gis_db -T postgistemplate 

*/

/* GPRMC: Recommended Minimum data. 
   $GPRMC,024710.000,A,3717.9832,N,12203.3000,W,0.00,276.22,231108,,,A*75
 */
CREATE TABLE gprmc (
       pk serial PRIMARY KEY,
       utc time NOT NULL,
       status char(1) NOT NULL,
       speed_knots float,
       angle_true float,
       the_date date NOT NULL,
       mag_var float,
       mode char(1) /* nmea >= v2.3*/
);
SELECT AddGeometryColumn('public', 'gprmc', 'latlong', 4326, 'POINT', 2);
ALTER TABLE gprmc ALTER COLUMN latlong SET NOT NULL;


/* GPGGA: Global Positioning System Fix and Error Information: 
   $GPGGA,093105.000,3718.0079,N,12203.3160,W,1,07,1.3,159.5,M,-26.0,M,,0000*61
 */
CREATE TABLE gpgga (
       pk serial PRIMARY KEY,
       utc time NOT NULL,
       gps_fix int NOT NULL,
       sats_in_view int,
       horiz_error float,
       alt_asl float,
       height_WGS84 float,

       /* DGPS fields are often null depending on your data logger */
       dgps_age float,
       dgps_id int 
);
SELECT AddGeometryColumn('public', 'gpgga', 'latlong', 4326, 'POINT', 2);
ALTER TABLE gpgga ALTER COLUMN latlong SET NOT NULL;



/* GPGSA: dilusion of precision (DOP) information and satellites
   used in the current fix.
   $GPGSA,A,3,20,22,32,14,11,31,,,,,,,2.4,1.5,2.0*36

CREATE TABLE gpgsa (
       pk serial PRIMARY KEY,
       mode char(1),
       fix int NOT NULL,
       pdop float,
       hdop float,
       vdop float,
);

CREATE TABLE sats_in_gpgsa (
       sat_id int,
              
);

CREATE TABLE satellites (
       satellite_id int PRIMARY KEY NOT NULL,       
);

CREATE TABLE gpgsv (
);

 */

