#!/usr/bin/env python3
"""
Script pour écrire directement dans la base de données MariaDB AWS
Utilisable depuis Raspberry Pi ou tout autre dispositif
"""

import mysql.connector
from dotenv import load_dotenv
import os
from datetime import datetime
import sys

# Charger les variables d'environnement
load_dotenv()


def get_db_connection():
    """Créer une connexion à la base de données"""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    except mysql.connector.Error as e:
        print(f"Erreur de connexion à la base de données: {e}")
        return None


def ajouter_donnee_capteur(type_capteur, valeur):
    """Ajouter une donnée de capteur dans la base"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        query = "INSERT INTO capteurs (type, valeur, date) VALUES (%s, %s, %s)"
        cursor.execute(query, (type_capteur, float(valeur), datetime.now()))
        conn.commit()
        print(f"✅ Données ajoutées: {type_capteur} = {valeur}")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def ajouter_commande(commande):
    """Ajouter une commande dans la base"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        query = "INSERT INTO instructions (commande, date) VALUES (%s, %s)"
        cursor.execute(query, (commande, datetime.now()))
        conn.commit()
        print(f"✅ Commande ajoutée: {commande}")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def lire_dernieres_donnees(limite=10):
    """Lire les dernières données des capteurs"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM capteurs ORDER BY date DESC LIMIT %s"
        cursor.execute(query, (limite,))
        donnees = cursor.fetchall()
        return donnees
    except Exception as e:
        print(f"❌ Erreur lors de la lecture: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def main():
    """Fonction principale pour tester le script"""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python write_to_db.py capteur <type> <valeur>")
        print("  python write_to_db.py commande <instruction>")
        print("  python write_to_db.py lire")
        print("\nExemples:")
        print("  python write_to_db.py capteur temperature 23.5")
        print("  python write_to_db.py capteur humidite 65")
        print("  python write_to_db.py commande LED_ON")
        print("  python write_to_db.py lire")
        return

    action = sys.argv[1].lower()

    if action == "capteur" and len(sys.argv) >= 4:
        type_capteur = sys.argv[2]
        valeur = sys.argv[3]
        ajouter_donnee_capteur(type_capteur, valeur)

    elif action == "commande" and len(sys.argv) >= 3:
        commande = sys.argv[2]
        ajouter_commande(commande)

    elif action == "lire":
        donnees = lire_dernieres_donnees()
        print("\n📊 Dernières données des capteurs:")
        for donnee in donnees:
            print(f"  {donnee['type']}: {donnee['valeur']} ({donnee['date']})")
    else:
        print("❌ Arguments invalides")


if __name__ == "__main__":
    main()
