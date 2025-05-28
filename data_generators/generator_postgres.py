from faker import Faker
from jproperties import Properties
import time
import pandas as pd
import os
import traceback
import psycopg2

configs = Properties()
with open('config/app-config.properties', 'rb') as config_file:
    configs.load(config_file)
Faker.seed(0)
fake = Faker('en_IN')


def generate_investor_account_data(conn, cursor):
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


            cursor.execute("INSERT INTO portfolio.investor (id, name, uid, pan, email, phone, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (investorId, name, aadhaar_id, pan, email, phone, address))
            cursor.execute("INSERT INTO portfolio.account (id, investorId, accountNo, accountOpenDate, accountCloseDate, retailInvestor) VALUES (%s, %s, %s, %s, %s, %s)",
                           (accountNo, investorId, accountNo, accountOpenDate, '', True))
            generate_trading_data(accountNo, conn, cursor)
        conn.commit()
        print(str(accountCount) + " portfolio records generated")
    except Exception as inst:
        print(type(inst))
        traceback.print_exc()
        print("Exception occurred while generating investor & account data")


def generate_trading_data(accountNo, conn, cursor):
    path = "files/for_tnxs/"
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    for file in files:
        df = pd.read_csv(path + file)
        ticker = file[:-4]
        count = 0

        for i, row in df.iterrows():
            chance = 5
            try:
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

                    cursor.execute("INSERT INTO portfolio.securitylot (id, accountNo, ticker, date, price, quantity, lotValue, type, description) VALUES (%s, %s, %s, to_timestamp(%s), %s, %s, %s, %s, %s)",
                                   (secLotId, accountNo, ticker, dateInUnix, buyingPrice, quantity, lotVal, "EQUITY", desc))
                    count += 1
                    if count >= 100:
                        conn.commit()
                        print(f"Insert command executed for {count}")
                        count = 0
            except Exception as inst:
                print(type(inst))
                print("Exception occurred while generating trading data")
        if count > 0:
            conn.commit()


if __name__ == '__main__':
    with psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'your_db'),
        user=os.getenv('DB_USER', 'your_user'),
        password=os.getenv('DB_PASSWORD', 'your_password'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    ) as conn:
        cursor = conn.cursor()
        try:
            # Generate investor, account & trading data
            generate_investor_account_data(conn, cursor)
        except Exception as inst:
            print(type(inst))
            print(inst)
            raise Exception('Exception occurred while generating data. Delete the corrupted data and try again')
