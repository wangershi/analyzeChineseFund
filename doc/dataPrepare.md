## crawl data

Most of the data are crawled from [天天基金网](https://fund.eastmoney.com/), follow below procedures to crawl all the data.

All commands are exectued in the root folder of this repo.
```
python src/data/crawlFundData.py crawlAllFundData --ifCrawlBasicInformation=True --ifCrawlPortfolio=True --ifCrawlHistoricalValue=True
```

### Optional commands

If you want to get latest fund, just use below commands.
```
python src\data\getLatestFund.py
```



