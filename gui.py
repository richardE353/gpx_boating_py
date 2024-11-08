import sqlite3
from datetime import timedelta

import PySimpleGUI as sg
import gpxpy
from gpxpy.gpx import GPXTrackSegment, GPX

import common as rt_args
from common import get_data_files
from database import get_entry_summaries, select_log_entry, select_log_entry_stats, create_database
from log_entry import create_log_entry, create_track_stats, persist
from track_stats import get_segment_stats


def process_args(values: dict, seg: GPXTrackSegment):
    fn = values['-SELECT_FILE-']
    title = values['-TITLE-']
    start_loc = values['-START-']
    end_loc = values['-END-']
    crew = values['-CREW-']
    notes = values['-NOTES-']

    stats = get_segment_stats(seg, 0.0)

    new_entry = create_log_entry(fn, seg, title, start_loc, end_loc, crew, notes)
    trk_stats = create_track_stats(new_entry, stats, 0.0)

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    persist(new_entry, trk_stats, con)
    con.close()


def extract_segments(fn):
    gpx: GPX = gpxpy.parse(open(rt_args.DATA_SOURCE_DIR + fn))
    all_segments: list[GPXTrackSegment] = []
    for t in gpx.tracks:
        for s in t.segments:
            if s.points[0].time > s.points[1].time:
                s.points.reverse()

            # skip segments w/ distance < 10m, or shorter than 10 minutes
            if s.length_2d() > 10.0 and s.get_duration() > 600:
                all_segments.append(s)

    return all_segments


def nullable_float_as_str(fmt: str, v: float) -> str:
    if v == None:
        return "unknown"
    else:
        return str.format(fmt, v)


def display_log_entry():
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    summaries = get_entry_summaries(con)

    entries_dict = {}
    for s in summaries:
        entries_dict[s.summary_string()] = s

    entry_strings = list(sorted(entries_dict.keys()))

    layout = [
        [sg.Text("Log Entries:"), sg.Combo(entry_strings, key='-LE_SELECT_ENTRY-', size=(60, 1), enable_events=True)],
        [sg.Text("Title:"), sg.InputText(key='-LE_TITLE-')],
        [sg.Text("Starting Loc:"), sg.InputText(key='-LE_START-'), sg.Text("Ending Loc:"),
         sg.InputText(key='-LE_END-')],
        [sg.Text("Moving Time:"), sg.Text(key='-LE_MTIME-'), sg.Text("Moving distance: (nm):"),
         sg.Text(key='-LE_MDIST-')],
        [sg.Text("Avg SOG (kts):"), sg.Text(key='-LE_ASOG-'), sg.Text("Max SOG (kts):"),
         sg.Text(key='-LE_MSOG-')],
        [sg.Text("Avg STW (kts):"), sg.Text(key='-LE_ASTW-'), sg.Text("Max STW (kts):"),
         sg.Text(key='-LE_MSTW-')],
        [sg.Text("Avg True Wind (kts):"), sg.Text(key='-LE_ATW-'), sg.Text("Max True Wind (kts):"),
         sg.Text(key='-LE_MTW-')],
        [sg.Text("Avg Wind Speed (kts):"), sg.Text(key='-LE_AWS-'), sg.Text("Avg Wind Dir:"),
         sg.Text(key='-LE_AWD-')],
        [sg.Text("Crew:"), sg.InputText(key='-LE_CREW-')],
        [sg.Text("Notes:"), sg.Multiline(key='-LE_NOTES-', size=(70, 4))],
        [sg.Button('Exit', key='-LE_EXIT-')]]

    # Create the Window
    window = sg.Window('Log Entry Info', layout, resizable=True, font='default 12')

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == '-LE_EXIT-':
            break

        if event == '-LE_SELECT_ENTRY-':
            selected_id = entries_dict[values['-LE_SELECT_ENTRY-']].start_timestamp
            selected_entry = select_log_entry(selected_id, con)
            selected_stats = select_log_entry_stats(selected_id, con)

            window['-LE_TITLE-'].update(value=selected_entry.title)
            window['-LE_START-'].update(value=selected_entry.start_loc)
            window['-LE_END-'].update(value=selected_entry.end_loc)
            window['-LE_MTIME-'].update(value=timedelta(seconds=int(selected_stats.moving_seconds)))
            window['-LE_MDIST-'].update(value=str.format('{:.2f}', selected_stats.moving_distance))

            window['-LE_ASOG-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.sog_avg))
            window['-LE_MSOG-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.sog_max))

            window['-LE_ASTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.stw_avg))
            window['-LE_MSTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.stw_max))

            window['-LE_ATW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.tws_avg))
            window['-LE_MTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.tws_max))

            window['-LE_AWS-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.avg_wind_spd))

            wind_dir = nullable_float_as_str('{:.1f}', selected_stats.avg_wind_dir)
            if wind_dir != 'unknown':
                wind_dir = wind_dir + '°'
            window['-LE_AWD-'].update(value=wind_dir)

            window['-LE_CREW-'].update(value=selected_entry.crew)
            window['-LE_NOTES-'].update(value=selected_entry.notes)
    #            window['-LE_NOTES-'].append(selected_entry.notes)

    con.close()
    window.close()


def process_gpx_file() -> bool:
    return_val = False
    segments_dict = {}

    layout = [[sg.Text("File:"), sg.Combo(get_data_files(), key='-SELECT_FILE-', enable_events=True)],
              [sg.Text("Segments:"), sg.Combo([], key='-SELECT_SEG-', size=(60, 1))],
              [sg.Text("Title:"), sg.InputText(key='-TITLE-')],
              [sg.Text("Starting Loc:"), sg.InputText(key='-START-')],
              [sg.Text("Ending Loc:"), sg.InputText(key='-END-')],
              [sg.Text("Crew:"), sg.InputText(key='-CREW-')],
              [sg.Text("Notes:"), sg.Multiline(key='-NOTES-', size=(70, 4))],
              [sg.Button('Save'), sg.Button('Exit', key='-EXIT-'), sg.Text('', key='-SAVE_STATUS-')]]

    # Create the Window
    window = sg.Window('GPX File Import', layout, resizable=True, font='default 12')

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == '-EXIT-':
            break

        if event == '-SELECT_FILE-':
            segments_dict = {}
            for s in extract_segments(values['-SELECT_FILE-']):
                segments_dict[str(s.points[0].time)] = s

            seg_strings = list(sorted(segments_dict.keys()))
            window['-SELECT_SEG-'].update(values=seg_strings, set_to_index=0)
            window['-TITLE-'].update(value='')
            window['-START-'].update(value='')
            window['-END-'].update(value='')
            window['-CREW-'].update(value='')
            window['-NOTES-'].update(value='')
            window['-SAVE_STATUS-'].update(value='')

        if event == 'Save':
            selected_seg = segments_dict[values['-SELECT_SEG-']]
            process_args(values, selected_seg)
            window['-SAVE_STATUS-'].update(value='Processed ' + values['-SELECT_SEG-'])
            return_val = True

    window.close()

    return return_val


def main_window():
    layout = [[sg.Text('GPX File processing and Review App')],
              [sg.Button('New Entry', key='-NEW_TRACK-'), sg.Button('View Entries', key='-VIEW_ENTRIES-')],
              [sg.Button('Exit')]]

    window = sg.Window('Boat Log', layout, resizable=True, font='default 12')

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == '-NEW_TRACK-':
            process_gpx_file()

        if event == '-VIEW_ENTRIES-':
            display_log_entry()

    window.close()


def initialize_and_startup():
    from pathlib import Path

    my_file = Path(rt_args.DATABASE_LOC)
    if not my_file.is_file():
        create_database()

    main_window()


if __name__ == '__main__':
    initialize_and_startup()
