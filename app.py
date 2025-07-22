from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
from dotenv import load_dotenv
import os
from datetime import datetime
import time

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

    # Récupérer seulement les capteurs utiles (exclure test_config)
    cursor.execute("""
        SELECT *, 
               FROM_UNIXTIME(timestamp_unix) as date_formatted,
               timestamp_unix
        FROM capteurs 
        WHERE type IN ('temperature', 'bouton_poussoir', 'capteur_texte') 
        ORDER BY timestamp_unix DESC LIMIT 20
    """)
    capteurs = cursor.fetchall()

    # Ajouter une valeur affichable qui combine valeur numérique et texte
    for capteur in capteurs:
        if capteur["valeur_texte"]:
            capteur["valeur_affichee"] = capteur["valeur_texte"]
        elif capteur["type"] == "bouton_poussoir":
            # Affichage optimisé pour les boutons poussoirs
            capteur["valeur_affichee"] = (
                "Appuyé" if capteur["valeur"] == 1 else "Relâché"
            )
        else:
            capteur["valeur_affichee"] = capteur["valeur"]

        # Utiliser la date formatée pour l'affichage
        capteur["date"] = capteur["date_formatted"]

    cursor.close()
    conn.close()
    return render_template("index.html", capteurs=capteurs)


@app.route("/commande", methods=["POST"])
def commande():
    action = request.form["commande"]
    current_timestamp = int(time.time())

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO instructions (commande, timestamp_unix) VALUES (%s, %s)",
        (action, current_timestamp),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/")


@app.route("/couleur", methods=["POST"])
def couleur():
    """Route pour envoyer une couleur vers l'Arduino via AWS IoT Core"""
    couleur_hex = request.form.get("couleur")

    if not couleur_hex:
        return "Erreur: couleur requise", 400

    # Convertir hex en RGB
    hex_color = couleur_hex.lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Format optimisé pour Arduino/Raspberry
    commande_couleur = f"SET_COLOR:{rgb[0]},{rgb[1]},{rgb[2]}"
    current_timestamp = int(time.time())

    try:
        # Sauvegarder en base de données comme avant
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO instructions (commande, type, status, timestamp_unix) VALUES (%s, %s, %s, %s)",
            (commande_couleur, "COLOR", "PENDING", current_timestamp),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # 🚀 NOUVEAU: Publier via AWS IoT Core
        from aws_iot_service import aws_iot_service

        if aws_iot_service.connected:
            success = aws_iot_service.publish_led_command(list(rgb))
            if success:
                print(f"✓ Commande LED envoyée via AWS IoT: RGB{rgb}")
            else:
                print(f"✗ Échec envoi AWS IoT, commande en base uniquement")
        else:
            print("⚠️  AWS IoT non connecté, commande sauvée en base uniquement")

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
            "SELECT * FROM instructions WHERE status = 'PENDING' ORDER BY timestamp_unix ASC"
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
        current_timestamp = int(time.time())

        # Essayer de convertir en nombre, sinon traiter comme texte
        try:
            valeur_num = float(valeur)
            cursor.execute(
                "INSERT INTO capteurs (type, valeur, timestamp_unix) VALUES (%s, %s, %s)",
                (type_capteur, valeur_num, current_timestamp),
            )
        except ValueError:
            # Si c'est un bouton poussoir, traiter comme booléen strict
            if type_capteur == "bouton_poussoir":
                if valeur.lower() == "true":
                    valeur_bool = 1
                elif valeur.lower() == "false":
                    valeur_bool = 0
                else:
                    return "Erreur: bouton_poussoir doit être 'true' ou 'false'", 400

                cursor.execute(
                    "INSERT INTO capteurs (type, valeur, timestamp_unix) VALUES (%s, %s, %s)",
                    (type_capteur, valeur_bool, current_timestamp),
                )
            else:
                # Sinon c'est du texte
                cursor.execute(
                    "INSERT INTO capteurs (type, valeur, valeur_texte, timestamp_unix) VALUES (%s, %s, %s, %s)",
                    (type_capteur, 0, valeur, current_timestamp),
                )

        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/")
    except Exception as e:
        return f"Erreur lors de l'insertion: {e}", 500


@app.route("/api/led", methods=["POST"])
def api_led():
    """API REST optimisée pour contrôler la LED via AWS IoT Core"""
    data = request.get_json()

    if not data or "rgb" not in data:
        return jsonify({"error": "Fournir 'rgb': [r,g,b]"}), 400

    rgb = data["rgb"]
    if not isinstance(rgb, list) or len(rgb) != 3:
        return jsonify({"error": "RGB doit être [R,G,B] avec 3 valeurs"}), 400

    # Valider les valeurs RGB (0-255)
    if not all(isinstance(val, int) and 0 <= val <= 255 for val in rgb):
        return jsonify({"error": "Valeurs RGB: entiers entre 0 et 255"}), 400

    # Format optimisé cohérent avec /couleur
    commande = f"SET_COLOR:{rgb[0]},{rgb[1]},{rgb[2]}"

    try:
        # Sauvegarder en base de données
        conn = get_db_connection()
        cursor = conn.cursor()
        current_timestamp = int(time.time())

        cursor.execute(
            "INSERT INTO instructions (commande, type, status, timestamp_unix) VALUES (%s, %s, %s, %s)",
            (commande, "COLOR", "PENDING", current_timestamp),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # 🚀 NOUVEAU: Publier via AWS IoT Core
        from aws_iot_service import aws_iot_service

        iot_success = False
        if aws_iot_service.connected:
            iot_success = aws_iot_service.publish_led_command(rgb)

        response_data = {
            "success": True,
            "message": "Commande LED envoyée",
            "rgb": rgb,
            "aws_iot_sent": iot_success,
            "database_saved": True,
        }

        return jsonify(response_data), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/capteur", methods=["POST"])
def api_capteur():
    """API REST pour que vos dispositifs IoT envoient des données"""
    data = request.get_json()

    if not data or "type" not in data or "valeur" not in data:
        return jsonify({"error": "type et valeur requis"}), 400

    try:
        # Sauvegarder en base de données comme avant
        conn = get_db_connection()
        cursor = conn.cursor()
        current_timestamp = int(time.time())

        # Essayer de convertir en nombre, sinon traiter comme texte
        try:
            valeur_num = float(data["valeur"])
            cursor.execute(
                "INSERT INTO capteurs (type, valeur, timestamp_unix) VALUES (%s, %s, %s)",
                (data["type"], valeur_num, current_timestamp),
            )
        except (ValueError, TypeError):
            # Si c'est un bouton poussoir, traiter comme booléen strict
            if data["type"] == "bouton_poussoir":
                valeur_str = str(data["valeur"]).lower()
                if valeur_str == "true":
                    valeur_bool = 1
                elif valeur_str == "false":
                    valeur_bool = 0
                else:
                    return jsonify(
                        {"error": "bouton_poussoir doit être 'true' ou 'false'"}
                    ), 400

                cursor.execute(
                    "INSERT INTO capteurs (type, valeur, timestamp_unix) VALUES (%s, %s, %s)",
                    (data["type"], valeur_bool, current_timestamp),
                )
            else:
                # Sinon c'est du texte
                cursor.execute(
                    "INSERT INTO capteurs (type, valeur, valeur_texte, timestamp_unix) VALUES (%s, %s, %s, %s)",
                    (data["type"], 0, str(data["valeur"]), current_timestamp),
                )

        conn.commit()
        cursor.close()
        conn.close()

        # 🚀 NOUVEAU: Publier les données capteur via AWS IoT Core
        from aws_iot_service import aws_iot_service

        iot_success = False
        if aws_iot_service.connected:
            iot_success = aws_iot_service.publish_sensor_data(
                sensor_type=data["type"],
                value=data["valeur"],
                timestamp=current_timestamp,
            )

        response_data = {
            "success": True,
            "message": "Données ajoutées",
            "aws_iot_sent": iot_success,
            "database_saved": True,
        }

        return jsonify(response_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/aws-iot/status", methods=["GET"])
def aws_iot_status():
    """API pour vérifier le statut de la connexion AWS IoT Core"""
    from aws_iot_service import aws_iot_service

    status = {
        "connected": aws_iot_service.connected,
        "client_id": aws_iot_service.client_id,
        "endpoint": aws_iot_service.endpoint,
        "region": aws_iot_service.region,
    }

    return jsonify(status), 200


@app.route("/api/aws-iot/send-command", methods=["POST"])
def aws_iot_send_command():
    """API pour envoyer des commandes génériques via AWS IoT Core"""
    data = request.get_json()

    if not data or "device_type" not in data or "command" not in data:
        return jsonify({"error": "device_type et command requis"}), 400

    from aws_iot_service import aws_iot_service

    if not aws_iot_service.connected:
        return jsonify({"error": "AWS IoT Core non connecté"}), 503

    success = aws_iot_service.publish_device_command(
        device_type=data["device_type"],
        command=data["command"],
        parameters=data.get("parameters", {}),
    )

    if success:
        return jsonify(
            {"success": True, "message": "Commande envoyée via AWS IoT"}
        ), 200
    else:
        return jsonify({"error": "Échec envoi commande AWS IoT"}), 500


if __name__ == "__main__":
    # Configuration pour production/développement
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
