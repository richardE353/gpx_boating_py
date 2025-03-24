import common as rt_args
import sqlite3
from typing import Optional

import FreeSimpleGUI as sg
from FreeSimpleGUI import Tab

from database import get_action_types, get_providers, MaintenanceRecord, add_to_database

actions_dict: dict = {}
providers_dict: dict = {}


def create_maintenance_tab(con) -> Tab:
    global actions_dict
    actions_dict = {a.description: a for a in get_action_types(con)}

    global providers_dict
    providers_dict = {p.name: p for p in get_providers(con)}

    t_layout = [
        [sg.Text("Maintenance Type:"),
         sg.Combo(list(actions_dict.keys()), key='-MT_SELECT_ACTION-', size=(55, 1), enable_events=True),
         sg.Button('New', key='-MT_NEW-')],
        [sg.Text("Service Date:"),
         sg.Combo([], key='-MT_SVC_DATE-', size=(59, 1), enable_events=True)],
        [sg.Text("Summary:"), sg.InputText(key='-MT_SUMMARY-', size=(63, 1))],
        [sg.Text("Provider:"),
         sg.InputText(key='-MT_PROVIDER-', size=(50, 1)), ],
        [sg.Text("Engine Hours:"), sg.InputText(key='-MT_EHOURS-', size=(25, 1))],
        [sg.Text("Notes:"), sg.Multiline(key='-MT_NOTES-', size=(70, 10))]]

    return Tab(title='Maintenance', layout=t_layout)


def create_maintenance_window():
    global actions_dict
    global providers_dict

    actions = list(actions_dict.keys())
    providers = list(providers_dict.keys())

    layout = [
        [sg.Text("Maintenance Type:"),
         sg.Combo(actions, key='-MW_SELECT_ACTION-', default_value=actions[0], size=(25, 1), enable_events=True)],
        [sg.Text("Summary:"), sg.InputText(key='-MW_SUMMARY-', size=(68, 10))],
        [sg.Text("Service Date:"),
         sg.InputText([], key='-MW_SELECT_SVC_DATE-', size=(16, 1)),
         sg.Text("Provider:"),
         sg.Combo(providers, key='-MW_SELECT_PROVIDER-', default_value='Owner', size=(38, 1))],
        [sg.Text("Engine Hours:"), sg.InputText(key='-MW_EHOURS-', size=(15, 1))],
        [sg.Text("Notes:"), sg.Multiline(key='-MW_NOTES-', size=(70, 10))],
        [sg.Button('Save'), sg.Button('Exit', key='-EXIT-'), sg.Text('', key='-SAVE_STATUS-')]]

    # Create the Window
    window = sg.Window('Maintenance Entry', layout, resizable=True, font='default 12')
    return window


def process_args(values: dict) -> Optional[MaintenanceRecord]:
    global actions_dict
    global providers_dict

    action = actions_dict[values['-MW_SELECT_ACTION-']]
    provider = providers_dict[values['-MW_SELECT_PROVIDER-']]

    svc_date = values['-MW_SELECT_SVC_DATE-']
    engine_hours = values['-MW_EHOURS-']
    notes = values['-MW_NOTES-']
    summary = values['-MW_SUMMARY-']

    new_entry = MaintenanceRecord(None, svc_date, action.id, provider.id, notes, summary, engine_hours)

    con = sqlite3.connect(rt_args.DATABASE_LOC)
    return_val = None
    try:
        add_to_database(new_entry.table_name(), new_entry.values_str(), con)
        return_val = new_entry
    finally:
        con.close()

    return return_val


def event_loop_for_new_maintenance_rec(return_val, window):
    while True:
        event, values = window.read()

        # if user closes window or clicks cancel
        if event == sg.WIN_CLOSED or event == '-EXIT-':
            break

        if event == 'Save':
            new_rec = process_args(values)

            if new_rec:
                window['-SAVE_STATUS-'].update(value='Added rec type: ' + values['-MW_SELECT_ACTION-'])
                return_val = new_rec
            else:
                window['-SAVE_STATUS-'].update(value='Failed to add record.  No action taken')
    return return_val


def update_upkeep_tab_entries(window, maintenance_recs, values, con):
    window['-MT_SVC_DATE-'].update(values=list(map(lambda mr: mr.info(), maintenance_recs)))

    if len(maintenance_recs) == 1:
        a_rec = maintenance_recs[0]
        update_upkeep_tab_fields(a_rec, window)
        window['-MT_SVC_DATE-'].update(value=a_rec.info())
    else:
        window['-MT_SUMMARY-'].update(value='')
        window['-MT_PROVIDER-'].update(value='')
        window['-MT_EHOURS-'].update(value=None)
        window['-MT_NOTES-'].update(value='')


def update_upkeep_tab_fields(a_rec, window):
    window['-MT_SUMMARY-'].update(value=a_rec.summary)
    window['-MT_PROVIDER-'].update(value=a_rec.provider)
    window['-MT_EHOURS-'].update(value=a_rec.engine_hours)
    window['-MT_NOTES-'].update(value=a_rec.notes)
