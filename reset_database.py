#!/usr/bin/env python3
"""
Script pour nettoyer complètement la base de données et créer la nouvelle structure MyAsset
"""

import mysql.connector
from dotenv import load_dotenv
import os
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


def reset_database():
    """Nettoyer complètement la base de données et créer la nouvelle structure"""
    conn = get_db_connection()
    if not conn:
        print("Impossible de se connecter à la base de données")
        return False

    try:
        cursor = conn.cursor()

        print("🔄 Suppression de toutes les tables existantes...")

        # Désactiver les vérifications de clés étrangères temporairement
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # Récupérer toutes les tables existantes
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()

        # Supprimer toutes les tables une par une
        for table in tables:
            table_name = table[0]
            print(f"  - Suppression de la table: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")

        # Réactiver les vérifications de clés étrangères
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        print("✅ Toutes les tables ont été supprimées")
        print("")
        print("🏗️  Création de la nouvelle table MyAsset...")

        # Créer la nouvelle table MyAsset avec la structure spécifiée
        create_table_query = """
        CREATE TABLE MyAsset (
            MyAssetNumber INT(11) AUTO_INCREMENT PRIMARY KEY,
            MyAssetType CHAR(12) NOT NULL,
            MyAssetName CHAR(20) NOT NULL,
            MyAssetValue FLOAT NOT NULL,
            MyAssetUnit CHAR(12) NOT NULL,
            MyAssetComment TEXT,
            MyAssetTimeStamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        cursor.execute(create_table_query)
        print("✅ Table MyAsset créée avec succès")
        print("")
        print("📋 Structure de la nouvelle table:")
        print("   - MyAssetNumber: INT(11) AUTO_INCREMENT PRIMARY KEY")
        print("   - MyAssetType: CHAR(12) NOT NULL")
        print("   - MyAssetName: CHAR(20) NOT NULL")
        print("   - MyAssetValue: FLOAT NOT NULL")
        print("   - MyAssetUnit: CHAR(12) NOT NULL")
        print("   - MyAssetComment: TEXT")
        print("   - MyAssetTimeStamp: TIMESTAMP (auto-généré)")
        print("")

        # Ajouter quelques données d'exemple pour tester
        print("📝 Ajout de données d'exemple...")
        sample_data = [
            (
                "temperature",
                "Capteur Temp 1",
                23.5,
                "°C",
                "Capteur de température salon",
            ),
            ("humidity", "Capteur Hum 1", 65.2, "%", "Capteur d'humidité salon"),
            (
                "pressure",
                "Capteur Press 1",
                1013.25,
                "hPa",
                "Capteur de pression atmosphérique",
            ),
            ("light", "Capteur Lum 1", 750.0, "lux", "Capteur de luminosité"),
            ("button", "Bouton 1", 0.0, "bool", "Bouton poussoir principal"),
        ]

        insert_query = """
        INSERT INTO MyAsset (MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.executemany(insert_query, sample_data)
        print(f"✅ {len(sample_data)} entrées d'exemple ajoutées")

        # Valider les changements
        conn.commit()
        print("")
        print("🎉 Base de données réinitialisée avec succès!")
        print("📊 Vous pouvez maintenant utiliser la nouvelle structure MyAsset")

        # Afficher le contenu de la table pour vérification
        print("")
        print("📋 Contenu actuel de la table MyAsset:")
        cursor.execute("SELECT * FROM MyAsset ORDER BY MyAssetNumber;")
        rows = cursor.fetchall()

        print(
            f"{'ID':<4} {'Type':<12} {'Name':<20} {'Value':<8} {'Unit':<12} {'Comment':<30} {'Timestamp'}"
        )
        print("-" * 100)
        for row in rows:
            print(
                f"{row[0]:<4} {row[1]:<12} {row[2]:<20} {row[3]:<8} {row[4]:<12} {row[5] or '':<30} {row[6]}"
            )

        cursor.close()
        conn.close()
        return True

    except mysql.connector.Error as e:
        print(f"❌ Erreur MySQL: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            conn.close()


def main():
    """Fonction principale"""
    print("🚨 ATTENTION: Ce script va SUPPRIMER TOUTES les données de la base!")
    print("📋 Nouvelle structure qui sera créée:")
    print("   Table: MyAsset")
    print(
        "   Colonnes: MyAssetNumber (PK), MyAssetType, MyAssetName, MyAssetValue, MyAssetUnit, MyAssetComment, MyAssetTimeStamp"
    )
    print("")

    # Demander confirmation
    if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
        confirmation = "oui"
    else:
        confirmation = input(
            "Êtes-vous sûr de vouloir continuer? (tapez 'oui' pour confirmer): "
        )

    if confirmation.lower() == "oui":
        print("")
        print("🚀 Démarrage de la réinitialisation de la base de données...")
        print("")
        if reset_database():
            print("")
            print("✅ Réinitialisation terminée avec succès!")
            sys.exit(0)
        else:
            print("")
            print("❌ Échec de la réinitialisation")
            sys.exit(1)
    else:
        print("❌ Opération annulée")
        sys.exit(0)


if __name__ == "__main__":
    main()
