# coding: utf-8
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import mean_squared_error
import fire
import os
import random
from scipy import sparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import gc
gc.enable()

def trainModel():
	print('Loading data...')

	ifLoadDatasetFromFile = False

	if not ifLoadDatasetFromFile:
		# create the dataset
		folderOfTrainDataset = "data/trainDataset"
		count = 0
		for file in os.listdir(folderOfTrainDataset):
			if count >= 500:
				break
			print ("count = %s\tfile=%s" % (count, file))

			filePath = os.path.join(folderOfTrainDataset, file)
			dfSingle = pd.read_csv(filePath, index_col=0).T
			#print (dfSingle)
			xSingle = dfSingle.drop("adjustFactorToLatestDay", axis=1)
			xSingleSparse = sparse.csr_matrix(xSingle)
			ySingle = dfSingle["adjustFactorToLatestDay"]
			#print (xSingle)
			#print (ySingle)
			#print (dfSingle)

			if count == 0:
				xSparseForTrainDataset = xSingleSparse
				yForTrainDataset = ySingle
			else:
				xSparseForTrainDataset = sparse.vstack((xSparseForTrainDataset, xSingleSparse))
				yForTrainDataset = pd.concat([yForTrainDataset, ySingle], axis=0)

			# clean the memory
			del(dfSingle)
			del(xSingle)
			del(xSingleSparse)
			del(ySingle)
			gc.collect()

			count += 1

		yForTrainDataset.reset_index(drop=True, inplace=True)
		sparse.save_npz('data/xSparseForTrainDataset.npz', xSparseForTrainDataset)
		yForTrainDataset.to_csv("data/yForTrainDataset.csv")
	else:
		xSparseForTrainDataset = sparse.load_npz('data/xSparseForTrainDataset.npz')
		yForTrainDataset = pd.read_csv("data/yForTrainDataset.csv", index_col=0)
		yForTrainDataset = yForTrainDataset["adjustFactorToLatestDay"]

	print (xSparseForTrainDataset.shape)	# (2958, 9574)
	print (yForTrainDataset.shape)	# (2958,)

	# split the dataset as train dataset and evaluate dataset
	ratioOfTrainInWholeDataset = 0.8
	indice = np.arange(xSparseForTrainDataset.shape[0])
	np.random.shuffle(indice)
	trainIndice = indice[:int(len(indice) * ratioOfTrainInWholeDataset)]
	evaluateIndice = indice[int(len(indice) * ratioOfTrainInWholeDataset):]
	print ("trainIndice = %s" % trainIndice)
	print ("evaluateIndice = %s" % evaluateIndice)

	print ("for train dataset...")
	xTrain = xSparseForTrainDataset[trainIndice]
	print (xTrain.shape)	# (2366, 9574)
	yTrain = yForTrainDataset[trainIndice]
	print (yTrain.shape)	# (2366,)

	xEvaluate = xSparseForTrainDataset[evaluateIndice]
	yEvaluate = yForTrainDataset[evaluateIndice]
	print (xEvaluate.shape)	# (592, 9574)
	print (yEvaluate.shape)	# (592,)

	# create dataset for lightgbm
	lgbTrain = lgb.Dataset(xTrain, yTrain)
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