import json
import os
from tempfile import mkdtemp

from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError

from FinanceController import FinanceController, USERNAME, USER_ID
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

finance_controller = FinanceController("sqlite:///finance.db")


def get_username_and_password() -> (str, str):
    try:
        username = request.form.get("username").lower()
        password = request.form.get("password")
        return username, password
    except:
        return "", ""


def get_symbol_and_shares() -> (str, str):
    symbol = request.form.get("symbol")
    shares = request.form.get("shares")

    return symbol, shares


def check_symbol_and_shares() -> (str, int):
    return


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    print(session[USERNAME])
    """Show portfolio of stocks"""
    finance_controller.set_session(session)

    user_shares = finance_controller.get_user_shares()

    current_cash = finance_controller.get_current_cash()

    for i, company_shares in enumerate(user_shares):
        current_quote = lookup(company_shares["symbol"])
        if not current_quote:
            continue

        company_shares["current price"] = round(current_quote["price"], 2)
        company_shares["total cost"] = company_shares["total"]
        del company_shares["total"]

    return render_template("index.html.jinja2", userShares=json.dumps(user_shares), cash=current_cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy/buy.html.jinja2")

    elif request.method == "POST":
        symbol, shares = get_symbol_and_shares()

        if not symbol:
            return apology("input is blank or the symbol does not exist", 403)
        if not shares or int(shares) <= 0:
            return apology("if the input is not a positive integer", 403)

        company_quote = lookup(symbol)

        if not company_quote:
            return apology("Company not found", 406)

        finance_controller.set_session(session)

        message, status = finance_controller.buy(company_quote, int(shares))

        if status > 400:
            return apology(message, status)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = finance_controller.get_history()

    for transaction in transactions:
        del transaction["user_id"]

    return render_template("history.html.jinja2", transactions=json.dumps(transactions))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username, password = get_username_and_password()
        message, status = finance_controller.login(username, password)

        if status >= 400:
            return apology(message, status)

        # Remember which user has logged in
        session[USER_ID] = message
        session[USERNAME] = username

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html.jinja2")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote/quote.html.jinja2")

    elif request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            apology("Symbol invalid")

        company_quote = lookup(symbol)

        if not company_quote:
            return apology("Company not found", 412)

        return render_template("quote/quoted.html.jinja2", quote=company_quote)

    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html.jinja2")
    elif request.method == "POST":
        username, password = get_username_and_password()

        message, status = finance_controller.register_new_user(username, password)

        if status >= 400:
            return apology(message, status)

        return redirect("/login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    finance_controller.set_session(session)

    if request.method == "GET":

        user_table = finance_controller.get_user_shares()

        companies = {row["symbol"]: row["shares"] for row in user_table}

        return render_template("sell.html.jinja2", companies=json.dumps(companies))
    elif request.method == "POST":
        symbol, shares = get_symbol_and_shares()

        if not symbol:
            return apology("input is blank or the symbol does not exist", 403)
        if not shares or int(shares) <= 0:
            return apology("if the input is not a positive integer", 403)

        shares = int(shares)

        company = finance_controller.get_company_from_user_table_by_symbol(symbol)

        if not company or shares > company["shares"]:
            return apology("does not own that many shares of the stock", 403)

        company_quote = lookup(symbol)

        finance_controller.sell(company_quote["name"], symbol, shares, company_quote["price"])

        return redirect("/")




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
