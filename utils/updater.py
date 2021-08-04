import argparse
import json
import openpyxl
import logging
import re
import requests

def download_gsheet(sheet_id, outfile):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    logging.info(f"Downloading from {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(outfile, 'wb') as file:
            file.write(response.content)
            file.close()


def get_sheet_column_map(sheet, matches):
    "Return a map of column names to index positions"
    map = {}
    # header row
    for row in sheet.iter_rows(max_row=1):
        for index, cell in enumerate(row): 
            cell_value = str(cell.value)
            if (cell_value):
                for regex in matches:
                    if re.match(regex, cell_value, re.IGNORECASE):
                        # add to map
                        map_value = {'index':index, 'regex':regex}
                        map[cell_value] = map_value
    logging.debug(map)
    return map

def get_row_cell_value(row, map, column_name):
    index = map[column_name].get('index')
    if index is not None:
        return row[index].value

def parse_constants(sheet_name):
    pass
    return

def parse_version(sheet):
    logging.info(f"Parsing version {sheet}")
    version = {}
    # get column map
    column_map = get_sheet_column_map(sheet, ["id","name","units","value_str","value_num","uncertainty_str","uncertainty_n","ellipsis","exponent"])
    # parse data
    for row in sheet.iter_rows(min_row=2):
        id = get_row_cell_value(row, column_map, "id")
        if id:
            data = {}
            for column in column_map:
                data[column] = get_row_cell_value(row, column_map, column)
            version[id] = data
    return version

def parse_workbook(filename):
    """Parses an Excel file and populates the constants model"""
    constants = {}
    logging.debug(f"workbook={filename}")
    wb = openpyxl.load_workbook(filename, data_only=True)
    for name in wb.sheetnames:
        logging.debug(f"sheet_name={name}")
        # parse versions
        regex = "v\d{4}" # match sheet name
        if re.match(regex, name, re.IGNORECASE):
            # process version
            sheet = wb[name]
            version_id = name[1:]
            sheet_version = parse_version(sheet)
            # add version to constants
            for (constant_id, entry) in sheet_version.items():
                # add constant if first entry
                if constant_id not in constants:
                    constants[constant_id] = {}
                constant = constants.get(constant_id)
                # add this version to the constant
                constant_version = {}
                constant[version_id] = constant_version
                # populate version data
                constant_version['name_en'] = entry.get('name')
                if entry.get('units'):
                    constant_version['units'] = entry.get('units')
                constant_version['value'] = entry.get('value_str')
                constant_version['uncertainty'] = entry.get('uncertainty_str')
                if entry.get('exponent'):
                    constant_version['exponent'] = entry.get('exponent')
                if entry.get('ellipsis'):
                    constant_version['ellipsis'] = True
    return constants

def main():
    sheet_filename = "codata_units.xlsx"
    download_gsheet("1m5Hm3uRsgDVXIarp7-AQqt2mYSvdk0Bvzgx3bvdMT6s", sheet_filename)
    constants = parse_workbook(sheet_filename)
    with open('codata_constants.json', 'w') as f:
        json.dump(constants, f, indent=4)

if __name__ == '__main__':
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("-ll","--loglevel", help="Python logging level", default="INFO")
    args = parser.parse_args()
    print(args)

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    if args.loglevel:
        logging.getLogger().setLevel(args.loglevel.upper())

    logging.info(args)

    main()
