from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app)

# ✅ Reads from Railway environment variable
db_url = os.environ.get('DATABASE_URL', '')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'agrirentx_secret'

db = SQLAlchemy(app)


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name           = db.Column(db.String(255), nullable=False)
    email          = db.Column(db.String(255), unique=True, nullable=False)
    phone          = db.Column(db.String(50),  nullable=False)
    password       = db.Column(db.String(255), nullable=False)
    role           = db.Column(db.String(10),  nullable=False)
    area           = db.Column(db.String(150), nullable=True)
    city           = db.Column(db.String(150), nullable=True)
    state          = db.Column(db.String(150), nullable=True)
    wallet_balance = db.Column(db.Numeric(12, 2), default=0.00)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)


class ActiveSession(db.Model):
    __tablename__ = 'active_sessions'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email    = db.Column(db.String(255), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name          = db.Column(db.String(255), nullable=False)
    category      = db.Column(db.String(100), nullable=False)
    area          = db.Column(db.String(150), nullable=False)
    city          = db.Column(db.String(150), nullable=False)
    state         = db.Column(db.String(150), nullable=False)
    price_per_day = db.Column(db.Numeric(12, 2), nullable=False)
    description   = db.Column(db.Text, nullable=True)
    specs         = db.Column(db.String(500), nullable=True)
    available     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    __tablename__ = 'bookings'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    farmer_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date   = db.Column(db.Date, nullable=False)
    end_date     = db.Column(db.Date, nullable=False)
    days         = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status       = db.Column(db.String(15), default='pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payments'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount     = db.Column(db.Numeric(12, 2), nullable=False)
    method     = db.Column(db.String(20), nullable=False)
    status     = db.Column(db.String(15), default='success')
    paid_at    = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = 'reviews'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    booking_id   = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    farmer_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating       = db.Column(db.Numeric(2, 1), nullable=False)
    comment      = db.Column(db.String(500), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text        = db.Column(db.String(1000), nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    body       = db.Column(db.String(500), nullable=True)
    icon       = db.Column(db.String(50),  nullable=True)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WalletTransaction(db.Model):
    __tablename__ = 'wallet_transactions'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount     = db.Column(db.Numeric(12, 2), nullable=False)
    type       = db.Column(db.String(10), nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def equipment_rating(equipment_id):
    reviews = Review.query.filter_by(equipment_id=equipment_id).all()
    if not reviews:
        return 0.0, 0
    avg = sum(float(r.rating) for r in reviews) / len(reviews)
    return round(avg, 1), len(reviews)


def equipment_json(e, include_owner=True):
    rating, count = equipment_rating(e.id)
    data = {
        'id': e.id, 'owner_id': e.owner_id, 'name': e.name,
        'category': e.category, 'area': e.area, 'city': e.city, 'state': e.state,
        'location': f'{e.area}, {e.city}, {e.state}',
        'price_per_day': float(e.price_per_day),
        'description': e.description, 'specs': e.specs,
        'available': bool(e.available), 'rating': rating, 'review_count': count,
    }
    if include_owner:
        owner = User.query.get(e.owner_id)
        data['owner_name']  = owner.name  if owner else 'Unknown'
        data['owner_phone'] = owner.phone if owner else ''
    return data


def make_notification(user_id, title, body, icon='info'):
    db.session.add(Notification(user_id=user_id, title=title, body=body, icon=icon))


def credit_wallet(user_id, amount, title):
    user = User.query.get(user_id)
    if not user:
        return
    user.wallet_balance = float(user.wallet_balance or 0) + float(amount)
    db.session.add(WalletTransaction(user_id=user_id, amount=amount, type='credit', title=title))


def debit_wallet(user_id, amount, title):
    user = User.query.get(user_id)
    if not user:
        return
    user.wallet_balance = float(user.wallet_balance or 0) - float(amount)
    db.session.add(WalletTransaction(user_id=user_id, amount=amount, type='debit', title=title))


def booking_json(b):
    e      = Equipment.query.get(b.equipment_id)
    farmer = User.query.get(b.farmer_id)
    owner  = User.query.get(b.owner_id)
    return {
        'id': b.id, 'equipment_id': b.equipment_id,
        'equipment_name': e.name if e else 'Equipment',
        'category': e.category if e else '',
        'farmer_id': b.farmer_id, 'farmer_name': farmer.name if farmer else 'Farmer',
        'farmer_phone': farmer.phone if farmer else '',
        'owner_id': b.owner_id, 'owner_name': owner.name if owner else 'Owner',
        'start_date': b.start_date.strftime('%d %b %Y'),
        'end_date':   b.end_date.strftime('%d %b %Y'),
        'dates': f"{b.start_date.strftime('%d %b')} - {b.end_date.strftime('%d %b %Y')}",
        'days': b.days, 'amount': float(b.total_amount),
        'status': b.status.capitalize(),
        'created_at': b.created_at.strftime('%d %b %Y'),
    }


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        required = ['name', 'email', 'phone', 'password', 'role']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['role'] not in ('farmer', 'owner'):
            return jsonify({'error': "role must be 'farmer' or 'owner'"}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        new_user = User(
            name=data['name'], email=data['email'], phone=data['phone'],
            password=generate_password_hash(data['password']),
            role=data['role'], area=data.get('area', ''),
            city=data.get('city', ''), state=data.get('state', '')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully', 'id': new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        user = User.query.filter_by(email=data['email']).first()
        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        db.session.add(ActiveSession(email=user.email))
        db.session.commit()
        return jsonify({'message': 'Login successful', 'user': {
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'role': user.role,
            'area': user.area, 'city': user.city, 'state': user.state,
            'wallet_balance': float(user.wallet_balance or 0)
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/get_current_user', methods=['GET'])
def get_current_user():
    try:
        last = ActiveSession.query.order_by(ActiveSession.id.desc()).first()
        if not last:
            return jsonify({'error': 'No active user found'}), 404
        user = User.query.filter_by(email=last.email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'role': user.role,
            'area': user.area, 'city': user.city, 'state': user.state,
            'wallet_balance': float(user.wallet_balance or 0)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    try:
        data  = request.get_json()
        email = data.get('email') if data else None
        if not email:
            return jsonify({'error': 'Email required'}), 400
        ActiveSession.query.filter_by(email=email).delete()
        db.session.commit()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────

@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({
            'id': user.id, 'name': user.name, 'email': user.email,
            'phone': user.phone, 'role': user.role,
            'area': user.area, 'city': user.city, 'state': user.state,
            'wallet_balance': float(user.wallet_balance or 0),
            'created_at': user.created_at.strftime('%d %b %Y')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user.name  = data.get('name',  user.name)
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email)
        user.area  = data.get('area',  user.area)
        user.city  = data.get('city',  user.city)
        user.state = data.get('state', user.state)
        db.session.commit()
        return jsonify({'message': 'Profile updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/change_password/<int:user_id>', methods=['PUT'])
def change_password(user_id):
    try:
        data = request.get_json()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if not data or 'old_password' not in data or 'new_password' not in data:
            return jsonify({'error': 'old_password and new_password required'}), 400
        if not check_password_hash(user.password, data['old_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        user.password = generate_password_hash(data['new_password'])
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# EQUIPMENT
# ─────────────────────────────────────────

@app.route('/equipment', methods=['GET'])
def list_equipment():
    try:
        q         = request.args.get('q')
        category  = request.args.get('category')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        available = request.args.get('available')
        city      = request.args.get('city')
        state     = request.args.get('state')
        query = Equipment.query
        if category and category != 'All':
            query = query.filter_by(category=category)
        if city:
            query = query.filter_by(city=city)
        if state:
            query = query.filter_by(state=state)
        if min_price is not None:
            query = query.filter(Equipment.price_per_day >= min_price)
        if max_price is not None:
            query = query.filter(Equipment.price_per_day <= max_price)
        if available is not None:
            query = query.filter_by(available=(available.lower() == 'true'))
        if q:
            like = f'%{q}%'
            query = query.filter(db.or_(
                Equipment.name.like(like), Equipment.area.like(like),
                Equipment.city.like(like), Equipment.state.like(like),
            ))
        items = query.order_by(Equipment.created_at.desc()).all()
        return jsonify([equipment_json(e) for e in items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/<int:equipment_id>', methods=['GET'])
def get_equipment(equipment_id):
    try:
        e = Equipment.query.get(equipment_id)
        if not e:
            return jsonify({'error': 'Equipment not found'}), 404
        data    = equipment_json(e)
        reviews = Review.query.filter_by(equipment_id=e.id).order_by(Review.created_at.desc()).all()
        data['reviews'] = [{
            'id': r.id,
            'farmer_name': (User.query.get(r.farmer_id).name if User.query.get(r.farmer_id) else 'User'),
            'rating': float(r.rating), 'comment': r.comment,
            'created_at': r.created_at.strftime('%d %b %Y')
        } for r in reviews]
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/owner/<int:owner_id>', methods=['GET'])
def owner_equipment(owner_id):
    try:
        items = Equipment.query.filter_by(owner_id=owner_id).order_by(Equipment.created_at.desc()).all()
        return jsonify([equipment_json(e, include_owner=False) for e in items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/nearby/<int:user_id>', methods=['GET'])
def nearby_equipment(user_id):
    try:
        user  = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        city  = request.args.get('city',  user.city)
        state = request.args.get('state', user.state)
        in_city = Equipment.query.filter_by(available=True, city=city).all()
        if in_city:
            return jsonify([equipment_json(e) for e in in_city]), 200
        in_state = Equipment.query.filter_by(available=True, state=state).all()
        return jsonify([equipment_json(e) for e in in_state]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/equipment', methods=['POST'])
def add_equipment():
    try:
        data     = request.get_json()
        required = ['owner_id', 'name', 'category', 'area', 'city', 'state', 'price_per_day']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        e = Equipment(
            owner_id=data['owner_id'], name=data['name'],
            category=data['category'], area=data['area'],
            city=data['city'], state=data['state'],
            price_per_day=data['price_per_day'],
            description=data.get('description', ''),
            specs=data.get('specs', ''), available=data.get('available', True)
        )
        db.session.add(e)
        db.session.commit()
        return jsonify({'message': 'Equipment added', 'id': e.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/<int:equipment_id>', methods=['PUT'])
def update_equipment(equipment_id):
    try:
        data = request.get_json()
        e    = Equipment.query.get(equipment_id)
        if not e:
            return jsonify({'error': 'Equipment not found'}), 404
        e.name          = data.get('name',          e.name)
        e.category      = data.get('category',      e.category)
        e.area          = data.get('area',           e.area)
        e.city          = data.get('city',           e.city)
        e.state         = data.get('state',          e.state)
        e.price_per_day = data.get('price_per_day',  e.price_per_day)
        e.description   = data.get('description',    e.description)
        e.specs         = data.get('specs',          e.specs)
        if 'available' in data:
            e.available = bool(data['available'])
        db.session.commit()
        return jsonify({'message': 'Equipment updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/equipment/<int:equipment_id>', methods=['DELETE'])
def delete_equipment(equipment_id):
    try:
        e = Equipment.query.get(equipment_id)
        if not e:
            return jsonify({'error': 'Equipment not found'}), 404
        db.session.delete(e)
        db.session.commit()
        return jsonify({'message': 'Equipment deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/locations', methods=['GET'])
def locations():
    try:
        rows   = db.session.query(Equipment.city, Equipment.state).distinct().all()
        cities = sorted({c for c, s in rows if c})
        states = sorted({s for c, s in rows if s})
        return jsonify({'cities': cities, 'states': states}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────

@app.route('/bookings', methods=['POST'])
def create_booking():
    try:
        data     = request.get_json()
        required = ['equipment_id', 'farmer_id', 'start_date', 'end_date']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        e = Equipment.query.get(data['equipment_id'])
        if not e:
            return jsonify({'error': 'Equipment not found'}), 404
        if not e.available:
            return jsonify({'error': 'Equipment not available'}), 400
        start = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end   = datetime.strptime(data['end_date'],   '%Y-%m-%d').date()
        if end < start:
            return jsonify({'error': 'end_date cannot be before start_date'}), 400
        days  = (end - start).days + 1
        total = days * float(e.price_per_day)
        booking = Booking(
            equipment_id=e.id, farmer_id=data['farmer_id'], owner_id=e.owner_id,
            start_date=start, end_date=end, days=days, total_amount=total, status='pending'
        )
        db.session.add(booking)
        db.session.flush()
        farmer = User.query.get(data['farmer_id'])
        make_notification(e.owner_id, 'New Booking Request',
                          f"{farmer.name if farmer else 'A farmer'} requested {e.name}.",
                          'event_available')
        db.session.commit()
        return jsonify({'message': 'Booking created', 'id': booking.id,
                        'days': days, 'total_amount': total}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/bookings/farmer/<int:farmer_id>', methods=['GET'])
def farmer_bookings(farmer_id):
    try:
        status = request.args.get('status')
        query  = Booking.query.filter_by(farmer_id=farmer_id)
        if status:
            query = query.filter_by(status=status)
        items  = query.order_by(Booking.created_at.desc()).all()
        result = []
        for b in items:
            data = booking_json(b)
            data['reviewed'] = Review.query.filter_by(booking_id=b.id).first() is not None
            result.append(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/bookings/owner/<int:owner_id>', methods=['GET'])
def owner_bookings(owner_id):
    try:
        status = request.args.get('status')
        query  = Booking.query.filter_by(owner_id=owner_id)
        if status:
            query = query.filter_by(status=status)
        items  = query.order_by(Booking.created_at.desc()).all()
        return jsonify([booking_json(b) for b in items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        b = Booking.query.get(booking_id)
        if not b:
            return jsonify({'error': 'Booking not found'}), 404
        return jsonify(booking_json(b)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/bookings/<int:booking_id>/status', methods=['PUT'])
def update_booking_status(booking_id):
    try:
        data       = request.get_json()
        new_status = (data or {}).get('status')
        valid      = ('pending', 'approved', 'rejected', 'completed', 'cancelled')
        if new_status not in valid:
            return jsonify({'error': f'status must be one of {valid}'}), 400
        b = Booking.query.get(booking_id)
        if not b:
            return jsonify({'error': 'Booking not found'}), 404
        b.status = new_status
        e        = Equipment.query.get(b.equipment_id)
        eq_name  = e.name if e else 'equipment'
        if new_status == 'approved':
            make_notification(b.farmer_id, 'Booking Approved',
                              f'Your booking for {eq_name} was approved.', 'check_circle')
        elif new_status == 'rejected':
            make_notification(b.farmer_id, 'Booking Rejected',
                              f'Your booking for {eq_name} was rejected.', 'cancel')
        elif new_status == 'completed':
            credit_wallet(b.owner_id, float(b.total_amount), f'Rental earning — {eq_name}')
            make_notification(b.farmer_id, 'Rental Completed',
                              f'Your rental of {eq_name} is marked completed.', 'done_all')
        db.session.commit()
        return jsonify({'message': f'Booking {new_status}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/bookings/<int:booking_id>/invoice', methods=['GET'])
def booking_invoice(booking_id):
    try:
        b = Booking.query.get(booking_id)
        if not b:
            return jsonify({'error': 'Booking not found'}), 404
        e       = Equipment.query.get(b.equipment_id)
        payment = Payment.query.filter_by(booking_id=b.id).first()
        return jsonify({
            'invoice_no': f'AGRX-{b.id:05d}',
            'equipment_name': e.name if e else 'Equipment',
            'dates': f"{b.start_date.strftime('%d %b')} - {b.end_date.strftime('%d %b %Y')}",
            'days': b.days, 'amount': float(b.total_amount),
            'status': 'Paid' if payment else 'Unpaid',
            'method': payment.method if payment else None,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────

@app.route('/payments', methods=['POST'])
def make_payment():
    try:
        data     = request.get_json()
        required = ['booking_id', 'user_id', 'amount', 'method']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['method'] not in ('upi', 'card', 'wallet'):
            return jsonify({'error': "method must be 'upi', 'card' or 'wallet'"}), 400
        booking = Booking.query.get(data['booking_id'])
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        if data['method'] == 'wallet':
            user = User.query.get(data['user_id'])
            if float(user.wallet_balance or 0) < float(data['amount']):
                return jsonify({'error': 'Insufficient wallet balance'}), 400
            debit_wallet(data['user_id'], data['amount'], 'Booking payment')
        payment = Payment(
            booking_id=data['booking_id'], user_id=data['user_id'],
            amount=data['amount'], method=data['method'], status='success'
        )
        db.session.add(payment)
        db.session.commit()
        return jsonify({'message': 'Payment successful', 'id': payment.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────

@app.route('/reviews', methods=['POST'])
def add_review():
    try:
        data     = request.get_json()
        required = ['equipment_id', 'farmer_id', 'rating']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        rating = float(data['rating'])
        if not (1 <= rating <= 5):
            return jsonify({'error': 'rating must be between 1 and 5'}), 400
        booking_id = data.get('booking_id')
        if booking_id and Review.query.filter_by(booking_id=booking_id).first():
            return jsonify({'error': 'Already reviewed this booking'}), 409
        review = Review(
            equipment_id=data['equipment_id'], booking_id=booking_id,
            farmer_id=data['farmer_id'], rating=rating,
            comment=data.get('comment', '')
        )
        db.session.add(review)
        db.session.commit()
        return jsonify({'message': 'Review submitted', 'id': review.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/reviews/<int:equipment_id>', methods=['GET'])
def get_reviews(equipment_id):
    try:
        reviews = Review.query.filter_by(equipment_id=equipment_id).order_by(Review.created_at.desc()).all()
        return jsonify([{
            'id': r.id,
            'farmer_name': (User.query.get(r.farmer_id).name if User.query.get(r.farmer_id) else 'User'),
            'rating': float(r.rating), 'comment': r.comment,
            'created_at': r.created_at.strftime('%d %b %Y')
        } for r in reviews]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────

@app.route('/messages', methods=['POST'])
def send_message():
    try:
        data     = request.get_json()
        required = ['sender_id', 'receiver_id', 'text']
        if not data or not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        if not str(data['text']).strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        msg = Message(sender_id=data['sender_id'], receiver_id=data['receiver_id'],
                      text=data['text'].strip())
        db.session.add(msg)
        db.session.commit()
        return jsonify({'message': 'Sent', 'id': msg.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/messages/<int:user_id>/<int:other_id>', methods=['GET'])
def get_conversation(user_id, other_id):
    try:
        msgs = Message.query.filter(db.or_(
            db.and_(Message.sender_id == user_id,   Message.receiver_id == other_id),
            db.and_(Message.sender_id == other_id,  Message.receiver_id == user_id),
        )).order_by(Message.created_at.asc()).all()
        for m in msgs:
            if m.receiver_id == user_id and not m.is_read:
                m.is_read = True
        db.session.commit()
        return jsonify([{
            'id': m.id, 'sender_id': m.sender_id, 'receiver_id': m.receiver_id,
            'text': m.text, 'mine': m.sender_id == user_id,
            'created_at': m.created_at.strftime('%d %b %Y %I:%M %p')
        } for m in msgs]), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/conversations/<int:user_id>', methods=['GET'])
def list_conversations(user_id):
    try:
        msgs = Message.query.filter(db.or_(
            Message.sender_id == user_id, Message.receiver_id == user_id
        )).order_by(Message.created_at.desc()).all()
        threads = {}
        for m in msgs:
            other = m.receiver_id if m.sender_id == user_id else m.sender_id
            if other not in threads:
                other_user = User.query.get(other)
                threads[other] = {
                    'user_id': other, 'name': other_user.name if other_user else 'User',
                    'last_message': m.text, 'last_at': m.created_at.strftime('%d %b %I:%M %p'),
                    'unread': 0,
                }
            if m.receiver_id == user_id and not m.is_read:
                threads[other]['unread'] += 1
        return jsonify(list(threads.values())), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────

@app.route('/notifications/<int:user_id>', methods=['GET'])
def get_notifications(user_id):
    try:
        items = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
        return jsonify([{
            'id': n.id, 'title': n.title, 'body': n.body, 'icon': n.icon,
            'is_read': bool(n.is_read),
            'created_at': n.created_at.strftime('%d %b %Y %I:%M %p')
        } for n in items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/notifications/<int:notif_id>/read', methods=['PUT'])
def mark_notification_read(notif_id):
    try:
        n = Notification.query.get(notif_id)
        if not n:
            return jsonify({'error': 'Notification not found'}), 404
        n.is_read = True
        db.session.commit()
        return jsonify({'message': 'Marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# WALLET
# ─────────────────────────────────────────

@app.route('/wallet/<int:user_id>', methods=['GET'])
def get_wallet(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        txns = WalletTransaction.query.filter_by(user_id=user_id).order_by(WalletTransaction.created_at.desc()).all()
        return jsonify({
            'balance': float(user.wallet_balance or 0),
            'transactions': [{
                'id': t.id, 'title': t.title, 'amount': float(t.amount), 'type': t.type,
                'created_at': t.created_at.strftime('%d %b %Y')
            } for t in txns]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/wallet/<int:user_id>/recharge', methods=['POST'])
def recharge_wallet(user_id):
    try:
        data   = request.get_json()
        amount = float((data or {}).get('amount', 0))
        if amount <= 0:
            return jsonify({'error': 'amount must be greater than 0'}), 400
        if not User.query.get(user_id):
            return jsonify({'error': 'User not found'}), 404
        credit_wallet(user_id, amount, 'Wallet recharge')
        db.session.commit()
        user = User.query.get(user_id)
        return jsonify({'message': 'Wallet recharged', 'balance': float(user.wallet_balance)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/wallet/<int:user_id>/withdraw', methods=['POST'])
def withdraw_wallet(user_id):
    try:
        data   = request.get_json()
        amount = float((data or {}).get('amount', 0))
        user   = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if amount <= 0:
            return jsonify({'error': 'amount must be greater than 0'}), 400
        if float(user.wallet_balance or 0) < amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        debit_wallet(user_id, amount, 'Withdrawal')
        db.session.commit()
        return jsonify({'message': 'Withdrawal requested', 'balance': float(user.wallet_balance)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# DASHBOARDS
# ─────────────────────────────────────────

@app.route('/farmer/dashboard/<int:user_id>', methods=['GET'])
def farmer_dashboard(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        recommended = Equipment.query.filter_by(available=True).order_by(Equipment.created_at.desc()).limit(8).all()
        recent      = Booking.query.filter_by(farmer_id=user_id).order_by(Booking.created_at.desc()).limit(5).all()
        return jsonify({
            'name': user.name,
            'recommended': [equipment_json(e) for e in recommended],
            'recent_bookings': [booking_json(b) for b in recent],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/owner/dashboard/<int:owner_id>', methods=['GET'])
def owner_dashboard(owner_id):
    try:
        user = User.query.get(owner_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        equipment_count = Equipment.query.filter_by(owner_id=owner_id).count()
        active_bookings = Booking.query.filter_by(owner_id=owner_id, status='approved').count()
        completed       = Booking.query.filter_by(owner_id=owner_id, status='completed').all()
        total_earnings  = sum(float(b.total_amount) for b in completed)
        now = datetime.utcnow()
        month_earnings  = sum(float(b.total_amount) for b in completed
                              if b.created_at.year == now.year and b.created_at.month == now.month)
        revenue = {}
        for b in completed:
            key = b.created_at.strftime('%b')
            revenue[key] = revenue.get(key, 0) + float(b.total_amount)
        recent_requests = Booking.query.filter_by(owner_id=owner_id).order_by(Booking.created_at.desc()).limit(5).all()
        return jsonify({
            'name': user.name, 'equipment_listed': equipment_count,
            'active_bookings': active_bookings,
            'total_earnings': round(total_earnings, 2),
            'month_earnings': round(month_earnings, 2),
            'wallet_balance': float(user.wallet_balance or 0),
            'monthly_revenue': revenue,
            'recent_requests': [booking_json(b) for b in recent_requests],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/owner/earnings/<int:owner_id>', methods=['GET'])
def owner_earnings(owner_id):
    try:
        user = User.query.get(owner_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        completed      = Booking.query.filter_by(owner_id=owner_id, status='completed').all()
        total_earnings = sum(float(b.total_amount) for b in completed)
        now = datetime.utcnow()
        month_earnings = sum(float(b.total_amount) for b in completed
                             if b.created_at.year == now.year and b.created_at.month == now.month)
        transactions = []
        for b in completed:
            e      = Equipment.query.get(b.equipment_id)
            farmer = User.query.get(b.farmer_id)
            transactions.append({
                'title': e.name if e else 'Rental',
                'farmer': farmer.name if farmer else 'Farmer',
                'amount': float(b.total_amount),
                'date': b.created_at.strftime('%d %b'),
            })
        return jsonify({
            'total_earnings': round(total_earnings, 2),
            'month_earnings': round(month_earnings, 2),
            'available': float(user.wallet_balance or 0),
            'transactions': transactions,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'AgriRentX API is running'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
