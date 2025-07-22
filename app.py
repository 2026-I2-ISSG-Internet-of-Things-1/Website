from flask import Flask, render_template, request, redirect
import mysql.connector
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


@app.route("/")
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM capteurs ORDER BY date DESC LIMIT 10")
    capteurs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", capteurs=capteurs)


@app.route("/commande", methods=["POST"])
def commande():
    action = request.form["commande"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO instructions (commande) VALUES (%s)", (action,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
