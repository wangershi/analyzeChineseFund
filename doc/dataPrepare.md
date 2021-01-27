## crawl data

Most of the data are crawled from [天天基金网](https://fund.eastmoney.com/), follow below procedures to crawl all the data.

All commands are exectued in the root folder of this repo.
```
python src/data/crawlFundData.py crawlAllFundData --ifCrawlBasicInformation=True --ifCrawlPortfolio=True --ifCrawlHistoricalValue=True
```
You can set the args False to ignore some informations.

### Optional commands

If you want to get latest fund, just use below commands.
```
python src\data\getLatestFund.py
```

## data analyze

### analyze historical value

Use below commands to get the return and risk in 3 years for all funds.
```
python src/data/analyzeData.py analyzeHistoricalValue --ifUseNewIssues=True --ifUseOldIssues=True --ifUseWatchList=False --ifUseAdjustFactorToLatestDay=False --ifPrintFundCode=False
```

We can set ifUseAdjustFactorToLatestDay be True after we prepare data in TODO: add location.

![risk_return_noWatchlist_useNewIssues_useOldIssues_notUseAdjustFactor](image/risk_return_noWatchlist_useNewIssues_useOldIssues_notUseAdjustFactor.png)


### quantitively analyze
Catogorize the return and risk in same days.
```
python src/data/analyzeData.py getAverageSlopeForFundsInSameRange --ifUseAdjustFactorToLatestDay=False
```
We can get the average of annualized return, it seems the average return varies in different time.

![averageReturn_30_notUseAdjustFactor](image/averageReturn_30_notUseAdjustFactor.png)


### fund managers tend to use similar strategy

We can use Pearson's correlation method to get the correlation between fund '110011' and other funds.
```
python src/data/analyzeData.py getCorrelationMatrixForOneFund --ifGetCorrFromFile=False --ifGetDfMergeFromFile=False
```

If intermediate file are generated, we can set related flags True.

![correlation_110011](image/correlation_110011.png)

### confirm it in all funds
To confirm it, I analyze the Pearsom's correlation matrix for all funds and try to find the maximum correlation for each fund, it seems all the maximum correlation is near 1, so we can find a similar fund for every fund.
```
python src/data/analyzeData.py getCorrelationMatrixForAllFunds --ifGetCorrFromFile=False --ifGetDfMergeFromFile=False
```

![maximum_correlation](image/maximum_correlation.png)

Based on analysis above, another way to estimate the return in 3 years is we can let newer fund imitate the return of the older fund with same portfolio. But we can't find two funds with same portfolio, so we should train a model to elimate the influence of different portfolio and unknown equities.

#### Cosine between portfolio of two funds
As we can get sparse matrix for portfolio of all funds, we can use cosine between two vectors in this matrix to represent the correlation of two funds.
We can analyze one fund.
```
python src/data/analyzeData.py analyzeCosineForOneFund
```

![cosine_110011](image/cosine_110011.png)

It seems most of the values are located around 0 or 1.

We can regard cosine as some forms of correlation, where cosine=1 means those two funds are related. But this image is different with the correlation image in [fund managers tend to use similar strategy](#fund-managers-tend-to-use-similar-strategy), where the last image have few correlation locating around 0. To confirm this, I print it in the image, coordinate x represents cosine, coordinate y represents Pearson's correlation.
```
python src/data/analyzeData.py compareCosineAndPearsonCorr --ifFetchCosineFundFromFile=False --ifFetchCorrFundFromFile=False
```

![cosine_PearsonCorr](image/cosine_PearsonCorr_110011.png)

It seems these 2 metrics are not related, and the Pearson correlation between them are 0.134506. I think we can understand it easily, two funds with different portfolio can have same returns.

## prepare data to train

You can use below commands.
```
python src/data/prepareDataset.py prepareTrainDataset
```
It will get dataset for every fund which found 3 years ago. I count it and the number is 4340, as there are 9159 funds in folder "dayInStandard", we substract it and we can get 4819 funds which found less than 3 years (actually get 4543).

