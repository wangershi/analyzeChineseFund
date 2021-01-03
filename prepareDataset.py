import fire
import os
import pandas as pd

def getAllElementsInPortfolio():
    rootFolder = "./data/portfolio"

    count = 0
    countAllElements = 0
    for file in os.listdir(rootFolder):
        if count >= 10000000:
            break

        if count % 100 == 0:
            print ("count = %s\tfile = %s" % (count, file))
        pathFund = os.path.join(rootFolder, file)
        df = pd.read_csv(pathFund)
        df["FullElements"] = df["ElementType"] + "_" + df["Name"]
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

if __name__ == "__main__":
	fire.Fire()