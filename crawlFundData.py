import requests
import random
import os
import datetime
import time
import json
from util import user_agent_list, referer_list, FundInformation, FundElement, parseStringIntoNumber, FundHistoricalValue
from getLatestFund import get_fund_code
from bs4 import BeautifulSoup 

def crawlStock(fundCode):
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
            # http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=000001&topline=10&year=&month=&rt=0.16432760653431278
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
    
    portfolio = []
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

                # elementType
                elementType = "stock"

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

                fundElement = FundElement(elementType, stockCode, stockName, ratio, numberOfShares, valueOfShares)

                portfolio.append(fundElement)
    return portfolio

def crawRisk(fundCode):
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
        try:
            soup = BeautifulSoup(data, 'lxml')

            for td in soup.find_all("td"):
                if ("基金类型：" in td.text):
                    risk = td.text.split("|")[-1].replace(" ", "")

                    # filter some funds without risk level, such as http://fund.eastmoney.com/000013.html
                    if "风险" in risk:
                        return risk
        except:
            pass

    return ""

def crawHistoricalValue(fundCode):
    fundCode = str(fundCode)
    folder = "./data/originalHistoricalValue"
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
            # http://api.fund.eastmoney.com/f10/lsjz?callback=jQuery18308008424329839205_1606919908899&fundCode=110011&pageIndex=1&pageSize=20&startDate=&endDate=&_=1606919908921
            website = "http://api.fund.eastmoney.com/f10/lsjz?callback=jQuery18308008424329839205_1606919908899&fundCode=%s&pageIndex=1&pageSize=1000&startDate=&endDate=&_=1606919908921" % fundCode
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
    
    folderToSave = "./data/historicalValue"
    if not os.path.exists(folderToSave):
        os.mkdir(folderToSave)
    pathOfHistoricalValue = os.path.join(folderToSave, nameOfPage)
    listOfFundHistoricalValue = []
    if data:
        try:
            data = data.split("(")[-1].split(")")[0]
            data = json.loads(data)
            for item in data["Data"]["LSJZList"]:
                date = item["FSRQ"]
                netAssetValue = item["DWJZ"]
                accumulativeNetAssetValue = item["LJJZ"]
                dividends = item["FHSP"]    # TODO: extract the dividends number
                fundHistoricalValue = FundHistoricalValue(date, netAssetValue, accumulativeNetAssetValue, dividends)
                listOfFundHistoricalValue.append(fundHistoricalValue)
        except:
            pass

    if len(listOfFundHistoricalValue):
        headerOfFundHistoricalValue = ""
        for key in listOfFundHistoricalValue[0].__dict__:
            headerOfFundHistoricalValue += "%s," % key
        headerOfFundHistoricalValue = headerOfFundHistoricalValue[:-1] + "\n"

        # save fundHistoricalValue into file
        with open(pathOfHistoricalValue, "w") as fw:
            fw.write(headerOfFundHistoricalValue)
            for fundHistoricalValue in listOfFundHistoricalValue:
                fw.write(str(fundHistoricalValue))

def crawlAssetsAllocation(fundCode):
    fundCode = str(fundCode)
    folder = "./data/assetsAllocation"
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
            # http://fundf10.eastmoney.com/zcpz_110011.html
            website = "http://fundf10.eastmoney.com/zcpz_%s.html" % fundCode
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

                                # TODO: get more allocation before))
                                break
        except:
            pass

    return portfolio

def crawlBond(fundCode):
    fundCode = str(fundCode)
    folder = "./data/originalBond"
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
            # http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=zqcc&code=110011&year=&rt=0.7806009533509729
            website = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=zqcc&code=%s&year=&rt=0.7806009533509729" % fundCode
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
                    # elementType
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

def crawlAllFundData():
    # get the list of fund code
    fund_code_list = get_fund_code()

    # save the fund information
    folderOfFundInformation = "./data/fundInformation"
    if not os.path.exists(folderOfFundInformation):
        os.mkdir(folderOfFundInformation)

    # save the portfolio
    folderOfPortfolio = "./data/portfolio"
    if not os.path.exists(folderOfPortfolio):
        os.mkdir(folderOfPortfolio)

    # get header of FundInformation
    headerOfFundInformation = ""
    tempFundInformation = FundInformation("", "", "", "")
    for key in tempFundInformation.__dict__:
        headerOfFundInformation += "%s," % key
    headerOfFundInformation = headerOfFundInformation[:-1] + "\n"
    #print (headerOfFundInformation) # Code,Name,FundType,Risk

    # get header of FundElement
    headerOfFundElement = ""
    tempFundElement = FundElement("", "", "", "", "", "")
    for key in tempFundElement.__dict__:
        headerOfFundElement += "%s," % key
    headerOfFundElement = headerOfFundElement[:-1] + "\n"
    #print (headerOfFundElement) # ElementType,Code,Name,Ratio,NumberOfShares,ValueOfShares
    
    ''' write basic information of fund '''
    if False:
        nameOfFundInformation = "fundInformation_%s.csv" % (datetime.datetime.now().strftime("%Y%m"))
        pathOfFundInformation = os.path.join(folderOfFundInformation, nameOfFundInformation)
        with open(pathOfFundInformation, "w") as fw:
            fw.write(headerOfFundInformation)
            count = 0
            for item in fund_code_list:
                #if item[0] != "110011":
                #    continue
                #if count >= 10:
                #    break

                fundCode = item[0]
                fundName = item[2]
                fundType = item[3]

                print ("%s\t%s\t%s" % (count, fundCode, fundName))

                risk = crawRisk(fundCode)
                if risk:
                    fundInformation = FundInformation(fundCode, fundName, fundType, risk)
                    fw.write(str(fundInformation))
                    count += 1

    ''' write porfolio of fund '''
    if True:
        count = 0
        for item in fund_code_list:
            #if item[0] != "110011":
            #    continue
            #if count >= 10:
            #    break

            fundCode = item[0]
            fundName = item[2]
            fundType = item[3]

            print ("%s\t%s\t%s" % (count, fundCode, fundName))

            nameOfFund = "%s_%s.csv" % (fundCode, datetime.datetime.now().strftime("%Y%m"))

            # crawl portfolio of stock, bond, assetsAllocation
            portfolio = []
            portfolio.extend(crawlStock(fundCode))
            portfolio.extend(crawlBond(fundCode))
            portfolio.extend(crawlAssetsAllocation(fundCode))

            if len(portfolio):
                # write it to file
                nameOfPortfolio = "%s_%s.csv" % (fundCode, datetime.datetime.now().strftime("%Y%m"))
                pathOfPortfolio = os.path.join(folderOfPortfolio, nameOfPortfolio)
                # save the data into file
                with open(pathOfPortfolio, "w") as fw:
                    fw.write(headerOfFundElement)
                    for fundElement in portfolio:
                        fw.write(str(fundElement))
                
                count += 1

    ''' write historical value of fund '''
    if False:
        count = 0
        for item in fund_code_list:
            #if item[0] != "110011":
            #    continue
            #if count >= 10:
            #    break

            fundCode = item[0]
            fundName = item[2]
            fundType = item[3]

            print ("%s\t%s\t%s" % (count, fundCode, fundName))

            crawHistoricalValue(fundCode)

            count += 1

if __name__ == "__main__":
    crawlAllFundData()