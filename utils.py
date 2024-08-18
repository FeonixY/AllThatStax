from openpyxl import load_workbook

def read_xlsx_excel(sheet_file_name, read_sheet_name):
    workbook = load_workbook(sheet_file_name)
    sheet = workbook[read_sheet_name]
    data = []
    for row in sheet.rows:
        data_row = []
        for cell in row:
            data_row.append(cell.value)
        data.append(data_row)
    return data

def sort_key(item):
    cmc = item[1]
    card_type = card_type_order[item[2]]
    card_english_name = item[3]
    return (cmc, card_type, card_english_name)

card_type_order = {
    "生物": 1,
    "神器": 2,
    "结界": 3,
    "其他": 4
}