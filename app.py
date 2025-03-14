from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User, Game, Admin
from datetime import datetime
from collections import Counter
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key') 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))  # Use Admin model instead of User model

@login_manager.unauthorized_handler
def unauthorized():
    flash("You need to be logged in to access this page!", "warning")
    return render_template('login.html', message="You need to be logged in to access this page!")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()  # Check admin table

        if admin and admin.check_password(password):  # Check password for admin
            login_user(admin)
            return redirect(url_for('index'))  # Redirect to home page after successful login
        else:
            return 'Invalid credentials'

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
#@login_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/')
def index():
    # Get the ranking of users based on the number of games won
    rankings = db.session.query(User.name, db.func.count(Game.id).label('wins'))\
                         .join(Game, Game.winner_id == User.id)\
                         .group_by(User.id)\
                         .order_by(db.desc('wins')).all()
    
    # Convert the rankings to a serializable format (list of dictionaries)
    rankings_data = [{'name': ranking[0], 'wins': ranking[1]} for ranking in rankings]
    
    return render_template('index.html', rankings=rankings_data)

@app.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        user = User(name=name)
        db.session.add(user)
        db.session.commit()
        return render_template('add_user.html', message="User added successfully!")
    return render_template('add_user.html')


@app.route('/add_game', methods=['GET', 'POST'])
@login_required
def add_game():
    selected_players = []
    winner_id = None
    amount = 1  # Default amount to 1

    if request.method == 'POST':
        # Get participants from the form (from player1 to player5)
        for i in range(1, 6):
            player_id = request.form.get(f'player{i}')
            if player_id:  # Only add non-empty player IDs
                selected_players.append(player_id)

        # Get the winner
        winner_id = request.form['winner']
        game_date = datetime.now()

        # Get the amount (how many times to submit this result)
        amount = int(request.form['amount'])

        # Ensure that at least two players are selected
        if len(selected_players) < 2:
            return render_template('add_game.html', message="Please select at least two players.", users=User.query.all(), selected_players=selected_players, winner_id=winner_id, amount=amount)

        # Ensure the winner is one of the selected players
        if winner_id not in selected_players:
            return render_template('add_game.html', message="The winner must be one of the selected players.", users=User.query.all(), selected_players=selected_players, winner_id=winner_id, amount=amount)

        # Add the game to the database multiple times based on the amount
        for i in range(amount):
            new_game = Game(date=game_date, players=",".join(selected_players), winner_id=winner_id)
            db.session.add(new_game)

        db.session.commit()

        # Stay on the current page after form submission (no redirection)
        return render_template('add_game.html', message=f"{amount} game(s) added successfully!", users=User.query.all(), selected_players=selected_players, winner_id=winner_id, amount=amount)

    users = User.query.all()
    return render_template('add_game.html', users=users, selected_players=selected_players, winner_id=winner_id, amount=amount)

@app.route('/player_stats', methods=['GET', 'POST'])
def player_stats():
    users = User.query.all()
    selected_user = None
    win_percentage = None
    total_games = 0
    games_won = 0

    if request.method == 'POST':
        user_id = request.form.get('user_id')

        if user_id:
            selected_user = User.query.get(user_id)
            total_games = Game.query.filter(Game.players.like(f"%{user_id}%")).count()  # Games where the user participated
            games_won = Game.query.filter_by(winner_id=user_id).count()  # Games won by the user
            win_percentage = (games_won / total_games * 100) if total_games > 0 else 0  # Avoid division by zero

    return render_template('player_stats.html', users=users, selected_user=selected_user, total_games=total_games, games_won=games_won, win_percentage=win_percentage)

@app.route('/matchup_stats', methods=['GET'])
def matchup_stats():
    all_games = Game.query.all()
    user_mapping = {str(user.id): user.name for user in User.query.all()}

    # Extract unique matchups
    unique_matchups = set()
    matchup_data = []

    for game in all_games:
        player_ids = tuple(sorted(game.players.split(",")))  # Sort to avoid duplicates
        unique_matchups.add(player_ids)

    for matchup in unique_matchups:
        relevant_games = [game for game in all_games if set(game.players.split(",")) == set(matchup)]
        total_games = len(relevant_games)
        
        win_counts = Counter()
        for game in relevant_games:
            win_counts[str(game.winner_id)] += 1  # Convert winner_id to string for comparison

        matchup_labels = [user_mapping[player_id] for player_id in matchup]
        win_data = [win_counts[player_id] for player_id in matchup]

        matchup_data.append({
            "players": matchup_labels,
            "total_games": total_games,
            "win_data": win_data
        })

    # Sort matchups by total_games in descending order
    matchup_data.sort(key=lambda x: x['total_games'], reverse=True)

    return render_template('matchup_stats.html', matchup_data=matchup_data)

if __name__ == '__main__':
    app.run()
