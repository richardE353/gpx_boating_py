from dataclasses import dataclass
from datetime import date, datetime, timedelta

import gpxpy

from gpxpy.gpx import GPXTrackSegment, GPXTrackPoint
from gpxpy.gpx import GPX

import common as rt_args

from typing import Optional


@dataclass()
class PointExtension:
    source: GPXTrackPoint
    extracted_values: dict

    def __init__(self, a_point):
        self.source = a_point
        self.extracted_values = self.parse_comment(a_point)

    def parse_comment(self, p: GPXTrackPoint) -> dict:
        result = dict()

        if p.comment:
            elements = p.comment.split('\n')
        else:
            elements = []

        for s in elements:
            kv = s.split(':')

            # handle the weird case of TWD, which doesn't use ':' to separate key/value
            if len(kv) == 1:
                kv = s.strip().split(' ')

            key = kv[0].strip()
            value = kv[1].strip()
            result[key] = value

            # handle compound key/values
            if -1 < key.find('/'):
                keys = key.split('/')
                values = value.split('/')

                for k, v in zip(keys, values):
                    sk = k.strip()
                    sv = v.strip()
                    result[sk] = sv

        return result

    def as_numerical_value(self, k: str) -> Optional[float]:
        import re

        v = self.extracted_values.get(k)
        if v:
            nus = re.sub('[^0-9.]', '', v)
            return float(nus)
        else:
            return None

    @property
    def depth(self) -> Optional[float]:
        return self.as_numerical_value('Depth')

    @property
    def stw(self) -> Optional[float]:
        return self.as_numerical_value('STW')

    @property
    def cog(self) -> Optional[float]:
        return self.as_numerical_value('COG')

    @property
    def sog(self) -> Optional[float]:
        return self.as_numerical_value('SOG')

    @property
    def twd(self) -> Optional[float]:
        return self.as_numerical_value('TWD')

    @property
    def tws(self) -> Optional[float]:
        return self.as_numerical_value('TWS')

    @property
    def awa(self) -> Optional[float]:
        return self.as_numerical_value('AWA')

    @property
    def aws(self) -> Optional[float]:
        return self.as_numerical_value('AWS')


@dataclass()
class SegmentStats:
    start_date: Optional[date]
    start_time: Optional[datetime]
    moving_time: float
    stopped_time: float
    moving_distance: float
    stopped_distance: float
    num_pts: int
    max_sog: Optional[float]
    avg_sog: Optional[float]
    max_stw: Optional[float]
    avg_stw: Optional[float]
    max_tws: Optional[float]
    avg_tws: Optional[float]

    def summary_str(self):
        fmt_str = 'Date: {}, Start T: {}, Points: {}'
        processed_str = fmt_str.format(self.start_date, self.start_time, self.num_pts)

        return processed_str

    def speeds_str(self):
        fmt_sog = '\tSpeed over ground (kts): max: {:.1f}, avg: {:.1f}'
        processed_str = fmt_sog.format(self.max_sog, self.avg_sog)

        if self.max_stw:
            fmt_stw = '\n\tSpeed thru water (kts): max: {:.1f}, avg: {:.1f}'
            processed_str = processed_str + fmt_stw.format(self.max_stw, self.avg_stw)

        return processed_str

    def wind_str(self):
        if self.max_tws:
            fmt_stw = '\tTrue Wind Speed (kts): max: {:.1f}, avg: {:.1f}'
            return fmt_stw.format(self.max_tws, self.avg_tws)
        else:
            return '\tNo wind data available'

    def distance_str(self):
        base_str = '\tMoving T: {} Stopped T: {} Moving Dist: {:.2f} nm Stopped Dist: {:.2f} nm'
        return base_str.format(str(self.moving_time), str(self.stopped_time), self.moving_distance,
                               self.stopped_distance)


# https://ocefpaf.github.io/python4oceanographers/blog/2014/08/18/gpx/
def main():
    fn = rt_args.select_data_file()

    speed_pct_ignore = int(input('Pct of top speeds to ignore (0 - 50, recommended: 5) : '))
    speed_pct_ignore = min(max(speed_pct_ignore, 0), 50) / 100.0

    gpx: GPX = gpxpy.parse(open(rt_args.DATA_SOURCE_DIR + fn))

    all_segments: list[GPXTrackSegment] = []
    for t in gpx.tracks:
        all_segments.extend(t.segments)

    for seg in all_segments:
        if seg.points[0].time > seg.points[1].time:
            seg.points.reverse()

        # skip segments w/ distance < 10m, or shorter than 10 minutes
        if seg.length_2d() > 10.0 and seg.get_duration() > 600:
            print_segment_stats(seg, speed_pct_ignore)
            print('\tEngine Hours:')


def m_to_nm(m: float) -> float:
    return m * 0.0005399566666666666


def mps_to_knots(mps: float) -> float:
    # bit of a hack but handle bug in gpxpy get_speed method where last data point location and previous
    # data point location are the same
    if mps:
        return mps * 1.94384
    else:
        return 0.0


def str_remove_units(s: str) -> float:
    import re

    nus = re.sub('[^0-9]', '', s)
    return float(nus)


def print_segment_stats(seg: GPXTrackSegment, speed_pct_ignore: float):
    print('')

    stats = get_segment_stats(seg, speed_pct_ignore)
    print(stats.summary_str())
    print(stats.distance_str())
    print(stats.speeds_str())
    print(stats.wind_str())


def get_segment_stats(seg: GPXTrackSegment, extreemes_percentile=0.05) -> SegmentStats:
    t_bounds = seg.get_time_bounds()
    if t_bounds[0] is not None:
        s_date = t_bounds[0].date()
        start_t = t_bounds[0].time()
    else:
        s_date = 'None'
        start_t = 'None'

    num_pts = len(seg.points)

    m_t, s_t, moving_m, stopped_m, max_spd = \
        seg.get_moving_data(speed_extreemes_percentiles=extreemes_percentile)

    max_sog = mps_to_knots(max_spd)
    avg_sog = mps_to_knots((moving_m + stopped_m) / (m_t + s_t))

    moving_t = timedelta(seconds=int(m_t))
    stopped_t = timedelta(seconds=int(s_t))

    moving_nm = m_to_nm(moving_m)
    stopped_nm = m_to_nm(stopped_m)

    # used to strip out entries without a numerical value
    def has_value(of: Optional[float]) -> bool:
        return of is not None

    extensions = list(map(lambda p: PointExtension(p), seg.points))

    stw = list(filter(has_value, (map(lambda pe: pe.stw, extensions))))
    if stw:
        max_stw = max(stw)
        avg_stw = sum(stw) / len(stw)
    else:
        max_stw = None
        avg_stw = None

    tws = list(filter(has_value, (map(lambda pe: pe.tws, extensions))))
    if tws:
        max_tws = max(tws)
        avg_tws = sum(tws) / len(tws)
    else:
        max_tws = None
        avg_tws = None

    return SegmentStats(s_date, start_t, moving_t, stopped_t, moving_nm, stopped_nm, num_pts,
                        max_sog, avg_sog, max_stw, avg_stw, max_tws, avg_tws)


if __name__ == '__main__':
    main()
