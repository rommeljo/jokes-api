from flask import Flask,jsonify,request
import requests
import jwt
import json
from flask_cors import CORS 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import sentry_sdk
from datetime import datetime
from datetime import timedelta
from functools import wraps

sentry_sdk.init(
    dsn="https://f65d41617cdbed3cf5f17a479313ea98@o4507805043785728.ingest.us.sentry.io/4507805098442752",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
) 

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:johnrommel@localhost/shop'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"]="1234gh"

db = SQLAlchemy(app)


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

with app.app_context():
    db.create_all()

CORS(app, resources={r"/products/*": {"origins": "http://127.0.0.1:5500"},r"/sales-per-day/*": {"origins": "http://127.0.0.1:5500"}})
CORS(app, resources={r"/products/*": {"origins": "http://127.0.0.1:5500"}, r"/sales/*": {"origins": "http://127.0.0.1:5500"},r"/login/*": {"origins": "http://127.0.0.1:5500"}})
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}})

@app.route("/")
def home():
    r = requests.get('https://official-joke-api.appspot.com/random_joke')
    print(type(r.json()))
    return r.json()


@app.route("/person")
def person():
    person={"id":1,"name":'john'}
    return json.dumps(person)



@app.route("/products", methods=['POST', 'GET'])
def products():
    if request.method == 'POST':
        try:
            myproducts = request.get_json()  
    
            new_product = Products(
                productname=myproducts['product_name'],
                productprice=myproducts['product_price'],
                stockquantity=myproducts.get('stock_quantity', 0)  
            )
            db.session.add(new_product)  
            db.session.commit()  
            return jsonify({"message": "Product added successfully"}), 201  
        except Exception as e:
            db.session.rollback()  
            return jsonify({"error": str(e)}), 500  

    elif request.method == 'GET':
        try:
           
            products = Products.query.all()
          
            prods = [{"product_name": product.productname, "product_price": product.productprice, "stock_quantity": product.stockquantity} for product in products]
            return jsonify(prods), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
def add_product():
    try:
        data = request.json
        new_product = Products(
            productname=data['productname'],
            productprice=data['productprice'],
            stockquantity=data['stockquantity']
        )
        db.session.add(new_product)
        db.session.commit()
        return jsonify({'id': new_product.id}), 201
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500
    
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            # Decode the token
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])

            # Extract the current user information (assuming "name" is in the token data)
            current_user = data.get("name")

            if not current_user:
                return jsonify({"message": "User not found!"}), 401

            # Pass the current user and any other args/kwargs to the decorated function
            return f(current_user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401

    return decorated

@app.route("/sales", methods=['POST', 'GET'])
@token_required
def sales(current_user):
    if request.method == 'POST':
        try:
            sale_data = request.get_json()

            # Retrieve the product by ID
            product = Products.query.get(sale_data['product_id'])

            if not product:
                return jsonify({"error": "Product not found"}), 404

            if product.stockquantity < sale_data['quantity']:
                return jsonify({"error": "Not enough stock available"}), 400

            # Create a new sale entry
            new_sale = Sales(
                product_id=sale_data['product_id'],
                quantity=sale_data['quantity']
            )

            # Update the product's stock quantity
            product.stockquantity -= sale_data['quantity']

            db.session.add(new_sale)
            db.session.commit()

            return jsonify({"message": "Sale recorded successfully", "sale_id": new_sale.id}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    elif request.method == 'GET':
        try:
            user=db.session.query(Users).filter(Users.name==current_user)
            if not user:
                return jsonify({"message":"not found"}),404
           
           

           
            # Retrieve all sales



            sales = Sales.query.all()

            # Serialize the sales data
            sales_list = [{
                "product_name": sale.product.productname,
                "quantity": sale.quantity,
                "sale_date": sale.sale_date
            } for sale in sales]

            return jsonify(sales_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500





@app.route("/sales-per-day", methods=['GET'])
def sales_per_day():
    try:
        sales_data = db.session.query(
            func.date(Sales.sale_date).label('sale_date'),  
            func.sum(Sales.quantity).label('total_quantity')  
        ).group_by(
            func.date(Sales.sale_date)  
        ).all()

        
        result = [{"sale_date": sale.sale_date.strftime('%Y-%m-%d'), "total_quantity": sale.total_quantity} for sale in sales_data]

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/login")
def login_user():
    data = request.json
    u = data["name"]
    p = data["password"]
    
    # Check if user exists
    existing_user = db.session.query(Users).filter(Users.name == u, Users.password == p).first()
    
    if not existing_user:
        return jsonify({"message": "login fail"}), 401  # Return a 401 Unauthorized status if login fails

    try:
        # Generate JWT token
        access_token = jwt.encode({"sub": u, "exp": datetime.utcnow() + timedelta(minutes=30)}, app.config["SECRET_KEY"])
        return jsonify({"access_token": access_token, "message": "login successful"}), 200
    except Exception as e:
        return jsonify({"error": "error creating access token", "details": str(e)}), 500




@app.route("/sentry")
def hello_world():
    try:
        division_by_zero = 1 / 0
        return jsonify({"result": division_by_zero})
    except ZeroDivisionError as e:
        sentry_sdk.capture_exception(e)
        return jsonify({"error": str(e)}), 500
    

app.run(debug=True)