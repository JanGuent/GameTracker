from flask import Flask, render_template, request, redirect, url_for
from models import db, User, Game
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

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
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        user = User(name=name)
        db.session.add(user)
        db.session.commit()
        return render_template('add_user.html', message="User added successfully!")
    return render_template('add_user.html')

@app.route('/add_game', methods=['GET', 'POST'])
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


if __name__ == '__main__':
    app.run(debug=True)
