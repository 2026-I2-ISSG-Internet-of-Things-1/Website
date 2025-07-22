"""
Script Python pour Raspberry Pi - Envoi de données IoT
Envoi direct vers base de données locale
"""

import mysql.connector
import time
import os
import requests
from dotenv import load_dotenv

# Essayer d'importer le contrôleur Arduino
try:
    from arduino_controller import ArduinoController

    ARDUINO_AVAILABLE = True
except ImportError:
    print("⚠️ Module arduino_controller non disponible - mode simulation")
    ARDUINO_AVAILABLE = False

# Charger la configuration
load_dotenv()

# Configuration pour hébergement local avec base de données directe

# Configuration API pour récupérer les instructions
FLASK_API_URL = "http://localhost:5000/api/instructions"

# Configuration base de données directe (plus efficace)
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Initialiser le contrôleur Arduino si disponible
arduino_controller = None
if ARDUINO_AVAILABLE:
    # Adapter le port selon votre système
    # Linux/MacOS: '/dev/ttyACM0' ou '/dev/ttyUSB0'
    # Windows: 'COM3', 'COM4', etc.
    ARDUINO_PORT = os.getenv("ARDUINO_PORT", "COM3")  # Port par défaut
    arduino_controller = ArduinoController(port=ARDUINO_PORT)


def recuperer_instructions():
    """Récupérer les instructions de couleur depuis l'API Flask"""
    try:
        response = requests.get(FLASK_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data.get("instructions", [])
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des instructions: {e}")
    return []


def traiter_instruction_couleur(instruction):
    """Traiter une instruction de couleur pour l'Arduino"""
    commande = instruction.get("commande", "")

    if commande.startswith("SET_COLOR:"):
        # Extraire les valeurs RGB
        rgb_values = commande.split(":")[1]
        r, g, b = map(int, rgb_values.split(","))

        print(f"🎨 Instruction couleur reçue: RGB({r}, {g}, {b})")

        # Ici vous devrez ajouter votre code pour communiquer avec l'Arduino
        # Par exemple via série (Serial) ou I2C
        envoyer_couleur_vers_arduino(r, g, b)

        return True

    return False


def envoyer_couleur_vers_arduino(r, g, b):
    """Envoyer la couleur vers l'Arduino (à adapter selon votre communication)"""
    try:
        if ARDUINO_AVAILABLE and arduino_controller and arduino_controller.is_connected:
            # Utiliser le contrôleur Arduino réel
            success = arduino_controller.send_color(r, g, b)
            if success:
                print(f"📡 Couleur envoyée vers Arduino: R={r}, G={g}, B={b}")
            else:
                print(f"❌ Échec envoi couleur vers Arduino")
        else:
            # Mode simulation
            print(f"📡 [SIMULATION] Couleur vers Arduino: R={r}, G={g}, B={b}")
            # Dans un vrai projet avec Arduino connecté:
            # 1. Décommentez les lignes suivantes
            # 2. Adaptez le port série (COM3, /dev/ttyACM0, etc.)
            # 3. Assurez-vous que Arduino utilise le code fourni

            # import serial
            # arduino = serial.Serial('COM3', 9600)  # Adaptez le port
            # commande = f"COLOR:{r},{g},{b}\n"
            # arduino.write(commande.encode())
            # arduino.close()

    except Exception as e:
        print(f"❌ Erreur envoi vers Arduino: {e}")


def lire_bouton_poussoir():
    """Lire l'état du bouton poussoir depuis l'Arduino"""
    if ARDUINO_AVAILABLE and arduino_controller and arduino_controller.is_connected:
        try:
            sensor_data = arduino_controller.read_sensor_data()
            return bool(sensor_data.get("button", 0))
        except Exception as e:
            print(f"❌ Erreur lecture bouton: {e}")

    # Mode simulation si Arduino non disponible
    import random

    return random.choice([True, False]) if random.random() < 0.1 else False


def lire_capteur_colorimetrie():
    """Lire les données du capteur de colorimétrie depuis l'Arduino"""
    if ARDUINO_AVAILABLE and arduino_controller and arduino_controller.is_connected:
        try:
            sensor_data = arduino_controller.read_sensor_data()
            return {
                "r": int(sensor_data.get("color_r", 0)),
                "g": int(sensor_data.get("color_g", 0)),
                "b": int(sensor_data.get("color_b", 0)),
            }
        except Exception as e:
            print(f"❌ Erreur lecture colorimétrie: {e}")

    # Mode simulation si Arduino non disponible
    import random

    return {
        "r": random.randint(0, 255),
        "g": random.randint(0, 255),
        "b": random.randint(0, 255),
    }


def lire_temperature_arduino():
    """Lire la température depuis l'Arduino"""
    if ARDUINO_AVAILABLE and arduino_controller and arduino_controller.is_connected:
        try:
            sensor_data = arduino_controller.read_sensor_data()
            return float(sensor_data.get("temp", 20.0))
        except Exception as e:
            print(f"❌ Erreur lecture température Arduino: {e}")

    # Mode simulation
    import random

    return round(random.uniform(18.0, 30.0), 1)


def envoyer_donnee_database(type_capteur, valeur):
    """Envoyer directement dans la base de données MariaDB"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = "INSERT INTO capteurs (type, valeur, localisation) VALUES (%s, %s, %s)"
        cursor.execute(query, (type_capteur, float(valeur), "Raspberry_Pi_1"))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Donnée sauvée en DB: {type_capteur} = {valeur}")
        return True

    except Exception as e:
        print(f"❌ Erreur DB: {e}")
        return False


def simuler_capteurs():
    """Lecture des capteurs depuis Arduino et capteurs simulés"""
    import random

    # Température depuis Arduino (ou simulée)
    temp_arduino = lire_temperature_arduino()

    # Exemple de données simulées + données Arduino
    capteurs_data = [
        ("temperature", temp_arduino),  # Depuis Arduino
        ("humidite", round(random.uniform(40.0, 80.0), 1)),  # Simulé
        ("luminosite", round(random.uniform(0, 1000), 0)),  # Simulé
        ("pression", round(random.uniform(980, 1030), 1)),  # Simulé
    ]

    # Ajouter les données du capteur de colorimétrie depuis Arduino
    couleur_detectee = lire_capteur_colorimetrie()
    capteurs_data.append(("colorimetrie_r", couleur_detectee["r"]))
    capteurs_data.append(("colorimetrie_g", couleur_detectee["g"]))
    capteurs_data.append(("colorimetrie_b", couleur_detectee["b"]))

    # Ajouter l'état du bouton poussoir depuis Arduino
    bouton_presse = lire_bouton_poussoir()
    capteurs_data.append(("bouton_poussoir", 1 if bouton_presse else 0))

    return capteurs_data


def main():
    """Boucle principale"""
    print("🚀 Démarrage du client IoT Raspberry Pi")
    print("📡 Envoi direct vers la base de données locale")
    print("🎨 Contrôle de couleur LED activé")

    # Essayer de connecter l'Arduino
    if ARDUINO_AVAILABLE and arduino_controller:
        if arduino_controller.connect():
            print("✅ Arduino connecté et prêt")
        else:
            print("⚠️ Arduino non connecté - mode simulation")

    try:
        while True:
            try:
                # Vérifier les nouvelles instructions de couleur
                instructions = recuperer_instructions()
                for instruction in instructions:
                    if instruction.get("type") == "COLOR":
                        traiter_instruction_couleur(instruction)

                # Lire les capteurs (Arduino + simulés)
                donnees_capteurs = simuler_capteurs()

                # Envoyer chaque donnée vers la base de données
                for type_capteur, valeur in donnees_capteurs:
                    envoyer_donnee_database(type_capteur, valeur)
                    time.sleep(0.5)  # Délai entre les envois

                print("⏰ Prochaine lecture dans 30 secondes...")
                time.sleep(30)  # Attendre 30 secondes avant la prochaine lecture

            except KeyboardInterrupt:
                print("\n🛑 Arrêt du programme")
                break
            except Exception as e:
                print(f"❌ Erreur inattendue: {e}")
                time.sleep(5)

    finally:
        # Fermer la connexion Arduino proprement
        if ARDUINO_AVAILABLE and arduino_controller:
            arduino_controller.disconnect()


if __name__ == "__main__":
    main()
