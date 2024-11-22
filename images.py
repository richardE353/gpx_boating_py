from typing import Tuple, Optional
from PIL import Image
from staticmap import Line
from gpxpy.gpx import GPXTrackSegment, GPX

import common as rt_args


# installed staticmap 0.5.7
# https://www.blog.pythonlibrary.org/2021/02/16/creating-an-image-viewer-with-pysimplegui/


def test_track():
    fn = rt_args.select_data_file()
    import gpxpy
    gpx: GPX = gpxpy.parse(open(rt_args.DATA_SOURCE_DIR + fn))

    a_seg = gpx.tracks[0].segments[0]
    seg_image = segment_image(a_seg)
    seg_image.save('segment_test.png')


def create_image_files():
    import sqlite3

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()
    res = cur.execute('select path_to_gpx_file from LOG_ENTRY')
    recs = list(res.fetchall())

    for r in recs:
        import gpxpy
        gpx: GPX = gpxpy.parse(open(rt_args.DATA_SOURCE_DIR + r[0]))

        a_seg = gpx.tracks[0].segments[0]
        seg_image = segment_image(a_seg)

        image_name = r[0].replace('.gpx', '.png')
        seg_image.save('./2024_images/' + image_name)

    con.close()


def segment_as_line(s: GPXTrackSegment) -> Line:
    def lon_lat(p) -> Tuple[float, float]:
        return p.longitude, p.latitude

    coords = list(map(lon_lat, s.points))
    line = Line(coords, '#D2322D', 4)
    return line


def segment_image(s: GPXTrackSegment) -> Image:
    from staticmap import StaticMap, Line

    m = StaticMap(1000, 1000, 80)
    line = segment_as_line(s)
    m.add_line(line)

    return m.render()


def load_image(dir: str, fn: str) -> Optional[Image]:
    import os

    full_path = dir + '/' + fn
    if os.path.exists(full_path):
        image = Image.open(full_path)
        return image
    else:
        return None


if __name__ == '__main__':
    create_image_files()
