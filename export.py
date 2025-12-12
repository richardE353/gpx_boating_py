import common as rt_args
import sqlite3

from openpyxl import Workbook

from database import MAINTENANCE_EXPORT_QRY


def get_maintenance_recs() -> list:
    con = sqlite3.connect(rt_args.DATABASE_LOC)
    cur = con.cursor()
    res = cur.execute(MAINTENANCE_EXPORT_QRY)

    recs = res.fetchall()
    con.close()

    return recs


def export_maintenance_log():
    wb = Workbook()
    ws = wb.active

    headers = ["Service Date", "Engine Hours", "Action", "Provider", "Summary", "Notes"]
    ws.append(headers)

    maintenance_recs = get_maintenance_recs()
    for row in maintenance_recs:
        ws.append(row)


    wb.save('maintenanceLog.xlsx')
    print('\t\tCreated maintenanceLog.xlsx')


if __name__ == '__main__':
    export_maintenance_log()