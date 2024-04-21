
import gpxpy

from gpxpy.gpx import GPX

import common as rt_args

def main():
    reversed = False

    fn = rt_args.select_data_file()

    gpx: GPX = gpxpy.parse(open(rt_args.DATA_SOURCE_DIR + fn))

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


if __name__ == '__main__':
    main()