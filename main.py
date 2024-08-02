from get_cards_information import get_cards_information
from genarate_latex import genarate_latex
import json

with open("config.json", 'r') as file:
    data = json.load(file)

sheet_name = data["sheet_name"]
multiface_sheet_name = data["multiface_sheet_name"]
list_name = data["list_name"]
latex_name = data["latex_name"]

#get_cards_information(sheet_name, multiface_sheet_name, list_name)
genarate_latex(sheet_name, multiface_sheet_name, latex_name)
