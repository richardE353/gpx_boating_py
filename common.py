import os

DATA_SOURCE_DIR = './2024_data/'
OUTPUT_DIR = './output/'
DATABASE_LOC = 'boat_log.db'

def get_data_files() :
    scanner = os.scandir(DATA_SOURCE_DIR)
    data_files = sorted([f.name for f in scanner if '.gpx' in f.name])
    scanner.close()

    return data_files

def select_data_file() -> str:
    data_files = get_data_files()

    print('Available .gpx files:')
    for i in range(0, len(data_files)):
        print('\t{}: {}'.format(i, data_files[i]))

    index = input('Select track file number: ')
    return data_files[int(index)]