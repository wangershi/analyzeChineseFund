import fire
import os
import pandas as pd
import configparser

def getAllElementsInPortfolio():
    rootFolder = "./data/portfolio"

    count = 0
    countAllElements = 0
    for file in os.listdir(rootFolder):
        if count >= 100000000000:
            break

        if count % 100 == 0:
            print ("count = %s\tfile = %s" % (count, file))
        pathFund = os.path.join(rootFolder, file)
        df = pd.read_csv(pathFund)

        # add stock code, because, "中国平安" can represents two stocks, "601318" and "02318"
        df["FullElements"] = df["ElementType"] + "_" + df["Code"].astype(str) + "_" + df["Name"]
        dfFullElements = df["FullElements"]
        countAllElements += dfFullElements.shape[0]
        #print (dfFullElements)

        if count == 0:
            dfMergeFullElements = dfFullElements
        else:
            dfMergeFullElements = pd.merge(dfMergeFullElements, dfFullElements, on=['FullElements'], how='outer')

        count += 1

    # merge is not useful
    dfMergeFullElements = dfMergeFullElements.drop_duplicates(subset=['FullElements'],keep='first')
    dfMergeFullElements = dfMergeFullElements.sort_values(by='FullElements')
    dfMergeFullElements.reset_index(drop=True, inplace=True)
    print (dfMergeFullElements)
    print ("countAllElements = %s" % countAllElements)

    dfMergeFullElements.to_csv("data/dfMergeFullElements.csv")

def getSparseMatrixForPortfolioInAllFunds():
    dfSparsePortfolio = pd.read_csv("data/dfMergeFullElements.csv", index_col=0)
    
    rootFolder = "./data/portfolio"

    count = 0
    for file in os.listdir(rootFolder):
        if count >= 100000000:
            break

        fundCode = file.split("_")[0]

        if count % 100 == 0:
            print ("count = %s\tfundCode = %s" % (count, fundCode))

        pathFund = os.path.join(rootFolder, file)
        df = pd.read_csv(pathFund)
        df["FullElements"] = df["ElementType"] + "_" + df["Code"].astype(str) + "_" + df["Name"]
        # fund "090019" have two bonds "bond_170207_17国开07"
        df = df.drop_duplicates(subset=['FullElements'],keep='first')
        #print ("df = %s" % df)

        try:
            s = df.set_index('FullElements')['Ratio']
            #print ("s = %s" % s)
            dfSparsePortfolio[fundCode] = dfSparsePortfolio["FullElements"].map(s)
        except Exception as e:
            print (fundCode)
            print (df)
            print (s)
            print (dfSparsePortfolio)
            raise e

        count += 1

    print (dfSparsePortfolio)
    dfSparsePortfolio.to_csv("data/dfSparsePortfolio.csv")

def prepareTrainDataset():
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    daysRangeInOneYear = int(cf.get("Data-Prepare", "daysRangeInOneYear"))
    numberOfYears = int(cf.get("Data-Prepare", "numberOfYears"))
    daysRange = daysRangeInOneYear * numberOfYears
    #print (daysRange)   # 756

    dfSparsePortfolio = pd.read_csv("data/dfSparsePortfolio_100.csv", index_col=0)
    print (dfSparsePortfolio)

    header = dfSparsePortfolio.columns[1:].to_list()
    print ("header = %s" % header)

    ifSavePortfolioIndex = False
    if ifSavePortfolioIndex:
        dfPortfolioIndex = dfSparsePortfolio["FullElements"]
        dfPortfolioIndex.to_csv("data/dfPortfolioIndex.csv")

    folderToSaveTrainDataset = "data/trainDataset/"
    if not os.path.exists(folderToSaveTrainDataset):
        os.mkdir(folderToSaveTrainDataset)

    count = 0
    for fundCode in header:
        if count >= 100000:
            break

        pathFund = os.path.join("data/dayInStandard", "%s_202012.csv" % fundCode)
        
        if not os.path.exists(pathFund):
            continue

        dfFund = pd.read_csv(pathFund, index_col=0)

        # must have 3 years
        maxDayInStandard = dfFund["DayInStandard"].max()
        if (maxDayInStandard < (daysRange - 1)):
            continue

        # must have value in latest day
        minDayInStandard = dfFund["DayInStandard"].min()
        if (minDayInStandard != 0):
            continue

        print ("count = %s\tfundCode = %s" % (count, fundCode))
        print ("maxDayInStandard = %s" % maxDayInStandard)  # 755

        '''
        # get the latest value
        latestDayForFund = dfFund[dfFund["DayInStandard"] == 0]
        print (latestDayForFund)
        valueInLatestDay = latestDayForFund.iloc[0]["AccumulativeNetAssetValue"]
        print ("valueInLatestDay = %s" % valueInLatestDay)  # 1.4696
        '''

        # get the earliest value
        earliestDayForFund = dfFund[dfFund["DayInStandard"] == (daysRange - 1)]
        #print (earliestDayForFund) # 1.3769999999999998
        valueInEarliestDay = earliestDayForFund.iloc[0]["AccumulativeNetAssetValue"]
        #print ("valueInEarliestDay = %s" % valueInEarliestDay)  # 1.4696

        # count the adjust factor, we can get the value in 3 years
        # by adjustFactorToLatestDay * (value[0]/value[day])
        dfFund["adjustFactorToLatestDay"] =  dfFund["AccumulativeNetAssetValue"] / valueInEarliestDay
        dfFund = dfFund[["DayInStandard", "adjustFactorToLatestDay"]]

        # abandon the latest day, it's meaningless
        dfFund.reset_index(drop=True, inplace=True)
        dfFund = dfFund.T
        dfFund = dfFund.drop(labels=0, axis=1)
        dfFund = dfFund.T
        # reset index to concat with dfSparsePortfolioForThisFund
        dfFund.reset_index(drop=True, inplace=True)
        dfFund = dfFund.T

        #print ("dfFund = \n%s" % dfFund)

        dfSparsePortfolioForThisFund = dfSparsePortfolio[[fundCode]]
        dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.T
        # duplicate to concat with dfSparsePortfolioForThisFund
        dfSparsePortfolioForThisFund = pd.concat([dfSparsePortfolioForThisFund]*dfFund.shape[1])
        # reset index to concat with dfSparsePortfolioForThisFund
        dfSparsePortfolioForThisFund.reset_index(drop=True, inplace=True)
        dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.T
        #print ("dfSparsePortfolioForThisFund = %s" % dfSparsePortfolioForThisFund)

        dfDataset = pd.concat([dfSparsePortfolioForThisFund, dfFund], axis=0)
        print (dfDataset)

        dfDataset.to_csv(os.path.join(folderToSaveTrainDataset, "%s.csv" % fundCode))

        count += 1
        #break

if __name__ == "__main__":
	fire.Fire()