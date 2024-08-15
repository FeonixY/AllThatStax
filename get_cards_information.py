import os
import re
import json
import time
import requests
from utils import read_xlsx_excel
from openpyxl import load_workbook
from urllib.parse import urlparse, unquote

def get_cards_information(sheet_file_name, sheet_name, multiface_sheet_name, list_name, is_from_scratch : bool = True):
    # 读取列表
    with open(list_name, "r") as f:
        card_names = f.readlines()

    # 读取表格
    workbook = load_workbook(sheet_file_name)
    multiface_sheet = workbook.create_sheet("multiface_sheet_temp")
    sheet = workbook.create_sheet("sheet_temp")
    last_multiface_sheet_data = read_xlsx_excel(sheet_file_name, multiface_sheet_name)
    last_sheet_data = read_xlsx_excel(sheet_file_name, sheet_name)

    # 读取锁牌类型字典
    with open("config.json", "r") as file:
        stax_type_dict = json.load(file)["stax_type"]

    # 遍历列表
    for card_name in card_names:
        # 整理卡牌名称
        card_name_match = re.search(r'\d+\s+(.+?)\s+\(.*?\)', card_name)
        if card_name_match:
            card_english_name = card_name_match.group(1)
        tags = re.findall(r'#(\S.+?)\s*(?=#|$)', card_name)


        # 检索中文信息
        url = f"https://api.scryfall.com/cards/search?q=lang:zhs%20!%22{card_english_name}%22"
        response = requests.get(url)

        # 如果存在中文信息，则使用
        if response.status_code == 200:
            card_data = response.json()["data"][0]

        # 如果不存在中文信息，则检索并使用默认信息
        elif response.status_code == 404:
            new_url = f"https://api.scryfall.com/cards/named?exact={card_english_name}"
            new_response = requests.get(new_url)
            if new_response.status_code != 200:
                print(f"Failed to get {card_english_name} Chinese card name or other versions. {new_response.status_code} - {new_response.text}")
                continue
            card_data = new_response.json()

        # 如果也不存在，则获取卡牌信息失败，跳过这张卡牌
        else:
            print(f"Failed to get {card_english_name} information. {response.status_code} - {response.text}")
            continue

        # 处理双面牌
        if "card_faces" in card_data:
            # 获取卡牌英文名称
            front_card_english_name = card_data["card_faces"][0]["name"]
            back_card_english_name = card_data["card_faces"][1]["name"]

            # 获取卡牌中文名称（如果有的话）
            is_last_has_chinese_name = False
            for row in last_multiface_sheet_data:
                if row[1] == front_card_english_name:
                    front_card_chinese_name = row[2]
                    back_card_chinese_name = row[7]
                    is_last_has_chinese_name = True
            if is_last_has_chinese_name == False:
                if "printed_name" in card_data["card_faces"][0]:
                    front_card_chinese_name = card_data["card_faces"][0]["printed_name"]
                else:
                    front_card_chinese_name = ""
                if "printed_name" in card_data["card_faces"][1]:
                    back_card_chinese_name = card_data["card_faces"][1]["printed_name"]
                else:
                    back_card_chinese_name = ""

            # 获取卡图
            if "image_uris" in card_data["card_faces"][0]:
                # 获取正面图片名
                front_image_uri = card_data["card_faces"][0]["image_uris"]["png"]
                front_response = requests.head(front_image_uri, allow_redirects = True)
                if front_response.status_code == 200:
                    if "Content-Disposition" in front_response.headers:
                        content_disposition = front_response.headers["Content-Disposition"]
                        front_card_image_name = content_disposition.split("filename=")[1].strip("'").strip('"')
                    else:
                        parsed_url = urlparse(front_image_uri)
                        front_card_image_name = os.path.basename(unquote(parsed_url.path))
                        print(f"{card_english_name} URL doesn't contain Content-Disposition, using name parsed from URL as filename")
                    
                    # 获取正面图片
                    os.makedirs("Images", exist_ok = True)
                    front_image_response = requests.get(front_image_uri)
                    if front_image_response.status_code == 200:
                        with open(f"Images/{front_card_image_name}", "wb") as f:
                            f.write(front_image_response.content)
                        print(f"{card_english_name} image downloaded and saved as {front_card_image_name}")
                    else:
                        front_card_image_name = ""
                        print(f"Failed to download {card_english_name} image. {front_image_response.status_code} - {front_image_response.text}")
                else:
                    front_card_image_name = ""
                    print(f"Failed to get {card_english_name} image headers. {front_response.status_code} - {front_response.text}")
            else:
                front_card_image_name = ""
                print(f"No image available for {card_english_name}.")
            if "image_uris" in card_data["card_faces"][1]:
                # 获取反面图片名
                back_image_uri = card_data["card_faces"][1]["image_uris"]["png"]
                back_response = requests.head(back_image_uri, allow_redirects = True)
                if back_response.status_code == 200:
                    if "Content-Disposition" in back_response.headers:
                        content_disposition = back_response.headers["Content-Disposition"]
                        back_card_image_name = content_disposition.split("filename=")[1].strip("'").strip('"')
                    else:
                        parsed_url = urlparse(back_image_uri)
                        back_card_image_name = os.path.basename(unquote(parsed_url.path))
                        print(f"{card_english_name} URL doesn't contain Content-Disposition, using name parsed from URL as filename")
                    
                    # 获取反面图片
                    os.makedirs("Images", exist_ok = True)
                    back_image_response = requests.get(back_image_uri)
                    if back_image_response.status_code == 200:
                        with open(f"Images/{back_card_image_name}", "wb") as f:
                            f.write(back_image_response.content)
                        print(f"{card_english_name} image downloaded and saved as {back_card_image_name}")
                    else:
                        back_card_image_name = ""
                        print(f"Failed to download {card_english_name} image. {back_image_response.status_code} - {back_image_response.text}")
                else:
                    back_card_image_name = ""
                    print(f"Failed to get {card_english_name} image headers. {back_response.status_code} - {back_response.text}")
            else:
                back_card_image_name = ""
                print(f"No image available for {card_english_name}.")

            # 获取法术力费用
            front_mana_cost = card_data["card_faces"][0]["mana_cost"]
            back_mana_cost = card_data["card_faces"][1]["mana_cost"]

            # 获取牌张类别
            front_card_type = card_data["card_faces"][0]["type_line"]
            back_card_type = card_data["card_faces"][1]["type_line"]
            sort_card_type = (str)(front_card_type).split(" ")[0]
            if "Legendary" in sort_card_type:
                sort_card_type = (str)(front_card_type).split(" ")[1]
            if "Creature" in sort_card_type:
                sort_card_type = "生物"
            elif "Artifact" in sort_card_type:
                sort_card_type = "神器"
            elif "Enchantment" in sort_card_type:
                sort_card_type = "结界"
            else:
                sort_card_type = "其他"
            
            # 获取卡牌描述
            if "printed_text" in card_data["card_faces"][0]:
                front_card_description = card_data["card_faces"][0]["printed_text"]
            else:
                front_card_description = card_data["card_faces"][0]["oracle_text"]
            if "printed_text" in card_data["card_faces"][1]:
                back_card_description = card_data["card_faces"][1]["printed_text"]
            else:
                back_card_description = card_data["card_faces"][1]["oracle_text"]
            
            # 获取锁牌类型
            stax_type = ""
            for tag in tags:
                stax_type = stax_type.join(stax_type_dict[tag] + "，")
            stax_type = stax_type.removesuffix("，")

            # 获取是否在不重印列表上
            if card_data["reserved"]:
                is_rl = "RL"
            else:
                is_rl = "Not RL"
            
            # 获取合法性
            legalities = card_data["legalities"]
            def replace_not_legal_in_legalities(legalities):
                def replace_values(obj):
                    if isinstance(obj, dict):
                        return {k: replace_values(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [replace_values(item) for item in obj]
                    elif obj == "not_legal":
                        return "notlegal"
                    else:
                        return obj
    
                return replace_values(legalities)
            legalities = replace_not_legal_in_legalities(legalities)

            cmc = card_data["cmc"]
        
            new_line = [front_card_english_name, front_card_chinese_name, front_card_image_name, front_mana_cost, front_card_type, front_card_description,
                        back_card_english_name, back_card_chinese_name, back_card_image_name, back_mana_cost, back_card_type, back_card_description,
                        stax_type, is_rl, 
                        legalities["standard"], legalities["alchemy"], legalities["pioneer"], legalities["explorer"],
                        legalities["modern"], legalities["historic"], legalities["legacy"], legalities["pauper"],
                        legalities["vintage"], legalities["timeless"], legalities["commander"], legalities["duel"], cmc, sort_card_type]
            multiface_sheet.append(new_line)
            workbook.save(sheet_file_name)
        
        # 处理单面牌
        else:
            # 获取卡牌英文名称
            front_card_english_name = card_data["name"]
            
            # 获取卡牌中文名称（如果有的话）
            is_last_has_chinese_name = False
            for row in last_multiface_sheet_data:
                if row[1] == card_english_name:
                    card_chinese_name = row[2]
                    is_last_has_chinese_name = True
            if is_last_has_chinese_name == False:
                if "printed_name" in card_data:
                    card_chinese_name = card_data["printed_name"]
                else:
                    card_chinese_name = ""

            # 获取卡图
            if "image_uris" in card_data:
                # 获取图片名
                image_uri = card_data["image_uris"]["png"]
                response = requests.head(image_uri, allow_redirects = True)
                if response.status_code == 200:
                    if "Content-Disposition" in response.headers:
                        content_disposition = response.headers["Content-Disposition"]
                        card_image_name = content_disposition.split("filename=")[1].strip("'").strip('"')
                    else:
                        parsed_url = urlparse(image_uri)
                        card_image_name = os.path.basename(unquote(parsed_url.path))
                        print(f"{card_english_name} URL doesn't contain Content-Disposition, using name parsed from URL as filename")
                    
                    # 获取图片
                    os.makedirs("Images", exist_ok = True)
                    image_response = requests.get(image_uri)
                    if image_response.status_code == 200:
                        with open(f"Images/{card_image_name}", "wb") as f:
                            f.write(image_response.content)
                        print(f"{card_english_name} image downloaded and saved as {card_image_name}")
                    else:
                        card_image_name = ""
                        print(f"Failed to download {card_english_name} image. {image_response.status_code} - {image_response.text}")
                else:
                    card_image_name = ""
                    print(f"Failed to get {card_english_name} image headers. {response.status_code} - {response.text}")
            else:
                card_image_name = ""
                print(f"No image available for {card_english_name}.")

            # 获取法术力费用
            mana_cost = card_data["mana_cost"]

            # 获取牌张类别
            card_type = card_data["type_line"]
            sort_card_type = (str)(card_type).split(" ")[0]
            if "Legendary" in sort_card_type:
                sort_card_type = (str)(card_type).split(" ")[1]
            if "Creature" in sort_card_type:
                sort_card_type = "生物"
            elif "Artifact" in sort_card_type:
                sort_card_type = "神器"
            elif "Enchantment" in sort_card_type:
                sort_card_type = "结界"
            else:
                sort_card_type = "其他"
            
            # 获取卡牌描述
            if "printed_text" in card_data:
                card_description = card_data["printed_text"]
            else:
                card_description = card_data["oracle_text"]
            
            # 获取锁牌类型
            stax_type = ""
            for tag in tags:
                stax_type = stax_type.join(stax_type_dict[tag] + "，")
            stax_type = stax_type.removesuffix("，")

            # 获取是否在不重印列表上
            if card_data["reserved"]:
                is_rl = "RL"
            else:
                is_rl = "Not RL"

            # 获取合法性
            legalities = card_data["legalities"]
            def replace_not_legal_in_legalities(legalities):
                def replace_values(obj):
                    if isinstance(obj, dict):
                        return {k: replace_values(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [replace_values(item) for item in obj]
                    elif obj == "not_legal":
                        return "notlegal"
                    else:
                        return obj
    
                return replace_values(legalities)
            legalities = replace_not_legal_in_legalities(legalities)

            cmc = card_data["cmc"]
        
            new_line = [card_english_name, card_chinese_name, card_image_name, mana_cost, card_type, card_description, stax_type, is_rl, 
                        legalities["standard"], legalities["alchemy"], legalities["pioneer"], legalities["explorer"],
                        legalities["modern"], legalities["historic"], legalities["legacy"], legalities["pauper"],
                        legalities["vintage"], legalities["timeless"], legalities["commander"], legalities["duel"], cmc, sort_card_type]
            sheet.append(new_line)
            workbook.save(sheet_file_name)
        
        print(f"Add {new_line}")
        time.sleep(0.3)
