from dataclasses import dataclass, astuple
from sqlite3 import Connection
from typing import Optional, List

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

    def path_to_image_file(self) -> str:
        return self.path_to_gpx_file.replace('.gpx', '.png')


@dataclass
class LogEntryAndHoursView(LogEntryRecord):
    hours: Optional[float]

    def table_name(self) -> str:
        return 'LOG_ENTRY_HOURS_VIEW'

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


@dataclass
class UpkeepActionRecord:
    id: int
    description: str

    def table_name(self) -> str:
        return 'UPKEEP_ACTION'

    def values_str(self) -> str:
        base_str = str(astuple(self))
        return base_str.replace(', None', ', Null')


@dataclass
class ProviderRecord:
    id: int
    name: str
    phone: str
    email: str

    def table_name(self) -> str:
        return 'PROVIDER'

    def values_str(self) -> str:
        base_str = str(astuple(self))
        return base_str.replace(', None', ', Null')


@dataclass
class MaintenanceRecord:
    id: Optional[int]
    service_date: str
    work_type_id: int
    provider_id: int
    notes: str
    summary: str
    engine_hours: Optional[float]

    def table_name(self) -> str:
        return 'MAINTENANCE'

    def values_str(self) -> str:
        base_str = str(astuple(self))
        return base_str.replace('(None,', '(Null,').replace('None)', 'Null)')

@dataclass
class EngineHoursRecord:
    date: str
    hours: float

    def table_name(self) -> str:
        return 'ENGINE_HOURS'

    def values_str(self) -> str:
        base_str = str(astuple(self))
        return base_str.replace('(None,', '(Null,').replace('None)', 'Null)')


@dataclass
class MaintenanceRecordView:
    id: Optional[int]
    service_date: str
    notes: str
    summary: str
    engine_hours: Optional[float]
    action: str
    provider: str

    def info(self) -> str:
        if self.action == 'Project':
            return self.service_date + ' : ' + self.summary

        return self.service_date


MAINTENANCE_VIEW_BASE_QRY = """
        SELECT MAINTENANCE.id, service_date, notes, summary, engine_hours, description as action, name as provider FROM MAINTENANCE
        INNER JOIN provider on maintenance.provider_id = provider.id
        INNER JOIN UPKEEP_ACTION on MAINTENANCE.work_type_id = UPKEEP_ACTION.id
    """


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


def get_action_types(con: Connection) -> List[UpkeepActionRecord]:
    cur = con.cursor()

    cmd = 'select * from UPKEEP_ACTION order by description'
    res = cur.execute(cmd)
    recs = res.fetchall()

    return_val = []
    for r in recs:
        action = UpkeepActionRecord(*r)
        return_val.append(action)

    return return_val


def get_providers(con: Connection) -> List[ProviderRecord]:
    cur = con.cursor()

    cmd = 'select * from PROVIDER order by name'
    res = cur.execute(cmd)
    recs = res.fetchall()

    return_val = []
    for r in recs:
        action = ProviderRecord(*r)
        return_val.append(action)

    return return_val


def get_maintenance_views(con: Connection, action_desc: str) -> List[MaintenanceRecordView]:
    cur = con.cursor()

    cmd = (MAINTENANCE_VIEW_BASE_QRY +
           'where UPKEEP_ACTION.description = ' + "'" + action_desc + "'" + ' order by service_date desc')
    res = cur.execute(cmd)
    recs = res.fetchall()

    return_val = []
    for r in recs:
        action = MaintenanceRecordView(*r)
        return_val.append(action)

    return return_val


def select_log_summary(an_id: int, con: Connection) -> Optional[LogEntrySummary]:
    qry_str = LOG_ENTRY_SUMMARY_BASE_QRY + ' WHERE start_timestamp=' + str(an_id)
    cur = con.cursor()
    res = cur.execute(qry_str)
    a_rec = res.fetchone()

    return LogEntrySummary(*a_rec)


def select_log_entry(an_id: int, con: Connection) -> Optional[LogEntryRecord]:
    cur = con.cursor()
    res = cur.execute("select * from LOG_ENTRY WHERE start_timestamp=" + str(an_id))
    a_rec = res.fetchone()

    return LogEntryRecord(*a_rec)


def select_log_entry_and_hours(an_id: int, con: Connection) -> Optional[LogEntryAndHoursView]:
    cur = con.cursor()
    res = cur.execute("select * from LOG_ENTRY_HOURS_VIEW WHERE start_timestamp=" + str(an_id))
    a_rec = res.fetchone()

    return LogEntryAndHoursView(*a_rec)


def select_log_entry_stats(an_id: int, con: Connection) -> Optional[TrackStats]:
    cur = con.cursor()
    res = cur.execute("select * from TRACK_STATS WHERE start_timestamp=" + str(an_id))
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

    cur.execute("""
        CREATE VIEW LOG_ENTRY_HOURS_VIEW AS
        select L.*, E.hours from LOG_ENTRY as L 
        left outer join engine_hours as E
        on L.date = E.date """
                )

    con.close()

    create_maintenance_tables()
    create_engine_hours_table()

def create_engine_hours_table():
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()

    cur.execute("""
        BEGIN;

        CREATE TABLE ENGINE_HOURS (
            date TEXT PRIMARY KEY
            , hours REAL
            , UNIQUE(date)
        );

        COMMIT;
    """)

def create_maintenance_tables():
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()

    cur.execute("""
        BEGIN;
        
        CREATE TABLE UPKEEP_ACTION (
            id INTEGER PRIMARY KEY
          , description TEXT
        );
        
        insert into UPKEEP_ACTION values (1, 'Change water impeller');
        insert into UPKEEP_ACTION values (2, 'Change engine oil');
        insert into UPKEEP_ACTION values (3, 'Change engine fuel filters');
        insert into UPKEEP_ACTION values (4, 'Change engine air intake filter');
        insert into UPKEEP_ACTION values (5, 'Refuel');
        insert into UPKEEP_ACTION values (6, 'Touch up varnish');
        insert into UPKEEP_ACTION values (7, 'Bottom paint');
        insert into UPKEEP_ACTION values (8, 'Project');

        COMMIT;   
    """)

    cur.execute("""
        BEGIN;

        CREATE TABLE PROVIDER (
            id INTEGER PRIMARY KEY
            , name TEXT
            , phone TEXT
            , email TEXT
        );
        
        insert into PROVIDER values (1, 'Owner', '', '');
        insert into PROVIDER values (2, 'Isaac Stone', '360 775-5704', 'stonmobilemarine@gmail.com');
        
        COMMIT;        
    """)

    cur.execute("""
        BEGIN;
        
        CREATE TABLE MAINTENANCE (
            id INTEGER NOT NULL PRIMARY KEY
          , service_date TEXT NOT NULL
          , work_type_id INTEGER NOT NULL
          , provider_id INTEGER NOT NULL DEFAULT(1)
          , notes TEXT NOT NULL DEFAULT(' ')
          , summary TEXT NOT NULL DEFAULT(' ')
          , engine_hours REAL
          , FOREIGN KEY(work_type_id) REFERENCES UPKEEP_ACTION(id) 
            ON DELETE NO ACTION 
            ON UPDATE NO ACTION 
            FOREIGN KEY(provider_id) REFERENCES PROVIDER(id) 
            ON DELETE NO ACTION 
            ON UPDATE NO ACTION
        );
        
        COMMIT;                
     """)
