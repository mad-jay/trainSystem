from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///train_booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Models
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    no_ic = db.Column(db.String(20), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('train_ticket.id'))
    seat_code = db.Column(db.String(100), nullable=True)  # Store seat codes (comma-separated for multiple seats)


class TrainTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    seats = db.relationship('Seat', backref='train', lazy=True)


class Seat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_code = db.Column(db.String(10), nullable=False)  # Example: TrainName A10
    train_name = db.Column(db.String(100), nullable=False)
    couch = db.Column(db.String(1), nullable=False)  # A, B, C, etc.
    seat_number = db.Column(db.Integer, nullable=False)  # 1-20
    is_booked = db.Column(db.Boolean, default=False)
    train_id = db.Column(db.Integer, db.ForeignKey('train_ticket.id'), nullable=False)
    status = db.Column(db.String(10), default='available')

@app.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    if request.method == 'POST':
        email = request.form['email']
        session['email'] = email

        if email == 'admin@admin':
            return redirect(url_for('admin_page'))
        return redirect(url_for('choose_ticket'))

    return render_template('index.html')

@app.route('/choose-ticket', methods=['GET', 'POST'])
def choose_ticket():
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']
        date = request.form['date']

        tickets = TrainTicket.query.filter_by(origin=origin, destination=destination, date=datetime.strptime(date, '%Y-%m-%d').date()).all()
        return render_template('choose_ticket.html', tickets=tickets)

    return render_template('choose_ticket.html', tickets=None)

@app.route('/choose-seat/<int:ticket_id>', methods=['GET', 'POST'])
def choose_seat(ticket_id):
    train = TrainTicket.query.get_or_404(ticket_id)
    seats = Seat.query.filter_by(train_id=ticket_id).all()

    if request.method == 'POST':
        selected_seats = request.form.getlist('seats')
        session['selected_seats'] = selected_seats
        return redirect(url_for('enter_customer_details', ticket_id=ticket_id))

    return render_template('choose_seat.html', train=train, seats=seats)

@app.route('/enter-customer-details/<int:ticket_id>', methods=['GET', 'POST'])
def enter_customer_details(ticket_id):
    if request.method == 'POST':
        selected_seats = session.get('selected_seats', [])
        name = request.form.get('name')
        no_ic = request.form.get('no_ic')
        email = session.get('email')

        customer = Customer(name=name, email=email, no_ic=no_ic, ticket_id=ticket_id, seat_code=",".join(selected_seats))
        db.session.add(customer)

        # Update seats to booked
        for seat_code in selected_seats:
            seat = Seat.query.filter_by(seat_code=seat_code, train_id=ticket_id).first()
            seat.is_booked = True
        db.session.commit()

        return redirect(url_for('payment', ticket_id=ticket_id))

    selected_seats = session.get('selected_seats', [])
    return render_template('customer_details.html', seats=selected_seats)

@app.route('/payment/<int:ticket_id>', methods=['GET', 'POST'])
def payment(ticket_id):
    selected_seats = session.get('selected_seats', [])
    total_price = len(selected_seats) * 50  # Assuming each ticket costs 50 units

    if request.method == 'POST':
        session.clear()
        # Render a payment success page with a redirect
        return render_template('payment_success.html', message="Payment successful! Thank you for booking.", redirect_url=url_for('index'))

    return render_template('payment.html', total_price=total_price)


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if request.method == 'POST':
        name = request.form['name']
        origin = request.form['origin']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']

        new_train = TrainTicket(name=name, origin=origin, destination=destination, date=datetime.strptime(date, '%Y-%m-%d').date(), time=datetime.strptime(time, '%H:%M').time())
        db.session.add(new_train)
        db.session.commit()

        # Generate seats for the train
        couches = ['A', 'B', 'C', 'D', 'E', 'F']
        for couch in couches:
            for seat_number in range(1, 21):
                seat_code = f"{name} {couch}{seat_number}"
                seat = Seat(seat_code=seat_code, train_name=name, couch=couch, seat_number=seat_number, train_id=new_train.id)
                db.session.add(seat)
        db.session.commit()

        return redirect(url_for('admin_page'))

    trains = TrainTicket.query.all()
    customers = Customer.query.all()
    return render_template('admin.html', trains=trains, customers=customers,)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
