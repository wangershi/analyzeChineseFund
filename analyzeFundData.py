import os
import pandas as pd

def analyzePortfolio():
    print ("Begin to analyze portfolio...")

    rootFolder = "./data/portfolio"
    count = 0
    for file in os.listdir(rootFolder):
        if file != "110011_202012.csv":
            continue

        pathOfFile = os.path.join(rootFolder, file)
        df = pd.read_csv(pathOfFile)
        print (df["Ratio"].sum())

def analyzeRisk():
    print ("Begin to analyze risk...")
    dictOfRisk = {}

    rootFolder = "./data/portfolio"
    count = 0
    for file in os.listdir(rootFolder):
        pathOfFile = os.path.join(rootFolder, file)
        df = pd.read_csv(pathOfFile)
        risk = df["Risk"][0]

        if risk not in dictOfRisk:
            dictOfRisk[risk] = 1
        else:
            dictOfRisk[risk] += 1
        print ("%s\t%s" % (count, risk))

        count += 1

    sumOfDictOfRisk = sum(list(dictOfRisk.values()))
    for key in dictOfRisk:
        print ("%s\t%s\t%.2f%%" % (key, dictOfRisk[key], 100.0*dictOfRisk[key]/sumOfDictOfRisk))
    print ("END.")

if __name__ == "__main__":
    #analyzeRisk()
    analyzePortfolio()