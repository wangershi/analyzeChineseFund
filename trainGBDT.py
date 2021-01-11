# coding: utf-8
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import mean_squared_error
import fire
import os
import random
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')

def trainModel():
	print('Loading data...')

	ifLoadDatasetFromFile = False
	ifSample = False
	ifOnlyUseAssetsAllocation = True

	listOfDfSingle = []
	if not ifLoadDatasetFromFile:
		# create the dataset
		folderOfTrainDataset = "data/trainDataset"
		count = 0
		for file in os.listdir(folderOfTrainDataset):
			if count >= 1000000:
				break
			print ("count = %s\tfile=%s" % (count, file))

			filePath = os.path.join(folderOfTrainDataset, file)
			dfSingle = pd.read_csv(filePath, index_col=0).T
			if ifSample:
				dfSingle = dfSingle.sample(frac=0.1, axis=0)
			if ifOnlyUseAssetsAllocation:
				dfSingle = dfSingle[[0, 1, 2, "DayInStandard", "adjustFactorToLatestDay"]]
			#print (dfSingle)

			listOfDfSingle.append(dfSingle)

			count += 1

		dfTrainEvaluate = pd.concat(listOfDfSingle, axis=0)
		dfTrainEvaluate = dfTrainEvaluate.sample(frac=1)	# shuffle
		dfTrainEvaluate.to_csv("data/dfTrainEvaluate.csv")
	else:
		dfTrainEvaluate = pd.read_csv("data/dfTrainEvaluate.csv", index_col=0)

	print (dfTrainEvaluate)

	ratioOfTrainInWholeDataset = 0.8
	numberOfRows = dfTrainEvaluate.shape[0]
	numberOfTrain = int(numberOfRows * ratioOfTrainInWholeDataset)
	numberOfEvaluate = numberOfRows - numberOfTrain
	#print ("numberOfRows = %s" % numberOfRows)
	dfTrain = dfTrainEvaluate.head(numberOfTrain)
	dfEvaluate = dfTrainEvaluate.tail(numberOfEvaluate)
	#print ("dfTrain = %s" % dfTrain)
	#print ("dfEvaluate = %s" % dfEvaluate)

	yLabel = "adjustFactorToLatestDay"
	yTrain = dfTrain[yLabel]
	XTrain = dfTrain.drop(yLabel, axis=1)

	yEvaluate = dfEvaluate[yLabel]
	xEvaluate = dfEvaluate.drop(yLabel, axis=1)


	# create dataset for lightgbm
	lgbTrain = lgb.Dataset(XTrain, yTrain)
	lgbEval = lgb.Dataset(xEvaluate, yEvaluate, reference=lgbTrain)

	# specify the configurations as a dict
	params = {
	    'boosting_type': 'gbdt',
	    'objective': 'regression',
	    'metric': {'l2', 'l1'},
	    'num_leaves': 31,
	    'learning_rate': 0.05,
	    'feature_fraction': 0.9,
	    'bagging_fraction': 0.8,
	    'bagging_freq': 5,
	    'verbose': 0
	}

	print('Starting training...')
	# train
	gbm = lgb.train(params,
	                lgbTrain,
	                num_boost_round=20,
	                valid_sets=lgbEval,
	                early_stopping_rounds=5)

	print('Saving model...')
	# save model to file
	gbm.save_model('model/model.txt')

	print('Starting predicting...')
	# predict
	yPred = gbm.predict(xEvaluate, num_iteration=gbm.best_iteration)
	print (yPred)
	# eval
	print('The rmse of prediction is:', mean_squared_error(yEvaluate, yPred) ** 0.5)

def testModel():
	print('Loading data...')

	ifLoadDatasetFromFile = True
	ifOnlyUseAssetsAllocation = True

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
			dfSingle = dfSingle.T
			if ifOnlyUseAssetsAllocation:
				dfSingle = dfSingle[[0, 1, 2, 9573]]
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
	#print ("type(yPred) = %s" % type(yPred))	# <class 'numpy.ndarray'>

	dfTest["adjustFactorToLatestDay"] = yPred
	dfAdjustFactorToLatestDay = dfTest[["adjustFactorToLatestDay"]].T
	print ("dfAdjustFactorToLatestDay = %s" % dfAdjustFactorToLatestDay)
	dfAdjustFactorToLatestDay.to_csv("data/dfAdjustFactorToLatestDay.csv")

	dfTest["yPred"] = yPred
	print ("dfTest = %s" % dfTest)

	dfTest.plot.scatter(x='9573', y='yPred', c='k')
	plt.xlabel("day in standard")
	plt.ylabel("adjust factor to latest day")
	plt.savefig("./data/adjust_factor_in_testing.png")

if __name__ == "__main__":
	fire.Fire()