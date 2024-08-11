# 万智牌锁牌名录

本项目是万智牌锁牌名录的源代码，包含了编写本书用到的所有图片和代码（LaTeX用于生成pdf文档，python用于爬取锁牌信息）。

本项目中文件有以下用途：

* figure：包含生成pdf文档用到的图片
* Images：包含所有锁牌图片，尽量保持了高清和中文
* 锁牌.md：没啥用的玩意，我之后会删掉
* AllThatStax.tex：用于生成pdf文档用到的LaTeX主文件
* config.json：用于配置python中会用到的文件的位置信息
* genarate_latex.py：包含从表格中提取信息，并生成可使用在LaTeX中的文本的方法
* get_cards_information.py：包含从srcyfall API获取卡牌信息，并存储于表格中的方法
* latex.txt：生成出的可用于LaTeX中的文本文件
* list.txt：用于向scryfall API获取卡牌信息的名称，采用MTGO格式
* main.py：主代码
* multiface_sheet.xlsx：包含双面牌（和翻转牌）的信息
* sheet.xlsx：包含单面牌的信息
