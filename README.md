# analyzeChineseFund

## clone this project
```
git clone https://github.com/wangershi/analyzeChineseFund.git
```

## data prepare

Use below commands to crawl the data.
```
python src/data/crawlFundData.py crawlAllFundData
```

To find more details, please refer to [dataPrepare](doc/dataPrepare.md).

## data analysis

We want the return and risk in 3 years for all funds.
[add image]
The funds with highest return are new issues, it's a problem, for more details, please refer to my paper TODO: add location.



## use GBDT to imitate the older fund
### training

I use [LightGBM](https://github.com/microsoft/LightGBM) to train GBDT, and I suggest to use Anaconda to install this repository in Ubuntu, it's useful.
```linux
conda create --name python36 python=3.6
source activate python36
conda install lightgbm
```

You can train the model and evaluate it like this.
```
python trainGBDT.py trainModel
```

Get the adjusted factor to latest day.
```
python trainGBDT.py testModel
```

I try to use optuna to fine tune automatically, but the result is not good, so I quit it.
```
python trainGBDT.py autoFineTune
```

Evaluate it again.
```
python analyzeFundData.py getAverageSlopeForFundsInSameRange --ifUseAdjustFactorToLatestDay=False
```

We get the adjustFactorToLatestDay to dayInStandard.
![adjust_factor_in_testing](image/adjust_factor_in_testing.png)

The model flatten the distribution of average return.
![averageReturn_30_useAdjustFactor](image/averageReturn_30_useAdjustFactor.png)

The standard deviation of average return drop from 0.0520 to 0.0175.