from openpyxl import load_workbook

"""
单面牌表格结构：
card_english_name, card_chinese_name, card_image_name, mana_cost, card_type, card_description,
stax_type, is_rl, 
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

def genarate_latex_text(
    sheet_file_name : str,
    sheet_name : str,
    multiface_sheet_name : str,
    latex_text_name : str):
    
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
    
    def sort_key_7plus(item):
        cmc = item[1]
        card_type = card_type_order[item[2]]
        card_english_name = item[3]
        return (card_type, cmc, card_english_name)

    card_type_order = {
        "生物": 1,
        "神器": 2,
        "结界": 3,
        "其他": 4
    }

    latex_datas = []

    # 处理单面牌数据
    data = read_xlsx_excel(sheet_file_name, sheet_name)
    data = data[1:]
    for data_row in data:
        card = f"\\card\n" \
            f"{{\n" \
            f"\tcard_english_name = {{{data_row[0]}}},\n" \
            f"\tcard_chinese_name = {{{data_row[1]}}},\n" \
            f"\tcard_image = {data_row[2]},\n" \
            f"\tmana_cost = {(str)(data_row[3]).replace("{", "\\MTGsymbol{").replace("}", "}{5}") if data_row[3] is not None else "无费用（法术力值为0）"},\n" \
            f"\tcard_type = {data_row[4]},\n" \
            f"\tdescription = {{{str(data_row[5]).replace("{", "\\MTGsymbol{").replace("}", "}{3}").replace("\n", "\\\\\n")}}},\n" \
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
            f"\tfront_card_english_name = {{{multiface_data_row[0]}}},\n" \
            f"\tfront_card_chinese_name = {{{multiface_data_row[1]}}},\n" \
            f"\tfront_card_image = {multiface_data_row[2]},\n" \
            f"\tfront_mana_cost = {(str)(multiface_data_row[3]).replace("{", "\\MTGsymbol{").replace("}", "}{5}")},\n" \
            f"\tfront_card_type = {multiface_data_row[4]},\n" \
            f"\tfront_description = {{{str(multiface_data_row[5]).replace("{", "\\MTGsymbol{").replace("}", "}{3}").replace("\n", "\\\\\n")}}},\n" \
            f"\tback_card_english_name = {{{multiface_data_row[6]}}},\n" \
            f"\tback_card_chinese_name = {{{multiface_data_row[7]}}},\n" \
            f"\tback_card_image = {multiface_data_row[8]},\n" \
            f"\tback_mana_cost = {(str)(multiface_data_row[9]).replace("{", "\\MTGsymbol{").replace("}", "}{5}")},\n" \
            f"\tback_card_type = {multiface_data_row[10]},\n" \
            f"\tback_description = {{{str(multiface_data_row[11]).replace("{", "\\MTGsymbol{").replace("}", "}{3}").replace("\n", "\\\\\n")}}},\n" \
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

    # 写入文件，同时插入章节和小节标记
    with open(latex_text_name, "w", encoding="utf-8") as f:
        # 按cmc分类卡牌数据
        cmc_groups = {i: [] for i in range(8)}
        cmc_groups["7+"] = []
        
        for latex_data in latex_datas:
            card, cmc, sort_card_type, card_english_name = latex_data
            if cmc >= 7:
                cmc_groups["7+"].append(latex_data)
            else:
                cmc_groups[cmc].append(latex_data)
        
        cmc_groups["7+"].sort(key = sort_key_7plus)
        
        # 按顺序写入1到6费的卡牌
        for cmc in range(1, 7):
            current_cmc = cmc
            f.write(f"\\chapter{{{current_cmc}费}}\n\n")
            current_sort_card_type = None
            
            for latex_data in cmc_groups[cmc]:
                card, cmc, sort_card_type, card_english_name = latex_data
                
                if sort_card_type != current_sort_card_type:
                    current_sort_card_type = sort_card_type
                    f.write(f"\\section{{{current_sort_card_type}}}\n\n")
                
                f.write(card)
        
        # 写入7+费的卡牌
        f.write(f"\\chapter{{7+费}}\n\n")
        current_sort_card_type = None
        
        for latex_data in cmc_groups["7+"]:
            card, cmc, sort_card_type, card_english_name = latex_data
            
            if sort_card_type != current_sort_card_type:
                current_sort_card_type = sort_card_type
                f.write(f"\\section{{{current_sort_card_type}}}\n\n")
            
            f.write(card)
        
        # 最后写入0费的卡牌
        f.write(f"\\chapter{{0费（包括地）}}\n\n")
        current_sort_card_type = None
        
        for latex_data in cmc_groups[0]:
            card, cmc, sort_card_type, card_english_name = latex_data
            
            if sort_card_type != current_sort_card_type:
                current_sort_card_type = sort_card_type
                f.write(f"\\section{{{current_sort_card_type}}}\n\n")
            
            f.write(card)
