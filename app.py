import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import random
import datetime
import webbrowser
import threading
import time
from flask import Flask
from flask_moment import Moment

app = Flask(__name__)
moment = Moment(app)



app = Flask(__name__)
app.secret_key = 'stocker_secret_key_2024'

# Email configuration (hardcoded for demo)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = 'your-email@gmail.com'
EMAIL_PASS = 'your-app-password'

# Stock data
STOCKS = {
    'AAPL': {'name': 'Apple Inc.', 'price': 150.00},
    'GOOGL': {'name': 'Alphabet Inc.', 'price': 2500.00},
    'MSFT': {'name': 'Microsoft Corp.', 'price': 300.00},
    'AMZN': {'name': 'Amazon.com Inc.', 'price': 3200.00},
    'TSLA': {'name': 'Tesla Inc.', 'price': 800.00},
    'META': {'name': 'Meta Platforms Inc.', 'price': 320.00},
    'NVDA': {'name': 'NVIDIA Corp.', 'price': 450.00},
    'NFLX': {'name': 'Netflix Inc.', 'price': 400.00},
    'ADBE': {'name': 'Adobe Inc.', 'price': 500.00},
    'CRM': {'name': 'Salesforce Inc.', 'price': 200.00},
    'ORCL': {'name': 'Oracle Corp.', 'price': 80.00},
    'IBM': {'name': 'IBM Corp.', 'price': 130.00},
    'INTC': {'name': 'Intel Corp.', 'price': 50.00},
    'AMD': {'name': 'Advanced Micro Devices', 'price': 90.00},
    'PYPL': {'name': 'PayPal Holdings Inc.', 'price': 70.00},
    'UBER': {'name': 'Uber Technologies Inc.', 'price': 40.00},
    'SPOT': {'name': 'Spotify Technology SA', 'price': 120.00},
    'ZOOM': {'name': 'Zoom Video Communications', 'price': 80.00},
    'TWTR': {'name': 'Twitter Inc.', 'price': 45.00},
    'SNAP': {'name': 'Snap Inc.', 'price': 25.00},
    'SQ': {'name': 'Block Inc.', 'price': 60.00},
    'SHOP': {'name': 'Shopify Inc.', 'price': 400.00}
}

def init_db():
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Portfolio table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_sns_notification(message):
    # SNS notification placeholder for local version
    print(f"SNS Notification: {message}")

def update_stock_prices():
    while True:
        for symbol in STOCKS:
            # Simulate price fluctuation
            change = random.uniform(-0.05, 0.05)
            STOCKS[symbol]['price'] *= (1 + change)
            STOCKS[symbol]['price'] = round(STOCKS[symbol]['price'], 2)
        time.sleep(10)

# Start background thread for price updates
threading.Thread(target=update_stock_prices, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?', 
                      (username, hash_password(password), role))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            
            # Send notifications
            send_email(user[2], 'Stocker Login', f'Hello {username}, you have successfully logged in to Stocker.')
            send_sns_notification(f'User {username} logged in as {role}')
            
            if role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', 
                          (username, email, hash_password(password), role))
            conn.commit()
            
            # Send notifications
            send_email(email, 'Welcome to Stocker', f'Hello {username}, welcome to Stocker! Your account has been created.')
            send_sns_notification(f'New user {username} signed up as {role}')
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('Username already exists')
        finally:
            conn.close()
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    return jsonify({'exists': exists})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('dashboard.html', stocks=STOCKS)

@app.route('/trade')
def trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('trade.html', stocks=STOCKS)

@app.route('/execute_trade', methods=['POST'])
def execute_trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        symbol = request.form.get('symbol', '').strip()
        action = request.form.get('action', '').strip()
        quantity_str = request.form.get('quantity', '').strip()
        price_str = request.form.get('price', '').strip()
        
        # Validate inputs
        if not symbol or not action or not quantity_str or not price_str:
            flash('All fields are required')
            return redirect(url_for('trade'))
        
        # Convert to appropriate types
        quantity = int(quantity_str)
        price = float(price_str)
        
        # Additional validation
        if quantity <= 0:
            flash('Quantity must be greater than 0')
            return redirect(url_for('trade'))
        
        if price <= 0:
            flash('Price must be greater than 0')
            return redirect(url_for('trade'))
        
        # Check if symbol exists in our stock list
        if symbol not in STOCKS:
            flash('Invalid stock symbol')
            return redirect(url_for('trade'))
        
    except (ValueError, TypeError):
        flash('Invalid input values. Please check your entries.')
        return redirect(url_for('trade'))
    total = quantity * price
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    try:
        # Record trade
        cursor.execute('''INSERT INTO trades (user_id, symbol, action, quantity, price, total) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (session['user_id'], symbol, action, quantity, price, total))
        
        # Update portfolio
        if action == 'Buy':
            cursor.execute('SELECT * FROM portfolio WHERE user_id = ? AND symbol = ?', 
                          (session['user_id'], symbol))
            existing = cursor.fetchone()
            
            if existing:
                new_quantity = existing[3] + quantity
                new_avg_price = ((existing[3] * existing[4]) + total) / new_quantity
                cursor.execute('''UPDATE portfolio SET quantity = ?, avg_price = ? 
                                WHERE user_id = ? AND symbol = ?''', 
                              (new_quantity, new_avg_price, session['user_id'], symbol))
            else:
                cursor.execute('''INSERT INTO portfolio (user_id, symbol, quantity, avg_price) 
                                VALUES (?, ?, ?, ?)''', 
                              (session['user_id'], symbol, quantity, price))
        
        elif action == 'Sell':
            cursor.execute('SELECT * FROM portfolio WHERE user_id = ? AND symbol = ?', 
                          (session['user_id'], symbol))
            existing = cursor.fetchone()
            
            if existing and existing[3] >= quantity:
                new_quantity = existing[3] - quantity
                if new_quantity > 0:
                    cursor.execute('''UPDATE portfolio SET quantity = ? 
                                    WHERE user_id = ? AND symbol = ?''', 
                                  (new_quantity, session['user_id'], symbol))
                else:
                    cursor.execute('DELETE FROM portfolio WHERE user_id = ? AND symbol = ?', 
                                  (session['user_id'], symbol))
            else:
                flash('Insufficient shares to sell')
                conn.close()
                return redirect(url_for('trade'))
        
        conn.commit()
        flash(f'Trade executed: {action} {quantity} shares of {symbol} at ${price:.2f}')
        
    except Exception as e:
        conn.rollback()
        flash('Error executing trade. Please try again.')
        print(f"Trade execution error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('portfolio'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM portfolio WHERE user_id = ?', (session['user_id'],))
    holdings = cursor.fetchall()
    conn.close()
    
    portfolio_data = []
    total_current = 0
    total_invested = 0

    for holding in holdings:
        symbol = holding[2]
        quantity = holding[3]
        avg_price = holding[4]
        current_price = STOCKS[symbol]['price']
        total_value = quantity * current_price

        total_current += total_value
        total_invested += quantity * avg_price

        portfolio_data.append({
            'symbol': symbol,
            'name': STOCKS[symbol]['name'],
            'quantity': quantity,
            'avg_price': avg_price,
            'current_price': current_price,
            'total_value': total_value,
            'created_at': holding[5]
        })

    total_gain_loss = total_current - total_invested

    return render_template('portfolio.html',
                           portfolio=portfolio_data,
                           stocks=STOCKS,
                           total_current=total_current,
                           total_invested=total_invested,
                           total_gain_loss=total_gain_loss)


@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trades WHERE user_id = ? ORDER BY created_at DESC', 
                  (session['user_id'],))
    trades = cursor.fetchall()
    conn.close()
    
    return render_template('history.html', trades=trades)

@app.route('/help', methods=['GET', 'POST'])
def help():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        message = request.form['message']
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (user_id, message) VALUES (?, ?)', 
                      (session['user_id'], message))
        conn.commit()
        conn.close()
        flash('Message sent successfully!')
    
    return render_template('help.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Get stats
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "Trader"')
    total_traders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM trades')
    total_trades = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(quantity * avg_price) FROM portfolio')
    total_portfolio_value = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_traders=total_traders,
                         total_trades=total_trades,
                         total_portfolio_value=total_portfolio_value)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.username, p.symbol, p.quantity, p.avg_price, p.created_at
                     FROM portfolio p 
                     JOIN users u ON p.user_id = u.id
                     ORDER BY u.username, p.symbol''')
    portfolios = cursor.fetchall()
    conn.close()
    
    return render_template('admin_portfolio.html', portfolios=portfolios, stocks=STOCKS)

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT u.username, t.symbol, t.action, t.quantity, t.price, t.total, t.created_at
                     FROM trades t 
                     JOIN users u ON t.user_id = u.id
                     ORDER BY t.created_at DESC''')
    trades = cursor.fetchall()
    conn.close()
    
    return render_template('admin_history.html', trades=trades)

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Get users
    cursor.execute('SELECT * FROM users WHERE role = "Trader"')
    users = cursor.fetchall()
    
    # Get messages
    cursor.execute('''SELECT m.message, m.created_at, u.username
                     FROM messages m 
                     JOIN users u ON m.user_id = u.id
                     ORDER BY m.created_at DESC''')
    messages = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin_manage.html', users=users, messages=messages)

@app.route('/get_stock_prices')
def get_stock_prices():
    return jsonify(STOCKS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':

    def open_browser():
        webbrowser.open_new('http://127.0.0.1:5000')

    threading.Timer(1.0, open_browser).start()
   app.run(debug=True, host='0.0.0.0',port=5000)
