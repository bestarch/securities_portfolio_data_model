from faker import Faker
from jproperties import Properties
import time
import pandas as pd
import os
import traceback
import sys

sys.path.append(os.path.abspath('redis_connection'))
from connection import RedisConnection


configs = Properties()
with open('config/app-config.properties', 'rb') as config_file:
    configs.load(config_file)
Faker.seed(0)
fake = Faker('en_IN')


def generate_investor_account_data():
    investorIdPrefix = "INV1000"
    accountIdPrefix = "ACC1000"
    accountCount = os.getenv('ACCOUNT_RECORD_COUNT', 500)
    try:
        for accs in range(int(accountCount)):
            investorId = investorIdPrefix + str(accs)
            accountNo = accountIdPrefix + str(accs)
            name = fake.name()
            address = fake.address()
            aadhaar_id = fake.aadhaar_id()
            email = fake.email()
            phone = fake.phone_number()
            pan = fake.bothify("?????####?")

            accountOpenDate = str(fake.date_between(start_date='-3y', end_date='-2y'))

            investor = {
                "id": investorId,
                "name": name,
                "uid": aadhaar_id,
                "pan": pan,
                "email": email,
                "phone": phone,
                "address": address
            }
            account = {
                "id": accountNo,
                "investorId": investorId,
                "accountNo": accountNo,
                "accountOpenDate": accountOpenDate,
                "accountCloseDate": '',
                "retailInvestor": True
            }

            conn.json().set("trading:investor:" + investorId, "$", investor)
            conn.json().set("trading:account:" + accountNo, "$", account)
            generate_trading_data(conn, accountNo)
        print(str(accountCount) + " portfolio records generated")
    except Exception as inst:
        print(type(inst))
        traceback.print_exc()
        print("Exception occurred while generating investor & account data")


def generate_trading_data(conn, accountNo):
    path = "files/for_tnxs/"
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    for file in files:
        df = pd.read_csv(path + file)
        ticker = file[:-4]

        count = 0
        pipeline = conn.pipeline()

        for i, row in df.iterrows():
            chance = 5
            try:
                securityLotPrefix = "trading:securitylot:" + accountNo + ":"
                buy = fake.boolean(chance_of_getting_true=chance)
                chance = chance - 1
                if chance < 0:
                    chance = 5
                if buy:
                    dateInUnix = int(time.mktime(time.strptime(row['Date '], "%d-%b-%Y")))
                    buyingPrice = float(str(row['OPEN ']).replace(',', '')) * 100

                    max_value = fake.pyint(min_value=1, max_value=18)
                    quantity = fake.pyint(min_value=1, max_value=max_value)
                    secLotId = fake.lexify("????").upper() + str(i) + str(fake.random_number(digits=8, fix_len=True))
                    lotVal = buyingPrice * quantity
                    desc = f"{row['Date ']}: {quantity} {ticker} stocks having unit price of INR {buyingPrice/100} credited to accountNo {accountNo}. The transaction value is INR {lotVal/100}"

                    securityLot = {
                        "id": secLotId,
                        "accountNo": accountNo,
                        "ticker": ticker,
                        "date": dateInUnix,
                        "price": buyingPrice,
                        "quantity": quantity,
                        "lotValue": lotVal,
                        "type": "EQUITY",
                        "desc": desc,
                        "embeddings": False
                    }

                    pipeline.json().set(securityLotPrefix + secLotId, "$", securityLot)
                    count += 1
                    if count >= 100:
                        pipeline.execute()
                        print(f"pipeline command executed for {count}")
                        count = 0
            except Exception as inst:
                print(type(inst))
                print("Exception occurred while generating trading data")
        if count > 0:
            pipeline.execute()


if __name__ == '__main__':
    conn = RedisConnection().get_connection()
    try:
        # Generate investor, account & trading data
        generate_investor_account_data()
    except Exception as inst:
        print(type(inst))
        print(inst)
        raise Exception('Exception occurred while generating data. Delete the corrupted data and try again')
