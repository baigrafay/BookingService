from flask import Flask, request, jsonify
import uuid
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  

# Mock data storage for users, hotels, rooms, and bookings
users = {"user1": "password123"}  
hotels = {
    "hotel1": {
        "name": "Hotel Cheval",
        "location": "Malaysia",
        "facilities": ["Free Wi-Fi", "Swimming Pool", "Gym"]
    },
    "hotel2": {
        "name": "Mountain Retreat",
        "location": "Malaysia",
        "facilities": ["Mountain View", "Spa", "Restaurant"]
    }
}
rooms = {
    "hotel1": [
        {"room_id": "room1", "type": "Single", "availability": 5, "price": 10000},
        {"room_id": "room2", "type": "Double", "availability": 3, "price": 15000}
    ],
    "hotel2": [
        {"room_id": "room1", "type": "Suite", "availability": 2, "price": 20000},
        {"room_id": "room2", "type": "Single", "availability": 4, "price": 12500}
    ]
}
bookings = {}

# Helper function to create a JWT token
def create_token(username):
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=1)  
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")

# Middleware for token verification
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401
        return f(*args, **kwargs)
    return wrapper

# Root route
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Hotel Booking Web Service "}), 200

# Login route to get a token
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

   
    if username in users and users[username] == password:
        token = create_token(username)
        return jsonify({"token": token}), 200

    return jsonify({"error": "Invalid credentials"}), 401

# Protected route to list all available hotels
@app.route('/hotels', methods=['GET'])
@token_required
def list_hotels():
    return jsonify(hotels), 200

# Protected route to get detailed information about a specific hotel
@app.route('/hotels/<hotel_id>', methods=['GET'])
@token_required
def hotel_details(hotel_id):
    hotel = hotels.get(hotel_id)
    if not hotel:
        return jsonify({"error": "Hotel not found"}), 404
    return jsonify(hotel), 200

# Protected route to check room availability for a specific hotel
@app.route('/hotels/<hotel_id>/rooms', methods=['GET'])
@token_required
def check_room_availability(hotel_id):
    hotel_rooms = rooms.get(hotel_id)
    if not hotel_rooms:
        return jsonify({"error": "Hotel not found"}), 404
    return jsonify(hotel_rooms), 200

# Protected route to book a room at a specific hotel
@app.route('/book-room', methods=['POST'])
@token_required
def book_room():
    data = request.json
    hotel_id = data.get("hotel_id")
    room_id = data.get("room_id")
    num_rooms = data.get("num_rooms")

    if not hotel_id or not room_id or not num_rooms:
        return jsonify({"error": "Hotel ID, Room ID, and Number of Rooms are required"}), 400

    hotel_rooms = rooms.get(hotel_id)
    if not hotel_rooms:
        return jsonify({"error": "Hotel not found"}), 404

    room = next((r for r in hotel_rooms if r["room_id"] == room_id), None)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    if room["availability"] < num_rooms:
        return jsonify({"error": "Not enough rooms available"}), 400

    booking_id = str(uuid.uuid4())
    booking = {
        "booking_id": booking_id,
        "hotel_id": hotel_id,
        "room_id": room_id,
        "num_rooms": num_rooms,
        "total_price": room["price"] * num_rooms,
        "status": "booked",
        "created_at": datetime.utcnow().isoformat()
    }

    bookings[booking_id] = booking
    room["availability"] -= num_rooms  # Decrease room availability
    return jsonify({"message": "Room booked", "booking_id": booking_id, "total_price": booking["total_price"]}), 200

# Protected route to check the status of a booking
@app.route('/booking-status/<booking_id>', methods=['GET'])
@token_required
def booking_status(booking_id):
    booking = bookings.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    return jsonify(booking), 200

# Protected route to process payment for a booking
@app.route('/make-payment', methods=['POST'])
@token_required
def make_payment():
    data = request.json
    booking_id = data.get("booking_id")
    
    if not booking_id:
        return jsonify({"error": "Booking ID is required"}), 400

    booking = bookings.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    
    booking["status"] = "paid"
    return jsonify({"message": "Payment successful", "booking_id": booking_id, "status": booking["status"]}), 200

# Protected route to cancel a booking
@app.route('/cancel-booking', methods=['POST'])
@token_required
def cancel_booking():
    data = request.json
    booking_id = data.get("booking_id")
    
    if not booking_id:
        return jsonify({"error": "Booking ID is required"}), 400

    booking = bookings.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

 
    hotel_id = booking["hotel_id"]
    room_id = booking["room_id"]
    num_rooms = booking["num_rooms"]

    room = next(r for r in rooms[hotel_id] if r["room_id"] == room_id)
    room["availability"] += num_rooms

    booking["status"] = "canceled"
    return jsonify({"message": "Booking canceled", "booking_id": booking_id, "status": booking["status"]}), 200

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)

