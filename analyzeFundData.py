import os
import pandas as pd
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
    watchlist = []
    for line in  open("./data/watchlist.txt", "r"):
        watchlist.append(line.split("\n")[0])

    # read fund information
    dfForFundInformation = pd.read_csv("./data/fundInformation/fundInformation_202012.csv", dtype=object)

    rootFolder = "./data/historicalValue"
    count = 0
    riskList = []
    returnList = []
    fundNameList = []
    for file in os.listdir(rootFolder):
        #if file != "110011_202012.csv":
        #if file != "000715_202012.csv":
        #    continue
        fundCode = file.split("_")[0]

        # exclude some funds
        if (fundCode == "000715") or (fundCode == "004638"):
            continue

        #if fundCode not in watchlist:
        #    continue
        #print ("fundCode = %s" % fundCode)  # 180003
        currentFund = dfForFundInformation[dfForFundInformation["Code"] == fundCode]
        fundName = currentFund.iloc[0]["Name"]
        #print ("fundName = %s" % fundName)  # 银华-道琼斯88指数A
        try:
            pathOfFile = os.path.join(rootFolder, file)
            df = pd.read_csv(pathOfFile)
            netValue = df["AccumulativeNetAssetValue"].head(252)
            print (netValue)
            earliestNetValue = netValue[netValue.last_valid_index()]
            countNetValue = netValue.count()    # 1000
            #print ("countNetValue = %s" % countNetValue)
            #print ("earliestNetValue = %s" % earliestNetValue)  # 3.004
            
            riskCurrent = netValue.std()
            returnCurrent = (netValue.mean()-earliestNetValue)/countNetValue*252
            riskList.append(riskCurrent)
            returnList.append(returnCurrent)
            fundNameList.append(fundCode)
        except:
            pass

    plt.scatter(riskList, returnList)
    plt.xlabel("Annualized Risk")
    plt.ylabel("Annualized Return")
    for i in range(len(fundNameList)):
        x = riskList[i]
        y = returnList[i]
        fundName = fundNameList[i]
        plt.text(x, y, fundName, fontsize=10)
    plt.savefig("./data/risk_return.png")
    print ("END.")

if __name__ == "__main__":
    #analyzeRisk()
    #analyzePortfolio()
    analyzeHistoricalValue()