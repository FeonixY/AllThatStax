from utils import read_xlsx_excel, sort_key

"""
单面牌表格结构：
card_english_name, card_chinese_name, card_image_name, mana_cost, card_type, card_description, stax_type, is_rl, 
legalities["standard"], legalities["alchemy"], legalities["pioneer"], legalities["explorer"],
legalities["modern"], legalities["historic"], legalities["legacy"], legalities["pauper"],
legalities["vintage"], legalities["timeless"], legalities["commander"], legalities["duel"],
cmc, sort_card_type

双面牌表格结构：
front_card_english_name, front_card_chinese_name, front_card_image_name, front_mana_cost, front_card_type, front_card_description,
back_card_english_name, back_card_chinese_name, back_card_image_name, back_mana_cost, back_card_type, back_card_description,
stax_type, is_rl, 
legalities["standard"], legalities["alchemy"], legalities["pioneer"], legalities["explorer"],
legalities["modern"], legalities["historic"], legalities["legacy"], legalities["pauper"],
legalities["vintage"], legalities["timeless"], legalities["commander"], legalities["duel"],
cmc, sort_card_type
"""

def genarate_latex(sheet_file_name, sheet_name, multiface_sheet_name, latex_name):
    latex_datas = []

    # 处理单面牌数据
    data = read_xlsx_excel(sheet_file_name, sheet_name)
    data = data[1:]
    for data_row in data:
        card = f"\\card\n" \
            f"{{\n" \
            f"\tcard_english_name = {data_row[0]},\n" \
            f"\tcard_chinese_name = {data_row[1]},\n" \
            f"\tcard_image = {data_row[2]},\n" \
            f"\tmana_cost = {(str)(data_row[3]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tcard_type = {data_row[4]},\n" \
            f"\tdescription = {(str)(data_row[5]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tstax_type = {data_row[6]},\n" \
            f"\tis_in_restricted_list = {data_row[7]},\n" \
            f"\tlegality / standard = {data_row[8]},\n" \
            f"\tlegality / alchemy = {data_row[9]},\n" \
            f"\tlegality / pioneer = {data_row[10]},\n" \
            f"\tlegality / explorer = {data_row[11]},\n" \
            f"\tlegality / modern = {data_row[12]},\n" \
            f"\tlegality / historic = {data_row[13]},\n" \
            f"\tlegality / legacy = {data_row[14]},\n" \
            f"\tlegality / pauper = {data_row[15]},\n" \
            f"\tlegality / vintage = {data_row[16]},\n" \
            f"\tlegality / timeless = {data_row[17]},\n" \
            f"\tlegality / commander = {data_row[18]},\n" \
            f"\tlegality / duel_commander = {data_row[19]}\n" \
            f"}}\n\n"
        cmc = int(data_row[20])
        sort_card_type = data_row[21]
        card_english_name = data_row[0]
        latex_datas.append([card, cmc, sort_card_type, card_english_name])

    # 处理双面牌数据
    multiface_data = read_xlsx_excel(sheet_file_name, multiface_sheet_name)
    multiface_data = multiface_data[1:]
    for multiface_data_row in multiface_data:
        multiface_card = f"\\mfcard\n" \
            f"{{\n" \
            f"\tfront_card_enlish_name = {multiface_data_row[0]},\n" \
            f"\tfront_card_chinese_name = {multiface_data_row[1]},\n" \
            f"\tfront_card_image = {multiface_data_row[2]},\n" \
            f"\tfront_mana_cost = {(str)(multiface_data_row[3]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tfront_card_type = {multiface_data_row[4]},\n" \
            f"\tfront_description = {(str)(multiface_data_row[5]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tback_card_english_name = {multiface_data_row[6]},\n" \
            f"\tback_card_chinese_name = {multiface_data_row[7]},\n" \
            f"\tback_card_image = {multiface_data_row[8]},\n" \
            f"\tback_mana_cost = {(str)(multiface_data_row[9]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tback_card_type = {multiface_data_row[10]},\n" \
            f"\tback_description = {(str)(multiface_data_row[11]).replace("{", "\\{").replace("}", "\\}")},\n" \
            f"\tstax_type = {multiface_data_row[12]},\n" \
            f"\tis_in_restricted_list = {multiface_data_row[13]},\n" \
            f"\tlegality / standard = {multiface_data_row[14]},\n" \
            f"\tlegality / alchemy = {multiface_data_row[15]},\n" \
            f"\tlegality / pioneer = {multiface_data_row[16]},\n" \
            f"\tlegality / explorer = {multiface_data_row[17]},\n" \
            f"\tlegality / modern = {multiface_data_row[18]},\n" \
            f"\tlegality / historic = {multiface_data_row[19]},\n" \
            f"\tlegality / legacy = {multiface_data_row[20]},\n" \
            f"\tlegality / pauper = {multiface_data_row[21]},\n" \
            f"\tlegality / vintage = {multiface_data_row[22]},\n" \
            f"\tlegality / timeless = {multiface_data_row[23]},\n" \
            f"\tlegality / commander = {multiface_data_row[24]},\n" \
            f"\tlegality / duel_commander = {multiface_data_row[25]}\n" \
            f"}}\n\n"
        multiface_cmc = int(multiface_data_row[26])
        multiface_sort_card_type = multiface_data_row[27]
        multiface_card_english_name = multiface_data_row[0]
        latex_datas.append([multiface_card, multiface_cmc, multiface_sort_card_type, multiface_card_english_name])
    
    latex_datas.sort(key = sort_key)

    with open(latex_name, "w", encoding = "utf-8") as f:
        for latex_data in latex_datas:
            f.write(latex_data[0])
