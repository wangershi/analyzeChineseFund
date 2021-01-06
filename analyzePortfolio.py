import fire
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')

from sklearn.metrics.pairwise import cosine_similarity

def getCosineOfSparseMatrixForPortfolio():
	'''
		use sklearn to get the cosine similarity of portfolio
		'1' means these 2 portfolios are similar, also means the degree equals to 0
	'''
	dfSparsePortfolio = pd.read_csv("data/dfSparsePortfolio.csv", index_col=0)
	dfSparsePortfolio = dfSparsePortfolio.drop(labels="FullElements", axis=1)
	header = dfSparsePortfolio.columns
	print ("header = %s" % header)

	# count cosine similarity mannually
	if False:
		dfSparsePortfolio = dfSparsePortfolio.replace(-1, 0)
		dfSparsePortfolio["AA"] = dfSparsePortfolio["150343"] * dfSparsePortfolio["150343"]
		dfSparsePortfolio["BB"] = dfSparsePortfolio["001347"] * dfSparsePortfolio["001347"]
		dfSparsePortfolio["AB"] = dfSparsePortfolio["150343"] * dfSparsePortfolio["001347"]
		print (dfSparsePortfolio["AA"].sum())
		print (dfSparsePortfolio["AB"].sum())
		print (dfSparsePortfolio["BB"].sum())

	# cosine_similarity required
	dfSparsePortfolio = dfSparsePortfolio.T
	# fill nan with 0, 0 is meaningless when count cosine
	dfSparsePortfolio = dfSparsePortfolio.fillna(0)
	# -1 represent not found, so we should set this be zero
	dfSparsePortfolio = dfSparsePortfolio.replace(-1, 0)
	print (dfSparsePortfolio)

	cosineSimilarityForPortfolio = cosine_similarity(dfSparsePortfolio)
	#print (cosineSimilarityForPortfolio)

	dfCosineSimilarityForPortfolio = pd.DataFrame(cosineSimilarityForPortfolio, columns=header)
	print (dfCosineSimilarityForPortfolio)

	dfCosineSimilarityForPortfolio.to_csv("data/dfCosineSimilarityForPortfolio.csv")

def analyzeCosineForOneFund():
	dfCosineSimilarityForPortfolio = pd.read_csv("data/dfCosineSimilarityForPortfolio.csv", index_col=0)
	nameFund = "110011"
	cosineFund = dfCosineSimilarityForPortfolio[nameFund].dropna(axis=0)
	print ("cosineFund = %s" % cosineFund)

	dictOfBucket = {}
	for i, v in cosineFund.items():
		name = dfCosineSimilarityForPortfolio.columns.values[i]
		if name == nameFund:
			continue

		cosine = "%.1f" % v
		if cosine == "1.0":
			print (name)
		if cosine not in dictOfBucket.keys():
			dictOfBucket[cosine] = 1
		else:
			dictOfBucket[cosine] += 1

	print (dictOfBucket)

	# show it in image
	plt.figure(figsize=(15, 10))
	plt.xlabel("cosine")
	plt.ylabel("count")
	for key in sorted(dictOfBucket):
		plt.bar(key, dictOfBucket[key], width=0.8, fc='k')

	plt.savefig("./data/cosine_%s.png" % nameFund)

def compareCosineAndPearsonCorr():
	ifFetchCosineFundFromFile = True
	if not ifFetchCosineFundFromFile:
		dfCosineSimilarityForPortfolio = pd.read_csv("data/dfCosineSimilarityForPortfolio.csv", index_col=0)
		header = dfCosineSimilarityForPortfolio.columns
		dfCosineSimilarityForPortfolio.set_index(header, inplace=True)
		nameFund = "110011"
		cosineFund = dfCosineSimilarityForPortfolio[nameFund].dropna(axis=0)
		cosineFund.to_csv("data/cosineFundFor110011.csv")
	else:
		cosineFund = pd.read_csv("data/cosineFundFor110011.csv", index_col=0)
	cosineFund["b"] = cosineFund.T.columns
	cosineFund["a"] = "AccumulativeNetAssetValue_" + cosineFund["b"].apply(str)
	cosineFund = cosineFund.drop(labels='b',axis=1)
	print ("cosineFund = \n%s" % cosineFund)

	ifFetchCorrFundFromFile = True
	if not ifFetchCorrFundFromFile:
		corr = pd.read_csv("data/corr.csv", index_col=0)
		nameFund = "AccumulativeNetAssetValue_110011"
		corrFund = corr[nameFund].dropna(axis=0)
		corrFund.to_csv("data/corrFundFor110011.csv")
	else:
		corrFund = pd.read_csv("data/corrFundFor110011.csv", index_col=0)
	corrFund["a"] = corrFund.T.columns
	print ("corrFund = \n%s" % corrFund)
	
	df = pd.merge(cosineFund, corrFund, on=['a'], how='outer')
	print (df)

	# delete useless columns
	df = df.drop(labels='a', axis=1)
	print (df)
	print (df.corr())
	df.plot.scatter(x='110011', y='AccumulativeNetAssetValue_110011')
	plt.xlabel("cosine")
	plt.ylabel("PearsonCorr")
	plt.savefig("./data/cosine_PearsonCorr.png")

if __name__ == "__main__":
	fire.Fire()