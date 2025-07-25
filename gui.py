from FreeSimpleGUI import TabGroup

from database import get_entry_summaries, create_database, LogEntryRecord, get_maintenance_views
from gui_track import create_track_tab, event_loop_for_process_gpx_file, create_process_file_window, \
    update_track_tab_entries

from gui_upkeep import *

entries_in_db = {}


def process_gpx_file() -> Optional[LogEntryRecord]:
    DEFAULT_YEAR = '2025'
    selected_year = DEFAULT_YEAR

    def match_year(candidate) -> bool:
        return selected_year in candidate

    return_val = None
    segments_dict = {}

    window = create_process_file_window(DEFAULT_YEAR, match_year)

    # Event Loop to process "events" and get the "values" of the inputs
    return_val = event_loop_for_process_gpx_file(match_year, return_val, segments_dict, window)

    window.close()

    return return_val


def create_maintenance_record() -> Optional[MaintenanceRecord]:
    return_val = None

    window = create_maintenance_window()

    # Event Loop to process "events" and get the "values" of the inputs
    return_val = event_loop_for_new_maintenance_rec(return_val, window)

    window.close()

    return return_val


def main_window():
    global entries_in_db

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    summaries = get_entry_summaries(con)

    for s in summaries:
        entries_in_db[s.summary_string()] = s

    layout = [[TabGroup(enable_events=True, layout=[[create_track_tab(entries_in_db), create_maintenance_tab(con)]])],
              [sg.Button('Exit')],
              ]

    window = sg.Window('Boat Log', layout, resizable=False, font='default 12', size=(676, 740))

    con = sqlite3.connect(rt_args.DATABASE_LOC)

    # Event Loop to process "events" and get the "values" of the inputs
    main_event_loop(con, window)


def main_event_loop(con, window):
    global entries_in_db
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == '-TT_NEW-':
            new_rec = process_gpx_file()

            if new_rec:
                entries_in_db = create_entry_summary_dict(con)
                new_selected_key = get_new_entries_key(entries_in_db, new_rec)

                window['-TT_SELECT_ENTRY-'].update(value=new_selected_key)
                values['-TT_SELECT_ENTRY-'] = new_selected_key

                update_track_tab_entries(window, entries_in_db, values, con)

        if event == '-TT_SELECT_ENTRY-':
            entries_in_db = create_entry_summary_dict(con)
            update_track_tab_entries(window, entries_in_db, values, con)

        if event == '-MT_SELECT_ACTION-':
            view_recs = get_maintenance_views(con, values['-MT_SELECT_ACTION-'])
            update_upkeep_tab_entries(window, view_recs, values, con)

        if event == '-MT_SVC_DATE-':
            view_recs = get_maintenance_views(con, values['-MT_SELECT_ACTION-'])
            info_to_match = values['-MT_SVC_DATE-']
            recs = list(filter(lambda r: r.info() == info_to_match, view_recs))

            if len(recs) > 0:
                update_upkeep_tab_fields(recs[0], window)

        if event == '-MT_NEW-':
            new_rec = create_maintenance_record()

            if new_rec:
                # need to update records and stuff
                window['-MT_SELECT_ACTION-'].update(value=get_action(new_rec.work_type_id).description)
                window['-MT_SVC_DATE-'].update(value=new_rec.service_date)
                window['-MT_SUMMARY-'].update(value=new_rec.summary)
                window['-MT_PROVIDER-'].update(value=get_provider(new_rec.provider_id).name)
                window['-MT_EHOURS-'].update(value=new_rec.engine_hours)
                window['-MT_NOTES-'].update(value=new_rec.notes)

    window.close()


def get_new_entries_key(e_dict, new_rec):
    key_start = new_rec.date + ': ' + new_rec.title
    new_selected_key = None
    for item in e_dict.keys():
        if item.startswith(key_start):
            new_selected_key = item

    return new_selected_key


def create_entry_summary_dict(con):
    summaries = get_entry_summaries(con)
    entries = {}
    for s in summaries:
        entries[s.summary_string()] = s
    summaries = get_entry_summaries(con)

    entries = {}
    for s in summaries:
        entries[s.summary_string()] = s
    return entries


def initialize_and_startup():
    from pathlib import Path

    my_file = Path(rt_args.DATABASE_LOC)
    if not my_file.is_file():
        create_database()

    main_window()


if __name__ == '__main__':
    initialize_and_startup()
