import requests
import random
import os
import datetime
import time
import json
from bs4 import BeautifulSoup
import fire
import configparser
import pandas as pd
import re

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from src.util import user_agent_list, referer_list, FundInformation, FundElement, parseStringIntoNumber, FundHistoricalValue, getFolderNameInConfig


def crawRisk(fundCode):
    fundCode = str(fundCode)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    minSecondsToWaitCrawler = int(cf.get("Parameter", "minSecondsToWaitCrawler"))
    maxSecondsToWaitCrawler = int(cf.get("Parameter", "maxSecondsToWaitCrawler"))

    folderOfOriginalRisk = getFolderNameInConfig("folderOfOriginalRisk")    # the folder to save the original risk

    # update every month, not every day
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfPage = os.path.join(folderOfOriginalRisk, nameOfPage)

    data = ""
    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        with open(pathOfPage, "r", encoding='utf-8') as fr:
            data = fr.read()
    else:
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}
        
        try:
            website = "http://fund.eastmoney.com/%s.html" % fundCode    # e.g. http://fund.eastmoney.com/110011.html
            req = requests.get(website, timeout=3, headers=header)
            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w", encoding='utf-8') as fw:
                fw.write(data)

            # sleep for some time
            time.sleep(random.randint(minSecondsToWaitCrawler, maxSecondsToWaitCrawler))
        except Exception as e:
            print(str(e))
    
    # data process
    if data:
        try:
            soup = BeautifulSoup(data, 'lxml')

            for td in soup.find_all("td"):
                if ("基金类型：" in td.text):
                    risk = td.text.split("|")[-1].replace(" ", "")

                    # filter some funds without risk level, such as http://fund.eastmoney.com/000013.html
                    if "风险" in risk:
                        return risk
        except Exception as e:
            print(str(e))

    return ""


def crawlStockPortfolio(fundCode):
    fundCode = str(fundCode)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    minSecondsToWaitCrawler = int(cf.get("Parameter", "minSecondsToWaitCrawler"))
    maxSecondsToWaitCrawler = int(cf.get("Parameter", "maxSecondsToWaitCrawler"))

    folderOfOriginalCcmx = getFolderNameInConfig("folderOfOriginalCcmx")    # the folder to save the original stock portfolio

    # update every month, not every day
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfPage = os.path.join(folderOfOriginalCcmx, nameOfPage)

    data = ""
    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        with open(pathOfPage, "r", encoding='utf-8') as fr:
            data = fr.read()
    else:
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}

        try:
            website = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=%s&topline=100&year=&month=&rt=0.9688781140527483" % fundCode
            # http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=110011&topline=100&year=&month=&rt=0.9688781140527483
            req = requests.get(website, timeout=3, headers=header)

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w", encoding='utf-8') as fw:
                fw.write(data)

            # sleep for some time
            time.sleep(random.randint(minSecondsToWaitCrawler, maxSecondsToWaitCrawler))
        except Exception as e:
            print(str(e))

    portfolio = []
    if data:
        # parse the data
        data = data.split("\"")[1]
        soup = BeautifulSoup(data, 'lxml')
        for tr in soup.find_all('tr'):
            td = tr.findChildren('td')

            # TODO: we can use the data happened 3 months ago or eariler if len is 7
            if (len(td) == 9):
                # the first value must be number
                try:
                    number = td[0].text.replace("*", "")
                except:
                    continue

                elementType = "stock"
                stockCode = td[1].text
                stockName = td[2].text
                ratio = parseStringIntoNumber(td[6].text)
                numberOfShares = parseStringIntoNumber(td[7].text)
                valueOfShares = parseStringIntoNumber(td[8].text)

                fundElement = FundElement(elementType, stockCode, stockName, ratio, numberOfShares, valueOfShares)
                portfolio.append(fundElement)
    return portfolio


def crawlBondPortfolio(fundCode):
    fundCode = str(fundCode)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    minSecondsToWaitCrawler = int(cf.get("Parameter", "minSecondsToWaitCrawler"))
    maxSecondsToWaitCrawler = int(cf.get("Parameter", "maxSecondsToWaitCrawler"))

    folderOfOriginalBond = getFolderNameInConfig("folderOfOriginalBond")    # the folder to save the original bond portfolio

    # update every month, not every day
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfPage = os.path.join(folderOfOriginalBond, nameOfPage)

    data = ""
    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        with open(pathOfPage, "r", encoding='utf-8') as fr:
            data = fr.read()
    else:
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}

        try:
            website = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=zqcc&code=%s&year=&rt=0.7806009533509729" % fundCode
            # http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=zqcc&code=110011&year=&rt=0.7806009533509729
            req = requests.get(website, timeout=3, headers=header)

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w", encoding='utf-8') as fw:
                fw.write(data)

            # sleep for some time
            time.sleep(random.randint(minSecondsToWaitCrawler, maxSecondsToWaitCrawler))
        except Exception as e:
            print(str(e))

    portfolio = []
    if data:
        # parse the data
        data = data.split("\"")[1]
        soup = BeautifulSoup(data, 'lxml')

        # TODO: use data in earlier reports
        div = soup.find("div")
        if not div:
            return portfolio

        for tr in div.find_all('tr'):
            td = tr.findChildren('td')

            if (len(td) == 5):
                number = td[0].text
                try:
                    number = int(number)
                except:
                    continue    # the first item must be int

                # the first value must be number
                try:
                    elementType = "bond"
                    bondCode = td[1].text
                    bondName = td[2].text
                    ratio = parseStringIntoNumber(td[3].text)
                    numberOfShares = -1
                    valueOfShares = parseStringIntoNumber(td[4].text)
                    fundElement = FundElement(elementType, bondCode, bondName, ratio, numberOfShares, valueOfShares)
                    portfolio.append(fundElement)
                except:
                    continue
    return portfolio


def crawlAssetsAllocation(fundCode):
    fundCode = str(fundCode)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    minSecondsToWaitCrawler = int(cf.get("Parameter", "minSecondsToWaitCrawler"))
    maxSecondsToWaitCrawler = int(cf.get("Parameter", "maxSecondsToWaitCrawler"))

    folderOfOriginalAssetsAllocation = getFolderNameInConfig("folderOfOriginalAssetsAllocation")    # the folder to save the original assets allocation

    # update every month, not every day
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfPage = os.path.join(folderOfOriginalAssetsAllocation, nameOfPage)

    data = ""
    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        with open(pathOfPage, "r", encoding='utf-8') as fr:
            data = fr.read()
    else:
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}

        try:
            website = "http://fundf10.eastmoney.com/zcpz_%s.html" % fundCode    # http://fundf10.eastmoney.com/zcpz_110011.html
            req = requests.get(website, timeout=3, headers=header)

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w", encoding='utf-8') as fw:
                fw.write(data)

            # sleep for some time
            time.sleep(random.randint(minSecondsToWaitCrawler, maxSecondsToWaitCrawler))
        except Exception as e:
            print(str(e))

    # TODO: error happens in fond "150343", stock is 81.99% and cash is 82.66%
    portfolio = []
    if data:
        try:
            soup = BeautifulSoup(data, 'lxml')

            for table in soup.find_all("table"):
                if ("报告期" in table.text):
                    for tbody in table:
                        if tbody.name == "tbody":
                            for tr in tbody:
                                td = tr.findChildren('td')

                                if (len(td) == 5):
                                    date = td[0].text

                                    # elementType
                                    elementType = "assetsAllocation"
                                    stockPortion = parseStringIntoNumber(td[1].text)
                                    bondPortion = parseStringIntoNumber(td[2].text)
                                    cashPortion = parseStringIntoNumber(td[3].text)
                                    portfolio.append(FundElement(elementType, -1, "stockPortion", stockPortion, -1, -1))
                                    portfolio.append(FundElement(elementType, -1, "bondPortion", bondPortion, -1, -1))
                                    portfolio.append(FundElement(elementType, -1, "cashPortion", cashPortion, -1, -1))

                                # TODO: get more allocation before
                                break
        except:
            pass

    return portfolio


def crawHistoricalValue(fundCode):
    fundCode = str(fundCode)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    minSecondsToWaitCrawler = int(cf.get("Parameter", "minSecondsToWaitCrawler"))
    maxSecondsToWaitCrawler = int(cf.get("Parameter", "maxSecondsToWaitCrawler"))

    # number of historical days to crawl
    numberOfHistoricalDaysToCrawl = cf.get("Parameter", "numberOfHistoricalDaysToCrawl")   # 3000

    folderOfOriginalHistoricalValue = getFolderNameInConfig("folderOfOriginalHistoricalValue")    # the folder to save the original historical value
    folderToSaveHistoricalValue = getFolderNameInConfig("folderToSaveHistoricalValue")    # the folder to save historical value

    # update every month, not every day
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    nameOfPage = "%s_%s.html" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfPage = os.path.join(folderOfOriginalHistoricalValue, nameOfPage)

    data = ""
    # if the page exists on local file, then read it directly
    if os.path.exists(pathOfPage):
        with open(pathOfPage, "r", encoding='utf-8') as fr:
            data = fr.read()
    else:
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}

        try:
            # TODO: get the website automatically
            # this websit would change after some days and we must modify it manually
            # manually setting : open http://fundf10.eastmoney.com/jjjz_000001.html in your browser, then press F12, you can find similar link in Sources/api.fund.eastmoney.com/f10
            website = "http://api.fund.eastmoney.com/f10/lsjz?callback=jQuery183039602021065042914_1611400671604&fundCode=%s&pageIndex=1&pageSize=%s&startDate=&endDate=&_=1611400671615" % (fundCode, numberOfHistoricalDaysToCrawl)
            req = requests.get(website, timeout=30, headers=header)

            req.encoding = 'utf-8'
            data = req.text

            # save the data into file
            with open(pathOfPage, "w", encoding='utf-8') as fw:
                fw.write(data)

            # sleep for some time
            time.sleep(random.randint(minSecondsToWaitCrawler, maxSecondsToWaitCrawler))
        except Exception as e:
            print(str(e))

    nameOfCsvPage = "%s_%s.csv" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
    pathOfHistoricalValue = os.path.join(folderToSaveHistoricalValue, nameOfCsvPage)
    listOfFundHistoricalValue = []
    if data:
        try:
            data = json.loads(data.split("(")[-1].split(")")[0])

            # Some funds don't show the net value, example: http://fundf10.eastmoney.com/jjjz_010288.html
            SYType = data["Data"]["SYType"]
            if (SYType == "每万份收益") or (SYType == "每百份收益") or (SYType == "每百万份收益"):
                raise Exception("The fund contains 每*份收益")

            for item in data["Data"]["LSJZList"]:
                date = item["FSRQ"]
                netAssetValue = item["DWJZ"]
                accumulativeNetAssetValue = item["LJJZ"]
                dividends = item["FHSP"]    # TODO: extract the dividends number
                fundHistoricalValue = FundHistoricalValue(date, netAssetValue, accumulativeNetAssetValue, dividends)
                listOfFundHistoricalValue.append(fundHistoricalValue)
        except Exception as e:
            print ("fundCode=%s\terror=%s" % (fundCode, str(e)))

    if len(listOfFundHistoricalValue):
        headerOfFundHistoricalValue = ""
        for key in listOfFundHistoricalValue[0].__dict__:
            headerOfFundHistoricalValue += "%s," % key
        headerOfFundHistoricalValue = headerOfFundHistoricalValue[:-1] + "\n"

        # save fundHistoricalValue into file
        with open(pathOfHistoricalValue, "w", encoding='utf-8') as fw:
            fw.write(headerOfFundHistoricalValue)
            for fundHistoricalValue in listOfFundHistoricalValue:
                fw.write(str(fundHistoricalValue))


def get_fund_code(forceCrawl=False):
    '''
        Get all funds from eastmoney.com and save it in local file, read it if find today's fund file.
		The crawl code from https://github.com/shengqiangzhang/examples-of-web-crawlers
        Args:
            forceCrawl: force crawl all funds
    '''
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    folderOfLatestFundCode = getFolderNameInConfig("folderOfLatestFundCode")  # the folder to save latest fund code
    updateEveryDay = cf.get("Parameter", "updateEveryDay") # store latest fund code every day
    pathToday = os.path.join(folderOfLatestFundCode, "fundCode_%s.csv" % datetime.datetime.now().strftime(updateEveryDay))
    if (not os.path.exists(pathToday) or forceCrawl):
        header = {'User-Agent': random.choice(user_agent_list), 'Referer': random.choice(referer_list)}
        req = requests.get('http://fund.eastmoney.com/js/fundcode_search.js', timeout=5, headers=header)
        fund_code_js = req.content.decode()
        fund_code = fund_code_js.split("= [")[-1].replace("];", "")
        fund_code = re.findall(r"[\[](.*?)[\]]", fund_code)
        
        fund_code_list = []
        for sub_data in fund_code:
            data = sub_data.replace("\"","").replace("'","")
            data_list = data.split(",")
            fund_code_list.append(data_list)

        df = pd.DataFrame(fund_code_list, columns= ['code', 'simpleSpelling', 'name', 'type', 'spelling'])
        df.to_csv(pathToday, index=None, header=True)

        return fund_code_list
    else:
        return pd.read_csv(pathToday, dtype=object).values.tolist() # the type is string


def crawlAllFundData(ifCrawlBasicInformation=True, ifCrawlPortfolio=True, ifCrawlHistoricalValue=True):
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    updateEveryMonth = cf.get("Parameter", "updateEveryMonth") # update every month, not every day
    folderOfFundInformation = getFolderNameInConfig("folderOfFundInformation")  # the folder to save the fund information
    folderOfPortfolio = getFolderNameInConfig("folderOfPortfolio")  # the folder to save the portfolio

    # get header of FundInformation
    headerOfFundInformation = ""
    tempFundInformation = FundInformation("", "", "", "")
    for key in tempFundInformation.__dict__:
        headerOfFundInformation += "%s," % key
    headerOfFundInformation = headerOfFundInformation[:-1] + "\n"   # Code,Name,FundType,Risk

    # get header of FundElement
    headerOfFundElement = ""
    tempFundElement = FundElement("", "", "", "", "", "")
    for key in tempFundElement.__dict__:
        headerOfFundElement += "%s," % key
    headerOfFundElement = headerOfFundElement[:-1] + "\n"   # ElementType,Code,Name,Ratio,NumberOfShares,ValueOfShares

    ''' write the header of basic information of fund '''
    if ifCrawlBasicInformation:
        nameOfFundInformation = "fundInformation_%s.csv" % (datetime.datetime.now().strftime(updateEveryMonth))
        pathOfFundInformation = os.path.join(folderOfFundInformation, nameOfFundInformation)
        with open(pathOfFundInformation, "w", encoding='utf-8') as fw:
            fw.write(headerOfFundInformation)

    # get the list of fund code
    fund_code_list = get_fund_code()

    count = 0
    # Please don't use multi processing and proxy to burden the server!!!
    for item in fund_code_list:
        fundCode = item[0]
        fundName = item[2]
        fundType = item[3]

        if count % 100 == 0:
            print ("%s\t%s\t%s" % (count, fundCode, fundName))

        ''' write basic information of fund '''
        if ifCrawlBasicInformation:
            risk = crawRisk(fundCode)   # e.g. 中高风险
            fundInformation = FundInformation(fundCode, fundName, fundType, risk)

            with open(pathOfFundInformation, "a+", encoding='utf-8') as fw:
                fw.write(str(fundInformation))

        ''' write porfolio of fund '''
        if ifCrawlPortfolio:
            portfolio = []  # crawl portfolio of stock, bond, assetsAllocation
            portfolio.extend(crawlStockPortfolio(fundCode))
            portfolio.extend(crawlBondPortfolio(fundCode))
            portfolio.extend(crawlAssetsAllocation(fundCode))

            if len(portfolio):
                # save the data into file
                nameOfPortfolio = "%s_%s.csv" % (fundCode, datetime.datetime.now().strftime(updateEveryMonth))
                pathOfPortfolio = os.path.join(folderOfPortfolio, nameOfPortfolio)
                with open(pathOfPortfolio, "w", encoding='utf-8') as fw:
                    fw.write(headerOfFundElement)
                    for fundElement in portfolio:
                        fw.write(str(fundElement))

        ''' write historical value of fund '''
        if ifCrawlHistoricalValue:
            crawHistoricalValue(fundCode)

        count += 1


if __name__ == "__main__":
    fire.Fire()