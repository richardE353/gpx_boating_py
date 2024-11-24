import math
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

    def speed_units(self) -> str:
        import re

        units = 'knots'
        v = self.extracted_values.get('STW')
        if v:
            units = re.sub('[0-9.]', '', v).strip()

        if units == 'knots':
            units = 'kts'

        return units

    # for points with no tws, SOG is 0.0 knots.  In this case, TWD = COG + AWA, and TWS = AWS
    def effective_twd(self) -> float:
        if self.twd:
            return self.twd
        else:
            etwd = self.cog + self.awa
            return etwd

    def effective_tws(self) -> float:
        if self.tws:
            return self.tws
        else:
            if self.sog and (self.sog > 0.0):
                print('sog > 0, but no tws!  Stop, and explore the data.')
            return self.aws

    @property
    def awa(self) -> Optional[float]:
        return self.as_numerical_value('AWA')

    @property
    def aws(self) -> Optional[float]:
        return self.as_numerical_value('AWS')

    # https://www.scadacore.com/2014/12/19/average-wind-direction-and-wind-speed/
    def ew_vector(self) -> Optional[float]:
        import math

        if self.twd and self.tws:
            return math.sin(math.radians(self.twd)) * self.tws
        else:
            return None

    def ns_vector(self) -> Optional[float]:
        import math

        if self.twd and self.tws:
            return math.cos(math.radians(self.twd)) * self.tws
        else:
            return None


@dataclass()
class SegmentStats:
    start_date: Optional[date]
    start_time: Optional[datetime]
    moving_time: timedelta
    stopped_time: timedelta
    moving_distance: float
    stopped_distance: float
    num_pts: int
    speed_units: str
    max_sog: Optional[float]
    avg_sog: Optional[float]
    max_stw: Optional[float]
    avg_stw: Optional[float]
    max_tws: Optional[float]
    avg_tws: Optional[float]
    avg_wind_dir: Optional[float]
    avg_wind_spd: Optional[float]

    def summary_str(self):
        fmt_str = 'Date: {}, Start T: {}, Points: {}'
        processed_str = fmt_str.format(self.start_date, self.start_time, self.num_pts)

        return processed_str

    def speeds_str(self):
        fmt_sog = '\tSOG (' + self.speed_units + '): max: {:.1f}, avg: {:.1f}'
        processed_str = fmt_sog.format(self.max_sog, self.avg_sog)

        if self.max_stw:
            fmt_stw = '\n\tSTW (' + self.speed_units + '): max: {:.1f}, avg: {:.1f}'
            processed_str = processed_str + fmt_stw.format(self.max_stw, self.avg_stw)

        return processed_str

    def d_units(self) -> str:
        if self.speed_units == 'm/s':
            return 'm'

        return 'nm'

    def wind_str(self):
        if self.max_tws:
            fmt_stw = '\tTWS (' + self.speed_units + '): max: {:.1f}, avg: {:.1f}\n\tAvg Wind dir: {:.1f}°'
            return fmt_stw.format(self.max_tws, self.avg_tws, self.avg_wind_dir)
        else:
            return '\tNo wind data available'

    def distance_str(self):
        base_str = ('\tMoving T: {} Stopped T: {}\n\tMoving D: {:.2f} ' + self.d_units() + ' Stopped D: {:.2f} ' +
                    self.d_units())
        return base_str.format(str(self.moving_time), str(self.stopped_time), self.moving_distance,
                               self.stopped_distance)


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
    stats = get_segment_stats(seg, speed_pct_ignore)

    print('\n' + stats.summary_str())
    print(stats.distance_str())
    print(stats.speeds_str())
    print(stats.wind_str())


# https://www.scadacore.com/2014/12/19/average-wind-direction-and-wind-speed/
# http://www.webmet.com/met_monitoring/622.html
def calculate_wind_averages(p_extensions: list[PointExtension]) -> (float, float):
    def spd_component(f, pe: PointExtension) -> float:
        rads = math.radians(pe.twd)
        return f(rads) * pe.tws

    ew_total = sum(map(lambda pe: spd_component(math.sin, pe), p_extensions))
    ew_avg = (ew_total / len(p_extensions)) * -1.0

    ns_total = sum(map(lambda pe: spd_component(math.cos, pe), p_extensions))
    ns_avg = (ns_total / len(p_extensions)) * -1.0

    # this is a vector length average, NOT the average of the speeds.
    avg_spd = math.sqrt(ew_avg ** 2 + ns_avg ** 2)

    atan2_dir = math.atan2(ew_avg, ns_avg)
    degrees_dir = math.degrees(atan2_dir)

    if degrees_dir > 180.0:
        degrees_dir = degrees_dir - 180.0
    elif degrees_dir < 180.0:
        degrees_dir = degrees_dir + 180.0

    return (degrees_dir, avg_spd)


def remove_stationary_pts(seg: GPXTrackSegment) -> GPXTrackSegment:
    # filter out all points with SOG of 0.  This is to handle leaving instruments on for anchor alarm
    p_extensions = list(map(lambda p: PointExtension(p), seg.points))
    moving_pts = list(filter(lambda pe: (pe.stw is not None) and (pe.stw > 0.8), p_extensions))
    culled_pts = list(map(lambda pe: pe.source, moving_pts))

    new_seg = GPXTrackSegment(culled_pts)

    return new_seg


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

    p_extensions = list(map(lambda p: PointExtension(p), seg.points))
    stw = list(filter(lambda s: (s is not None), (map(lambda pe: pe.stw, p_extensions))))

    if len(p_extensions) > 0:
        speed_units = p_extensions[0].speed_units()
    else:
        speed_units = 'kts'

    if speed_units == 'kts':
        max_sog = mps_to_knots(max_spd)
        avg_sog = mps_to_knots((moving_m + stopped_m) / (m_t + s_t))
        moving_d = m_to_nm(moving_m)
        stopped_d = m_to_nm(stopped_m)
    else:
        max_sog = max_spd
        avg_sog = (moving_m + stopped_m) / (m_t + s_t)
        moving_d = moving_m
        stopped_d = stopped_m

    moving_t = timedelta(seconds=int(m_t))
    stopped_t = timedelta(seconds=int(s_t))

    if len(stw) > 0:
        max_stw = max(stw)
        avg_stw = sum(stw) / len(stw)

        tw_data = list(filter(lambda pe: (pe.tws is not None) and (pe.twd is not None), p_extensions))

        if len(tw_data):
            max_tws = max(map(lambda pe: pe.tws, tw_data))
            avg_tws = sum(map(lambda pe: pe.tws, tw_data)) / len(tw_data)
        else:
            max_tws = None
            avg_tws = None

        (avg_wind_dir, avg_wind_speed) = calculate_wind_averages(tw_data)

        return SegmentStats(s_date, start_t, moving_t, stopped_t, moving_d, stopped_d, num_pts, speed_units,
                            max_sog, avg_sog, max_stw, avg_stw, max_tws, avg_tws, avg_wind_dir, avg_wind_speed)
    else:
        return SegmentStats(s_date, start_t, moving_t, stopped_t, moving_d, stopped_d, num_pts, 'kts',
                            max_sog, avg_sog, None, None, None, None, None, None)


def analyze_track_segments(gpx, speed_pct_ignore):
    all_segments: list[GPXTrackSegment] = []
    for t in gpx.tracks:
        all_segments.extend(t.segments)
    for seg in all_segments:
        if seg.points[0].time > seg.points[1].time:
            seg.points.reverse()

        # skip segments w/ distance < 10m, or shorter than 10 minutes
        if seg.length_2d() > 10.0 and seg.get_duration() > 600:
            print_segment_stats(seg, speed_pct_ignore)

            # exploratory to study removing pts where stw is 0
            # filtered_seg = remove_stationary_pts(seg)
            # if filtered_seg.length_2d() > 10.0:
            #     print_segment_stats(filtered_seg, speed_pct_ignore)


def get_speed_pct_to_ignore():
    speed_pct_ignore = int(input('Pct of top speeds to ignore (0 - 50, recommended: 5) : '))
    speed_pct_ignore = min(max(speed_pct_ignore, 0), 50) / 100.0
    return speed_pct_ignore


# https://ocefpaf.github.io/python4oceanographers/blog/2014/08/18/gpx/
def main():
    fn = rt_args.select_data_file()
    gpx: GPX = gpxpy.parse(open(rt_args.get_file_loc(fn)))

    speed_pct_ignore = get_speed_pct_to_ignore()

    analyze_track_segments(gpx, speed_pct_ignore)


if __name__ == '__main__':
    main()
