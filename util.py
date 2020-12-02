
# user_agent列表
user_agent_list = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.4.3.4000 Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 UBrowser/4.0.3214.0 Safari/537.36'
]

# referer列表
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
			"1"	-> 1.0
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

class FundElement:
	def __init__(self, stockCode, stockName, ratio, numberOfShares, valueOfShares):
		self.StockCode = stockCode
		self.StockName = stockName
		self.Ratio = ratio
		self.NumberOfShares = numberOfShares
		self.ValueOfShares = valueOfShares

	def __str__(self):
		returnStr = ""

		for key in self.__dict__:
			returnStr += "\t%s:\t%s\n" % (key, self.__dict__[key])

		return returnStr

class Fund:
	def __init__(self, code, name, fundType):
		self.Code = code
		self.Name = name
		self.FundType = fundType
		self.Portfolio = []

	def __str__(self):
		returnStr = ""

		for key in self.__dict__:
			if key != "Portfolio":
				returnStr += "%s:\t%s\n" % (key, self.__dict__[key])
			else:
				returnStr += "%s:\n" % key
				for item in self.__dict__[key]:
					returnStr += "%s\n" % item

		return returnStr