# coding: utf-8
import lightgbm as lgb
import pandas as pd
from pandas.tseries.offsets import DateOffset
from sklearn.metrics import mean_squared_error
import fire
import os
import random
from scipy import sparse
import numpy as np
import qlib
from qlib.data import D
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
from src.analyzeData import getSparseMatrixForPortfolioInAllFunds

def prepareTrainDataset(ifSavePortfolioIndex=False):
    print ("------------------------ Begin to prepare train dataset... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    minDaysRange = int(cf.get("Parameter", "minDaysRange"))

    # offset of days
    numberOfYears = int(cf.get("Parameter", "numberOfYears"))
    numberOfMonths = int(cf.get("Parameter", "numberOfMonths"))
    numberOfDays = int(cf.get("Parameter", "numberOfDays"))

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
    
    # get portfolio
    pathOfDfSparsePortfolio = cf.get("Analyze", "pathOfDfSparsePortfolio")
    if not os.path.exists(pathOfDfSparsePortfolio):
        getSparseMatrixForPortfolioInAllFunds()
    dfSparsePortfolio = pd.read_csv(pathOfDfSparsePortfolio, index_col=0)
    
    if ifSavePortfolioIndex:
        dfPortfolioIndex = dfSparsePortfolio["FullElements"]
        dfPortfolioIndex.to_csv("data/dfPortfolioIndex.csv")

    folderToSaveTrainDataset = getFolderNameInConfig("folderToSaveTrainDataset")    # the folder to save train dataset
    folderToSaveTestDataset = getFolderNameInConfig("folderToSaveTestDataset")    # the folder to save test dataset

    count = 0
    instruments = D.instruments(market='all')
    for file in D.list_instruments(instruments=instruments, as_list=True):
        fundCode = file.split("_")[0]   # 000001
        
        if count % 100 == 0:
            print ("count = %s\tfundCode=%s" % (count, fundCode))

        try:
            # can't find portfolio for this fund
            try:
                dfSparsePortfolioForThisFund = dfSparsePortfolio[[fundCode]]
            except:
                continue

            # read file and remove empty line
            df = D.features([file], [
                '$AccumulativeNetAssetValue'
                ], start_time=firstDayToAnalyze, end_time=lastDayToAnalyze)
            df.columns = [
                'AccumulativeNetAssetValue'
                ]
            #df = df.unstack(level=0)
            df["datetime"] = df.index.levels[1]

            # reset the index
            df = df.dropna(axis=0, subset=['datetime']).reset_index(drop=True)

            # like http://fundf10.eastmoney.com/jjjz_010476.html, the return in 30 days is 26%, so the annualized return is too high
            if df.shape[0] <= minDaysRange:
                continue

            # count the days between first day and last day
            day = df['datetime']
            # TODO: how about fund 519858, which trade in 2018-01-28 (Sunday)
            firstDayInThisFund = day[day.first_valid_index()]   # 2018-02-12 00:00:00, 2018-02-10 is Satuaday
            lastDayInThisFund = day[day.last_valid_index()] # 2021-02-10 00:00:00

            # must have value in latest day
            if (lastDayInThisFund - lastDayToAnalyze).days != 0:
                continue

            df['daysDiffWithLastDay'] = df['datetime'].apply(lambda x: (lastDayInThisFund - x).days)

            # get the value in important days
            lastestNetValue = df[df['datetime'] == lastDayInThisFund]["AccumulativeNetAssetValue"].tolist()[0] # 4.046

            # get train dataset which found more than 3 years
            if (firstDayInThisFund - firstDayToAnalyze).days <= 0:
                 # count the adjust factor, we can get the value in 3 years by adjustFactorToLatestDay * (value[0]/value[day])
                df["adjustFactorToLatestDay"] =  df["AccumulativeNetAssetValue"] / lastestNetValue
                df = df[["daysDiffWithLastDay", "adjustFactorToLatestDay"]]

                # abandon the latest day, it's meaningless
                df.reset_index(drop=True, inplace=True)
                df = df.T.drop(labels=0, axis=1).T
                # reset index to concat with dfSparsePortfolioForThisFund
                df.reset_index(drop=True, inplace=True)
                df = df.T

                # duplicate to concat with dfSparsePortfolioForThisFund
                dfSparsePortfolioForThisFund = pd.concat([dfSparsePortfolioForThisFund.T]*df.shape[1])
                # reset index to concat with dfSparsePortfolioForThisFund
                dfSparsePortfolioForThisFund = dfSparsePortfolioForThisFund.reset_index(drop=True).T

                dfDataset = pd.concat([dfSparsePortfolioForThisFund, df], axis=0)
                dfDataset.to_csv(os.path.join(folderToSaveTrainDataset, "%s.csv" % fundCode))
            else:
                dfInFirstDay = df[df['datetime'] == firstDayInThisFund].reset_index(drop=True)
                dfInFirstDay = dfInFirstDay[["daysDiffWithLastDay"]].T
                dfInFirstDay[fundCode] = dfInFirstDay[0]
                dfDataset = pd.concat([dfSparsePortfolioForThisFund, dfInFirstDay[[fundCode]]], axis=0)
                dfDataset.to_csv(os.path.join(folderToSaveTestDataset, "%s.csv" % fundCode))

            count += 1
        except Exception as e:
            print ("fundCode = %s\terror = %s" % (fundCode, e))
            continue        

    print ("------------------------ Done. ------------------------")


def loadDataset(ifLoadDatasetFromFile=True, ratioOfTrainInWholeDataset=0.8, ratioOfTrainValInWholeDataset=0.9):
    '''
        train:val:test=8:1:1 if we set ratioOfTrainInWholeDataset be 0.8 and ratioOfTrainValInWholeDataset be 0.9
    '''
    print ("------------------------ Loading data... ------------------------")

    # the file don't exist, so it's mandatory to generate the file
    if ifLoadDatasetFromFile:
        if not os.path.exists('data/xSparseForTrainDataset.npz') or not os.path.exists("data/yForTrainDataset.csv"):
            ifLoadDatasetFromFile = False

    if not ifLoadDatasetFromFile:
        # create the dataset
        folderOfTrainDataset = "data/trainDataset"

        # didn't generate dataset before
        if len(os.listdir(folderOfTrainDataset)) <= 0:
            prepareTrainDataset()

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
        xSparseForTrainDataset = sparse.load_npz('data/xSparseForTrainDataset.npz') # xSparseForTrainDataset.shape = (2958, 9574)
        yForTrainDataset = pd.read_csv("data/yForTrainDataset.csv", index_col=0)
        yForTrainDataset = yForTrainDataset["adjustFactorToLatestDay"]  # yForTrainDataset.shape = (2958,)

    # split the dataset as train dataset and evaluate dataset
    lenOfDataset = xSparseForTrainDataset.shape[0]
    trainValSplitNumber = int(lenOfDataset * ratioOfTrainInWholeDataset)
    valTestSplitNumber = int(lenOfDataset * ratioOfTrainValInWholeDataset)
    indice = np.arange(lenOfDataset)
    np.random.shuffle(indice)
    trainIndice = indice[:trainValSplitNumber]  # len(trainIndice) = 2611130
    evaluateIndice = indice[trainValSplitNumber:valTestSplitNumber] # len(evaluateIndice) = 326391
    testIndice = indice[valTestSplitNumber:]    # len(testIndice) = 326392

    xTrain = xSparseForTrainDataset[trainIndice]    # xTrain.shape = (2366, 9574)
    yTrain = yForTrainDataset[trainIndice]  # yTrain.shape = (2366,)

    xEvaluate = xSparseForTrainDataset[evaluateIndice]  # xEvaluate.shape = (592, 9574)
    yEvaluate = yForTrainDataset[evaluateIndice]    # yEvaluate.shape = (592,)

    xTest = xSparseForTrainDataset[testIndice]  # xTest.shape = (592, 9574)
    yTest = yForTrainDataset[testIndice]    # yTest.shape = (592,)

    print ("------------------------ Done. ------------------------")

    return xTrain, yTrain, xEvaluate, yEvaluate, xTest, yTest


def objective(trial):
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
        'num_leaves': 555,
        'learning_rate': 0.048,
        'feature_fraction': 0.607,
        'bagging_fraction': 0.607,
        'bagging_freq': 8,
        'verbose': 0,
        'min_data_in_leaf': 530
    }

    # train
    gbm = lgb.train(params,
                    lgbTrain,
                    num_boost_round=20,
                    valid_sets=lgbEval,
                    early_stopping_rounds=18)

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
    print ("------------------------ Train model... ------------------------")

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
        'num_leaves': 2**10-1,  # already fine tune
        'learning_rate': 0.2,   # already fine tune
        'feature_fraction': 0.6,    # already fine tune
        'bagging_fraction': 0.6,    # already fine tune
        'bagging_freq': 8,  # already fine tune
        'verbose': 0,
        'min_data_in_leaf': 530 # already fine tune
    }

    print('Starting training...')
    gbm = lgb.train(params,
                    lgbTrain,
                    num_boost_round=200,    # already fine tune
                    valid_sets=lgbEval,
                    early_stopping_rounds=10)   # already fine tune

    print('Saving model...')
    if not os.path.exists("model"):
        os.mkdir("model")
    gbm.save_model('model/model.txt')

    print('Starting predicting...')
    yPred = gbm.predict(xTest, num_iteration=gbm.best_iteration)
    print (yPred[:10])
    print('The rmse of prediction is:', mean_squared_error(yTest, yPred) ** 0.5)

    print ("------------------------ Done. ------------------------")


def testModel(ifLoadDatasetFromFile=True):
    print ("------------------------ Test model... ------------------------")

    # read config file
    cf = configparser.ConfigParser()
    cf.read("config/config.ini")

    # the file don't exist, so it's mandatory to generate the file
    if ifLoadDatasetFromFile:
        if not os.path.exists("data/dfTest.csv"):
            ifLoadDatasetFromFile = False

    if not ifLoadDatasetFromFile:
        folderToSaveTestDataset = getFolderNameInConfig("folderToSaveTestDataset")    # the folder to save test dataset
        
        count = 0
        for file in os.listdir(folderToSaveTestDataset):
            if count % 100 == 0:
                print ("count = %s\tfile=%s" % (count, file))

            filePath = os.path.join(folderToSaveTestDataset, file)
            dfSingle = pd.read_csv(filePath, index_col=0)
            dfSingle.reset_index(drop=True, inplace=True)
            dfSingle = dfSingle.T.fillna(0)

            if count == 0:
                dfTest = dfSingle
            else:
                dfTest = pd.concat([dfTest, dfSingle], axis=0)

            count += 1

        # save df
        dfTest.to_csv("data/dfTest.csv")
        
    dfTest = pd.read_csv("data/dfTest.csv", dtype={'Unnamed: 0':object})
    dfTest.set_index(['Unnamed: 0'], inplace=True)

    print ("dfTest = \n%s" % dfTest)

    # load model to predict
    if not os.path.exists("model"):
        os.mkdir("model")
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

    print ("------------------------ Done. ------------------------")

if __name__ == "__main__":
    fire.Fire()