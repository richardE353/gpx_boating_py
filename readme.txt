These scripts have the following required packages:

    Package     |  Pip Installation command | Install Info
    ------------+---------------------------+----------------
    gpxpy       |   pip install gpxpy       | https://pypi.org/project/gpxpy/


Modify common.py to specify the directory containing .gpx files to analyze, and also to specify a target directory
for writing gpx files modified by the flip_point_order script.

There are currently 2 different scripts.  They are as follows:

track_stats.py
    Lets you specify which .gpx file to analyze, then analyzes each track segment and outputs information about them.
    It reads the <cmt> element to extract depth, wind, and speed data when present.

    Sample output:

    Date: 2024-04-17, Start T: 15:39:30, Points: 90
	    Moving T: 0:29:30 Stopped T: 0:12:00 Moving Dist: 2.13 nm Stopped Dist: 0.02 nm
            Speed over ground (kts): max: 5.4, avg: 3.1
	    Speed thru water (kts): max: 5.9, avg: 3.1
	    True Wind Speed (kts): max: 8.5, avg: 5.8

flip_point_order.py
    Detects if any track segment has its points ordered with the most recent point first, and flips them into ascending
    chronological order and exports the modified file to the specified output directory.

