import json
from genarate_latex import genarate_latex
from get_cards_information import get_cards_information

with open("config.json", "r") as file:
    data = json.load(file)

sheet_file_name = data["sheet_file_name"]
sheet_name = data["sheet_name"]
multiface_sheet_name = data["multiface_sheet_name"]
list_name = data["list_name"]
latex_name = data["latex_name"]
stax_type_dict = data["stax_type"]

get_cards_information(sheet_file_name, sheet_name, multiface_sheet_name, list_name, stax_type_dict)
genarate_latex(sheet_file_name, sheet_name, multiface_sheet_name, latex_name)
