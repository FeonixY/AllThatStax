import json
from run_latex import run_latex
from genarate_latex_text import genarate_latex_text
from get_cards_information import get_cards_information

with open("config.json", "r", encoding = "utf-8") as file:
    data = json.load(file)

image_folder_name = data["image_folder_name"]
sheet_file_name = data["sheet_file_name"]
sheet_name = data["sheet_name"]
multiface_sheet_name = data["multiface_sheet_name"]
card_list_name = data["card_list_name"]
latex_text_name = data["latex_text_name"]
latex_file_name = data["latex_file_name"]
stax_type_dict = data["stax_type"]

#get_cards_information(image_folder_name, sheet_file_name, sheet_name, multiface_sheet_name, card_list_name, stax_type_dict,
                      #from_scratch = True)
genarate_latex_text(sheet_file_name, sheet_name, multiface_sheet_name, latex_text_name)
run_latex(latex_file_name, latex_text_name)
