import random
import requests
import re
import datetime
import os
import pandas
from util import user_agent_list, referer_list

'''
The crawl code from https://github.com/shengqiangzhang/examples-of-web-crawlers
'''

def get_fund_code(forceCrawl=False):
    '''
        Get all funds from eastmoney.com and save it in local file, read it if find today's fund file
        Args:
            forceCrawl: force crawl all funds
    '''
    pathToday = "data/latestFundCode/fund_code_%s.csv" % datetime.datetime.now().strftime("%Y%m%d")
    if (not os.path.exists(pathToday) or forceCrawl):
        # 获取一个随机user_agent和Referer
        header = {'User-Agent': random.choice(user_agent_list),
                  'Referer': random.choice(referer_list)
        }

        # 访问网页接口
        req = requests.get('http://fund.eastmoney.com/js/fundcode_search.js', timeout=5, headers=header)

        # 获取所有基金代码
        fund_code_js = req.content.decode()

        fund_code = fund_code_js.split("= [")[-1].replace("];", "")

        # 正则批量提取
        fund_code = re.findall(r"[\[](.*?)[\]]", fund_code)

        # 对每行数据进行处理，并存储到fund_code_list列表中
        fund_code_list = []
        for sub_data in fund_code:
            data = sub_data.replace("\"","").replace("'","")
            data_list = data.split(",")
            fund_code_list.append(data_list)

        df = pandas.DataFrame(fund_code_list, columns= ['code', 'simpleSpelling', 'name', 'type', 'spelling'])
        print (df)
        df.to_csv(pathToday, index=None, header=True)

        return fund_code_list
    else:
        # the type is string
        return pandas.read_csv(pathToday, dtype=object).values.tolist()

if __name__ == '__main__':
    print (get_fund_code(forceCrawl=True))