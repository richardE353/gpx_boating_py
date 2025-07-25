import sqlite3
from sqlite3 import Connection
from typing import Optional

import gpxpy
from gpxpy.gpx import GPX, GPXTrackSegment

import common as rt_args
from database import LogEntryRecord, TrackStats, add_to_database, EngineHoursRecord
from track_stats import get_speed_pct_to_ignore, get_segment_stats, SegmentStats


def persist(entry: LogEntryRecord, stats: TrackStats, hours_rec: Optional[EngineHoursRecord], con: Connection):
    add_to_database(entry.table_name(), entry.values_str(), con)
    add_to_database(stats.table_name(), stats.values_str(), con)

    if hours_rec is not None:
        try:
            add_to_database(hours_rec.table_name(), hours_rec.values_str(), con)
        except:
            print('failed to persist hours')

def input_log_entry(gpx_file_name: str, seg: GPXTrackSegment, speed_pct_ignore: float) -> Optional[LogEntryRecord]:
    title = input('Entry Title : ')
    start_loc = input('Starting Location :')
    end_loc = input('End Location :')
    crew = input('Crew : ')

    print("Notes: ")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)

    notes = '\n'.join(lines)

    return create_log_entry(gpx_file_name, seg, title, start_loc, end_loc, crew, notes)


def create_log_entry(gpx_file_name: str, seg: GPXTrackSegment, title: str, start_loc: str, end_loc: str, crew: str,
                     notes: str) -> LogEntryRecord:
    date = str(seg.get_time_bounds().start_time.date())
    start_seconds = int(seg.get_time_bounds().start_time.timestamp())

    return LogEntryRecord(start_seconds, title, date, crew, gpx_file_name, start_loc, end_loc, notes)


def create_track_stats(le: LogEntryRecord, stats: SegmentStats, pct: float) -> Optional[TrackStats]:
    return TrackStats(le.start_timestamp,
                      pct,
                      stats.moving_time.seconds,
                      stats.stopped_time.seconds,
                      stats.moving_distance,
                      stats.stopped_distance,
                      stats.avg_sog,
                      stats.max_sog,
                      stats.avg_stw,
                      stats.max_stw,
                      stats.avg_tws,
                      stats.max_tws,
                      stats.avg_wind_dir,
                      stats.avg_wind_spd)


def select_and_process_file():
    fn = rt_args.select_data_file()
    speed_pct_ignore = get_speed_pct_to_ignore()
    process_selected_file(fn, speed_pct_ignore)


def process_selected_file(fn: str, speed_pct_ignore: float):
    gpx: GPX = gpxpy.parse(open(rt_args.get_file_loc(fn)))

    all_segments: list[GPXTrackSegment] = []
    for t in gpx.tracks:
        all_segments.extend(t.segments)

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    for seg in all_segments:
        if seg.points[0].time > seg.points[1].time:
            seg.points.reverse()

        # skip segments w/ distance < 10m, or shorter than 10 minutes
        if seg.length_2d() > 10.0 and seg.get_duration() > 600:
            stats = get_segment_stats(seg, speed_pct_ignore)

            new_entry = input_log_entry(fn, seg, speed_pct_ignore)
            trk_stats = create_track_stats(new_entry, stats, speed_pct_ignore)

            con = sqlite3.connect(rt_args.DATABASE_LOC)
            persist(new_entry, trk_stats, con)

    con.close()


if __name__ == '__main__':
    select_and_process_file()
