from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash

USER_ID = "user_id"
USERNAME = "username"


class FinanceController:

    def __init__(self, database_url: str):
        # Configure CS50 Library to use SQLite database
        self.__db = SQL(database_url)

        self.__id = None
        self.__username = None

        pass

    def register_new_user(self, username: str, password: str):
        verification_message = self.__check_user_or_password_is_not_typed(username, password)
        if verification_message != "OK":
            return verification_message, 403

        if self.__get_user_from_db(username):
            return "User really exist", 406

        self.__add_user_in_users_table(username, password)

        self.__create_user_table(username)

        return verification_message, 201

    def login(self, username: str, password: str) -> (str, int):

        verification_message = self.__check_user_or_password_is_not_typed(username, password)
        if verification_message != "OK":
            return verification_message, 403

        user = self.__get_user_from_db(username)
        if not user:
            return "invalid username and/or password", 406

        if not check_password_hash(user["hash"], password):
            return "invalid username and/or password", 406

        self.__username = username
        self.__id = user["id"]

        return self.__id, 202

    def buy(self, company_quote: dict, shares: int) -> (str, bool):
        cash = self.get_current_cash()

        cash_after_buy = cash - shares * company_quote["price"]

        if cash_after_buy < 0:
            return "cannot afford the number of shares at the current price", 406

        self.__update_databases_after_buy(company_quote, shares, cash_after_buy)

        return "OK", 201

    def sell(self, company_name: str, company_symbol: str, shares: int, price: float):
        current_cash = self.get_current_cash()

        total = price * shares

        cash_after_sold = current_cash + total

        self.__update_user_cash(cash_after_sold)

        self.__update_current_user_database(company_symbol, company_name, -shares, -total)

        self.__add_to_history_purchases(-shares, price, company_name)

        pass

    def get_current_cash(self):
        rows = self.__db.execute("SELECT cash FROM  users WHERE id = :id", id=self.__id)
        cash = rows[0]["cash"]
        return cash

    def __update_databases_after_buy(self, company_quote: dict, shares: int, cash_after_buy):

        self.__update_user_cash(cash_after_buy)

        company_name = company_quote["name"]
        price = company_quote["price"]

        self.__add_to_history_purchases(shares, price, company_name)

        total = price * shares

        self.__update_current_user_database(company_quote["symbol"], company_name, shares, total)

    def __update_user_cash(self, cash: float):
        self.__db.execute("UPDATE users SET cash = :cash WHERE id =:id", id=self.__id, cash=cash)

    def __add_to_history_purchases(self, shares: int, price: float, company_name: str):

        self.__create_purchase_table()

        self.__db.execute("INSERT INTO purchases (user_id,shares,price,company) VALUES (:id,:shares,:price,:company)",
                          id=self.__id, shares=shares, price=price, company=company_name)

    def __update_current_user_database(self, symbol: str, company_name: str, shares: int, total: float):

        company = self.get_company_from_user_table_by_symbol(symbol)

        if company:
            self.__db.execute(
                "UPDATE :user SET shares = shares + :shares, total = total + :total WHERE symbol = :symbol"
                , user=self.__username, symbol=symbol, shares=shares, total=total)

        else:
            self.__db.execute(
                "INSERT INTO :user (symbol, company, shares, total) VALUES (:symbol, :company, :shares, :total)"
                , user=self.__username, symbol=symbol, company=company_name, shares=shares, total=total)

    def get_company_from_user_table_by_symbol(self, symbol: str) -> dict:
        try:
            companies = self.__db.execute("SELECT * FROM :user WHERE symbol = :symbol", user=self.__username,
                                          symbol=symbol)
            return companies[0]
        except:
            return dict()

    @staticmethod
    def __check_user_or_password_is_not_typed(username: str, password: str) -> str:
        # Ensure username was submitted
        if not username:
            return "must provide username"

        # Ensure password was submitted
        elif not password:
            return "must provide password"

        return "OK"

    def set_session(self, session: dict):
        self.__id = session[USER_ID]
        self.__username = session[USERNAME]

    def get_user_shares(self):
        return self.__db.execute("SELECT * FROM :user", user=self.__username)

    def get_history(self) -> list:
        return self.__db.execute("SELECT * FROM purchases WHERE user_id = :id", id=self.__id)

    def __create_purchase_table(self):
        self.__db.execute(
            "CREATE TABLE IF NOT EXISTS purchases"
            " (user_id INTEGER NOT NULL, shares INTEGER NOT NULL, price REAL NOT NULL, company TEXT NOT NULL,"
            " timestamp DATATIME DEFAULT CURRENT_TIMESTAMP);")

    def __create_user_table(self, username: str):
        self.__db.execute(
            "CREATE TABLE IF NOT EXISTS :name (symbol TEXT NOT NULL, company TEXT NOT NULL,"
            " shares INTEGER NOT NULL, total REAL NOT  NULL)",
            name=username)

    def __add_user_in_users_table(self, username: str, password: str):
        password_hash = generate_password_hash(password)

        self.__create_users_table()

        self.__db.execute("INSERT INTO users (username,hash) VALUES (:username,:password_hash)",
                          username=username, password_hash=password_hash)

    def __get_user_from_db(self, username: str) -> dict:
        try:
            rows = self.__db.execute("SELECT * FROM users WHERE username = :username",
                                     username=username)
            return rows[0]

        except:
            return dict()

    def __create_users_table(self):
        self.__db.execute(
            "CREATE TABLE IF NOT EXISTS 'users' "
            "('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'username' TEXT NOT NULL, 'hash' TEXT NOT NULL,"
            " 'cash' NUMERIC NOT NULL DEFAULT 10000.00 );")
