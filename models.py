from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    games = db.relationship('Game', backref='user', lazy=True)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    players = db.Column(db.String(255), nullable=False)  # Store players as a comma-separated string
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
