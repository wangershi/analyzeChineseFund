import os
import pandas as pd
import math
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')

def analyzePortfolio():
    print ("Begin to analyze portfolio...")

    rootFolder = "./data/portfolio"
    count = 0
    for file in os.listdir(rootFolder):
        if file != "110011_202012.csv":
            continue

        pathOfFile = os.path.join(rootFolder, file)
        df = pd.read_csv(pathOfFile)
        print (df[df["ElementType"] == "stock"])
        print (df[df["ElementType"] == "stock"]["Ratio"].sum())
    print ("END.")

def analyzeRisk():
    print ("Begin to analyze risk...")
    dictOfRisk = {}

    df = pd.read_csv("./data/fundInformation/fundInformation_202012.csv", dtype=object)
    risk = df["Risk"]
    print (risk.value_counts())
    print (risk.count())

    print ("END.")

def analyzeHistoricalValue():
    print ("Begin to analyze historical value...")

    # read watchlist
    ifUseWatchList = False
    watchlist = []
    for line in  open("./data/watchlist.txt", "r"):
        watchlist.append(line.split("\n")[0])
    #print ("watchlist = %s" % watchlist)    # ['110011', '161028', '110020', '180003', '006479', '007994', '001015']

    # read fund information
    dfForFundInformation = pd.read_csv("./data/fundInformation/fundInformation_202012.csv", dtype=object)

    # days range to analyze, 252 is the trading days in one year
    daysRangeInOneYear = 252
    daysRangeToAnalyze = daysRangeInOneYear * 3

    rootFolder = "./data/historicalValue"
    count = 0
    riskList = []
    returnList = []
    fundNameList = []
    for file in os.listdir(rootFolder):
        #if file != "110011_202012.csv":
        #if file != "000715_202012.csv":
        #if file != "006479_202012.csv":
        #if file != "502048_202012.csv":
        #if file != "150282_202012.csv":
        #    continue
        fundCode = file.split("_")[0]

        # exclude some funds
        #if (fundCode == "000715") or (fundCode == "004638"):
        #    continue

        if ifUseWatchList and fundCode not in watchlist:
            continue
        print ("\ncount = %s\tfundCode = %s" % (count, fundCode))  # 180003
        currentFund = dfForFundInformation[dfForFundInformation["Code"] == fundCode]
        fundName = currentFund.iloc[0]["Name"]
        print ("fundName = %s" % fundName)  # 银华-道琼斯88指数A
        try:
            pathOfFile = os.path.join(rootFolder, file)
            df = pd.read_csv(pathOfFile)

            # remove empty line
            df = df.dropna(axis=0, subset=['AccumulativeNetAssetValue'])
            if df.shape[0] <= 0:
                continue


            # get growth ratio for AccumulativeNetAssetValue
            df["PreviousValue"] = df["AccumulativeNetAssetValue"].shift(-1)
            df["GrowthRatio"] = (df["AccumulativeNetAssetValue"] - df["PreviousValue"]) / df["PreviousValue"]
            
            # TODO: abandom those values before the date when GrowthRatio is too large

            # reset the index
            df = df.dropna(axis=0, subset=['GrowthRatio'])
            df.reset_index(drop=True, inplace=True)
            df = df.head(daysRangeToAnalyze)

            if df.shape[0] <= 0:
                continue

            netValue = df["AccumulativeNetAssetValue"]
            earliestNetValue = netValue[netValue.last_valid_index()]
            countNetValue = netValue.count()
            print ("countNetValue = %s" % countNetValue)   # 252
            #print ("earliestNetValue = %s" % earliestNetValue)  # 3.004
            
            # TODO: standardrize the risk in one year
            # assume the value is a list like (0, 1, 0, 1,...), growth ratio is a list like (1, -1, 1, -1,...)
            # set ddof be 0 to standardrize the risk by n, not (n - 1), then the std is 1, not related to countNetValue
            riskCurrent = df["GrowthRatio"].std(ddof=0)
            
            # use mean value to elimate the return fluctuation
            #returnCurrent = (netValue.mean()-earliestNetValue)/earliestNetValue/countNetValue*daysRangeInOneYear
            
            # use latest value to reflect the true percentage gain
            # this is worthful if the fund rise rapidly recently but have no change in long previous days
            returnCurrent = (netValue[0]-earliestNetValue)/earliestNetValue/countNetValue*252
            riskList.append(riskCurrent)
            returnList.append(returnCurrent)

            # if countNetValue is less than daysRangeToAnalyze, add an * to claim this fund has been adjusted
            if countNetValue < daysRangeToAnalyze:
                fundCode += '*'
            fundNameList.append(fundCode)

            count += 1
        except Exception as e:
            raise e

    plt.scatter(riskList, returnList)
    plt.xlabel("Annualized Risk")
    plt.ylabel("Annualized Return")
    for i in range(len(fundNameList)):
        x = riskList[i]
        y = returnList[i]
        fundName = fundNameList[i]
        plt.text(x, y, fundName, fontsize=10)

    nameOfPicture = "risk_return"
    if ifUseWatchList:
        nameOfPicture += "_watchlist"

    plt.savefig("./data/%s.png" % nameOfPicture)
    print ("END.")

if __name__ == "__main__":
    #analyzeRisk()
    #analyzePortfolio()
    analyzeHistoricalValue()