import fire
import os
import pandas as pd

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
        if count >= 1000000000000:
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

if __name__ == "__main__":
	fire.Fire()