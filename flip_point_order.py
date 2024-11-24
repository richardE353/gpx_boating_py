import os

import gpxpy
from gpxpy.gpx import GPX

import common as rt_args
from track_stats import get_speed_pct_to_ignore, analyze_track_segments


def main():
    reversed = False

    fn = rt_args.select_data_file()

    gpx: GPX = gpxpy.parse(open(rt_args.get_file_loc(fn)))

    all_segments = []
    for t in gpx.tracks:
        all_segments.extend(t.segments)

    for seg in all_segments:
        if seg.points[0].time > seg.points[1].time:
            reversed = True
            seg.points.reverse()

    if reversed:
        print('Backwards track detected.  Writing corrected file to output directory.')
        with open(rt_args.OUTPUT_DIR + fn, 'w') as f:
            f.write(gpx.to_xml())

    else:
        print('All tracks correct order.  No action taken.')

    pct_to_ignore = get_speed_pct_to_ignore()
    analyze_track_segments(gpx, pct_to_ignore)


if __name__ == '__main__':
    main()
