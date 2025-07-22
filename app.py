from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
from dotenv import load_dotenv
import os
from datetime import datetime

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


@app.route("/couleur", methods=["POST"])
def couleur():
    """Route pour envoyer une couleur vers l'Arduino"""
    couleur_hex = request.form.get("couleur")

    if not couleur_hex:
        return "Erreur: couleur requise", 400

    # Convertir hex en RGB
    hex_color = couleur_hex.lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Formater la commande pour l'Arduino
    commande_couleur = f"SET_COLOR:{rgb[0]},{rgb[1]},{rgb[2]}"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO instructions (commande, type, status) VALUES (%s, %s, %s)",
            (commande_couleur, "COLOR", "PENDING"),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/")
    except Exception as e:
        return f"Erreur lors de l'envoi de la couleur: {e}", 500


@app.route("/api/instructions", methods=["GET"])
def api_get_instructions():
    """API pour que l'Arduino récupère les instructions en attente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM instructions WHERE status = 'PENDING' ORDER BY date ASC"
        )
        instructions = cursor.fetchall()

        # Marquer les instructions comme envoyées
        if instructions:
            instruction_ids = [str(instr["id"]) for instr in instructions]
            cursor.execute(
                f"UPDATE instructions SET status = 'SENT' WHERE id IN ({','.join(instruction_ids)})"
            )
            conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"instructions": instructions}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ajouter_capteur", methods=["POST"])
def ajouter_capteur():
    """Route pour ajouter des données de capteur"""
    type_capteur = request.form.get("type")
    valeur = request.form.get("valeur")

    if not type_capteur or not valeur:
        return "Erreur: type et valeur requis", 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO capteurs (type, valeur, date) VALUES (%s, %s, %s)",
            (type_capteur, float(valeur), datetime.now()),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/")
    except Exception as e:
        return f"Erreur lors de l'insertion: {e}", 500


@app.route("/api/capteur", methods=["POST"])
def api_capteur():
    """API REST pour que vos dispositifs IoT envoient des données"""
    data = request.get_json()

    if not data or "type" not in data or "valeur" not in data:
        return jsonify({"error": "type et valeur requis"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO capteurs (type, valeur, date) VALUES (%s, %s, %s)",
            (data["type"], float(data["valeur"]), datetime.now()),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Données ajoutées"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Configuration pour production/développement
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
