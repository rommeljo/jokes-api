from flask import Flask,jsonify,request
import requests
import jwt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import json
from flask_cors import CORS 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_bcrypt import Bcrypt
import base64
from requests.auth import HTTPBasicAuth
from datetime import datetime
from datetime import timedelta
from functools import wraps
from mpesa import make_stk_push


app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:johnrommel@localhost/shop'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"]="1234gh"


pass_key = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
consumer_secret = "eC7ujbAcQ7lMZzmgTT9RBU2nWxNY4mNIVLGe6vQRz5Fp0OCUDgh5gsAtdyttJp0T"
consumer_key = "kec26HTeIOkfpFHUBFMe2ZNMGE2wYj4587ij1lEAwGFfDgSu"
short_code = "174379"

# API URLs
token_api = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
stk_push_api = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
callback_url = "https://4cd1186f963f.ngrok-free.app/callback" 






db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

class Products(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(100), nullable=False)
    productprice = db.Column(db.Float, nullable=False)
    stockquantity = db.Column(db.Integer, nullable=False)
    sales = db.relationship('Sales', backref='product', lazy=True)


class Sales(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(15), nullable=True)

class Payment(db.Model):
    __tablename__ = 'payments' 
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)  
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="PENDING")
    checkout_request_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    
    sale = db.relationship('Sales', backref='payments')







with app.app_context():
    db.create_all()

CORS(app)  

@app.route("/")
def home():
    return "Welcome to the Shop API!"
     


@app.route("/products", methods=["GET"])
def get_products():
    products = Products.query.all()
    return jsonify([
        {
            "id": p.id,
            "productname": p.productname,
            "productprice": p.productprice,
            "stockquantity": p.stockquantity
        } for p in products
    ]), 200


@app.route("/products", methods=["POST"])
def add_product():
    data = request.get_json()

    required_fields = ["productname", "productprice", "stockquantity"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    new_product = Products(
        productname=data["productname"],
        productprice=data["productprice"],
        stockquantity=data["stockquantity"]
    )
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"message": "Product added successfully"}), 201

   
@app.route('/sales', methods=['GET'])
def get_sales():
    sales = Sales.query.all()
    return jsonify([
        {
            "id": s.id,
            "product_id": s.product_id,
            "productname": s.product.productname,
            "quantity": s.quantity,
            "sale_date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S")
        }
        for s in sales
    ])

# Add sale
@app.route('/sales', methods=['POST'])
def add_sale():
    data = request.json

    
    product = Products.query.get(data['product_id'])
    if not product:
        return jsonify({"error": "Product not found"}), 404

    
    if product.stockquantity < data['quantity']:
        return jsonify({"error": "Not enough stock"}), 400

    # Deduct stock
    product.stockquantity -= data['quantity']

    # Create sale
    new_sale = Sales(
        product_id=data['product_id'],
        quantity=data['quantity']
    )
    db.session.add(new_sale)
    db.session.commit()
    return jsonify({"message": "Sale added successfully"}), 201


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = Users(
        name=data['name'],
        email=data['email'],
        password=hashed_pw,
        phone=data.get('phone')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = Users.query.filter_by(email=data['email']).first()

    if user and bcrypt.check_password_hash(user.password, data['password']):
        token = create_access_token(identity=user.id)
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }), 200

    return jsonify({"error": "Invalid email or password"}), 401










# Get Access Token
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(consumer_key, consumer_secret))
    return response.json()['access_token']

# Encode password
def lipa_na_mpesa_password():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    data_to_encode = short_code + pass_key + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    return password, timestamp

# Trigger STK Push
@app.route('/mpesa/stkpush', methods=['POST'])
def stkpush():
    data = request.json
    phone = data.get("phone")
    sale_id = data.get("sale_id")

    sale = Sales.query.get(sale_id)
    if not sale:
        return jsonify({"error": "Sale not found"}), 404

    
    amount = sale.quantity * sale.product.productprice

    access_token = get_access_token()
    password, timestamp = lipa_na_mpesa_password()

    payload = {
        "BusinessShortCode": short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": str(sale_id),
        "TransactionDesc": "Sale Payment"
    }

    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

    res_data = res.json()

    # Save payment record
    payment = Payment(
        sale_id=sale_id,
        phone_number=phone,
        amount=amount,
        checkout_request_id=res_data.get("CheckoutRequestID"),
        status="PENDING"
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify(res_data)

# Callback URL
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.json
    stk_callback = data['Body']['stkCallback']
    checkout_id = stk_callback['CheckoutRequestID']
    result_code = stk_callback['ResultCode']

    payment = Payment.query.filter_by(checkout_request_id=checkout_id).first()
    if payment:
        payment.status = "SUCCESS" if result_code == 0 else "FAILED"
        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


    
if __name__ == "__main__":
    app.run(debug=True)