from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
import yfinance as yf
import plotly.express as px
import pandas as pd
from datetime import datetime
import matplotlib
from datetime import timedelta
from sqlalchemy.orm.exc import NoResultFound


matplotlib.use('Agg')


app = Flask(__name__)
app.secret_key = 'your_secret_key'  

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=100000.0)  
# Transaction Database
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(5), nullable=False)  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



with app.app_context():
    db.create_all()

    db.session.commit()


@app.route('/')
def index():
    return render_template('login.html')

#welcome page
@app.route('/welcome')
def welcome():
    if 'user_id' in session:
        
        return render_template('welcome.html', username=session['username'])
    else:
        return redirect(url_for('index'))


#register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('index'))

    return render_template('register.html')

#login page
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('index'))

#function for getting the top 5 companies on the basis of closing price of last 4 days
def get_top_companies(symbol_list, lookback_period='4d', top_count=5, get_gainers=True):
    top_companies = []

    for symbol in symbol_list:
        try:
            historical_data = yf.download(symbol, period=lookback_period)

            historical_data = historical_data.dropna()

            percent_change = (historical_data['Close'].pct_change() * 100).iloc[-1]

            top_companies.append({'symbol': symbol, 'percent_change': percent_change})
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")

    # Sort the list by percentage change in ascending or descending order based on the parameter
    top_companies.sort(key=lambda x: x['percent_change'], reverse=not get_gainers)

    return top_companies[:top_count]

#Home page
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:

        symbol_list = ['ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BPCL.NS', 'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'COALINDIA.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS', 'INDUSINDBK.NS', 'INFY.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LTIM.NS', 'LT.NS', 'MARUTI.NS', 'NTPC.NS', 'NESTLEIND.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'TECHM.NS', 'TITAN.NS', 'UPL.NS', 'ULTRACEMCO.NS', 'WIPRO.NS']
        # top gaining and losing companies
        top_gaining_companies = get_top_companies(symbol_list, lookback_period='4d', get_gainers=False)
        top_losing_companies = get_top_companies(symbol_list, lookback_period='4d', get_gainers=True)

        return render_template('welcome.html', username=session['username'],top_gaining_companies=top_gaining_companies,top_losing_companies=top_losing_companies)
    else:
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

#graph analysis page
@app.route('/home_page')
def home_page():
    if 'user_id' in session:
        return render_template('home_page.html')
    else:
        return redirect(url_for('index'))

#function for filter by average price
def filter_by_average_price(symbol, min_avg_price, max_avg_price, lookback_period='1mo'):
    try:
        historical_data = yf.download(symbol, period=lookback_period)

        # Calculate average closing price
        avg_price = historical_data['Close'].mean()

        stock_info = yf.Ticker(symbol).info

        company_name = stock_info.get('longName', symbol)  
        pe_ratio = stock_info.get('trailingPE', None)

        # Filter stocks based on average price
        if min_avg_price <= avg_price <= max_avg_price:
            return {'symbol': symbol, 'company_name': company_name, 'pe_ratio': pe_ratio, 'avg_price': avg_price}
        else:
            return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None
    
def filter_by_pe_ratio(symbol, min_pe_ratio, max_pe_ratio):
    try:
        stock_info = yf.Ticker(symbol).info
        historical_data = yf.download(symbol, period='1mo')

        pe_ratio = stock_info.get('trailingPE', None)
        company_name = stock_info.get('longName', symbol)  
        avg_price = historical_data['Close'].mean()

        # Filter stocks based on P/E ratio within the specified range
        if pe_ratio is not None and min_pe_ratio <= pe_ratio <= max_pe_ratio:
            return {'symbol': symbol, 'company_name': company_name, 'pe_ratio': pe_ratio, 'avg_price': avg_price}
        else:
            return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None



@app.route('/filter')
def filter():
    if 'user_id' in session:
        return render_template('filter.html')
    else:
        return redirect(url_for('index'))
    
@app.route('/process_filter', methods=['POST'])
def process_filter():
    if 'user_id' in session:
        if request.method == 'POST':
            symbol_list = ['ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BPCL.NS', 'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'COALINDIA.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS', 'INDUSINDBK.NS', 'INFY.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LTIM.NS', 'LT.NS', 'MARUTI.NS', 'NTPC.NS', 'NESTLEIND.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'TECHM.NS', 'TITAN.NS', 'UPL.NS', 'ULTRACEMCO.NS', 'WIPRO.NS']
            pe_ratio_checkbox = request.form.get('pe_ratio_checkbox')
            avg_price_checkbox = request.form.get('avg_price_checkbox')

            if pe_ratio_checkbox:
                min_pe_ratio = float(request.form.get('min_pe_ratio', 0))
                max_pe_ratio = float(request.form.get('max_pe_ratio', float('inf')))
            else:
                min_pe_ratio = 0
                max_pe_ratio = float('inf')

            if avg_price_checkbox:
                min_avg_price = float(request.form.get('min_avg_price', 0))
                max_avg_price = float(request.form.get('max_avg_price', float('inf')))
            else:
                min_avg_price = 0
                max_avg_price = float('inf')
            print(f"PE Ratio Checkbox: {pe_ratio_checkbox}")
            print(f"Min P/E Ratio: {min_pe_ratio}, Max P/E Ratio: {max_pe_ratio}")
            print(f"Avg Price Checkbox: {avg_price_checkbox}")
            print(f"Min Avg Price: {min_avg_price}, Max Avg Price: {max_avg_price}")

            filtered_stocks = []

            for symbol in symbol_list:
                if not pe_ratio_checkbox and not avg_price_checkbox:
                    # If no filter is selected, include information for all companies
                    pe_ratio_info = filter_by_pe_ratio(symbol, min_pe_ratio, max_pe_ratio)
                    avg_price_info = filter_by_average_price(symbol, min_avg_price, max_avg_price)

                    if pe_ratio_info and avg_price_info:
                        stock_info = {
                            'symbol': symbol,
                            'company_name': pe_ratio_info['company_name'],
                            'pe_ratio': pe_ratio_info['pe_ratio'],
                            'avg_price': avg_price_info['avg_price'],
                        }
                        filtered_stocks.append(stock_info)
                elif pe_ratio_checkbox and avg_price_checkbox:
                    # Apply both P/E Ratio and Average Price filters
                    pe_ratio_info = filter_by_pe_ratio(symbol, min_pe_ratio, max_pe_ratio)
                    avg_price_info = filter_by_average_price(symbol, min_avg_price, max_avg_price)
                    
                    if pe_ratio_info and avg_price_info:
                        stock_info = {
                            'symbol': symbol,
                            'company_name': pe_ratio_info['company_name'],
                            'pe_ratio': pe_ratio_info['pe_ratio'],
                            'avg_price': avg_price_info['avg_price'],
                        }
                        filtered_stocks.append(stock_info)
                elif pe_ratio_checkbox:
                    # Apply only P/E Ratio filter
                    pe_ratio_info = filter_by_pe_ratio(symbol, min_pe_ratio, max_pe_ratio)
                    if pe_ratio_info:
                        stock_info = {
                            'symbol': symbol,
                            'company_name': pe_ratio_info['company_name'],
                            'pe_ratio': pe_ratio_info['pe_ratio'],
                            'avg_price': pe_ratio_info['avg_price'],
                        }
                        filtered_stocks.append(stock_info)
                elif avg_price_checkbox:
                    # Apply only Average Price filter
                    avg_price_info = filter_by_average_price(symbol, min_avg_price, max_avg_price)
                    if avg_price_info:
                        stock_info = {
                            'symbol': symbol,
                            'company_name': avg_price_info['company_name'],
                            'pe_ratio': avg_price_info['pe_ratio'],
                            'avg_price': avg_price_info['avg_price'],
                        }
                        filtered_stocks.append(stock_info)

            print("Filtered Stocks:", filtered_stocks)
            return render_template('filter.html', filtered_stocks=filtered_stocks)

        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('index'))

@app.route('/process_dates', methods=['POST'])
def process_dates():
    if 'user_id' in session:
        if request.method == 'POST':
            enter_time_range = 'enter_time_range' in request.form
            
            if enter_time_range:
                # If the checkbox is ticked, calculate start_date and end_date based on the selected time range
                time_range = request.form['time_range']
                end_date = datetime.now()
                # options correspomding to time ranges 
                if time_range == 'weekly':
                    start_date = end_date - timedelta(weeks=1)
                elif time_range == 'monthly':
                    start_date = end_date - timedelta(weeks=4)  
                elif time_range == 'yearly':
                    start_date = end_date - timedelta(weeks=52)
                elif time_range == 'yearly3':
                    start_date = end_date - timedelta(days=365*3)
                elif time_range == 'yearly10':
                    start_date = end_date - timedelta(days=3650)
                else:
                    start_date = end_date
                #convert the date from string to %Y-%m-%d format
                start_dateo = start_date.strftime('%Y-%m-%d')
                end_dateo = end_date.strftime('%Y-%m-%d')
            
            else:
                start_date = request.form['start_date']
                start_dateo = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = request.form['end_date']
                end_dateo = datetime.strptime(end_date, '%Y-%m-%d')
                
            company_codes = request.form.getlist('company_codes[]')
           
            stock_type = request.form['stock_type']
            #the combined data of all the selected companies
            combined_data = pd.DataFrame()

            for company_code in company_codes:
                try:
                    stock_data = yf.download(company_code, start=start_dateo, end=end_dateo)
                    combined_data[company_code] = stock_data[stock_type]
                except Exception as e:
                    return f"Failed to fetch data for {company_code}: {e}"

            # Creating a graph thorugh Plotly
            fig = px.line(combined_data, x=combined_data.index, y=combined_data.columns, labels={'value': stock_type})
            fig.update_layout(height = 900)
            plot_div = fig.to_html(full_html=False)
            
            
            return render_template('home_page.html', plot_div=plot_div)
            
        else:
            return redirect(url_for('home_page'))
    else:
        return redirect(url_for('index'))
    
    
@app.route('/buysell', methods=['GET', 'POST'])
def buysell():
    if 'user_id' in session:
        # Fetch user data
        user = User.query.get(session['user_id'])

        if request.method == 'POST':
            symbol = request.form['symbol']
            amount = float(request.form['amount'])
            transaction_type = request.form['transaction_type']

            # Fetch stock information
            stock_info = yf.Ticker(symbol)
            current_price = stock_info.history(period='1d')['Close'].iloc[-1]
            transaction_cost = current_price * amount

            if transaction_type == 'buy' and user.balance < transaction_cost:
                flash('Insufficient balance!')
                return redirect(url_for('buysell'))

            # Execute the transaction
            if transaction_type == 'buy':
                # Deduct the amount from the user's balance
                user.balance -= transaction_cost
                print(user.balance)
                # Record the buy transaction
                buy_transaction = Transaction(user_id=user.id, symbol=symbol, amount=amount, transaction_type='buy')
                db.session.add(buy_transaction)
            elif transaction_type == 'sell':
                try:
                    # Try to find the user's stock of the given symbol
                    user_stock_buy = Transaction.query.filter_by(user_id=user.id, symbol=symbol, transaction_type='buy').first()

                    if user_stock_buy and user_stock_buy.amount >= amount:
                        # Calculate the amount to add to the user's balance
                        sell_transaction_cost = current_price * amount
                        user.balance += sell_transaction_cost

                        # Record the sell transaction
                        sell_transaction = Transaction(user_id=user.id, symbol=symbol, amount=amount, transaction_type='sell')
                        db.session.add(sell_transaction)

                        # Update the user's stock amount
                        user_stock_buy.amount -= amount

                        # If the user sold all the stocks, delete the 'buy' record
                        if user_stock_buy.amount == 0:
                            db.session.delete(user_stock_buy)

                        flash(f'Transaction successful! {transaction_type.capitalize()} {amount} shares of {symbol}.')
                    elif user_stock_buy and user_stock_buy.amount < amount:
                        flash(f'Not enough stocks to sell!')
                    else:
                        flash(f"Couldn't find stocks of {symbol}.")
                except NoResultFound:
                    flash(f"Couldn't find stocks of {symbol}.")
                    
            # Commit changes to the database
            db.session.commit()

            return redirect(url_for('buysell'))

        company_symbols = ['ADANIENT.NS', 'ADANIPORTS.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJAJ-AUTO.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BPCL.NS', 'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS', 'COALINDIA.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'GRASIM.NS', 'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS', 'INDUSINDBK.NS', 'INFY.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LTIM.NS', 'LT.NS', 'MARUTI.NS', 'NTPC.NS', 'NESTLEIND.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS', 'SBILIFE.NS', 'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'TECHM.NS', 'TITAN.NS', 'UPL.NS', 'ULTRACEMCO.NS', 'WIPRO.NS']

        stock_prices = get_stock_prices(company_symbols)

        # Fetch user's stocks
        user_stocks = get_user_stocks(session['user_id'])

        return render_template('buysell.html', user_balance=user.balance, stock_prices=stock_prices, user_stocks=user_stocks)
    else:
        return redirect(url_for('index'))

def get_stock_prices(symbols):
    stock_prices = []

    for symbol in symbols:
        try:
            # Fetch stock information
            stock_info = yf.Ticker(symbol)
            
            # Get the current stock price
            current_price = stock_info.history(period='1d')['Close'].iloc[-1]

            # Append the data to the list
            stock_prices.append({
                'symbol': symbol,
                'company_name': get_company_name(symbol),  
                'current_price': current_price
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")

    return stock_prices

#function to get company name given the symbol
def get_company_name(symbol):
    company_names = {
        "ADANIENT.NS": "Adani Enterprises Limited",
        "ADANIPORTS.NS": "Adani Ports and Special Economic Zone Limited",
        "APOLLOHOSP.NS": "Apollo Hospitals Enterprise Limited",
        "ASIANPAINT.NS": "Asian Paints Limited",
        "AXISBANK.NS": "Axis Bank Limited",
        "BAJAJ-AUTO.NS": "Bajaj Auto Limited",
        "BAJFINANCE.NS": "Bajaj Finance Limited",
        "BAJAJFINSV.NS": "Bajaj Finserv Limited",
        "BPCL.NS": "Bharat Petroleum Corporation Limited",
        "BHARTIARTL.NS": "Bharti Airtel Limited",
        "BRITANNIA.NS": "Britannia Industries Limited",
        "CIPLA.NS": "Cipla Limited",
        "COALINDIA.NS": "Coal India Limited",
        "DIVISLAB.NS": "Divi's Laboratories Limited",
        "DRREDDY.NS": "Dr. Reddy's Laboratories Limited",
        "EICHERMOT.NS": "Eicher Motors Limited",
        "GRASIM.NS": "Grasim Industries Limited",
        "HCLTECH.NS": "HCL Technologies Limited",
        "HDFCBANK.NS": "HDFC Bank Limited",
        "HDFCLIFE.NS": "HDFC Life Insurance Company Limited",
        "HEROMOTOCO.NS": "Hero MotoCorp Limited",
        "HINDALCO.NS": "Hindalco Industries Limited",
        "HINDUNILVR.NS": "Hindustan Unilever Limited",
        "ICICIBANK.NS": "ICICI Bank Limited",
        "ITC.NS": "ITC Limited",
        "INDUSINDBK.NS": "IndusInd Bank Limited",
        "INFY.NS": "Infosys Limited",
        "JSWSTEEL.NS": "JSW Steel Limited",
        "KOTAKBANK.NS": "Kotak Mahindra Bank Limited",
        "LTIM.NS": "Larsen & Toubro Infotech Limited",
        "LT.NS": "Larsen & Toubro Limited",
        "MARUTI.NS": "Maruti Suzuki India Limited",
        "NTPC.NS": "NTPC Limited",
        "NESTLEIND.NS": "Nestle India Limited",
        "ONGC.NS": "Oil and Natural Gas Corporation Limited",
        "POWERGRID.NS": "Power Grid Corporation of India Limited",
        "RELIANCE.NS": "Reliance Industries Limited",
        "SBILIFE.NS": "SBI Life Insurance Company Limited",
        "SBIN.NS": "State Bank of India",
        "SUNPHARMA.NS": "Sun Pharmaceutical Industries Limited",
        "TCS.NS": "Tata Consultancy Services Limited",
        "TATACONSUM.NS": "Tata Consumer Products Limited",
        "TATAMOTORS.NS": "Tata Motors Limited",
        "TATASTEEL.NS": "Tata Steel Limited",
        "TECHM.NS": "Tech Mahindra Limited",
        "TITAN.NS": "Titan Company Limited",
        "UPL.NS": "UPL Limited",
        "ULTRACEMCO.NS": "UltraTech Cement Limited",
        "WIPRO.NS": "Wipro Limited"
    }
    return company_names.get(symbol, "Unknown")
    
    # Return the company name based on the symbol
def get_user_stocks(user_id):
    # Query the database to get the user's stocks
    user_stocks_query = Transaction.query.filter_by(user_id=user_id, transaction_type='buy').all()

    user_stocks = {}

    for stock in user_stocks_query:
        if stock.symbol not in user_stocks:
            user_stocks[stock.symbol] = {
                'company_name': get_company_name(stock.symbol),  
                'symbol': stock.symbol,
                'amount': 0,
            }

        user_stocks[stock.symbol]['amount'] += stock.amount

    return list(user_stocks.values())


if __name__ == '__main__':
    app.run(debug=True)
