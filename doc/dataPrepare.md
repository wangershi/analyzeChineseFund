## crawl data
Most of the data are crawled from [天天基金网](https://fund.eastmoney.com/).
```
python src/crawlFundData.py crawlAllFundData --ifCrawlBasicInformation=True --ifCrawlPortfolio=True --ifCrawlHistoricalValue=True
```
You can set any arg be False to ignore some informations, all commands are exectued in the root folder of this repo.

## data analyze
### analyze historical value
Use below commands to get the return and risk in 3 years for all funds.
```
python src/analyzeData.py analyzeHistoricalValue --ifUseNewIssues=True --ifUseOldIssues=True --ifUseWatchList=False --ifUseAdjustFactorToLatestDay=False --ifPrintFundCode=False --fund_to_specify_date=000934
```

The result:
![risk_return_noWatchlist_useNewIssues_useOldIssues_notUseAdjustFactor](image/risk_return_noWatchlist_useNewIssues_useOldIssues_notUseAdjustFactor.png)


### quantitively analyze
Catogorize the return and risk in near days.
```
python src/analyzeData.py getAverageSlopeForFundsInSameRange --ifUseAdjustFactorToLatestDay=False
```
We can get the average of annualized return, it seems the average return varies in different time.
![averageReturn_30_notUseAdjustFactor](image/averageReturn_30_notUseAdjustFactor.png)

### fund managers tend to use similar strategy
We can use Pearson's correlation method to get the correlation between fund '110011' and other funds.
```
python src/analyzeData.py getCorrelationMatrixForOneFund --ifGetCorrFromFile=False --ifGetDfMergeFromFile=False --fundCodeToAnalyze=110011
```
If intermediate file are generated, we can set related flags True.
![correlation_110011](image/correlation_110011.png)

### confirm it in all funds
I analyze the Pearsom's correlation matrix for all funds.
```
python src/analyzeData.py getCorrelationMatrixForAllFunds --ifGetCorrFromFile=False --ifGetDfMergeFromFile=False
```
![maximum_correlation](image/maximum_correlation.png)

#### Cosine between portfolio of two funds
Use cosine between two vectors in this matrix to represent the correlation of two funds.
```
python src/analyzeData.py analyzeCosineForOneFund --nameFund=110011
```
![cosine_110011](image/cosine_110011.png)

Get the relation between cosine relation and Pearson's correlation.
```
python src/analyzeData.py compareCosineAndPearsonCorr --ifFetchCosineFundFromFile=False --ifFetchCorrFundFromFile=False --nameFund=110011
```
![cosine_PearsonCorr](image/cosine_PearsonCorr_110011.png)
