import os
from typing import Tuple, Optional
from PIL import Image
from staticmap import Line
from gpxpy.gpx import GPXTrackSegment, GPX

import common as rt_args


# installed staticmap 0.5.7
# https://www.blog.pythonlibrary.org/2021/02/16/creating-an-image-viewer-with-pysimplegui/


def create_image_files():
    import sqlite3

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()
    res = cur.execute('select path_to_gpx_file from LOG_ENTRY')
    recs = list(res.fetchall())

    for r in recs:
        import gpxpy
        gpx: GPX = gpxpy.parse(open(rt_args.get_file_loc(r[0])))

        a_seg = gpx.tracks[0].segments[0]
        seg_image = segment_image(a_seg)

        image_name = r[0].replace('.gpx', '.png')
        seg_image.save(rt_args.TRACK_IMAGES_DIR + os.sep + image_name)

    con.close()


def segment_as_line(s: GPXTrackSegment) -> Line:
    def lon_lat(p) -> Tuple[float, float]:
        return p.longitude, p.latitude

    coords = list(map(lon_lat, s.points))
    line = Line(coords, '#D2322D', 4)
    return line


def segment_image(s: GPXTrackSegment) -> Image:
    from staticmap import StaticMap

    m = StaticMap(1000, 1000, 80)
    line = segment_as_line(s)
    m.add_line(line)

    return m.render()


def load_image(fn: str) -> Optional[Image]:
    import os

    full_path = rt_args.get_file_loc(fn)
    if os.path.exists(full_path):
        image = Image.open(full_path)
        return image
    else:
        return None


if __name__ == '__main__':
    create_image_files()
