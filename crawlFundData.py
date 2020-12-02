import requests
import random
import os
import datetime
import time
from util import user_agent_list, referer_list, Fund, FundElement, parseStringIntoNumber
from getLatestFund import get_fund_code
from bs4 import BeautifulSoup 

def crawlPorfolio(fundCode, fundName, fundType):
    fund = Fund(fundCode, fundName, fundType)

    fundCode = str(fundCode)
    folder = "./data/ccmx"
    if not os.path.exists(folder):
        os.mkdir(folder)

    # update every month, not every day
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime("%Y%m"))
    pathOfPage = os.path.join(folder, nameOfPage)
    data = ""

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
            # http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=110011&topline=100&year=&month=&rt=0.9688781140527483
            website = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=%s&topline=100&year=&month=&rt=0.9688781140527483" % fundCode
            req = requests.get(website, timeout=3, headers=header)

            # sleep for some time
            time.sleep(random.randint(3, 6))

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w") as fw:
                fw.write(data)
        except Exception as e:
            print(str(e))
    
    if data:
        # parse the data
        data = data.split("\"")[1]
        soup = BeautifulSoup(data, 'lxml')
        for tr in soup.find_all('tr'):
            td = tr.findChildren('td')

            # TODO: the data is happened 3 months ago or eariler if len is 7, we can use it in the future
            if (len(td) == 9):
                # the first value must be number
                try:
                    #print (td)
                    number = td[0].text.replace("*", "")
                    index = int(number)
                except:
                    continue

                # stockCode
                stockCode = td[1].text

                # stockName
                stockName = td[2].text

                # ratio
                ratio = parseStringIntoNumber(td[6].text)

                # number of shares
                numberOfShares = parseStringIntoNumber(td[7].text)

                # value of shares
                valueOfShares = parseStringIntoNumber(td[8].text)

                fundElement = FundElement(stockCode, stockName, ratio, numberOfShares, valueOfShares)

                fund.Portfolio.append(fundElement)
    return fund

def crawRisk(fundCode, fundName, fundType):
    fund = Fund(fundCode, fundName, fundType)

    fundCode = str(fundCode)
    folder = "./data/risk"
    if not os.path.exists(folder):
        os.mkdir(folder)

    # update every month, not every day
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime("%Y%m"))
    pathOfPage = os.path.join(folder, nameOfPage)
    data = ""

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
            # http://fund.eastmoney.com/110011.html
            website = "http://fund.eastmoney.com/%s.html" % fundCode
            req = requests.get(website, timeout=3, headers=header)

            # sleep for some time
            time.sleep(random.randint(3, 6))

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w") as fw:
                fw.write(data)
        except Exception as e:
            print(str(e))
    
    if data:
        soup = BeautifulSoup(data, 'lxml')

        for td in soup.find_all("td"):
            if ("基金类型：" in td.text):
                risk = td.text.split("|")[-1].replace(" ", "")
                return risk

    return ""

def crawlAllFundData():
    fund_code_list = get_fund_code()

    listOfFund = []
    for item in fund_code_list:
        # test in one fund
        if item[0] != "110011":
            continue

        fundCode = item[0]
        fundName = item[2]
        fundType = item[3]

        '''
        fund = crawlPorfolio(fundCode, fundName, fundType)
        print (fund)
        listOfFund.append(fund)
        '''

        risk = crawRisk(fundCode, fundName, fundType)
        if risk:
            print ("risk = %s" % risk)


if __name__ == "__main__":
    crawlAllFundData()