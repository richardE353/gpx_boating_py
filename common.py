import os

DATA_DIR = './data/'
GPX_FILES_DIR = DATA_DIR + os.sep + 'gpx_files'
TRACK_IMAGES_DIR = DATA_DIR + os.sep + 'track_images'

OUTPUT_DIR = './output/'
DATABASE_LOC = 'boat_log.db'

def get_data_files() :
    scanner = os.scandir(GPX_FILES_DIR)
    data_files = sorted([f.name for f in scanner if '.gpx' in f.name])
    scanner.close()

    return data_files

def get_file_loc(fn: str) -> str:
    if fn.endswith('.gpx'):
        return GPX_FILES_DIR + os.sep + fn
    else:
        return TRACK_IMAGES_DIR + os.sep + fn

def select_data_file() -> str:
    data_files = get_data_files()

    print('Available .gpx files:')
    for i in range(0, len(data_files)):
        print('\t{}: {}'.format(i, data_files[i]))

    index = input('Select track file number: ')
    return data_files[int(index)]