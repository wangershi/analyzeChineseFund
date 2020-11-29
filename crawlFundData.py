import requests
import random
import os
import datetime
from util import user_agent_list, referer_list
from getLatestFund import get_fund_code

def crawlPorfolio(fund_code):
    fund_code = str(fund_code)
    folder = "./data/ccmx"
    if not os.path.exists(folder):
        os.mkdir(folder)
    nameOfPage = "%s_%s.html" % (fund_code, datetime.datetime.now().strftime("%Y%m%d"))
    pathOfPage = os.path.join(folder, nameOfPage)

    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        # save the data into file
        with open(pathOfPage, "r") as fr:
            data = fr.read()
    else:
        # 获取一个随机user_agent和Referer
        header = {'User-Agent': random.choice(user_agent_list),
            'Referer': random.choice(referer_list)
        }

        # 使用try、except来捕获异常
        # 如果不捕获异常，程序可能崩溃
        try:
            # TODO: use proxy to visit the website
            req = requests.get("http://fundf10.eastmoney.com/ccmx_" + fund_code + ".html", timeout=3, headers=header)
            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w") as fw:
                fw.write(data)
        except Exception as e:
            print(str(e))
    print (data)


def crawlAllFundData():
    fund_code_list = get_fund_code()

    listOfPortfolio = []
    for item in fund_code_list:
        # test in one fund
        if item[0] != "110011":
            continue

        fund_code = item[0]
        portfolio = crawlPorfolio(fund_code)
        listOfPortfolio.append(portfolio)

if __name__ == "__main__":
    crawlAllFundData()