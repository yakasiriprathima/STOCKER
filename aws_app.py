import boto3
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
from decimal import Decimal
import uuid

app = Flask(__name__)
app.secret_key = 'stocker_secret_key_2024'

# AWS Configuration (hardcoded for demo)
AWS_ACCESS_KEY_ID = 'your-access-key-id'
AWS_SECRET_ACCESS_KEY = 'your-secret-access-key'
AWS_REGION = 'us-east-1'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:stocker-notifications'

# Email configuration (hardcoded for demo)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = 'your-email@gmail.com'
EMAIL_PASS = 'your-app-password'

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', 
                         aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                         region_name=AWS_REGION)

sns = boto3.client('sns',
                   aws_access_key_id=AWS_ACCESS_KEY_ID,
                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                   region_name=AWS_REGION)

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

def init_dynamodb():
    try:
        # Create Users table
        users_table = dynamodb.create_table(
            TableName='stocker_users',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'username', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'username-index',
                    'KeySchema': [
                        {'AttributeName': 'username', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create Portfolio table
        portfolio_table = dynamodb.create_table(
            TableName='stocker_portfolio',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'symbol', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create Trades table
        trades_table = dynamodb.create_table(
            TableName='stocker_trades',
            KeySchema=[
                {'AttributeName': 'trade_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'trade_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create Messages table
        messages_table = dynamodb.create_table(
            TableName='stocker_messages',
            KeySchema=[
                {'AttributeName': 'message_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'message_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("DynamoDB tables created successfully!")
        
    except Exception as e:
        print(f"Tables might already exist: {e}")

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
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject='Stocker Notification'
        )
        return True
    except Exception as e:
        print(f"SNS notification failed: {e}")
        return False

def update_stock_prices():
    while True:
        for symbol in STOCKS:
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
        
        users_table = dynamodb.Table('stocker_users')
        response = users_table.query(
            IndexName='username-index',
            KeyConditionExpression='username = :username',
            ExpressionAttributeValues={':username': username}
        )
        
        if response['Items']:
            user = response['Items'][0]
            if user['password'] == hash_password(password) and user['role'] == role:
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                
                # Send notifications
                send_email(user['email'], 'Stocker Login', f'Hello {username}, you have successfully logged in to Stocker.')
                send_sns_notification(f'User {username} logged in as {role}')
                
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
        
        user_id = str(uuid.uuid4())
        
        users_table = dynamodb.Table('stocker_users')
        
        try:
            users_table.put_item(
                Item={
                    'user_id': user_id,
                    'username': username,
                    'email': email,
                    'password': hash_password(password),
                    'role': role,
                    'created_at': datetime.datetime.now().isoformat()
                },
                ConditionExpression='attribute_not_exists(username)'
            )
            
            # Send notifications
            send_email(email, 'Welcome to Stocker', f'Hello {username}, welcome to Stocker! Your account has been created.')
            send_sns_notification(f'New user {username} signed up as {role}')
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('Username already exists')
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    
    users_table = dynamodb.Table('stocker_users')
    response = users_table.query(
        IndexName='username-index',
        KeyConditionExpression='username = :username',
        ExpressionAttributeValues={':username': username}
    )
    
    exists = len(response['Items']) > 0
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
    
    symbol = request.form['symbol']
    action = request.form['action']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])
    total = quantity * price
    
    # Record trade
    trades_table = dynamodb.Table('stocker_trades')
    trades_table.put_item(
        Item={
            'trade_id': str(uuid.uuid4()),
            'user_id': session['user_id'],
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': Decimal(str(price)),
            'total': Decimal(str(total)),
            'created_at': datetime.datetime.now().isoformat()
        }
    )
    
    # Update portfolio
    portfolio_table = dynamodb.Table('stocker_portfolio')
    
    if action == 'Buy':
        try:
            response = portfolio_table.get_item(
                Key={'user_id': session['user_id'], 'symbol': symbol}
            )
            
            if 'Item' in response:
                existing = response['Item']
                new_quantity = existing['quantity'] + quantity
                new_avg_price = ((existing['quantity'] * existing['avg_price']) + total) / new_quantity
                
                portfolio_table.update_item(
                    Key={'user_id': session['user_id'], 'symbol': symbol},
                    UpdateExpression='SET quantity = :q, avg_price = :p',
                    ExpressionAttributeValues={
                        ':q': new_quantity,
                        ':p': Decimal(str(new_avg_price))
                    }
                )
            else:
                portfolio_table.put_item(
                    Item={
                        'user_id': session['user_id'],
                        'symbol': symbol,
                        'quantity': quantity,
                        'avg_price': Decimal(str(price)),
                        'created_at': datetime.datetime.now().isoformat()
                    }
                )
        except Exception as e:
            print(f"Error updating portfolio: {e}")
    
    elif action == 'Sell':
        try:
            response = portfolio_table.get_item(
                Key={'user_id': session['user_id'], 'symbol': symbol}
            )
            
            if 'Item' in response:
                existing = response['Item']
                if existing['quantity'] >= quantity:
                    new_quantity = existing['quantity'] - quantity
                    if new_quantity > 0:
                        portfolio_table.update_item(
                            Key={'user_id': session['user_id'], 'symbol': symbol},
                            UpdateExpression='SET quantity = :q',
                            ExpressionAttributeValues={':q': new_quantity}
                        )
                    else:
                        portfolio_table.delete_item(
                            Key={'user_id': session['user_id'], 'symbol': symbol}
                        )
        except Exception as e:
            print(f"Error updating portfolio: {e}")
    
    flash(f'Trade executed: {action} {quantity} shares of {symbol}')
    return redirect(url_for('portfolio'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    portfolio_table = dynamodb.Table('stocker_portfolio')
    response = portfolio_table.query(
        KeyConditionExpression='user_id = :user_id',
        ExpressionAttributeValues={':user_id': session['user_id']}
    )
    
    portfolio_data = []
    for item in response['Items']:
        current_price = STOCKS[item['symbol']]['price']
        total_value = float(item['quantity']) * current_price
        portfolio_data.append({
            'symbol': item['symbol'],
            'name': STOCKS[item['symbol']]['name'],
            'quantity': item['quantity'],
            'avg_price': float(item['avg_price']),
            'current_price': current_price,
            'total_value': total_value,
            'created_at': item['created_at']
        })
    
    return render_template('portfolio.html', portfolio=portfolio_data, stocks=STOCKS)

@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    trades_table = dynamodb.Table('stocker_trades')
    response = trades_table.query(
        IndexName='user-id-index',
        KeyConditionExpression='user_id = :user_id',
        ExpressionAttributeValues={':user_id': session['user_id']},
        ScanIndexForward=False
    )
    
    trades = []
    for item in response['Items']:
        trades.append([
            item['trade_id'],
            item['user_id'],
            item['symbol'],
            item['action'],
            item['quantity'],
            float(item['price']),
            float(item['total']),
            item['created_at']
        ])
    
    return render_template('history.html', trades=trades)

@app.route('/help', methods=['GET', 'POST'])
def help():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        message = request.form['message']
        
        messages_table = dynamodb.Table('stocker_messages')
        messages_table.put_item(
            Item={
                'message_id': str(uuid.uuid4()),
                'user_id': session['user_id'],
                'message': message,
                'created_at': datetime.datetime.now().isoformat()
            }
        )
        flash('Message sent successfully!')
    
    return render_template('help.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    # Get stats from DynamoDB
    users_table = dynamodb.Table('stocker_users')
    trades_table = dynamodb.Table('stocker_trades')
    portfolio_table = dynamodb.Table('stocker_portfolio')
    
    # Count traders
    users_response = users_table.scan(
        FilterExpression='#role = :role',
        ExpressionAttributeNames={'#role': 'role'},
        ExpressionAttributeValues={':role': 'Trader'}
    )
    total_traders = users_response['Count']
    
    # Count trades
    trades_response = trades_table.scan()
    total_trades = trades_response['Count']
    
    # Calculate portfolio value
    portfolio_response = portfolio_table.scan()
    total_portfolio_value = 0
    for item in portfolio_response['Items']:
        total_portfolio_value += float(item['quantity']) * float(item['avg_price'])
    
    return render_template('admin_dashboard.html', 
                         total_traders=total_traders,
                         total_trades=total_trades,
                         total_portfolio_value=total_portfolio_value)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    portfolio_table = dynamodb.Table('stocker_portfolio')
    users_table = dynamodb.Table('stocker_users')
    
    portfolio_response = portfolio_table.scan()
    portfolios = []
    
    for item in portfolio_response['Items']:
        user_response = users_table.get_item(Key={'user_id': item['user_id']})
        username = user_response['Item']['username'] if 'Item' in user_response else 'Unknown'
        
        portfolios.append([
            username,
            item['symbol'],
            item['quantity'],
            float(item['avg_price']),
            item['created_at']
        ])
    
    return render_template('admin_portfolio.html', portfolios=portfolios, stocks=STOCKS)

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    trades_table = dynamodb.Table('stocker_trades')
    users_table = dynamodb.Table('stocker_users')
    
    trades_response = trades_table.scan()
    trades = []
    
    for item in trades_response['Items']:
        user_response = users_table.get_item(Key={'user_id': item['user_id']})
        username = user_response['Item']['username'] if 'Item' in user_response else 'Unknown'
        
        trades.append([
            username,
            item['symbol'],
            item['action'],
            item['quantity'],
            float(item['price']),
            float(item['total']),
            item['created_at']
        ])
    
    # Sort by created_at descending
    trades.sort(key=lambda x: x[6], reverse=True)
    
    return render_template('admin_history.html', trades=trades)

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    users_table = dynamodb.Table('stocker_users')
    messages_table = dynamodb.Table('stocker_messages')
    
    # Get users
    users_response = users_table.scan(
        FilterExpression='#role = :role',
        ExpressionAttributeNames={'#role': 'role'},
        ExpressionAttributeValues={':role': 'Trader'}
    )
    
    users = []
    for item in users_response['Items']:
        users.append([
            item['user_id'],
            item['username'],
            item['email'],
            item['password'],
            item['role'],
            item['created_at']
        ])
    
    # Get messages
    messages_response = messages_table.scan()
    messages = []
    
    for item in messages_response['Items']:
        user_response = users_table.get_item(Key={'user_id': item['user_id']})
        username = user_response['Item']['username'] if 'Item' in user_response else 'Unknown'
        
        messages.append([
            item['message'],
            item['created_at'],
            username
        ])
    
    # Sort messages by created_at descending
    messages.sort(key=lambda x: x[1], reverse=True)
    
    return render_template('admin_manage.html', users=users, messages=messages)

@app.route('/get_stock_prices')
def get_stock_prices():
    return jsonify(STOCKS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_dynamodb()
    
    # Auto-open browser
    def open_browser():
        webbrowser.open('http://127.0.0.1:5000')
    
    threading.Timer(1, open_browser).start()
    app.run(debug=True, host='0.0.0.0', port=5000)
