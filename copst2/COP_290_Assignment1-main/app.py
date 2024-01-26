from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
import yfinance as yf
import plotly.express as px
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use('Agg')


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# Initialize Database within Application Context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

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

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('welcome.html', username=session['username'])
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/home_page')
def home_page():
    return render_template('home_page.html')

@app.route('/process_dates', methods=['POST'])
def process_dates():
    if 'user_id' in session:
        if request.method == 'POST':
            start_date = request.form['start_date']
            start_dateo = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = request.form['end_date']
            end_dateo = datetime.strptime(end_date, '%Y-%m-%d')
            company_codes = request.form.getlist('company_codes[]')
            
            
            combined_data = pd.DataFrame()

            for company_code in company_codes:
                try:
                    stock_data = yf.download(company_code, start=start_dateo, end=end_dateo)
                    combined_data[company_code] = stock_data['Close']
                except Exception as e:
                    return f"Failed to fetch data for {company_code}: {e}"

            # Create an interactive Plotly graph
            fig = px.line(combined_data, x=combined_data.index, y=combined_data.columns, labels={'value': 'Close'})
            plot_div = fig.to_html(full_html=False)

            return render_template('graph.html', plot_div=plot_div)
            
            # plot_filename = None

            # # Create a plot for selected companies
            # plt.figure(figsize=(10, 6))
            # for company_code in company_codes:
            #     try:
            #         stock_data = yf.download(company_code, start=start_dateo, end=end_dateo)
            #     except Exception as e:
            #         return f"Failed to fetch data for {company_code}: {e}"

            #     plt.plot(stock_data.index, stock_data['Close'], label=f'{company_code} Closing Price')

            # plt.title('Stock Price Over Time')
            # plt.xlabel('Date')
            # plt.ylabel('Closing Price (USD)')
            # plt.legend()
            # plt.grid(True)
            


            # # Save the plot as an image
            # plot_filename = f'static/stock_comparison_plot.png'
            # plt.savefig(plot_filename)
            # plt.close()

            # # Pass the plot image filename to the template
            # return render_template('graph.html', plot_filename=plot_filename)
        else:
            return redirect(url_for('home_page'))
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
