from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
from dotenv import load_dotenv
import os
import requests

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration Raspberry Pi
RASPBERRY_PI_URL = "http://10.0.215.7:5001"  # IP réelle du Raspberry Pi


def send_to_raspberry(data):
    """Envoie des données vers le Raspberry Pi"""
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/api/data", json=data, timeout=5)
        return response.status_code == 200
    except:
        return False


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

    # Récupérer les derniers capteurs depuis MyAsset - approche mixte
    # D'abord les capteurs généraux (température, bouton, lumière) - limité à 5 par type
    cursor.execute("""
        SELECT 
            MyAssetNumber as id,
            MyAssetType as type,
            MyAssetValue as valeur,
            MyAssetComment as valeur_texte,
            UNIX_TIMESTAMP(MyAssetTimeStamp) as timestamp_unix,
            MyAssetTimeStamp as date_formatted,
            MyAssetName as nom,
            MyAssetUnit as unite
        FROM MyAsset 
        WHERE MyAssetType IN ('temperature', 'bouton_poussoir', 'capteur_texte', 'humidity', 'pressure', 'light', 'motion', 'button') 
        ORDER BY MyAssetTimeStamp DESC LIMIT 25
    """)
    capteurs = cursor.fetchall()

    # Puis ajouter spécifiquement les derniers événements joystick - limité à 5
    cursor.execute("""
        SELECT 
            MyAssetNumber as id,
            MyAssetType as type,
            MyAssetValue as valeur,
            MyAssetComment as valeur_texte,
            UNIX_TIMESTAMP(MyAssetTimeStamp) as timestamp_unix,
            MyAssetTimeStamp as date_formatted,
            MyAssetName as nom,
            MyAssetUnit as unite
        FROM MyAsset 
        WHERE MyAssetType = 'joystick'
        ORDER BY MyAssetTimeStamp DESC LIMIT 5
    """)
    joystick_data = cursor.fetchall()

    # Combiner les deux listes
    capteurs.extend(joystick_data)

    # Trier par timestamp pour avoir l'ordre chronologique correct
    capteurs.sort(key=lambda x: x["timestamp_unix"], reverse=True)

    # Limiter chaque type de capteur à 5 entrées maximum
    capteurs_limites = []
    compteurs_types = {}

    for capteur in capteurs:
        type_capteur = capteur["type"]

        # Conversion des types pour compatibilité
        if type_capteur == "button":
            type_capteur = "bouton_poussoir"
            capteur["type"] = "bouton_poussoir"

        # Compter les occurrences de chaque type
        if type_capteur not in compteurs_types:
            compteurs_types[type_capteur] = 0

        # N'ajouter que si on n'a pas encore 5 entrées pour ce type
        if compteurs_types[type_capteur] < 5:
            capteurs_limites.append(capteur)
            compteurs_types[type_capteur] += 1

    # Utiliser la liste limitée
    capteurs = capteurs_limites

    # Ajouter une valeur affichable qui combine valeur numérique et texte (compatibilité)
    for capteur in capteurs:
        if capteur["valeur_texte"] and capteur["unite"] == "text":
            capteur["valeur_affichee"] = capteur["valeur_texte"]
        elif capteur["type"] == "bouton_poussoir":
            # Affichage optimisé pour les boutons poussoirs
            capteur["valeur_affichee"] = (
                "Appuyé" if capteur["valeur"] == 1 else "Relâché"
            )
        elif capteur["type"] == "joystick":
            # Affichage optimisé pour le joystick Sense HAT
            if capteur["valeur_texte"]:
                # Afficher la direction depuis le commentaire
                capteur["valeur_affichee"] = capteur["valeur_texte"]
            else:
                capteur["valeur_affichee"] = (
                    "Actionné" if capteur["valeur"] == 1 else "Inactif"
                )
                print(f"Debug joystick (pas de texte): valeur={capteur['valeur']}")
        else:
            # Pour les autres capteurs, afficher valeur + unité
            capteur["valeur_affichee"] = (
                f"{capteur['valeur']} {capteur.get('unite', '')}"
            )

        # Utiliser la date formatée pour l'affichage
        capteur["date"] = capteur["date_formatted"]

    # Récupérer la dernière couleur définie
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT MyAssetComment 
        FROM MyAsset 
        WHERE MyAssetType = 'color' 
        ORDER BY MyAssetTimeStamp DESC 
        LIMIT 1
    """)
    last_color_result = cursor.fetchone()

    # Convertir SET_COLOR:R,G,B en format hex
    last_color_hex = "#ff0000"  # Couleur par défaut
    if last_color_result and last_color_result["MyAssetComment"]:
        color_command = last_color_result["MyAssetComment"]
        if color_command.startswith("SET_COLOR:"):
            try:
                # Extraire les valeurs RGB
                rgb_str = color_command.replace("SET_COLOR:", "")
                r, g, b = map(int, rgb_str.split(","))
                # Convertir en hex
                last_color_hex = f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                pass  # Garder la couleur par défaut en cas d'erreur

    cursor.close()
    conn.close()
    return render_template("index.html", capteurs=capteurs, last_color=last_color_hex)


@app.route("/debug/joystick")
def debug_joystick():
    """Route de debug pour voir les données joystick"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM MyAsset 
        WHERE MyAssetType = 'joystick' 
        ORDER BY MyAssetTimeStamp DESC 
        LIMIT 10
    """)
    joystick_data = cursor.fetchall()

    cursor.close()
    conn.close()

    html = "<h1>Debug Joystick Data</h1><ul>"
    for data in joystick_data:
        html += f"<li>{data['MyAssetTimeStamp']}: {data['MyAssetComment']} (Value: {data['MyAssetValue']})</li>"
    html += "</ul>"
    html += f"<p>Total: {len(joystick_data)} entrées trouvées</p>"
    html += '<a href="/">Retour</a>'

    return html


@app.route("/commande", methods=["POST"])
def commande():
    action = request.form["commande"]

    # Ajouter la commande comme un asset de type "instruction"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
           VALUES (%s, %s, %s, %s, %s)""",
        ("instruction", "Commande Web", 1.0, "cmd", action),
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Envoyer aussi vers le Raspberry Pi
    raspberry_data = {
        "type": "command",
        "name": "Web Command",
        "value": 1.0,
        "unit": "cmd",
        "comment": action,
    }
    send_to_raspberry(raspberry_data)

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

    # Format optimisé pour Arduino/Raspberry
    commande_couleur = f"SET_COLOR:{rgb[0]},{rgb[1]},{rgb[2]}"

    try:
        # Sauvegarder en base de données MyAsset
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
               VALUES (%s, %s, %s, %s, %s)""",
            ("color", "LED Color", 1.0, "rgb", commande_couleur),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Envoyer aussi vers le Raspberry Pi
        raspberry_data = {
            "type": "command",
            "name": "LED RGB",
            "value": 1.0,
            "unit": "rgb",
            "comment": commande_couleur,
        }
        send_to_raspberry(raspberry_data)

        print(f"✓ Commande LED sauvegardée et envoyée: RGB{rgb}")
        return redirect("/")
    except Exception as e:
        return f"Erreur lors de l'envoi de la couleur: {e}", 500


@app.route("/api/instructions", methods=["GET"])
def api_get_instructions():
    """API pour que l'Arduino récupère les instructions en attente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Récupérer les instructions depuis MyAsset
        cursor.execute("""
            SELECT 
                MyAssetNumber as id,
                MyAssetComment as commande,
                MyAssetType as type,
                'PENDING' as status,
                UNIX_TIMESTAMP(MyAssetTimeStamp) as timestamp_unix
            FROM MyAsset 
            WHERE MyAssetType IN ('instruction', 'color') 
            AND MyAssetTimeStamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY MyAssetTimeStamp ASC
        """)
        instructions = cursor.fetchall()

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

        # Essayer de convertir en nombre, sinon traiter comme texte
        try:
            valeur_num = float(valeur)
            # Déterminer l'unité selon le type
            unite_map = {
                "temperature": "°C",
                "humidity": "%",
                "pressure": "hPa",
                "light": "lux",
                "bouton_poussoir": "bool",
                "button": "bool",
            }
            unite = unite_map.get(type_capteur, "")

            cursor.execute(
                """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    type_capteur,
                    f"Capteur {type_capteur}",
                    valeur_num,
                    unite,
                    "Ajouté via formulaire",
                ),
            )
        except ValueError:
            # Si c'est un bouton poussoir, traiter comme booléen strict
            if type_capteur in ["bouton_poussoir", "button"]:
                if valeur.lower() == "true":
                    valeur_bool = 1
                elif valeur.lower() == "false":
                    valeur_bool = 0
                else:
                    return "Erreur: bouton_poussoir doit être 'true' ou 'false'", 400

                cursor.execute(
                    """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        type_capteur,
                        f"Bouton {type_capteur}",
                        valeur_bool,
                        "bool",
                        "Ajouté via formulaire",
                    ),
                )
            else:
                # Sinon c'est du texte
                cursor.execute(
                    """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (type_capteur, f"Capteur {type_capteur}", 0.0, "text", valeur),
                )

        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/")
    except Exception as e:
        return f"Erreur lors de l'insertion: {e}", 500


@app.route("/api/led", methods=["POST"])
def api_led():
    """API REST optimisée pour contrôler la LED"""
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
        # Sauvegarder en base de données MyAsset
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
               VALUES (%s, %s, %s, %s, %s)""",
            ("color", "LED API", 1.0, "rgb", commande),
        )
        conn.commit()
        cursor.close()
        conn.close()

        response_data = {
            "success": True,
            "message": "Commande LED envoyée",
            "rgb": rgb,
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
        # Sauvegarder en base de données MyAsset
        conn = get_db_connection()
        cursor = conn.cursor()

        # Essayer de convertir en nombre, sinon traiter comme texte
        try:
            valeur_num = float(data["valeur"])
            # Déterminer l'unité selon le type
            unite_map = {
                "temperature": "°C",
                "humidity": "%",
                "pressure": "hPa",
                "light": "lux",
                "bouton_poussoir": "bool",
                "button": "bool",
            }
            unite = unite_map.get(data["type"], "")

            cursor.execute(
                """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    data["type"],
                    f"API {data['type']}",
                    valeur_num,
                    unite,
                    "Ajouté via API",
                ),
            )
        except (ValueError, TypeError):
            # Si c'est un bouton poussoir, traiter comme booléen strict
            if data["type"] in ["bouton_poussoir", "button"]:
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
                    """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        data["type"],
                        f"API {data['type']}",
                        valeur_bool,
                        "bool",
                        "Ajouté via API",
                    ),
                )
            else:
                # Sinon c'est du texte
                cursor.execute(
                    """INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        data["type"],
                        f"API {data['type']}",
                        0.0,
                        "text",
                        str(data["valeur"]),
                    ),
                )

        conn.commit()
        cursor.close()
        conn.close()

        response_data = {
            "success": True,
            "message": "Données ajoutées",
            "database_saved": True,
        }

        return jsonify(response_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Configuration pour production/développement
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
