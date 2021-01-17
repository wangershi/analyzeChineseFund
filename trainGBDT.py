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
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import gc
gc.enable()

def loadDataset(ifPrint=True, ifLoadDatasetFromFile = True):
    if ifPrint:
        print('Loading data...')    

    if not ifLoadDatasetFromFile:
        # create the dataset
        folderOfTrainDataset = "data/trainDataset"
        count = 0
        for file in os.listdir(folderOfTrainDataset):
            if count >= 100000:
                break
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
    #print ("trainIndice = %s" % trainIndice)
    #print ("evaluateIndice = %s" % evaluateIndice)
    #print ("testIndice = %s" % testIndice)
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
    '''
    params = {
        'boosting_type': 'gbdt',
        'objective': 'regression',
        'metric': {'l2', 'l1'},
        'num_threads': 4,   # real CPU cores in Surface Book 2, modify this in other machine
        'num_leaves': trial.suggest_int("num_leaves", 2, 2**12-1),
        'learning_rate': trial.suggest_float("learning_rate", 0.01, 1.0),
        'feature_fraction': trial.suggest_float("feature_fraction", 0.4, 1.0),
        'bagging_fraction': trial.suggest_float("bagging_fraction", 0.4, 1.0),
        'bagging_freq': trial.suggest_int("bagging_freq", 1, 10),
        'verbose': 0,
        'min_data_in_leaf': trial.suggest_int("min_data_in_leaf", 10, 1000)
    }
    '''
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
    '''
    gbm = lgb.train(params,
                    lgbTrain,
                    num_boost_round=trial.suggest_int("num_boost_round", 10, 1000),
                    valid_sets=lgbEval,
                    early_stopping_rounds=trial.suggest_int("early_stopping_rounds", 1, 100))
    '''
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
    yPred = gbm.predict(xEvaluate, num_iteration=gbm.best_iteration)
    print (yPred[:10])
    # eval
    print('The rmse of prediction is:', mean_squared_error(yEvaluate, yPred) ** 0.5)

def testModel():
    print('Loading data...')

    ifLoadDatasetFromFile = True

    if not ifLoadDatasetFromFile:
        # create the dataset
        folderOfTestDataset = "data/testDataset"
        count = 0
        for file in os.listdir(folderOfTestDataset):
            if count >= 1000000:
                break
            print ("count = %s\tfile=%s" % (count, file))

            filePath = os.path.join(folderOfTestDataset, file)
            dfSingle = pd.read_csv(filePath, index_col=0)
            #dfSingle.rename(columns={"Unnamed: 0":"FundCode"}, inplace=True)
            dfSingle.reset_index(drop=True, inplace=True)
            dfSingle = dfSingle.T.fillna(0)
            #print (dfSingle)

            if count == 0:
                dfTest = dfSingle
            else:
                dfTest = pd.concat([dfTest, dfSingle], axis=0)

            count += 1

        print ("count = %s" % count)
        #dfTest.reset_index(drop=True, inplace=True)

        # save df
        dfTest.to_csv("data/dfTest.csv")
    else:
        dfTest = pd.read_csv("data/dfTest.csv", dtype={'Unnamed: 0':object})
        dfTest.set_index(['Unnamed: 0'], inplace=True)

    print ("dfTest = \n%s" % dfTest)

    # load model to predict
    bst = lgb.Booster(model_file='model/model.txt')
    # can only predict with the best iteration (or the saving iteration)
    yPred = bst.predict(dfTest)
    print ("yPred = %s" % yPred)
    print ("yPred.shape = %s" % yPred.shape)
    #print ("type(yPred) = %s" % type(yPred))    # <class 'numpy.ndarray'>

    dfTest["adjustFactorToLatestDay"] = yPred
    dfAdjustFactorToLatestDay = dfTest[["adjustFactorToLatestDay"]].T
    print ("dfAdjustFactorToLatestDay = %s" % dfAdjustFactorToLatestDay)
    dfAdjustFactorToLatestDay.to_csv("data/dfAdjustFactorToLatestDay.csv")

    dfTest["yPred"] = yPred
    print ("dfTest = %s" % dfTest)

    try:
        dfTest.plot.scatter(x='9573', y='yPred', c='k')
    except:
        dfTest.plot.scatter(x=9573, y='yPred', c='k')
    plt.xlabel("Count of trading days")
    plt.ylabel("Adjusted factor to latest day")
    plt.xlim((0, 800))
    plt.ylim((0.5, 2.75))
    ax = plt.gca()
    # no line in right and top border
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    plt.savefig("./data/adjust_factor_in_testing.png")

if __name__ == "__main__":
    fire.Fire()