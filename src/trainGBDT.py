# coding: utf-8
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import mean_squared_error
import fire
import os
import random
from scipy import sparse
import numpy as np
import optuna
import configparser
import datetime
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import gc
gc.enable()

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from src.util import getFolderNameInConfig
from src.analyzeData import getSparseMatrixForPortfolioInAllFunds, getHistoricalValue

def prepareTrainDataset(ifSavePortfolioIndex=False):
    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")
    daysRangeInOneYear = int(cf.get("Parameter", "daysRangeInOneYear"))
    numberOfYears = int(cf.get("Parameter", "numberOfYears"))
    daysRange = daysRangeInOneYear * numberOfYears  # 756
    updateEveryMonth = cf.get("Parameter", "updateEveryMonth")
    folderOfDayInStandard = getFolderNameInConfig("folderOfDayInStandard")    # the folder of data which day is standard
    
    pathOfDfSparsePortfolio = cf.get("Analyze", "pathOfDfSparsePortfolio")
    if not os.path.exists(pathOfDfSparsePortfolio):
        getSparseMatrixForPortfolioInAllFunds()
    
    # didn't generate dayInStandard before
    if len(os.listdir(folderOfDayInStandard)) <= 0:
        getHistoricalValue()

    dfSparsePortfolio = pd.read_csv(pathOfDfSparsePortfolio, index_col=0)
    header = dfSparsePortfolio.columns[1:].to_list()
    
    if ifSavePortfolioIndex:
        dfPortfolioIndex = dfSparsePortfolio["FullElements"]
        dfPortfolioIndex.to_csv("data/dfPortfolioIndex.csv")

    folderToSaveTrainDataset = getFolderNameInConfig("folderToSaveTrainDataset")    # the folder to save train dataset
    folderToSaveTestDataset = getFolderNameInConfig("folderToSaveTestDataset")    # the folder to save test dataset

    month = "%s" % datetime.datetime.now().strftime(updateEveryMonth)   # 202101
    count = 0
    for fundCode in header:
        if count % 100 == 0:
            print ("count = %s\tfundCode=%s" % (count, fundCode))

        pathFund = os.path.join(folderOfDayInStandard, "%s_%s.csv" % (fundCode, month))
        if not os.path.exists(pathFund):
            continue
        dfFund = pd.read_csv(pathFund, index_col=0)

        maxDayInStandard = dfFund["DayInStandard"].max()    # 755
        # get train dataset which found more than 3 years
        if (maxDayInStandard >= (daysRange - 1)):
            # must have value in latest day
            if (dfFund["DayInStandard"].min() != 0):
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

            # duplicate to concat with dfSparsePortfolioForThisFund
            dfSparsePortfolioForThisFund = pd.concat([dfSparsePortfolio[[fundCode]].T]*dfFund.shape[1])
            # reset index to concat with dfSparsePortfolioForThisFund
            dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.reset_index(drop=True).T

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

def loadDataset(ifPrint=True, ifLoadDatasetFromFile = True):
    if ifPrint:
        print('Loading data...')

    # the file don't exist, so it's mandatory to generate the file
    if ifLoadDatasetFromFile:
        if not os.path.exists('data/xSparseForTrainDataset.npz') or not os.path.exists("data/yForTrainDataset.csv"):
            ifLoadDatasetFromFile = False

    if not ifLoadDatasetFromFile:
        # create the dataset
        folderOfTrainDataset = "data/trainDataset"
        count = 0
        for file in os.listdir(folderOfTrainDataset):
            if count % 100 == 0:
                print ("count = %s\tfile=%s" % (count, file))

            filePath = os.path.join(folderOfTrainDataset, file)
            dfSingle = pd.read_csv(filePath, index_col=0).T.fillna(0)

            xSingle = dfSingle.drop("adjustFactorToLatestDay", axis=1)
            xSingleSparse = sparse.csr_matrix(xSingle)
            ySingle = dfSingle["adjustFactorToLatestDay"]
            
            if count == 0:
                xSparseForTrainDataset = xSingleSparse
                yForTrainDataset = ySingle
            else:
                xSparseForTrainDataset = sparse.vstack((xSparseForTrainDataset, xSingleSparse))
                yForTrainDataset = pd.concat([yForTrainDataset, ySingle], axis=0)

            # clean the memory
            del dfSingle
            del xSingle
            del xSingleSparse
            del ySingle
            gc.collect()

            count += 1

        yForTrainDataset.reset_index(drop=True, inplace=True)
        sparse.save_npz('data/xSparseForTrainDataset.npz', xSparseForTrainDataset)
        yForTrainDataset.to_csv("data/yForTrainDataset.csv")
    else:
        xSparseForTrainDataset = sparse.load_npz('data/xSparseForTrainDataset.npz')
        yForTrainDataset = pd.read_csv("data/yForTrainDataset.csv", index_col=0)
        yForTrainDataset = yForTrainDataset["adjustFactorToLatestDay"]

    if ifPrint:
        print (xSparseForTrainDataset.shape)    # (2958, 9574)
        print (yForTrainDataset.shape)    # (2958,)

    # split the dataset as train dataset and evaluate dataset
    # train:val:test=8:1:1 if we set ratioOfTrainInWholeDataset be 0.8 and ratioOfTrainValInWholeDataset be 0.9
    ratioOfTrainInWholeDataset = 0.8
    ratioOfTrainValInWholeDataset = 0.9
    lenOfDataset = xSparseForTrainDataset.shape[0]
    trainValSplitNumber = int(lenOfDataset * ratioOfTrainInWholeDataset)
    valTestSplitNumber = int(lenOfDataset * ratioOfTrainValInWholeDataset)
    indice = np.arange(lenOfDataset)
    np.random.shuffle(indice)
    trainIndice = indice[:trainValSplitNumber]
    evaluateIndice = indice[trainValSplitNumber:valTestSplitNumber]
    testIndice = indice[valTestSplitNumber:]
    #print ("len(trainIndice) = %s" % len(trainIndice))  # 2611130
    #print ("len(evaluateIndice) = %s" % len(evaluateIndice))    # 326391
    #print ("len(testIndice) = %s" % len(testIndice))    # 326392

    if ifPrint:
        print ("for train dataset...")
    xTrain = xSparseForTrainDataset[trainIndice]
    yTrain = yForTrainDataset[trainIndice]

    xEvaluate = xSparseForTrainDataset[evaluateIndice]
    yEvaluate = yForTrainDataset[evaluateIndice]

    xTest = xSparseForTrainDataset[testIndice]
    yTest = yForTrainDataset[testIndice]

    if ifPrint:
        print (xTrain.shape)    # (2366, 9574)
        print (yTrain.shape)    # (2366,)
        print (xEvaluate.shape)    # (592, 9574)
        print (yEvaluate.shape)    # (592,)
        print (xTest.shape)    # (592, 9574)
        print (yTest.shape)    # (592,)

    return xTrain, yTrain, xEvaluate, yEvaluate, xTest, yTest


def objective(trial):
    xTrain, yTrain, xEvaluate, yEvaluate, xTest, yTest = loadDataset(ifPrint=False)

    # create dataset for lightgbm
    lgbTrain = lgb.Dataset(xTrain, yTrain)
    lgbEval = lgb.Dataset(xEvaluate, yEvaluate, reference=lgbTrain)

    # specify the configurations as a dict
    params = {
        'boosting_type': 'gbdt',
        'objective': 'regression',
        'metric': {'l2', 'l1'},
        'num_threads': 4,   # real CPU cores in Surface Book 2, modify this in other machine
        'num_leaves': 555,  # already fine tune
        'learning_rate': 0.048,  # already fine tune
        'feature_fraction': 0.607,  # already fine tune
        'bagging_fraction': 0.607,  # already fine tune
        'bagging_freq': 8,  # already fine tune
        'verbose': 0,
        'min_data_in_leaf': 530  # already fine tune
    }

    # train
    gbm = lgb.train(params,
                    lgbTrain,
                    num_boost_round=20,  # already fine tune
                    valid_sets=lgbEval,
                    early_stopping_rounds=18)  # already fine tune

    # predict
    yPred = gbm.predict(xTest)
    # eval
    return mean_squared_error(yTest, yPred) ** 0.5


def autoFineTune():
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=10)

    print("Number of finished trials: {}".format(len(study.trials)))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: {}".format(trial.value))

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))


def trainModel():
    xTrain, yTrain, xEvaluate, yEvaluate, xTest, yTest = loadDataset()

    # create dataset for lightgbm
    lgbTrain = lgb.Dataset(xTrain, yTrain)
    lgbEval = lgb.Dataset(xEvaluate, yEvaluate, reference=lgbTrain)

    # specify the configurations as a dict
    params = {
        'boosting_type': 'gbdt',
        'objective': 'regression',
        'metric': {'l2', 'l1'},
        'num_threads': 4,   # real CPU cores in Surface Book 2, modify this in other machine
        'num_leaves': 2**10-1,
        'learning_rate': 0.2,
        'feature_fraction': 0.6,
        'bagging_fraction': 0.6,
        'bagging_freq': 8,
        'verbose': 0,
        'min_data_in_leaf': 530
    }

    print('Starting training...')
    # train
    gbm = lgb.train(params,
                    lgbTrain,
                    num_boost_round=200,
                    valid_sets=lgbEval,
                    early_stopping_rounds=10)

    print('Saving model...')
    # save model to file
    gbm.save_model('model/model.txt')

    print('Starting predicting...')
    # predict
    yPred = gbm.predict(xTest, num_iteration=gbm.best_iteration)
    print (yPred[:10])
    # eval
    print('The rmse of prediction is:', mean_squared_error(yTest, yPred) ** 0.5)


def testModel(ifLoadDatasetFromFile = True):
    print('Loading data...')

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    # the file don't exist, so it's mandatory to generate the file
    if ifLoadDatasetFromFile:
        if not os.path.exists("data/dfTest.csv"):
            ifLoadDatasetFromFile = False

    if not ifLoadDatasetFromFile:
        # create the dataset
        folderOfTestDataset = "data/testDataset"
        count = 0
        for file in os.listdir(folderOfTestDataset):
            if count % 100 == 0:
                print ("count = %s\tfile=%s" % (count, file))

            filePath = os.path.join(folderOfTestDataset, file)
            dfSingle = pd.read_csv(filePath, index_col=0)
            dfSingle.reset_index(drop=True, inplace=True)
            dfSingle = dfSingle.T.fillna(0)

            if count == 0:
                dfTest = dfSingle
            else:
                dfTest = pd.concat([dfTest, dfSingle], axis=0)

            count += 1

        print ("count = %s" % count)

        # save df
        dfTest.to_csv("data/dfTest.csv")
        
    dfTest = pd.read_csv("data/dfTest.csv", dtype={'Unnamed: 0':object})
    dfTest.set_index(['Unnamed: 0'], inplace=True)

    print ("dfTest = \n%s" % dfTest)

    # load model to predict
    bst = lgb.Booster(model_file='model/model.txt')
    yPred = bst.predict(dfTest)

    dfTest["yPred"] = yPred
    dfAdjustFactorToLatestDay = dfTest[["yPred"]].T
    dfAdjustFactorToLatestDay.to_csv(cf.get("Analyze", "pathOfDfAdjustFactorToLatestDay"))

    print ("dfAdjustFactorToLatestDay = \n%s" % dfAdjustFactorToLatestDay)

    xMax = dfTest.shape[1] - 2  # 8812
    try:
        dfTest.plot.scatter(x=str(xMax), y='yPred', c='k')
    except:
        dfTest.plot.scatter(x=xMax, y='yPred', c='k')
    plt.xlabel("Count of trading days")
    plt.ylabel("Adjusted factor to latest day")
    plt.xlim((0, 800))
    plt.ylim((0.5, 2.75))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.savefig("./image/adjust_factor_in_testing.png")


if __name__ == "__main__":
    fire.Fire()