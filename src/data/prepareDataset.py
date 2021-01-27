import fire
import os
import pandas as pd
import configparser
import datetime

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.data.analyzeData import getSparseMatrixForPortfolioInAllFunds

def prepareTrainDataset():
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    daysRangeInOneYear = int(cf.get("Data-Prepare", "daysRangeInOneYear"))
    numberOfYears = int(cf.get("Data-Prepare", "numberOfYears"))
    daysRange = daysRangeInOneYear * numberOfYears  # 756
    pathOfDfSparsePortfolio = cf.get("Data-Analyze", "pathOfDfSparsePortfolio")
    folderOfDayInStandard = cf.get("Data-Analyze", "folderOfDayInStandard")
    updateEveryMonth = cf.get("Data-Crawler-Frequency", "updateEveryMonth")

    if not os.path.exists(pathOfDfSparsePortfolio):
        getSparseMatrixForPortfolioInAllFunds()

    dfSparsePortfolio = pd.read_csv(pathOfDfSparsePortfolio, index_col=0)

    header = dfSparsePortfolio.columns[1:].to_list()

    ifSavePortfolioIndex = False
    if ifSavePortfolioIndex:
        dfPortfolioIndex = dfSparsePortfolio["FullElements"]
        dfPortfolioIndex.to_csv("data/dfPortfolioIndex.csv")

    folderToSaveTrainDataset = "data/trainDataset/"
    if not os.path.exists(folderToSaveTrainDataset):
        os.mkdir(folderToSaveTrainDataset)
    folderToSaveTestDataset = "data/testDataset/"
    if not os.path.exists(folderToSaveTestDataset):
        os.mkdir(folderToSaveTestDataset)

    month = "%s" % datetime.datetime.now().strftime(updateEveryMonth)   # 202101
    count = 0
    for fundCode in header:
        if count % 100 == 0:
            print ("count = %s\tfundCode=%s" % (count, fundCode))

        pathFund = os.path.join(folderOfDayInStandard, "%s_%s.csv" % (fundCode, month))
        
        if not os.path.exists(pathFund):
            continue

        dfFund = pd.read_csv(pathFund, index_col=0)

        maxDayInStandard = dfFund["DayInStandard"].max()
        # get train dataset which found more than 3 years
        if (maxDayInStandard >= (daysRange - 1)):
            # must have value in latest day
            minDayInStandard = dfFund["DayInStandard"].min()    # 755
            if (minDayInStandard != 0):
                continue

            # get the earliest value
            earliestDayForFund = dfFund[dfFund["DayInStandard"] == (daysRange - 1)] # 1.3769999999999998
            valueInEarliestDay = earliestDayForFund.iloc[0]["AccumulativeNetAssetValue"]    # 1.4696

            # count the adjust factor, we can get the value in 3 years by adjustFactorToLatestDay * (value[0]/value[day])
            dfFund["adjustFactorToLatestDay"] =  dfFund["AccumulativeNetAssetValue"] / valueInEarliestDay
            dfFund = dfFund[["DayInStandard", "adjustFactorToLatestDay"]]

            # abandon the latest day, it's meaningless
            dfFund.reset_index(drop=True, inplace=True)
            dfFund = dfFund.T.drop(labels=0, axis=1).T
            # reset index to concat with dfSparsePortfolioForThisFund
            dfFund.reset_index(drop=True, inplace=True)
            dfFund = dfFund.T

            dfSparsePortfolioForThisFund = dfSparsePortfolio[[fundCode]]
            dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.T
            # duplicate to concat with dfSparsePortfolioForThisFund
            dfSparsePortfolioForThisFund = pd.concat([dfSparsePortfolioForThisFund]*dfFund.shape[1])
            # reset index to concat with dfSparsePortfolioForThisFund
            dfSparsePortfolioForThisFund.reset_index(drop=True, inplace=True)
            dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.T

            dfDataset = pd.concat([dfSparsePortfolioForThisFund, dfFund], axis=0)

            dfDataset.to_csv(os.path.join(folderToSaveTrainDataset, "%s.csv" % fundCode))
        else:
            dfInLatestDay = dfFund[dfFund["DayInStandard"] == maxDayInStandard]

            dfInLatestDay[fundCode] = dfInLatestDay["DayInStandard"]
            dfInLatestDay = dfInLatestDay[[fundCode]]

            dfSparsePortfolioForThisFund = dfSparsePortfolio[[fundCode]]

            dfDataset = pd.concat([dfSparsePortfolioForThisFund, dfInLatestDay], axis=0)

            dfDataset.to_csv(os.path.join(folderToSaveTestDataset, "%s.csv" % fundCode))

        count += 1

if __name__ == "__main__":
	fire.Fire()