import os
import configparser

# list of user agent
user_agent_list = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.4.3.4000 Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 UBrowser/4.0.3214.0 Safari/537.36'
]

# list of referer
referer_list = [
    'http://fund.eastmoney.com/110022.html',
    'http://fund.eastmoney.com/110023.html',
    'http://fund.eastmoney.com/110024.html',
    'http://fund.eastmoney.com/110025.html'
]

def parseStringIntoNumber(inputString):
    '''
        parse string into number, return -1 if convert failed
        Example:
            "9.8%" -> 0.098
            "1"    -> 1.0
            "2.0" -> 2.0
    '''
    try:
        inputString = inputString.replace(",", "")
        if ("%" in inputString):
            return float(inputString.replace("%", "")) / 100.0
        else:
            return float(inputString)
    except:
        return -1

class FundHistoricalValue:
    def __init__(self, date, netAssetValue, accumulativeNetAssetValue, dividends):
        self.Date = date
        self.NetAssetValue = netAssetValue
        self.AccumulativeNetAssetValue = accumulativeNetAssetValue
        self.Dividends = dividends

    def __str__(self):
        returnStr = ""

        for key in self.__dict__:
            returnStr += "%s," % self.__dict__[key]

        return returnStr[:-1] + "\n"

class FundElement:
    def __init__(self, elementType, code, name, ratio, numberOfShares, valueOfShares):
        self.ElementType = elementType
        self.Code = code
        self.Name = name
        self.Ratio = ratio
        self.NumberOfShares = numberOfShares
        self.ValueOfShares = valueOfShares

    def __str__(self):
        returnStr = ""

        for key in self.__dict__:
            returnStr += "%s," % self.__dict__[key]

        return returnStr[:-1] + "\n"

class FundInformation:
    def __init__(self, code, name, fundType, risk):
        self.Code = code
        self.Name = name
        self.FundType = fundType
        self.Risk = risk

    def __str__(self):
        returnStr = ""

        for key in self.__dict__:
            returnStr += "%s," % self.__dict__[key]

        return returnStr[:-1] + "\n"

def getLatestFile(folder):
    '''
        example: return "fundInformation_202102.csv" when the folder contains 3 files,
        "fundInformation_202101.csv", "fundInformation_202102.csv", "fundInformation_202012.csv"
    '''
    dictOfDate = {}
    for item in os.listdir(folder):
        dictOfDate[item] = int(item.split(".")[0].split("_")[-1])
    return sorted(dictOfDate.items(), key=lambda d:d[1], reverse=True)[0][0]

def getFolderNameInConfig(subFolder):
    '''
        the sub folder is a sub folder in ./data, confirm the folder exists and return the combination
    '''
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    # root folder of data
    rootFolderOfData = cf.get("Data", "rootFolderOfData")
    if not os.path.exists(rootFolderOfData):
        os.mkdir(rootFolderOfData)

    folderOfSubFolder = os.path.join(rootFolderOfData, cf.get("Data", subFolder))
    if not os.path.exists(folderOfSubFolder):
        os.mkdir(folderOfSubFolder)

    return folderOfSubFolder