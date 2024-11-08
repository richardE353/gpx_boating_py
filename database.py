import dataclasses
from dataclasses import dataclass, astuple
from sqlite3 import Connection
from typing import Tuple, Optional, List

import common as rt_args

import sqlite3


@dataclass
class LogEntryRecord:
    start_timestamp: int
    title: str
    date: str
    crew: str
    path_to_gpx_file: str
    start_loc: str
    end_loc: str
    notes: str

    def table_name(self) -> str:
        return 'LOG_ENTRY'

    def values_str(self) -> str:
        return str(astuple(self))


@dataclass
class TrackStats:
    start_timestamp: int
    pct_top_spd_ignored: float
    moving_seconds: int
    stopped_seconds: int
    moving_distance: float
    stopped_distance: float
    sog_avg: float
    sog_max: float
    stw_avg: float
    stw_max: float
    tws_avg: float
    tws_max: float
    avg_wind_dir: float
    avg_wind_spd: float

    def table_name(self) -> str:
        return 'TRACK_STATS'

    def values_str(self) -> str:
        base_str = str(astuple(self))
        return base_str.replace(', None', ', Null')


@dataclass
class LogEntrySummary:
    start_timestamp: int
    date: str
    title: str
    moving_distance: float

    def summary_string(self) -> str:
        return self.date + ': ' + self.title + ', ' + '{:.2f}'.format(self.moving_distance) + 'nm'


def add_to_database(tbl_name: str, values_str: str, con: Connection):
    stmt = "INSERT INTO " + tbl_name + " VALUES " + values_str

    cur = con.cursor()
    cur.execute(stmt)
    con.commit()


LOG_ENTRY_SUMMARY_BASE_QRY = 'select * from LOG_ENTRY_SUMMARY'

LOG_ENTRY_SUMMARIES_QRY = LOG_ENTRY_SUMMARY_BASE_QRY + ' Order By date, start_timestamp'


def get_entry_summaries(con: Connection) -> List[LogEntrySummary]:
    cur = con.cursor()
    res = cur.execute(LOG_ENTRY_SUMMARIES_QRY)
    recs = res.fetchall()

    return_val = []
    for r in recs:
        summary = LogEntrySummary(*r)
        return_val.append(summary)

    return return_val


def select_log_summary(id: int, con: Connection) -> Optional[LogEntrySummary]:
    qry_str = LOG_ENTRY_SUMMARY_BASE_QRY + ' WHERE start_timestamp=' + str(id)
    cur = con.cursor()
    res = cur.execute(qry_str)
    a_rec = res.fetchone()

    return LogEntrySummary(*a_rec)


def select_log_entry(id: int, con: Connection) -> Optional[LogEntryRecord]:
    cur = con.cursor()
    res = cur.execute("select * from LOG_ENTRY WHERE start_timestamp=" + str(id))
    a_rec = res.fetchone()

    return LogEntryRecord(*a_rec)


def select_log_entry_stats(id: int, con: Connection) -> Optional[TrackStats]:
    cur = con.cursor()
    res = cur.execute("select * from TRACK_STATS WHERE start_timestamp=" + str(id))
    a_rec = res.fetchone()

    return TrackStats(*a_rec)


def create_database():
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()

    cur.execute("""
     CREATE TABLE LOG_ENTRY (
	    start_timestamp integer PRIMARY KEY,
	    title text,
	    date text,
	    crew text,
	    path_to_gpx_file text,
	    start_loc text,
	    end_loc text,
	    notes text
    )
    """)

    cur.execute("""
     CREATE TABLE TRACK_STATS (
	    start_timestamp integer PRIMARY KEY,
	    pct_top_spd_ignored real,
	    moving_time_seconds integer,
	    stopped_time_seconds integer,
	    moving_distance real,
	    stopped_distance real,
	    sog_avg real,
	    sog_max real,
	    stw_avg real,
	    stw_max real,
	    tws_avg real,
	    tws_max real,
	    avg_wind_dir real,
	    avg_wind_spd real,
	 FOREIGN KEY (start_timestamp)
		REFERENCES LOG_ENTRY (start_timestamp)
			ON DELETE CASCADE
			ON UPDATE NO ACTION
    )
    """)

    cur.execute("""
        CREATE VIEW LOG_ENTRY_SUMMARY AS
        select LOG_ENTRY.start_timestamp, date, title, moving_distance
        from LOG_ENTRY 
        LEFT JOIN TRACK_STATS
        ON LOG_ENTRY.start_timestamp = TRACK_STATS.start_timestamp"""
                )

    con.close()
