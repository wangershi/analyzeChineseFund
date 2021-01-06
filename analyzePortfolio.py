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
	corrForPortfolio = pd.read_csv("data/dfCosineSimilarityForPortfolio.csv", index_col=0)
	nameFund = "110011"
	corrFund = corrForPortfolio[nameFund].dropna(axis=0)
	print ("corrFund = %s" % corrFund)

	dictOfBucket = {}
	for i, v in corrFund.items():
		name = corrForPortfolio.columns.values[i]
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

if __name__ == "__main__":
	fire.Fire()