import mysql.connector
from flask import Flask, request, jsonify
from pymysql import connect



def get_db_connection():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="root",
        database="L1DB"
    )
    return conn

app = Flask(__name__)


#variables
#users = {}
# games = {}
#next_user_id = 1
#next_game_id = 1


# users endpoints
#create a new user
# make documentation for swagger
#basic validation
#save the user in our fake database
#add links to help the client know where to go next
# POST http://localhost:5000/users
# HATEOAS?
#update endpoints to connect to database
#replace next_user_id with  id from database
@app.route("/users", methods=["POST"])
def create_user():
    data = request.json

    try:
        name = data["name"]
        email = data["email"]
        password = data["password"]
        address = data["address"]
    except KeyError:
        return jsonify({"error": "missing required field"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, address) VALUES (%s, %s, %s, %s)",
            (name, email, password, address)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except mysql.connector.IntegrityError:
        return jsonify({"error": "email already exists"}), 400

    user = {
        "id": user_id,
        "name": name,
        "email": email,
        "password": password,
        "address": address,

        "links": 
            [
            {"method": "GET", "user_details": f"/users/{user_id}",},
            {"method": "PATCH", "update": f"/users/{user_id}"},
            {"method": "DELETE", "delete": f"/users/{user_id}" },
            ]
    }
    
    conn.close()
    return jsonify(user), 201


# get all users
# GET http://localhost:5000/users
# build hateoes cause db cant see them>?
@app.route("/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    result = []
    for user in users:
        result.append({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "address": user["address"],
            "links": [
                {"method": "GET", "user_details": f"/users/{user['id']}"},
                {"method": "PATCH", "update": f"/users/{user['id']}"},
                {"method": "DELETE", "delete": f"/users/{user['id']}"}
            ]
        })
    return jsonify(result), 200

#get users by id
# GET http://localhost:5000/users/1
@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "password": user["password"],
        "address": user["address"],
        "links": [
            {"method": "GET", "self": f"/users/{user['id']}"},
            {"method": "PATCH", "update": f"/users/{user['id']}"},
            {"method": "DELETE", "delete": f"/users/{user['id']}"}
        ]}), 200


# partially update user
# only let name and address be updated
# PATCH http://localhost:5000/users/1
@app.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    data = request.json

    fields = []
    values = []

    if "name" in data:
        fields.append("name = %s")
        values.append(data["name"])

    if "address" in data:
        fields.append("address = %s")
        values.append(data["address"])

    if not fields:
        return jsonify({"error": "no valid fields to update"}), 400

    values.append(user_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE id = %s",
        tuple(values)
    )

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "user updated"}), 200

# delete user
# DELETE http://localhost:5000/users/1
@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.commit()
    conn.close()
    return jsonify({"message": "deleted"}), 200


#======================================================
# GAME 
#game nendpots 
# create a game
#add hatoeas links?
# POST http://localhost:5000/games
# check owner exists
@app.route("/games", methods=["POST"])
def add_game():
    data = request.json

    try:
        name = data["name"]
        publisher = data["publisher"]
        year = data["year"]
        system = data["system"]
        condition = data["condition"]
        ownerId = data["ownerId"]
    except KeyError:
        return jsonify({"error": "missing required field"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE id = %s", (ownerId,))
    owner = cursor.fetchone()
    if not owner:
        conn.close()
        return jsonify({"error": "ownerId does not exist"}), 400

    cursor.execute(
    """
    INSERT INTO games (name, publisher, year, `system`, `condition`, ownerId)
    VALUES (%s, %s, %s, %s, %s, %s)
    """,
    (name, publisher, year, system, condition, ownerId)
    )

    conn.commit()
    game_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "id": game_id,
        "name": name,
        "publisher": publisher,
        "year": year,
        "system": system,
        "condition": condition,
        "ownerId": ownerId,
        "links": [
            {"method": "GET", "self": f"/games/{game_id}"},
            {"method": "PATCH", "update": f"/games/{game_id}"},
            {"method": "DELETE", "delete": f"/games/{game_id}"},
            {"method": "GET", "owner": f"/users/{ownerId}"}
        ]
    }), 201

# search games
# GET http://localhost:5000/games
@app.route("/games", methods=["GET"])
def get_games():

    name = request.args.get("name", "")
    publisher = request.args.get("publisher", "")
    system = request.args.get("system", "")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
    """
    SELECT * FROM games
    WHERE name LIKE %s
    AND publisher LIKE %s
    AND `system` LIKE %s
    """,
    (f"%{name}%", f"%{publisher}%", f"%{system}%")
    )


    rows = cursor.fetchall()
    conn.close()

    result = []
    for g in rows:
        result.append({
            "id": g["id"],
            "name": g["name"],
            "publisher": g["publisher"],
            "year": g["year"],
            "system": g["system"],
            "condition": g["condition"],
            "ownerId": g["ownerId"],
            "links": [
                {"method": "GET", "self": f"/games/{g['id']}"},
                {"method": "GET", "owner": f"/users/{g['ownerId']}"}
            ]
        })

    return jsonify(result), 200

#search games by id
# GET http://localhost:5000/games/1
@app.route("/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM games WHERE id = %s", (game_id,))
    game = cursor.fetchone()
    conn.close()

    if not game:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": game["id"],
        "name": game["name"],
        "publisher": game["publisher"],
        "year": game["year"],
        "system": game["system"],
        "condition": game["condition"],
        "ownerId": game["ownerId"],
        "links": [
            {"method": "GET", "self": f"/games/{game['id']}"},
            {"method": "PATCH", "update": f"/games/{game['id']}"},
            {"method": "DELETE", "delete": f"/games/{game['id']}"},
            {"method": "GET", "owner": f"/users/{game['ownerId']}"}
        ]
    }), 200


# partially update game
# PATCH http://localhost:5000/games/1
@app.route("/games/<int:game_id>", methods=["PATCH"])
def update_game(game_id):

    data = request.json
    fields = []
    values = []

    for field in ["name", "publisher", "year", "system", "condition"]:
        if field in data:
            fields.append(f"{field} = %s")
            values.append(data[field])

    if not fields:
        return jsonify({"error": "no valid fields"}), 400

    values.append(game_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE games SET {', '.join(fields)} WHERE id = %s",
        tuple(values)
    )

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "game updated"}), 200

# delete game
# DELETE http://localhost:5000/games/1
# check game exists
# delete game
@app.route("/games/<int:game_id>", methods=["DELETE"])
def delete_game(game_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("SELECT id FROM games WHERE id = %s", (game_id,))
    game = cursor.fetchone()

    if not game:
        conn.close()
        return jsonify({"error": "game not found"}), 404

    
    cursor.execute("DELETE FROM games WHERE id = %s", (game_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "game deleted",
        "links": [
            {"method": "POST", "create": "/games"},
            {"method": "GET", "all_games": "/games"}
        ]
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)