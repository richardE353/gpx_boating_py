import sqlite3
from datetime import timedelta
from typing import Optional

import PySimpleGUI as sg
import gpxpy
from PIL.Image import Resampling
from PySimpleGUI import Tab, TabGroup
from gpxpy.gpx import GPXTrackSegment, GPX

import common as rt_args
from common import get_data_files
from database import get_entry_summaries, select_log_entry, select_log_entry_stats, create_database, LogEntryRecord
from images import load_image, segment_image
from log_entry import create_log_entry, create_track_stats, persist
from track_stats import get_segment_stats

IMAGE_SIZE = (440, 440)


def process_args(values: dict, seg: GPXTrackSegment) -> Optional[LogEntryRecord]:
    file_name = values['-SELECT_FILE-']
    title = values['-TITLE-']
    start_loc = values['-START-']
    end_loc = values['-END-']
    crew = values['-CREW-']
    notes = values['-NOTES-']

    return_val = persist_track_data(crew, end_loc, file_name, notes, seg, start_loc, title)

    create_and_save_image(file_name, seg)

    return return_val


def create_and_save_image(fn, seg):
    img = segment_image(seg)
    image_name = fn.replace('.gpx', '.png')
    img.save(rt_args.get_file_loc(image_name))

    return img


def persist_track_data(crew, end_loc, file_name, notes, seg, start_loc, title) -> Optional[LogEntryRecord]:
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    return_val = None
    try:
        stats = get_segment_stats(seg, 0.0)

        new_entry = create_log_entry(file_name, seg, title, start_loc, end_loc, crew, notes)
        trk_stats = create_track_stats(new_entry, stats, 0.0)

        persist(new_entry, trk_stats, con)
        return_val = new_entry
    finally:
        con.close()
    return return_val


def extract_segments(fn):
    gpx: GPX = gpxpy.parse(open(rt_args.get_file_loc(fn)))
    all_segments: list[GPXTrackSegment] = []
    for t in gpx.tracks:
        for s in t.segments:
            if s.points[0].time > s.points[1].time:
                s.points.reverse()

            # skip segments w/ distance < 10m, or shorter than 10 minutes
            if s.length_2d() > 10.0 and s.get_duration() > 600:
                all_segments.append(s)

    return all_segments


def nullable_float_as_str(fmt: str, v: float, units='') -> str:
    if v is None:
        return "unknown"
    else:
        return str.format(fmt, v) + ' ' + units


def update_track_tab_entries(window, entries_dict, values, con):
    selected_id = entries_dict[values['-TT_SELECT_ENTRY-']].start_timestamp

    selected_entry = select_log_entry(selected_id, con)
    selected_stats = select_log_entry_stats(selected_id, con)

    window['-TT_TITLE-'].update(value=selected_entry.title)
    window['-TT_START-'].update(value=selected_entry.start_loc)
    window['-TT_END-'].update(value=selected_entry.end_loc)
    window['-TT_MTIME-'].update(value=timedelta(seconds=int(selected_stats.moving_seconds)))
    window['-TT_MDIST-'].update(value=str.format('{:.2f}', selected_stats.moving_distance) + ' nm')

    window['-TT_ASOG-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.sog_avg, 'kts'))
    window['-TT_MSOG-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.sog_max, 'kts'))

    window['-TT_ASTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.stw_avg, 'kts'))
    window['-TT_MSTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.stw_max, 'kts'))

    window['-TT_ATW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.tws_avg, 'kts'))
    window['-TT_MTW-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.tws_max, 'kts'))

    window['-TT_AWS-'].update(value=nullable_float_as_str('{:.1f}', selected_stats.avg_wind_spd, 'kts'))

    wind_dir = nullable_float_as_str('{:.1f}', selected_stats.avg_wind_dir)
    if wind_dir != 'unknown':
        wind_dir = wind_dir + '°'
    window['-TT_AWD-'].update(value=wind_dir)

    window['-TT_CREW-'].update(value=selected_entry.crew)
    window['-TT_NOTES-'].update(value=selected_entry.notes)

    image = load_image(selected_entry.path_to_image_file())
    if not image:
        file_name = selected_entry.path_to_gpx_file
        selected_seg = None
        segs = extract_segments(file_name)

        desired_timestamp = selected_entry.start_timestamp
        matches = list(filter(lambda s: int(s.get_time_bounds().start_time.timestamp()) == desired_timestamp, segs))

        if matches:
            image = create_and_save_image(file_name, matches[0])

    if image:
        image = image.resize(IMAGE_SIZE, resample=Resampling.LANCZOS)

        import io
        bio = io.BytesIO()
        image.save(bio, format="PNG")

        window["-TT_TRACK_IMAGE-"].update(data=bio.getvalue())


def process_gpx_file() -> Optional[LogEntryRecord]:
    return_val = None
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
            new_rec = process_args(values, selected_seg)

            if new_rec:
                window['-SAVE_STATUS-'].update(value='Processed ' + values['-SELECT_SEG-'])
                return_val = new_rec
            else:
                window['-SAVE_STATUS-'].update(value='Failed to process file.  No action taken')

    window.close()

    return return_val


def create_track_tab(entries_dict) -> Tab:
    entry_strings = list(sorted(entries_dict.keys()))

    stats_col = sg.Column(vertical_alignment='top', layout=[[sg.Text("Moving Time:"), sg.Text(key='-TT_MTIME-')],
                                                            [sg.Text("Moving distance:"),
                                                             sg.Text(key='-TT_MDIST-')],
                                                            [sg.Text("Avg SOG:"), sg.Text(key='-TT_ASOG-')],
                                                            [sg.Text("Max SOG:"), sg.Text(key='-TT_MSOG-')],
                                                            [sg.Text("Avg STW:"), sg.Text(key='-TT_ASTW-')],
                                                            [sg.Text("Max STW:"), sg.Text(key='-TT_MSTW-')],
                                                            [sg.Text("Avg True Wind:"), sg.Text(key='-TT_ATW-')],
                                                            [sg.Text("Max True Wind:"), sg.Text(key='-TT_MTW-')],
                                                            [sg.Text("Avg Wind Speed:"), sg.Text(key='-TT_AWS-')],
                                                            [sg.Text("Avg Wind Dir:"), sg.Text(key='-TT_AWD-')]])
    t_layout = [
        [sg.Text("Log Entries:"), sg.Combo(entry_strings, key='-TT_SELECT_ENTRY-', size=(60, 1), enable_events=True),
         sg.Button('New', key='-TT_NEW-')],
        [sg.Text("Title:"), sg.InputText(key='-TT_TITLE-')],
        [sg.Text("Starting Loc:"), sg.InputText(size=(20, 1), key='-TT_START-'), sg.Text("Ending Loc:"),
         sg.InputText(size=(20, 1), key='-TT_END-')],
        [sg.Text("Crew:"), sg.InputText(key='-TT_CREW-')],
        [sg.Text("Notes:"), sg.Multiline(key='-TT_NOTES-', size=(70, 4))],
        [stats_col, sg.Image(key="-TT_TRACK_IMAGE-", size=IMAGE_SIZE)]]

    return Tab(title='Tracks', layout=t_layout)


def create_maintenance_tab() -> Tab:
    return Tab(title='Maintenance', layout=[[sg.Text('Visualize work log')]])


def main_window():
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    summaries = get_entry_summaries(con)

    entries_dict = {}
    for s in summaries:
        entries_dict[s.summary_string()] = s

    layout = [[TabGroup(enable_events=True, layout=[[create_track_tab(entries_dict), create_maintenance_tab()]])],
              [sg.Button('Exit')],
              ]

    window = sg.Window('Boat Log', layout, resizable=False, font='default 12', size=(676, 700))

    con = sqlite3.connect(rt_args.DATABASE_LOC)

    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == '-TT_NEW-':
            new_rec = process_gpx_file()

            if new_rec:
                entries_dict = create_entry_summary_dict(con)
                new_selected_key = get_new_entries_key(entries_dict, new_rec)

                window['-TT_SELECT_ENTRY-'].update(value=new_selected_key)
                values['-TT_SELECT_ENTRY-'] = new_selected_key

                update_track_tab_entries(window, entries_dict, values, con)

        if event == '-TT_SELECT_ENTRY-':
            entries_dict = create_entry_summary_dict(con)
            update_track_tab_entries(window, entries_dict, values, con)

    window.close()


def get_new_entries_key(entries_dict, new_rec):
    key_start = new_rec.date + ': ' + new_rec.title
    new_selected_key = None
    for item in entries_dict.keys():
        if item.startswith(key_start):
            new_selected_key = item

    return new_selected_key


def create_entry_summary_dict(con):
    summaries = get_entry_summaries(con)
    entries_dict = {}
    for s in summaries:
        entries_dict[s.summary_string()] = s
    summaries = get_entry_summaries(con)
    entries_dict = {}
    for s in summaries:
        entries_dict[s.summary_string()] = s
    return entries_dict


def initialize_and_startup():
    from pathlib import Path

    my_file = Path(rt_args.DATABASE_LOC)
    if not my_file.is_file():
        create_database()

    main_window()


if __name__ == '__main__':
    initialize_and_startup()
