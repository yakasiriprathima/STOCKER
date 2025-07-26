import boto3
import hashlib
import secrets
import smtplib
import json
import time
import random
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import webbrowser
import threading
from decimal import Decimal
import uuid

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global variable to track if browser was already opened
browser_opened = False

# AWS Configuration - Use environment variables with fallbacks
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SNS_TOPIC_ARN ='arn:aws:sns:us-east-1:794038220422:arntopic:27f7a381-8043-40da-99bb-cf449e2411d3'
DYNAMODB_TABLE_PREFIX = os.environ.get('DYNAMODB_TABLE_PREFIX', 'stocker_')

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
EMAIL_USER = os.environ.get('EMAIL_USER', 'stocker.demo@gmail.com')
EMAIL_PASS = os.environ.get('EMAIL_PASS', 'demo_password_123')

# Initialize AWS clients
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    sns = boto3.client('sns', region_name=AWS_REGION)
    print("AWS services initialized successfully")
except Exception as e:
    print(f"AWS initialization failed: {e}")
    # Fallback to local simulation
    dynamodb = None
    sns = None

# Stock data simulation
STOCK_DATA = {
    'AAPL': {'name': 'Apple Inc.', 'base_price': 150.00},
    'GOOGL': {'name': 'Alphabet Inc.', 'base_price': 2500.00},
    'MSFT': {'name': 'Microsoft Corporation', 'base_price': 300.00},
    'AMZN': {'name': 'Amazon.com Inc.', 'base_price': 3200.00},
    'TSLA': {'name': 'Tesla Inc.', 'base_price': 800.00},
    'META': {'name': 'Meta Platforms Inc.', 'base_price': 320.00},
    'NVDA': {'name': 'NVIDIA Corporation', 'base_price': 900.00},
    'NFLX': {'name': 'Netflix Inc.', 'base_price': 500.00},
    'BABA': {'name': 'Alibaba Group', 'base_price': 100.00},
    'JPM': {'name': 'JPMorgan Chase', 'base_price': 140.00},
    'JNJ': {'name': 'Johnson & Johnson', 'base_price': 170.00},
    'V': {'name': 'Visa Inc.', 'base_price': 220.00},
    'WMT': {'name': 'Walmart Inc.', 'base_price': 145.00},
    'PG': {'name': 'Procter & Gamble', 'base_price': 155.00},
    'HD': {'name': 'Home Depot Inc.', 'base_price': 330.00},
    'MA': {'name': 'Mastercard Inc.', 'base_price': 350.00},
    'BAC': {'name': 'Bank of America', 'base_price': 40.00},
    'DIS': {'name': 'Walt Disney Company', 'base_price': 110.00},
    'ADBE': {'name': 'Adobe Inc.', 'base_price': 550.00},
    'CRM': {'name': 'Salesforce Inc.', 'base_price': 210.00},
    'ORCL': {'name': 'Oracle Corporation', 'base_price': 85.00}
}

def get_current_stock_prices():
    """Get current stock prices with simulated fluctuation"""
    prices = {}
    for symbol, data in STOCK_DATA.items():
        # Simulate price fluctuation
        base_price = data['base_price']
        fluctuation = random.uniform(-0.05, 0.05)  # +/- 5% fluctuation
        current_price = base_price * (1 + fluctuation)
        prices[symbol] = {
            'name': data['name'],
            'price': round(current_price, 2),
            'change': round(fluctuation * 100, 2)
        }
    return prices

def init_dynamodb():
    """Initialize DynamoDB tables"""
    if not dynamodb:
        print("DynamoDB not available, using simulation mode")
        return
    
    try:
        # Users table
        try:
            users_table = dynamodb.create_table(
                TableName=f'{DYNAMODB_TABLE_PREFIX}users',
                KeySchema=[
                    {'AttributeName': 'username', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'username', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("Users table created")
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Users table already exists")
        
        # Portfolio table
        try:
            portfolio_table = dynamodb.create_table(
                TableName=f'{DYNAMODB_TABLE_PREFIX}portfolio',
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'stock_symbol', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'stock_symbol', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("Portfolio table created")
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Portfolio table already exists")
        
        # Trade history table
        try:
            trade_history_table = dynamodb.create_table(
                TableName=f'{DYNAMODB_TABLE_PREFIX}trade_history',
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("Trade history table created")
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Trade history table already exists")
        
        # Help messages table
        try:
            help_messages_table = dynamodb.create_table(
                TableName=f'{DYNAMODB_TABLE_PREFIX}help_messages',
                KeySchema=[
                    {'AttributeName': 'message_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'message_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("Help messages table created")
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Help messages table already exists")
        
        print("DynamoDB tables initialization completed")
        
    except Exception as e:
        print(f"DynamoDB table creation failed: {e}")

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def send_email_notification(to_email, subject, body):
    """Send email notification"""
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
        
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_sns_notification(message):
    """Send SNS notification"""
    try:
        if sns:
            response = sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject='Stocker Alert'
            )
            print(f"SNS notification sent: {response['MessageId']}")
            return True
        else:
            print(f"SNS Notification (simulated): {message}")
            return True
    except Exception as e:
        print(f"SNS notification failed: {e}")
        return False

# DynamoDB helper functions
def get_user_by_email(email):
    """Get user by email"""
    if not dynamodb:
        return None
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}users')
        response = table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"DynamoDB get_user_by_email error: {e}")
        return None

def get_user_by_username(username):
    """Get user by username"""
    if not dynamodb:
        return None
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}users')
        response = table.get_item(Key={'username': username})
        return response.get('Item')
    except Exception as e:
        print(f"DynamoDB get_user_by_username error: {e}")
        return None

def create_user(username, email, password_hash, role):
    """Create new user"""
    if not dynamodb:
        return False
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}users')
        table.put_item(Item={
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'created_at': datetime.now().isoformat()
        })
        return True
    except Exception as e:
        print(f"DynamoDB create_user error: {e}")
        return False

def get_user_portfolio(user_id):
    """Get user portfolio"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}portfolio')
        response = table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_user_portfolio error: {e}")
        return []

def update_portfolio(user_id, stock_symbol, quantity, average_price):
    """Update user portfolio"""
    if not dynamodb:
        return False
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}portfolio')
        if quantity > 0:
            table.put_item(Item={
                'user_id': user_id,
                'stock_symbol': stock_symbol,
                'quantity': quantity,
                'average_price': Decimal(str(average_price)),
                'created_at': datetime.now().isoformat()
            })
        else:
            table.delete_item(Key={'user_id': user_id, 'stock_symbol': stock_symbol})
        return True
    except Exception as e:
        print(f"DynamoDB update_portfolio error: {e}")
        return False

def add_trade_history(user_id, stock_symbol, trade_type, quantity, price, total_amount):
    """Add trade to history"""
    if not dynamodb:
        return False
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}trade_history')
        timestamp = datetime.now().isoformat()
        table.put_item(Item={
            'user_id': user_id,
            'timestamp': timestamp,
            'stock_symbol': stock_symbol,
            'trade_type': trade_type,
            'quantity': quantity,
            'price': Decimal(str(price)),
            'total_amount': Decimal(str(total_amount)),
            'created_at': timestamp
        })
        return True
    except Exception as e:
        print(f"DynamoDB add_trade_history error: {e}")
        return False

def get_user_trade_history(user_id):
    """Get user trade history"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}trade_history')
        response = table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id},
            ScanIndexForward=False
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_user_trade_history error: {e}")
        return []

def add_help_message(user_id, username, message):
    """Add help message"""
    if not dynamodb:
        return False
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}help_messages')
        message_id = f"{user_id}_{int(time.time())}"
        table.put_item(Item={
            'message_id': message_id,
            'user_id': user_id,
            'username': username,
            'message': message,
            'created_at': datetime.now().isoformat()
        })
        return True
    except Exception as e:
        print(f"DynamoDB add_help_message error: {e}")
        return False

def get_all_users():
    """Get all users"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}users')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_all_users error: {e}")
        return []

def get_all_portfolios():
    """Get all portfolios"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}portfolio')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_all_portfolios error: {e}")
        return []

def get_all_trades():
    """Get all trades"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}trade_history')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_all_trades error: {e}")
        return []

def get_all_help_messages():
    """Get all help messages"""
    if not dynamodb:
        return []
    
    try:
        table = dynamodb.Table(f'{DYNAMODB_TABLE_PREFIX}help_messages')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"DynamoDB get_all_help_messages error: {e}")
        return []

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        password_hash = hash_password(password)
        user = get_user_by_email(email)
        
        if user and user['password_hash'] == password_hash and user['role'] == role:
            session['user_id'] = user['username']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            
            # Send notifications
            send_email_notification(user['email'], "Login Alert", f"User {user['username']} logged in as {role}")
            send_sns_notification(f"User {user['username']} logged in as {role}")
            
            if role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
        flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Check if username already exists
        if get_user_by_username(username):
            flash('Username already exists')
            return render_template('signup.html')
        
        password_hash = hash_password(password)
        if create_user(username, email, password_hash, role):
            # Send notifications
            send_email_notification(email, "Welcome to Stocker", f"Welcome {username}! Your account has been created.")
            send_sns_notification(f"New user signup: {username} as {role}")
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
        else:
            flash('Signup failed')
    
    return render_template('signup.html')

@app.route('/check_username/<username>')
def check_username(username):
    exists = get_user_by_username(username) is not None
    return jsonify({'exists': exists})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/trade')
def trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('trade.html', username=session['username'])

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('portfolio.html', username=session['username'])

@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('history.html', username=session['username'])

@app.route('/help', methods=['GET', 'POST'])
def help():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        message = request.form['message']
        
        if add_help_message(session['user_id'], session['username'], message):
            flash('Message sent successfully!')
        else:
            flash('Failed to send message')
    
    return render_template('help.html', username=session['username'])

# Admin routes
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session['username'])

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    return render_template('admin_portfolio.html', username=session['username'])

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    return render_template('admin_history.html', username=session['username'])

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    return render_template('admin_manage.html', username=session['username'])

# API endpoints
@app.route('/api/stock_prices')
def api_stock_prices():
    return jsonify(get_current_stock_prices())

@app.route('/api/execute_trade', methods=['POST'])
def api_execute_trade():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    stock_symbol = data['stock_symbol']
    trade_type = data['trade_type']
    quantity = int(data['quantity'])
    price = float(data['price'])
    total_amount = quantity * price
    
    # Record trade in history
    add_trade_history(session['user_id'], stock_symbol, trade_type, quantity, price, total_amount)
    
    # Update portfolio
    portfolio = get_user_portfolio(session['user_id'])
    portfolio_item = None
    for item in portfolio:
        if item['stock_symbol'] == stock_symbol:
            portfolio_item = item
            break
    
    if trade_type == 'buy':
        if portfolio_item:
            current_quantity = int(portfolio_item['quantity'])
            current_avg_price = float(portfolio_item['average_price'])
            new_quantity = current_quantity + quantity
            new_avg_price = ((current_quantity * current_avg_price) + (quantity * price)) / new_quantity
            
            update_portfolio(session['user_id'], stock_symbol, new_quantity, new_avg_price)
        else:
            update_portfolio(session['user_id'], stock_symbol, quantity, price)
    
    elif trade_type == 'sell':
        if portfolio_item:
            current_quantity = int(portfolio_item['quantity'])
            if current_quantity >= quantity:
                new_quantity = current_quantity - quantity
                avg_price = float(portfolio_item['average_price'])
                update_portfolio(session['user_id'], stock_symbol, new_quantity, avg_price)
    
    return jsonify({'success': True})

@app.route('/api/portfolio')
def api_portfolio():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    portfolio = get_user_portfolio(session['user_id'])
    current_prices = get_current_stock_prices()
    
    result = []
    for item in portfolio:
        symbol = item['stock_symbol']
        quantity = int(item['quantity'])
        avg_price = float(item['average_price'])
        current_price = current_prices.get(symbol, {}).get('price', 0)
        
        result.append({
            'symbol': symbol,
            'name': STOCK_DATA[symbol]['name'],
            'quantity': quantity,
            'average_price': avg_price,
            'current_price': current_price,
            'total_value': quantity * current_price,
            'created_at': item['created_at']
        })
    
    return jsonify(result)

@app.route('/api/trade_history')
def api_trade_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    history = get_user_trade_history(session['user_id'])
    
    result = []
    for item in history:
        symbol = item['stock_symbol']
        result.append({
            'symbol': symbol,
            'name': STOCK_DATA[symbol]['name'],
            'trade_type': item['trade_type'],
            'quantity': int(item['quantity']),
            'price': float(item['price']),
            'total_amount': float(item['total_amount']),
            'created_at': item['created_at']
        })
    
    return jsonify(result)

# Admin API endpoints
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        users = get_all_users()
        trades = get_all_trades()
        portfolios = get_all_portfolios()
        
        total_traders = len([u for u in users if u.get('role') == 'Trader'])
        total_trades = len(trades)
        
        # Calculate total portfolio value
        total_portfolio_value = 0
        current_prices = get_current_stock_prices()
        for portfolio_item in portfolios:
            symbol = portfolio_item['stock_symbol']
            quantity = int(portfolio_item['quantity'])
            current_price = current_prices.get(symbol, {}).get('price', 0)
            total_portfolio_value += quantity * current_price
        
        return jsonify({
            'total_traders': total_traders,
            'total_trades': total_trades,
            'total_portfolio_value': round(total_portfolio_value, 2)
        })
    except Exception as e:
        print(f"Admin stats error: {e}")
        return jsonify({
            'total_traders': 0,
            'total_trades': 0,
            'total_portfolio_value': 0.00
        })

@app.route('/api/admin/all_portfolios')
def api_admin_all_portfolios():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        portfolios = get_all_portfolios()
        users = get_all_users()
        current_prices = get_current_stock_prices()
        
        # Create username lookup
        username_lookup = {user['username']: user['username'] for user in users}
        
        result = []
        for item in portfolios:
            symbol = item['stock_symbol']
            quantity = int(item['quantity'])
            avg_price = float(item['average_price'])
            current_price = current_prices.get(symbol, {}).get('price', 0)
            username = username_lookup.get(item['user_id'], item['user_id'])
            
            result.append({
                'username': username,
                'symbol': symbol,
                'name': STOCK_DATA.get(symbol, {}).get('name', symbol),
                'quantity': quantity,
                'average_price': avg_price,
                'current_price': current_price,
                'total_value': quantity * current_price,
                'created_at': item['created_at']
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Admin portfolios error: {e}")
        return jsonify([])

@app.route('/api/admin/all_trades')
def api_admin_all_trades():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        trades = get_all_trades()
        users = get_all_users()
        
        # Create username lookup
        username_lookup = {user['username']: user['username'] for user in users}
        
        result = []
        for item in trades:
            symbol = item['stock_symbol']
            username = username_lookup.get(item['user_id'], item['user_id'])
            
            result.append({
                'username': username,
                'symbol': symbol,
                'name': STOCK_DATA.get(symbol, {}).get('name', symbol),
                'trade_type': item['trade_type'],
                'quantity': int(item['quantity']),
                'price': float(item['price']),
                'total_amount': float(item['total_amount']),
                'created_at': item['created_at']
            })
        
        # Sort by created_at descending
        result.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(result)
    except Exception as e:
        print(f"Admin trades error: {e}")
        return jsonify([])

@app.route('/api/admin/users')
def api_admin_users():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        users = get_all_users()
        
        result = []
        for user in users:
            result.append({
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'created_at': user['created_at']
            })
        
        # Sort by created_at descending
        result.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(result)
    except Exception as e:
        print(f"Admin users error: {e}")
        return jsonify([])

@app.route('/api/admin/messages')
def api_admin_messages():
    if 'user_id' not in session or session['role'] != 'Admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        messages = get_all_help_messages()
        
        result = []
        for message in messages:
            result.append({
                'username': message['username'],
                'message': message['message'],
                'created_at': message['created_at']
            })
        
        # Sort by created_at descending
        result.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(result)
    except Exception as e:
        print(f"Admin messages error: {e}")
        return jsonify([])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def open_browser():
    global browser_opened
    if not browser_opened:
        webbrowser.open('http://127.0.0.1:5000')
        browser_opened = True

if __name__ == '__main__':
    init_dynamodb()
    print("Stocker AWS Version Starting...")
    print("Database: AWS DynamoDB")
    print("Notifications: AWS SNS")
    
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Opening browser...")
        timer = threading.Timer(1.0, open_browser)
        timer.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
