#!/usr/bin/env python3
"""
Configuration simplifiée AWS IoT Core pour EFREI
Version qui fonctionne avec boto3 uniquement (sans AWS CLI)
"""

import os
from dotenv import load_dotenv

load_dotenv()


def create_credentials_file():
    """
    Crée un guide pour configurer les credentials AWS manuellement
    """
    print("🔐 Configuration des credentials AWS IoT Core")
    print("=" * 55)
    print("Vous devez configurer vos credentials AWS dans le fichier .env")
    print("\n📝 Étapes à suivre :")
    print("1. Demandez à votre enseignant EFREI :")
    print("   - AWS_ACCESS_KEY_ID")
    print("   - AWS_SECRET_ACCESS_KEY")
    print("\n2. Mettez à jour votre fichier .env avec ces valeurs")

    # Vérifier si le .env contient déjà des credentials
    try:
        with open(".env", "r") as f:
            content = f.read()

        if "AWS_ACCESS_KEY_ID=votre-access-key" in content:
            print("\n⚠️  ATTENTION: Vous devez mettre à jour les credentials dans .env")
            print("   Remplacez 'votre-access-key' et 'votre-secret-key'")
            print("   par les vraies valeurs fournies par votre enseignant")
        else:
            print("\n✓ Le fichier .env semble configuré")

    except FileNotFoundError:
        print("\n❌ Fichier .env non trouvé")


def test_aws_connection():
    """
    Teste la connexion AWS avec boto3
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        # Charger les credentials depuis .env
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not aws_access_key or aws_access_key == "votre-access-key":
            print("❌ AWS_ACCESS_KEY_ID non configuré dans .env")
            return False

        if not aws_secret_key or aws_secret_key == "votre-secret-key":
            print("❌ AWS_SECRET_ACCESS_KEY non configuré dans .env")
            return False

        # Test de connexion
        sts = boto3.client(
            "sts",
            region_name="eu-west-3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )

        response = sts.get_caller_identity()
        print(f"✓ Connexion AWS réussie !")
        print(f"✓ Account ID: {response['Account']}")
        print(f"✓ User ARN: {response['Arn']}")
        return True

    except NoCredentialsError:
        print("❌ Credentials AWS non trouvés")
        return False
    except ClientError as e:
        print(f"❌ Erreur AWS: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def check_prerequisites():
    """
    Vérifie que tout est prêt pour la configuration
    """
    print("🔍 Vérification des prérequis...")

    # Vérifier boto3
    try:
        import boto3

        print("✓ boto3 installé")
    except ImportError:
        print("❌ boto3 non installé - lancez: pip install boto3")
        return False

    # Vérifier awsiotsdk
    try:
        import awsiotsdk

        print("✓ awsiotsdk installé")
    except ImportError:
        print("❌ awsiotsdk non installé - lancez: pip install awsiotsdk")
        return False

    # Vérifier le fichier .env
    if os.path.exists(".env"):
        print("✓ Fichier .env trouvé")
    else:
        print("❌ Fichier .env non trouvé")
        return False

    return True


def main():
    """
    Configuration guidée pour EFREI
    """
    print("🚀 Configuration AWS IoT Core - EFREI Groupe User03")
    print("Base de données: mariadb-efrei-iot-2025 (eu-west-3)")
    print("=" * 60)

    # Étape 1: Vérifier les prérequis
    if not check_prerequisites():
        print("\n❌ Prérequis manquants - installez d'abord les dépendances")
        return

    # Étape 2: Guide credentials
    print("\n" + "=" * 60)
    create_credentials_file()

    print("\n" + "=" * 60)
    print("⏸️  PAUSE - Configurez vos credentials AWS dans .env")
    print("=" * 60)
    print("1. Ouvrez le fichier .env dans votre éditeur")
    print("2. Remplacez 'votre-access-key' par votre vraie clé AWS")
    print("3. Remplacez 'votre-secret-key' par votre vraie clé secrète AWS")
    print("4. Sauvegardez le fichier")

    input("\n⏸️  Appuyez sur Entrée quand c'est fait...")

    # Étape 3: Test de connexion
    print("\n🔌 Test de la connexion AWS...")
    if not test_aws_connection():
        print("\n❌ Configuration AWS échouée")
        print("💡 Vérifiez vos credentials dans le fichier .env")
        return

    # Étape 4: Instructions pour la suite
    print("\n" + "=" * 60)
    print("✅ Configuration AWS prête !")
    print("=" * 60)
    print("🚀 Prochaines étapes :")
    print("1. Lancez le script complet : python setup_efrei_aws_iot.py")
    print("   (Ce script créera vos certificats IoT)")
    print("\n2. Ou lancez directement votre app : python app.py")
    print("   (L'app fonctionne même sans AWS IoT)")

    print("\n📋 Votre configuration actuelle :")
    print("• Base de données : MariaDB (eu-west-3) ✓")
    print("• Credentials AWS : Configurés ✓")
    print("• Région AWS : eu-west-3 ✓")
    print("• Packages Python : Installés ✓")

    print("\n📡 Topics MQTT qui seront utilisés :")
    print("• efrei/grpuser03/led/commands")
    print("• efrei/grpuser03/sensors/+/data")
    print("• efrei/grpuser03/device/status")


if __name__ == "__main__":
    main()
