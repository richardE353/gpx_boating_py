import os

DATA_SOURCE_DIR = './yd_data/'
OUTPUT_DIR = './output/'

def select_data_file() -> str:
    scanner = os.scandir(DATA_SOURCE_DIR)
    data_files = sorted([f.name for f in scanner if '.gpx' in f.name])
    scanner.close()

    print('Available .gpx files:')
    for i in range(0, len(data_files)):
        print('\t{}: {}'.format(i, data_files[i]))

    index = input('Select track file number: ')
    return data_files[int(index)]