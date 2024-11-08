These scripts have the following required packages:

    Package     |  Pip Installation command | Install Info
    ------------+---------------------------+----------------
    gpxpy       |   pip install gpxpy       | https://pypi.org/project/gpxpy/
    pysimplegui |   pip install pysimplegui | https://pypi.org/project/PySimpleGUI/

Modify common.py to specify the directory containing .gpx files to analyze, and also to specify a target directory
for writing gpx files modified by the flip_point_order script.

There are currently 3 different scripts.  They are as follows:

gui.py
    The start of a logbook application.  GPX segments are analyzed using the track_stats.py functionality, and stored in
    a SQLLite database, along with other data entered by the user.

track_stats.py
    Lets you specify which .gpx file to analyze, then analyzes each track segment and outputs information about them.
    It reads the <cmt> element to extract depth, wind, and speed data when present.  The extra data is typically
    included in Yacht Devices server exports.

    Sample output:

    Date: 2024-04-17, Start T: 15:39:30, Points: 87
	    Moving T: 0:29:30 Stopped T: 0:10:30
	    Moving D: 2.13 nm Stopped D: 0.02 nm
	    SOG (kts): max: 5.3, avg: 3.2
	    STW (kts): max: 5.9, avg: 3.2
	    TWS (kts): max: 8.5, avg: 5.8
	    Avg Wind dir: 314.8°

flip_point_order.py
    Detects if any track segment has its points ordered with the most recent point first, and flips them into ascending
    chronological order and exports the modified file to the specified output directory.

