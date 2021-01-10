# coding: utf-8
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import mean_squared_error
import fire
import os
import random

def trainModel():
	print('Loading data...')

	ifLoadDatasetFromFile = False

	if not ifLoadDatasetFromFile:
		# create the dataset
		folderOfTrainDataset = "data/trainDataset"
		count = 0
		countTrain = 0
		countEvaluate = 0
		ratioOfTrainInWholeDataset = 0.8
		for file in os.listdir(folderOfTrainDataset):
			if count >= 100:
				break
			print ("count = %s\tfile=%s" % (count, file))

			filePath = os.path.join(folderOfTrainDataset, file)
			dfSingle = pd.read_csv(filePath, index_col=0).T
			#print (dfSingle)

			# use it as train dataset
			if random.random() <= ratioOfTrainInWholeDataset:
				if countTrain == 0:
					dfTrain = dfSingle
				else:
					dfTrainTemp = dfTrain.append(dfSingle, ignore_index=True)
					del(dfTrain)
					dfTrain = dfTrainTemp
					del(dfTrainTemp)

				countTrain += 1
			# use it as evaluate dataset
			else:
				if countEvaluate == 0:
					dfEvaluate = dfSingle
				else:
					dfEvaluateTemp = dfEvaluate.append(dfSingle, ignore_index=True)
					del(dfEvaluate)
					dfEvaluate = dfEvaluateTemp
					del(dfEvaluateTemp)

				countEvaluate += 1

			del(dfSingle)
			count += 1

		#dfTrain = dfTrain.T
		dfTrain.reset_index(drop=True, inplace=True)
		print ("dfTrain = %s" % dfTrain)
		print ("countTrain = %s" % countTrain)

		#dfEvaluate = dfEvaluate.T
		dfEvaluate.reset_index(drop=True, inplace=True)
		print ("dfEvaluate = %s" % dfEvaluate)
		print ("countEvaluate = %s" % countEvaluate)

		print ("count = %s" % count)

		raise

		# save df
		dfTrain.to_csv("data/dfTrain.csv")
		dfEvaluate.to_csv("data/dfEvaluate.csv")
	else:
		dfTrain = pd.read_csv("data/dfTrain.csv", index_col=0)
		dfEvaluate = pd.read_csv("data/dfEvaluate.csv", index_col=0)

	# TODO: deal with -1 and nan
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
	#print ("type(yPred) = %s" % type(yPred))	# <class 'numpy.ndarray'>

	dfTest["adjustFactorToLatestDay"] = yPred
	dfAdjustFactorToLatestDay = dfTest[["adjustFactorToLatestDay"]].T
	print ("dfAdjustFactorToLatestDay = %s" % dfAdjustFactorToLatestDay)
	dfAdjustFactorToLatestDay.to_csv("data/dfAdjustFactorToLatestDay.csv")

if __name__ == "__main__":
	fire.Fire()