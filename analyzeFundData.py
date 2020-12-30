import os
import pandas as pd
import math
import fire
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

    # days range of some funds are less than daysRangeToAnalyze
    ifAddAdjustedFund = False

    # read watchlist
    ifUseWatchList = True
    watchlist = []
    for line in  open("./data/watchlist.txt", "r"):
        watchlist.append(line.split("\n")[0])
    #print ("watchlist = %s" % watchlist)    # ['110011', '161028', '110020', '180003', '006479', '007994', '001015']

    # we should ignore some strange funds
    ignorelist = []
    for line in  open("./data/ignorelist.txt", "r"):
        ignorelist.append(line.split("\n")[0])
    #print ("ignorelist = %s" % ignorelist)  # ['009317', '009763']

    # read fund information
    dfForFundInformation = pd.read_csv("./data/fundInformation/fundInformation_202012.csv", dtype=object)

    # days range to analyze, 252 is the trading days in one year
    daysRangeInOneYear = 252
    daysRangeToAnalyze = daysRangeInOneYear * 3
    minDaysRange = 60

    rootFolder = "./data/historicalValue"

    # use fund "000001" be the standard of trading day
    pathOfFileStandard = os.path.join(rootFolder, "000934_202012.csv")
    dfStandard = pd.read_csv(pathOfFileStandard)
    dfStandard['Date'] = pd.to_datetime(dfStandard['Date'])
    dfStandard = dfStandard.head(daysRangeToAnalyze)
    dateStandard = dfStandard["Date"]
    firstDay = dateStandard[dateStandard.first_valid_index()]
    lastDay = dateStandard[dateStandard.last_valid_index()]
    #print (lastDay) # 2017-11-02 00:00:00

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
        #if file != "150282_202012.csv":
        #if file != "006401_202012.csv":
        #if file != "161122_202012.csv":
        #if file != "511620_202012.csv":
        #if file != "160135_202012.csv":
        #    continue
        fundCode = file.split("_")[0]

        # exclude some funds
        if fundCode in ignorelist:
            continue
        #if (fundCode == "000715") or (fundCode == "004638"):
        #    continue

        if ifUseWatchList and fundCode not in watchlist:
            continue
        if count >= 1000000:
            break
        print ("\ncount = %s\tfundCode = %s" % (count, fundCode))  # 180003
        currentFund = dfForFundInformation[dfForFundInformation["Code"] == fundCode]
        fundName = currentFund.iloc[0]["Name"]
        print ("fundName = %s" % fundName)  # 银华-道琼斯88指数A
        try:
            pathOfFile = os.path.join(rootFolder, file)
            df = pd.read_csv(pathOfFile)

            # remove empty line
            df = df.dropna(axis=0, subset=['AccumulativeNetAssetValue'])

            # like http://fundf10.eastmoney.com/jjjz_010476.html, the return in 30 days is 26%, so the annualized return is too high
            if df.shape[0] <= minDaysRange:
                continue

            # get growth ratio for AccumulativeNetAssetValue
            df["PreviousValue"] = df["AccumulativeNetAssetValue"].shift(-1)
            df["GrowthRatio"] = (df["AccumulativeNetAssetValue"] - df["PreviousValue"]) / df["PreviousValue"]
            
            # TODO: use adjust factor to do this
            # TODO: maybe we can use 日增长率 to adjust it
            # abandom those values before the date when GrowthRatio is too large (abs >= 1.0)
            df["AbsoluteGrowthRatio"] = df["GrowthRatio"].abs()
            #print (df[df["AbsoluteGrowthRatio"] > 1].first_valid_index())   # 346
            if df[df["AbsoluteGrowthRatio"] > 1].shape[0] > 0:
                df = df.loc[0:df[df["AbsoluteGrowthRatio"] > 1].first_valid_index() - 1]
            #print (df.tail(40))

            # reset the index
            df = df.dropna(axis=0, subset=['GrowthRatio'])
            df.reset_index(drop=True, inplace=True)

            # only choose much days
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[df["Date"] <= firstDay]
            df = df[df["Date"] >= lastDay]
            print (df)

            # too less data
            if df.shape[0] <= minDaysRange:
                continue

            netValue = df["AccumulativeNetAssetValue"]
            #print ("netValue = %s" % netValue)
            earliestNetValue = netValue[netValue.last_valid_index()]
            lastestNetValue = netValue[netValue.first_valid_index()]
            #print ("earliestNetValue = %s" % earliestNetValue)  # 3.004

            # count the days between first day and last day
            day = df['Date']
            firstDayInStandard = dfStandard[dfStandard['Date'] == day[day.first_valid_index()]].index
            lastDayInStandard = dfStandard[dfStandard['Date'] == day[day.last_valid_index()]].index
            try:
                countNetValue = (lastDayInStandard - firstDayInStandard)._data[0]
            except:
                # TODO: how about fund 519858, which trade in 2018-01-28 (Sunday)
                continue
            countNetValue += 1
            print ("countNetValue = %s" % countNetValue)   # 756
            
            # TODO: standardrize the risk in one year
            # assume the value is a list like (0, 1, 0, 1,...), growth ratio is a list like (1, -1, 1, -1,...)
            # set ddof be 0 to standardrize the risk by n, not (n - 1), then the std is 1, not related to countNetValue
            riskCurrent = df["GrowthRatio"].std(ddof=0)
            
            # use mean value to elimate the return fluctuation
            #returnCurrent = (netValue.mean()-earliestNetValue)/earliestNetValue/countNetValue*daysRangeInOneYear
            
            if not ifAddAdjustedFund:
                if countNetValue < daysRangeToAnalyze:
                    continue

            # use latest value to reflect the true percentage gain
            # this is worthful if the fund rise rapidly recently but have no change in long previous days
            returnCurrent = (lastestNetValue-earliestNetValue)/earliestNetValue/countNetValue*252
            riskList.append(riskCurrent)
            returnList.append(returnCurrent)

            # if countNetValue is less than daysRangeToAnalyze, add an * to claim this fund has been adjusted
            if countNetValue < daysRangeToAnalyze:
                fundCode += '*'
            fundNameList.append(fundCode)

            count += 1
        except Exception as e:
            raise e

    if not ifUseWatchList:
        plt.figure(figsize=(10, 10))
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
    else:
        nameOfPicture += "_noWatchlist"

    if ifAddAdjustedFund:
        nameOfPicture += "_addAdjustedFund"
    else:
        nameOfPicture += "_notAddAdjustedFund"

    plt.savefig("./data/%s.png" % nameOfPicture)
    print ("END.")

def getHistoricalValue():
    print ("Begin to get historical value...")

    # we should ignore some strange funds
    ignorelist = []
    for line in  open("./data/ignorelist.txt", "r"):
        ignorelist.append(line.split("\n")[0])
    #print ("ignorelist = %s" % ignorelist)  # ['009317', '009763']

    # read fund information
    dfForFundInformation = pd.read_csv("./data/fundInformation/fundInformation_202012.csv", dtype=object)

    # days range to analyze, 252 is the trading days in one year
    daysRangeInOneYear = 252
    daysRangeToAnalyze = daysRangeInOneYear * 3
    minDaysRange = 60

    rootFolder = "./data/historicalValue"

    # use fund "000001" be the standard of trading day
    pathOfFileStandard = os.path.join(rootFolder, "000934_202012.csv")
    dfStandard = pd.read_csv(pathOfFileStandard)
    dfStandard['Date'] = pd.to_datetime(dfStandard['Date'])
    dfStandard = dfStandard.head(daysRangeToAnalyze)
    dateStandard = dfStandard["Date"]
    firstDay = dateStandard[dateStandard.first_valid_index()]
    lastDay = dateStandard[dateStandard.last_valid_index()]
    #print (lastDay) # 2017-11-02 00:00:00

    # save data in this folder
    folderToSave = "data/dayInStandard/"
    if not os.path.exists(folderToSave):
        os.mkdir(folderToSave)

    count = 0
    for file in os.listdir(rootFolder):
        #if file != "110011_202012.csv":
        #    continue
        fundCode = file.split("_")[0]

        # exclude some funds
        if fundCode in ignorelist:
            continue

        if count >= 1000000:
            break
        print ("\ncount = %s\tfundCode = %s" % (count, fundCode))  # 180003
        currentFund = dfForFundInformation[dfForFundInformation["Code"] == fundCode]
        fundName = currentFund.iloc[0]["Name"]
        print ("fundName = %s" % fundName)  # 银华-道琼斯88指数A
        try:
            pathOfFile = os.path.join(rootFolder, file)
            df = pd.read_csv(pathOfFile)

            # remove empty line
            df = df.dropna(axis=0, subset=['AccumulativeNetAssetValue'])

            # like http://fundf10.eastmoney.com/jjjz_010476.html, the return in 30 days is 26%, so the annualized return is too high
            if df.shape[0] <= minDaysRange:
                continue

            # get growth ratio for AccumulativeNetAssetValue
            df["PreviousValue"] = df["AccumulativeNetAssetValue"].shift(-1)
            df["GrowthRatio"] = (df["AccumulativeNetAssetValue"] - df["PreviousValue"]) / df["PreviousValue"]
            
            # TODO: use adjust factor to do this
            # TODO: maybe we can use 日增长率 to adjust it
            # abandom those values before the date when GrowthRatio is too large (abs >= 1.0)
            df["AbsoluteGrowthRatio"] = df["GrowthRatio"].abs()
            #print (df[df["AbsoluteGrowthRatio"] > 1].first_valid_index())   # 346
            if df[df["AbsoluteGrowthRatio"] > 1].shape[0] > 0:
                df = df.loc[0:df[df["AbsoluteGrowthRatio"] > 1].first_valid_index() - 1]
            #print (df.tail(40))

            # reset the index
            df = df.dropna(axis=0, subset=['GrowthRatio'])
            df.reset_index(drop=True, inplace=True)

            # only choose much days
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[df["Date"] <= firstDay]
            df = df[df["Date"] >= lastDay]

            # too less data
            if df.shape[0] <= minDaysRange:
                continue

            #df['DayInStandard'] = df['Date']
            listOfDayInStandard = []
            for index, row in df.iterrows():
                try:
                    indexOfDayInStandard = dfStandard[dfStandard['Date'] == df.loc[index]['Date']].index
                    listOfDayInStandard.append(indexOfDayInStandard._data[0])
                # cannot find this day in standardFund
                except:
                    listOfDayInStandard.append(-1)
            df.insert(0, 'DayInStandard', listOfDayInStandard)

            # save data
            pathToSave = os.path.join(folderToSave, file)
            df.to_csv(pathToSave)

            count += 1
        except Exception as e:
            raise e

    print ("END.")

def getAverageSlopeForFundsInSameRange():
    '''
        in return-risk figure, the return is proportional to risk in most cases,
        so we can use slope(return/risk) as the feature of this fund, if we want
        to summarize funds in same range, we can use average slope to represent it.
    '''

if __name__ == "__main__":
    '''
        analyzeRisk
        analyzePortfolio
        analyzeHistoricalValue
        getHistoricalValue
    '''
    fire.Fire()