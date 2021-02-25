import pandas as pd
from pandas.tseries.offsets import DateOffset
import configparser
import fire
import os
import math
import numpy as np
import qlib
from qlib.data import D
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')

from sklearn.metrics.pairwise import cosine_similarity

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from src.util import getLatestFile, getFolderNameInConfig

def analyzeHistoricalValue(ifUseNewIssues = True, ifUseOldIssues = True, ifUseWatchList = False, ifUseAdjustFactorToLatestDay = False, ifPrintFundCode = False):
    '''
        Args:
            ifUseNewIssues: if use those funds whose days range are less than daysRangeToAnalyze
            ifUseOldIssues: if use those funds whose days range are more than daysRangeToAnalyze
            ifUseWatchList: if only figure funds in config/watchlist.txt
            ifUseAdjustFactorToLatestDay: if use adjustFactorToLatestDay generated by trainGBDT.py
            ifPrintFundCode: if print fund code, if so, the image would be larger
    '''
    print ("------------------------ Begin to analyze historical value... ------------------------")
    
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    # offset of days
    numberOfYears = int(cf.get("Parameter", "numberOfYears"))
    numberOfMonths = int(cf.get("Parameter", "numberOfMonths"))
    numberOfDays = int(cf.get("Parameter", "numberOfDays"))

    minDaysRange = int(cf.get("Parameter", "minDaysRange"))
    daysRangeInOneYear = int(cf.get("Parameter", "daysRangeInOneYear"))

    if ifUseAdjustFactorToLatestDay:
        dfAdjustFactorToLatestDay = pd.read_csv(cf.get("Analyze", "pathOfDfAdjustFactorToLatestDay"), dtype={'Unnamed: 0':object})

    # read watchlist
    watchlist = []
    for line in  open("./config/watchlist.txt", "r"):   # ['110011', '161028', '110020', '180003', '006479', '007994', '001015']
        watchlist.append(line.split("\n")[0])

    # we should ignore some strange funds
    ignorelist = []
    for line in  open("./config/ignorelist.txt", "r"):  # ['009317', '009763', '009764']
        ignorelist.append(line.split("\n")[0])

    # qlib init
    qlib.init(provider_uri='data/bin')

    # use one fund be the standard of trading day
    calendar = D.calendar(freq='day')
    lastDay = calendar[-1]  # 2021-02-10 00:00:00
    firstDay = lastDay - DateOffset(years=numberOfYears, months=numberOfMonths, days=numberOfDays)  # 2018-02-10 00:00:00
    
    # exclude the influence of days without trading
    calendarBetweenFirstDayAndLastDay = D.calendar(freq='day', start_time=firstDay, end_time=lastDay)
    firstDayToAnalyze = calendarBetweenFirstDayAndLastDay[0]
    lastDayToAnalyze = calendarBetweenFirstDayAndLastDay[-1]
    daysRangeToAnalyze = (lastDayToAnalyze - firstDayToAnalyze).days    # 1094

    count = 0
    riskListForOldIssues = []
    returnListForOldIssues = []
    fundCodeListForOldIssues = []
    riskListForNewIssues = []
    returnListForNewIssues = []
    fundCodeListForNewIssues = []

    instruments = D.instruments(market='all')
    for file in D.list_instruments(instruments=instruments, as_list=True):
        fundCode = file.split("_")[0]   # 000001
        
        # exclude some funds
        if fundCode in ignorelist:
            continue

        if ifUseWatchList and fundCode not in watchlist:
            continue

        if count % 100 == 0:
            print ("\ncount = %s\tfundCode = %s" % (count, fundCode))  # 180003

        try:
            # read file and remove empty line
            df = D.features([file], [
                '$AccumulativeNetAssetValue',
                '($AccumulativeNetAssetValue - Ref($AccumulativeNetAssetValue, 1)) / Ref($AccumulativeNetAssetValue, 1)'
                ], start_time=firstDayToAnalyze, end_time=lastDayToAnalyze)
            df.columns = [
                'AccumulativeNetAssetValue',
                'GrowthRatio'
                ]
            #df = df.unstack(level=0)
            df["datetime"] = df.index.levels[1]

            # abandom those values before the date when GrowthRatio is too large (abs >= 1.0)
            df["AbsoluteGrowthRatio"] = df["GrowthRatio"].abs()
            if df[df["AbsoluteGrowthRatio"] > 1].shape[0] > 0:
                df = df.loc[0:df[df["AbsoluteGrowthRatio"] > 1].first_valid_index() - 1]

            # reset the index
            df = df.dropna(axis=0, subset=['datetime', 'GrowthRatio']).reset_index(drop=True)

            # like http://fundf10.eastmoney.com/jjjz_010476.html, the return in 30 days is 26%, so the annualized return is too high
            if df.shape[0] <= minDaysRange:
                continue
            
            # count the days between first day and last day
            day = df['datetime']
            # TODO: how about fund 519858, which trade in 2018-01-28 (Sunday)
            firstDayInThisFund = day[day.first_valid_index()]   # 2018-02-12 00:00:00, 2018-02-10 is Satuaday
            lastDayInThisFund = day[day.last_valid_index()] # 2021-02-10 00:00:00
            daysRange = (lastDayInThisFund - firstDayInThisFund).days   # 1094

            # get the value in important days
            earliestNetValue = df[df['datetime'] == firstDayInThisFund]["AccumulativeNetAssetValue"].tolist()[0] # 3.49
            lastestNetValue = df[df['datetime'] == lastDayInThisFund]["AccumulativeNetAssetValue"].tolist()[0] # 4.046

            # standardrize the risk in one year
            # assume the value is a list like (0, 1, 0, 1,...), growth ratio is a list like (1, -1, 1, -1,...)
            # set ddof be 0 to standardrize the risk by n, not (n - 1), then the std is 1, not related to daysRange
            riskCurrent = df["GrowthRatio"].std(ddof=0)
            returnCurrent = (lastestNetValue-earliestNetValue)/earliestNetValue/daysRange*daysRangeInOneYear

            if not ifUseNewIssues:
                if (firstDayInThisFund - firstDayToAnalyze).days > 0:
                    continue
            else:
                # use latest value to reflect the true percentage gain
                # this is worthful if the fund rise rapidly recently but have no change in long previous days
                if ifUseAdjustFactorToLatestDay:
                    if (firstDayInThisFund - firstDayToAnalyze).days > 0:
                        # if the fund code locates in dfAdjustFactorToLatestDay, adjust the latest value and days range
                        adjustedFactor = dfAdjustFactorToLatestDay[fundCode]
                        adjustedFactor = adjustedFactor[adjustedFactor.first_valid_index()] # 0.987561058590916
                        lastestNetValue = lastestNetValue * adjustedFactor
                        returnCurrent = (lastestNetValue-earliestNetValue)/earliestNetValue/daysRangeToAnalyze*daysRangeInOneYear

            # new issues
            if (firstDayInThisFund - firstDayToAnalyze).days > 0:
                riskListForNewIssues.append(riskCurrent)
                returnListForNewIssues.append(returnCurrent)
                fundCodeListForNewIssues.append(fundCode)
            else:
                riskListForOldIssues.append(riskCurrent)
                returnListForOldIssues.append(returnCurrent)
                fundCodeListForOldIssues.append(fundCode)
            
            count += 1
        except Exception as e:
            print ("fundCode = %s\terror = %s" % (fundCode, e))
            continue

    if not ifUseWatchList and ifPrintFundCode:
        plt.figure(figsize=(10, 10))
    if ifUseOldIssues:
        plt.scatter(riskListForOldIssues, returnListForOldIssues, c='k')
    if ifUseNewIssues:
        plt.scatter(riskListForNewIssues, returnListForNewIssues, c='k')
    plt.xlabel("Risk")
    plt.ylabel("Annualized return")

    plt.xlim((0, 0.06))
    plt.ylim((-0.4, 1.4))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')

    if ifPrintFundCode:
        if ifUseOldIssues:
            for i in range(len(fundCodeListForOldIssues)):
                x = riskListForOldIssues[i]
                y = returnListForOldIssues[i]
                fundCode = fundCodeListForOldIssues[i]
                plt.text(x, y, fundCode, fontsize=10)

        if ifUseNewIssues:
            for i in range(len(fundCodeListForNewIssues)):
                x = riskListForNewIssues[i]
                y = returnListForNewIssues[i]
                fundCode = fundCodeListForNewIssues[i]
                plt.text(x, y, fundCode, fontsize=10)

    nameOfPicture = "risk_return"
    nameOfPicture = nameOfPicture + "_watchlist" if ifUseWatchList else nameOfPicture + "_noWatchlist"
    nameOfPicture = nameOfPicture + "_useNewIssues" if ifUseNewIssues else nameOfPicture + "_notUseNewIssues"
    nameOfPicture = nameOfPicture + "_useOldIssues" if ifUseOldIssues else nameOfPicture + "_notUseOldIssues"
    nameOfPicture = nameOfPicture + "_useAdjustFactor" if ifUseAdjustFactorToLatestDay else nameOfPicture + "_notUseAdjustFactor"

    plt.savefig("./image/%s.png" % nameOfPicture)
    
    print ("------------------------ Done. ------------------------")


def getAverageSlopeForFundsInSameRange(ifUseAdjustFactorToLatestDay=True):
    '''
        in return-risk figure, the return is proportional to risk in most cases,
        so we can use slope(return/risk) as the feature of this fund, if we want
        to summarize funds in same range, we can use average slope to represent it.
    '''
    print ("------------------------ Begin to get average slope for funds in same range... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    daysRangeInOneYear = int(cf.get("Parameter", "daysRangeInOneYear"))  # 252 is the trading days in one year
    numberOfYears = int(cf.get("Parameter", "numberOfYears"))
    daysRangeToAnalyze = daysRangeInOneYear * numberOfYears
    divideNumber = int(cf.get("Analyze", "divideNumber"))
    folderOfDayInStandard = getFolderNameInConfig("folderOfDayInStandard")    # the folder of data which day is standard

    # if use adjustFactorToLatestDay generated by trainGBDT.py
    if ifUseAdjustFactorToLatestDay:
        dfAdjustFactorToLatestDay = pd.read_csv(cf.get("Analyze", "pathOfDfAdjustFactorToLatestDay"), dtype={'Unnamed: 0':object})

    # didn't generate dayInStandard before
    if len(os.listdir(folderOfDayInStandard)) <= 0:
        getHistoricalValue()

    dictOfSlopeInCountNetValue = {}
    dictOfReturnInCountNetValue = {}
    dictOfRiskInCountNetValue = {}

    count = 0
    for file in os.listdir(folderOfDayInStandard):
        fundCode = file.split("_")[0]

        if count % 100 == 0:
            print ("count = %s\tfundCode = %s" % (count, fundCode))  # 180003

        try:
            df = pd.read_csv(os.path.join(folderOfDayInStandard, file))

            netValue = df["AccumulativeNetAssetValue"]
            earliestNetValue = netValue[netValue.last_valid_index()]    # 3.004
            lastestNetValue = netValue[netValue.first_valid_index()]

            dayInStandard = df["DayInStandard"]
            firstDayInStandard = dayInStandard[dayInStandard.first_valid_index()]
            lastDayInStandard = dayInStandard[dayInStandard.last_valid_index()]
            countNetValue = lastDayInStandard - firstDayInStandard + 1  # 756

            # TODO: standardrize the risk in one year
            # assume the value is a list like (0, 1, 0, 1,...), growth ratio is a list like (1, -1, 1, -1,...)
            # set ddof be 0 to standardrize the risk by n, not (n - 1), then the std is 1, not related to countNetValue
            riskCurrent = df["GrowthRatio"].std(ddof=0) # 0.014161537768387899

            # use latest value to reflect the true percentage gain
            # this is worthful if the fund rise rapidly recently but have no change in long previous days
            countNetValueAdjusted = countNetValue
            if ifUseAdjustFactorToLatestDay:
                if countNetValue < daysRangeToAnalyze:
                    # if the fund code locates in dfAdjustFactorToLatestDay
                    try:
                        # adjust the latest value and days range
                        adjustedFactor = dfAdjustFactorToLatestDay[fundCode]
                        adjustedFactor = adjustedFactor[adjustedFactor.first_valid_index()]
                        lastestNetValue = lastestNetValue * adjustedFactor
                        countNetValueAdjusted = daysRangeToAnalyze
                    except Exception as e:
                        print (e)
                        continue

            # use latest value to reflect the true percentage gain
            # this is worthful if the fund rise rapidly recently but have no change in long previous days
            returnCurrent = (lastestNetValue-earliestNetValue)/earliestNetValue/countNetValueAdjusted*daysRangeInOneYear    # 0.3984541490442937

            slope = returnCurrent / riskCurrent # 28.136361711631576

            # TODO: exclude 005337
            if math.isnan(slope):
                continue

            # count them in period, not a single day
            approximateCountValue = countNetValue // divideNumber * divideNumber

            if approximateCountValue not in dictOfSlopeInCountNetValue.keys():
                dictOfSlopeInCountNetValue[approximateCountValue] = []
            dictOfSlopeInCountNetValue[approximateCountValue].append(slope)

            if approximateCountValue not in dictOfReturnInCountNetValue.keys():
                dictOfReturnInCountNetValue[approximateCountValue] = []
            dictOfReturnInCountNetValue[approximateCountValue].append(returnCurrent)

            if approximateCountValue not in dictOfRiskInCountNetValue.keys():
                dictOfRiskInCountNetValue[approximateCountValue] = []
            dictOfRiskInCountNetValue[approximateCountValue].append(riskCurrent)

            count += 1
        except Exception as e:
            raise e

    # ------------------------ Plot Return/Risk ------------------------
    plt.xlim((0, 800))
    plt.ylim((-40, 100))
    plt.xlabel("Count of trading days")
    plt.ylabel("Return/Risk")
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    for key in dictOfSlopeInCountNetValue.keys():
        n = len(dictOfSlopeInCountNetValue[key])    # Number of observations
        mean = sum(dictOfSlopeInCountNetValue[key]) / n # Mean of the data
        deviations = [(x - mean) ** 2 for x in dictOfSlopeInCountNetValue[key]] # Square deviations
        standardDeviation = math.sqrt(sum(deviations) / n)  # standard deviation

        plt.errorbar(key, mean, standardDeviation, c='k', marker='+')

    nameOfReturnRisk = "averageSlopeForReturnRisk_%s" % divideNumber

    if ifUseAdjustFactorToLatestDay:
        nameOfReturnRisk += "_useAdjustFactor"
    else:
        nameOfReturnRisk += "_notUseAdjustFactor"

    plt.savefig("./image/%s.png" % nameOfReturnRisk)

    # ------------------------ Plot Return ------------------------
    plt.clf()
    plt.xlim((0, 800))
    plt.ylim((-0.2, 0.6))
    plt.xlabel("Count of trading days")
    plt.ylabel("Return")
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    listOfMean = []
    for key in dictOfReturnInCountNetValue.keys():
        n = len(dictOfReturnInCountNetValue[key])   # Number of observations
        mean = sum(dictOfReturnInCountNetValue[key]) / n    # Mean of the data
        listOfMean.append(mean)
        deviations = [(x - mean) ** 2 for x in dictOfReturnInCountNetValue[key]]    # Square deviations
        standardDeviation = math.sqrt(sum(deviations) / n)  # standard deviation

        plt.errorbar(key, mean, standardDeviation, c='k', marker='+')

    nameOfReturn = "averageReturn_%s" % divideNumber

    # get the standard deviation of mean
    standardDeviationOfReturn = np.std(listOfMean, ddof = 0)
    print ("standardDeviationOfReturn = %s" % standardDeviationOfReturn)

    if ifUseAdjustFactorToLatestDay:
        nameOfReturn += "_useAdjustFactor"
    else:
        nameOfReturn += "_notUseAdjustFactor"
    plt.savefig("./image/%s.png" % nameOfReturn)

    # ------------------------ Plot Risk ------------------------
    plt.clf()
    plt.xlim((0, 800))
    plt.ylim((-0.005, 0.02))
    plt.xlabel("Count of trading days")
    plt.ylabel("Risk")
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    for key in dictOfRiskInCountNetValue.keys():
        n = len(dictOfRiskInCountNetValue[key]) # Number of observations
        mean = sum(dictOfRiskInCountNetValue[key]) / n  # Mean of the data
        deviations = [(x - mean) ** 2 for x in dictOfRiskInCountNetValue[key]]  # Square deviations
        standardDeviation = math.sqrt(sum(deviations) / n)  # standard deviation

        plt.errorbar(key, mean, standardDeviation, c='k', marker='+')

    nameOfRisk = "averageRisk_%s" % divideNumber

    if ifUseAdjustFactorToLatestDay:
        nameOfRisk += "_useAdjustFactor"
    else:
        nameOfRisk += "_notUseAdjustFactor"
    plt.savefig("./image/%s.png" % nameOfRisk)

    print ("------------------------ Done. ------------------------")


def getDfMerge():
    print ("------------------------ Begin to get dfMerge... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    
    # offset of days
    numberOfYears = int(cf.get("Parameter", "numberOfYears"))
    numberOfMonths = int(cf.get("Parameter", "numberOfMonths"))
    numberOfDays = int(cf.get("Parameter", "numberOfDays"))

    # use one fund be the standard of trading day
    calendar = D.calendar(freq='day')
    lastDay = calendar[-1]  # 2021-02-10 00:00:00
    firstDay = lastDay - DateOffset(years=numberOfYears, months=numberOfMonths, days=numberOfDays)  # 2018-02-10 00:00:00
    
    # exclude the influence of days without trading
    calendarBetweenFirstDayAndLastDay = D.calendar(freq='day', start_time=firstDay, end_time=lastDay)
    firstDayToAnalyze = calendarBetweenFirstDayAndLastDay[0]
    lastDayToAnalyze = calendarBetweenFirstDayAndLastDay[-1]

    count = 0

    instruments = D.instruments(market='all')
    for file in D.list_instruments(instruments=instruments, as_list=True):
        fundCode = file.split("_")[0]

        if count <= 700:
            count += 1
            continue
        
        if count % 100 == 0:
            print ("count = %s\tfundCode = %s" % (count, fundCode))

        # read file and remove empty line
        df = D.features([file], [
            '$AccumulativeNetAssetValue'
            ], start_time=firstDayToAnalyze, end_time=lastDayToAnalyze)
        df.columns = [
            "AccumulativeNetAssetValue_%s" % fundCode
            ]
        #df = df.unstack(level=0)
        try:
            df["datetime"] = df.index.levels[1]
        except:
            continue

        # reset the index
        df = df.dropna(axis=0, subset=['datetime']).reset_index(drop=True)

        try:
            dfMerge = pd.merge(dfMerge, df, on=['datetime'], how='outer')
        except:
            dfMerge = df

        count += 1

    dfMerge.to_csv("data/dfMerge.csv")

    print ("------------------------ Done. ------------------------")

    return dfMerge


def getCorrelationMatrixForOneFund(ifGetCorrFromFile = True, ifGetDfMergeFromFile = True, fundCodeToAnalyze="110011"):
    print ("------------------------ Begin to get Pearson's correlation matrix for fund '%s'... ------------------------" % fundCodeToAnalyze)
    
    # qlib init
    qlib.init(provider_uri='data/bin')

    if ifGetCorrFromFile:
        if not os.path.exists("data/corr.csv"):
            ifGetCorrFromFile = False

    if not ifGetCorrFromFile:
        if ifGetDfMergeFromFile:
            if not os.path.exists("data/dfMerge.csv"):
                ifGetDfMergeFromFile = False

        if ifGetDfMergeFromFile:
            dfMerge = pd.read_csv("data/dfMerge.csv", index_col=0)
        else:
            dfMerge = getDfMerge()

        dfMerge = dfMerge.drop(labels='datetime',axis=1)

        # count correlation
        corr = dfMerge.corr()
        corr.to_csv("data/corr.csv")
    else:
        corr = pd.read_csv("data/corr.csv", index_col=0)

    print ("corr = %s" % corr)

    corrFund = corr["AccumulativeNetAssetValue_%s" % fundCodeToAnalyze].dropna(axis=0)

    dictOfCorr = {}
    minNumber = 0.98
    nameFund = "%s" % fundCodeToAnalyze

    instruments = D.instruments(market='all')
    for file in D.list_instruments(instruments=instruments, as_list=True):
        fund = file.split("_")[0]
        if fund == nameFund:
            continue

        nameDf = "AccumulativeNetAssetValue_%s" % fund

        try:
            corrSingle = float("%.1f" % corrFund[nameDf])
            if corrSingle not in dictOfCorr:
                dictOfCorr[corrSingle] = 1
            else:
                dictOfCorr[corrSingle] += 1
        except:
            continue

    # show it in image
    plt.figure(figsize=(10, 5))
    plt.ylim((0, 3000))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.xlabel("Correlation")
    plt.ylabel("Count")
    for key in sorted(dictOfCorr.keys()):
        if key != 'nan':
            if key == minNumber:
                plt.bar("<=%s" % str(key), dictOfCorr[key], width=0.8, fc='k')
            else:
                plt.bar(str(key), dictOfCorr[key], width=0.8, fc='k')

    plt.savefig("./image/correlation_%s.png" % nameFund)

    print ("------------------------ Done. ------------------------")


def getCorrelationMatrixForAllFunds(ifGetCorrFromFile = True, ifGetDfMergeFromFile = True):
    print ("Begin to get Pearson's correlation matrix for all funds...")

    # qlib init
    qlib.init(provider_uri='data/bin')
    
    if ifGetCorrFromFile:
        if not os.path.exists("data/corr.csv"):
            ifGetCorrFromFile = False

    if not ifGetCorrFromFile:
        if ifGetDfMergeFromFile:
            if not os.path.exists("data/dfMerge.csv"):
                ifGetDfMergeFromFile = False

        if ifGetDfMergeFromFile:
            dfMerge = pd.read_csv("data/dfMerge.csv", index_col=0)
        else:
            dfMerge = getDfMerge()

        dfMerge = dfMerge.drop(labels='datetime',axis=1)

        # count correlation
        corr = dfMerge.corr()
        corr.to_csv("data/corr.csv")
    else:
        corr = pd.read_csv("data/corr.csv", index_col=0)

    print (corr)

    dictOfMaxCorr = {}
    minNumber = 0.9

    instruments = D.instruments(market='all')
    for file in D.list_instruments(instruments=instruments, as_list=True):
        fund = file.split("_")[0]
        nameDf = "AccumulativeNetAssetValue_%s" % fund

        # nameDf don't exist in corr
        try:
            corrSingle = corr[nameDf].dropna(axis=0)
            corrWithoutSelf = corrSingle.drop(labels=nameDf, axis=0)
        except:
            continue

        maxCorr = float(corrWithoutSelf.max())
        maxCorr = float("%.2f" % maxCorr)
        if maxCorr <= minNumber:
            maxCorr = minNumber
        if maxCorr not in dictOfMaxCorr:
            dictOfMaxCorr[maxCorr] = 1
        else:
            dictOfMaxCorr[maxCorr] += 1

    print (dictOfMaxCorr)

    # show it in image
    plt.figure(figsize=(15, 5))
    plt.ylim((0, 5000))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.xlabel("Maximum correlation")
    plt.ylabel("Count")
    for key in sorted(dictOfMaxCorr.keys()):
        if key != 'nan':
            if key == minNumber:
                plt.bar("<=%s" % str(key), dictOfMaxCorr[key], width=0.8, fc='k')
            else:
                plt.bar(str(key), dictOfMaxCorr[key], width=0.8, fc='k')

    plt.savefig("./image/maximum_correlation.png")

    print ("END.")


def getAllElementsInPortfolio():
    print ("------------------------ Begin to get all elements in portfolio... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    folderOfPortfolio = getFolderNameInConfig("folderOfPortfolio")  # the folder to save the portfolio
    pathOfDfMergeFullElements = cf.get("Analyze", "pathOfDfMergeFullElements")

    count = 0
    countAllElements = 0
    for file in os.listdir(folderOfPortfolio):
        if count % 100 == 0:
            print ("count = %s\tfile = %s" % (count, file))
        pathFund = os.path.join(folderOfPortfolio, file)
        df = pd.read_csv(pathFund)

        # add stock code, because, "中国平安" can represents two stocks, "601318" and "02318"
        df["FullElements"] = df["ElementType"] + "_" + df["Code"].astype(str) + "_" + df["Name"]
        dfFullElements = df["FullElements"]
        countAllElements += dfFullElements.shape[0]

        if count == 0:
            dfMergeFullElements = dfFullElements
        else:
            dfMergeFullElements = pd.merge(dfMergeFullElements, dfFullElements, on=['FullElements'], how='outer')

        count += 1

    # merge is not useful
    dfMergeFullElements = dfMergeFullElements.drop_duplicates(subset=['FullElements'],keep='first')\
        .sort_values(by='FullElements')\
        .reset_index(drop=True)
    print (dfMergeFullElements)
    print ("countAllElements = %s" % countAllElements)

    dfMergeFullElements.to_csv(pathOfDfMergeFullElements)
    print ("------------------------ Done. ------------------------")

def getSparseMatrixForPortfolioInAllFunds():
    print ("------------------------ Begin to get sparse matrix for portfolio in all funds... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    folderOfPortfolio = getFolderNameInConfig("folderOfPortfolio")  # the folder to save the portfolio
    pathOfDfMergeFullElements = cf.get("Analyze", "pathOfDfMergeFullElements")
    pathOfDfSparsePortfolio = cf.get("Analyze", "pathOfDfSparsePortfolio")

    if not os.path.exists(pathOfDfMergeFullElements):
        getAllElementsInPortfolio()

    dfSparsePortfolio = pd.read_csv(pathOfDfMergeFullElements, index_col=0)
    
    count = 0
    for file in os.listdir(folderOfPortfolio):
        fundCode = file.split("_")[0]

        if count % 100 == 0:
            print ("count = %s\tfundCode = %s" % (count, fundCode))

        pathFund = os.path.join(folderOfPortfolio, file)
        df = pd.read_csv(pathFund)
        df["FullElements"] = df["ElementType"] + "_" + df["Code"].astype(str) + "_" + df["Name"]
        # fund "090019" have two bonds "bond_170207_17国开07"
        df = df.drop_duplicates(subset=['FullElements'],keep='first')\
            .fillna(0)\
            .replace(-1, 0)

        try:
            s = df.set_index('FullElements')['Ratio']
            dfSparsePortfolio[fundCode] = dfSparsePortfolio["FullElements"].map(s)
        except Exception as e:
            print ("fundCode=%s\tdf=%s\ts=%s\tdfSparsePortfolio=%s" % (fundCode, df, s, dfSparsePortfolio))
            raise e

        count += 1

    print (dfSparsePortfolio)
    dfSparsePortfolio.to_csv(pathOfDfSparsePortfolio)

    print ("------------------------ Done. ------------------------")

def getCosineOfSparseMatrixForPortfolio(countCosineSimilarityManually=False):
    '''
        use sklearn to get the cosine similarity of portfolio
        '1' means these 2 portfolios are similar, also means the degree equals to 0
    '''
    print ("------------------------ Begin to get cosine of sparse matrix for portfolio... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    pathOfDfSparsePortfolio = cf.get("Analyze", "pathOfDfSparsePortfolio")
    pathOfDfCosineSimilarityForPortfolio = cf.get("Analyze", "pathOfDfCosineSimilarityForPortfolio")

    if not os.path.exists(pathOfDfSparsePortfolio):
        getSparseMatrixForPortfolioInAllFunds()

    dfSparsePortfolio = pd.read_csv(pathOfDfSparsePortfolio, index_col=0)
    dfSparsePortfolio = dfSparsePortfolio.drop(labels="FullElements", axis=1)
    header = dfSparsePortfolio.columns

    # count cosine similarity manually
    if countCosineSimilarityManually:
        dfSparsePortfolio = dfSparsePortfolio.replace(-1, 0)
        dfSparsePortfolio["AA"] = dfSparsePortfolio["150343"] * dfSparsePortfolio["150343"]
        dfSparsePortfolio["BB"] = dfSparsePortfolio["001347"] * dfSparsePortfolio["001347"]
        dfSparsePortfolio["AB"] = dfSparsePortfolio["150343"] * dfSparsePortfolio["001347"]
        print (dfSparsePortfolio["AA"].sum())
        print (dfSparsePortfolio["AB"].sum())
        print (dfSparsePortfolio["BB"].sum())

    # cosine_similarity required
    # fill nan with 0, 0 is meaningless when count cosine
    # -1 represent not found, so we should set this be zero
    dfSparsePortfolio = dfSparsePortfolio.T.fillna(0).replace(-1, 0)
    print (dfSparsePortfolio)

    cosineSimilarityForPortfolio = cosine_similarity(dfSparsePortfolio)
    dfCosineSimilarityForPortfolio = pd.DataFrame(cosineSimilarityForPortfolio, columns=header)
    print (dfCosineSimilarityForPortfolio)

    dfCosineSimilarityForPortfolio.to_csv(pathOfDfCosineSimilarityForPortfolio)

    print ("------------------------ Done. ------------------------")

def analyzeCosineForOneFund(nameFund="110011"):
    print ("------------------------ Begin to analyze cosine for fund '%s'... ------------------------" % nameFund)

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    pathOfDfCosineSimilarityForPortfolio = cf.get("Analyze", "pathOfDfCosineSimilarityForPortfolio")

    if not os.path.exists(pathOfDfCosineSimilarityForPortfolio):
        getCosineOfSparseMatrixForPortfolio()

    dfCosineSimilarityForPortfolio = pd.read_csv(pathOfDfCosineSimilarityForPortfolio, index_col=0)
    
    cosineFund = dfCosineSimilarityForPortfolio[nameFund].dropna(axis=0)
    print ("cosineFund = %s" % cosineFund)

    dictOfBucket = {}
    for i, v in cosineFund.items():
        name = dfCosineSimilarityForPortfolio.columns.values[i]
        if name == nameFund:
            continue

        cosine = "%.1f" % v
        if cosine == "1.0":
            print (name)
        if cosine not in dictOfBucket.keys():
            dictOfBucket[cosine] = 1
        else:
            dictOfBucket[cosine] += 1

    print (dictOfBucket)

    # show it in image
    plt.figure(figsize=(10, 5))
    plt.ylim((0, 4000))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.xlabel("Cosine")
    plt.ylabel("Count")
    for key in sorted(dictOfBucket):
        plt.bar(key, dictOfBucket[key], width=0.8, fc='k')

    plt.savefig("./image/cosine_%s.png" % nameFund)

    print ("------------------------ Done. ------------------------")


def compareCosineAndPearsonCorr(ifFetchCosineFundFromFile=True, ifFetchCorrFundFromFile=True, nameFund="110011"):
    print ("------------------------ Begin to compare consine and Pearson's corr... ------------------------")
    
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    pathOfDfCosineSimilarityForPortfolio = cf.get("Analyze", "pathOfDfCosineSimilarityForPortfolio")

    if not os.path.exists(pathOfDfCosineSimilarityForPortfolio):
        getCosineOfSparseMatrixForPortfolio()

    if ifFetchCosineFundFromFile:
        if not os.path.exists("data/cosineFundFor%s.csv" % nameFund):
            ifFetchCosineFundFromFile = False

    if not ifFetchCosineFundFromFile:
        dfCosineSimilarityForPortfolio = pd.read_csv(pathOfDfCosineSimilarityForPortfolio, index_col=0)
        header = dfCosineSimilarityForPortfolio.columns
        dfCosineSimilarityForPortfolio.set_index(header, inplace=True)
        cosineFund = dfCosineSimilarityForPortfolio[nameFund].dropna(axis=0)
        cosineFund.to_csv("data/cosineFundFor%s.csv" % nameFund)
    else:
        cosineFund = pd.read_csv("data/cosineFundFor%s.csv" % nameFund, index_col=0)
        
    cosineFund["b"] = cosineFund.T.columns
    cosineFund["a"] = "AccumulativeNetAssetValue_" + cosineFund["b"].apply(str)
    cosineFund = cosineFund.drop(labels='b',axis=1)
    print ("cosineFund = \n%s" % cosineFund)

    if ifFetchCorrFundFromFile:
        if not os.path.exists("data/corrFundFor%s.csv" % nameFund):
            ifFetchCorrFundFromFile = False

    if not ifFetchCorrFundFromFile:
        corr = pd.read_csv("data/corr.csv", index_col=0)
        corrFund = corr["AccumulativeNetAssetValue_%s" % nameFund].dropna(axis=0)
        corrFund.to_csv("data/corrFundFor%s.csv" % nameFund)
        
    corrFund = pd.read_csv("data/corrFundFor%s.csv" % nameFund, index_col=0)

    corrFund["a"] = corrFund.T.columns
    
    df = pd.merge(cosineFund, corrFund, on=['a'], how='outer')

    # delete useless columns
    df = df.drop(labels='a', axis=1)
    print (df.corr())
    df.plot.scatter(x=nameFund, y='AccumulativeNetAssetValue_%s' % nameFund, c='k')
    plt.xlim((0, 1.0))
    plt.ylim((-1.0, 1.0))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.xlabel("Cosine")
    plt.ylabel("Pearson's correlation")
    plt.savefig("./image/cosine_PearsonCorr_%s.png" % nameFund)

    print ("------------------------ Done. ------------------------")


if __name__ == "__main__":
    fire.Fire()