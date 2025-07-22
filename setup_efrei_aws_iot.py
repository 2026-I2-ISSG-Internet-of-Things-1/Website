#!/usr/bin/env python3
"""
Configuration AWS IoT Core pour EFREI - Groupe User03
Région: eu-west-3 (pour correspondre à votre base MariaDB)
"""

import boto3
import json
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


def setup_aws_credentials():
    """
    Guide pour configurer les credentials AWS
    """
    print("🔐 Configuration des credentials AWS")
    print("=" * 50)
    print("Vous devez configurer vos credentials AWS. Plusieurs options :")
    print("\n1. Via AWS CLI (recommandé) :")
    print("   aws configure")
    print("   AWS Access Key ID: [Votre clé]")
    print("   AWS Secret Access Key: [Votre secret]")
    print("   Default region: eu-west-3")
    print("   Default output format: json")

    print("\n2. Via variables d'environnement :")
    print("   set AWS_ACCESS_KEY_ID=votre-access-key")
    print("   set AWS_SECRET_ACCESS_KEY=votre-secret-key")
    print("   set AWS_DEFAULT_REGION=eu-west-3")

    print("\n3. Via le fichier .env (déjà créé) :")
    print("   Modifiez AWS_ACCESS_KEY_ID et AWS_SECRET_ACCESS_KEY dans .env")

    print("\n⚠️  Demandez les credentials à votre enseignant EFREI")


def check_aws_connection():
    """
    Vérifie la connexion AWS
    """
    try:
        # Test avec STS pour vérifier les credentials
        sts = boto3.client("sts", region_name="eu-west-3")
        response = sts.get_caller_identity()
        print(f"✓ Connexion AWS réussie - Account: {response['Account']}")
        print(f"✓ User ARN: {response['Arn']}")
        return True
    except Exception as e:
        print(f"✗ Erreur connexion AWS: {e}")
        print("💡 Configurez vos credentials AWS (voir étape précédente)")
        return False


def create_iot_thing_for_efrei():
    """
    Crée une Thing IoT spécifique pour EFREI Groupe User03
    """
    thing_name = "efrei-grpuser03-device"
    region = "eu-west-3"

    try:
        iot_client = boto3.client("iot", region_name=region)

        # Créer la Thing
        response = iot_client.create_thing(
            thingName=thing_name,
            thingTypeName="EFREIDevice",
            attributePayload={
                "attributes": {
                    "group": "GrpUser03",
                    "project": "EFREI_IoT_2025",
                    "location": "EFREI_Lab",
                    "database": "MyDbGrpUser03",
                }
            },
        )

        print(f"✓ Thing '{thing_name}' créée avec succès")
        return thing_name

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"✓ Thing '{thing_name}' existe déjà")
            return thing_name
        else:
            print(f"✗ Erreur création Thing: {e}")
            return None


def create_iot_policy_for_efrei():
    """
    Crée une politique IoT pour EFREI
    """
    policy_name = "EFREI_GrpUser03_Policy"
    region = "eu-west-3"

    try:
        iot_client = boto3.client("iot", region_name=region)

        # Politique sécurisée mais flexible pour l'apprentissage
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["iot:Connect"],
                    "Resource": f"arn:aws:iot:eu-west-3:*:client/efrei-grpuser03-*",
                },
                {
                    "Effect": "Allow",
                    "Action": ["iot:Publish"],
                    "Resource": [
                        f"arn:aws:iot:eu-west-3:*:topic/efrei/grpuser03/*",
                        f"arn:aws:iot:eu-west-3:*:topic/devices/*/commands/status",
                        f"arn:aws:iot:eu-west-3:*:topic/sensors/*/data",
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": ["iot:Subscribe", "iot:Receive"],
                    "Resource": [
                        f"arn:aws:iot:eu-west-3:*:topic/efrei/grpuser03/*",
                        f"arn:aws:iot:eu-west-3:*:topic/devices/*/commands",
                        f"arn:aws:iot:eu-west-3:*:topicfilter/efrei/grpuser03/*",
                    ],
                },
            ],
        }

        response = iot_client.create_policy(
            policyName=policy_name, policyDocument=json.dumps(policy_document)
        )

        print(f"✓ Politique '{policy_name}' créée avec succès")
        return policy_name

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print(f"✓ Politique '{policy_name}' existe déjà")
            return policy_name
        else:
            print(f"✗ Erreur création politique: {e}")
            return None


def create_certificates_for_efrei():
    """
    Crée les certificats pour le dispositif EFREI
    """
    region = "eu-west-3"

    try:
        iot_client = boto3.client("iot", region_name=region)

        response = iot_client.create_keys_and_certificate(setAsActive=True)

        # Créer le dossier des certificats
        os.makedirs("aws-iot-certs", exist_ok=True)

        # Sauvegarder les certificats
        with open("aws-iot-certs/device-certificate.pem.crt", "w") as f:
            f.write(response["certificatePem"])

        with open("aws-iot-certs/private.pem.key", "w") as f:
            f.write(response["keyPair"]["PrivateKey"])

        with open("aws-iot-certs/public.pem.key", "w") as f:
            f.write(response["keyPair"]["PublicKey"])

        print("✓ Certificats créés et sauvegardés dans aws-iot-certs/")

        # Télécharger le certificat racine Amazon
        import urllib.request

        url = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
        urllib.request.urlretrieve(url, "aws-iot-certs/root-CA.crt")
        print("✓ Certificat racine Amazon téléchargé")

        return response

    except ClientError as e:
        print(f"✗ Erreur création certificats: {e}")
        return None


def get_iot_endpoint():
    """
    Récupère l'endpoint AWS IoT Core pour eu-west-3
    """
    try:
        iot_client = boto3.client("iot", region_name="eu-west-3")
        response = iot_client.describe_endpoint(endpointType="iot:Data-ATS")
        endpoint = response["endpointAddress"]
        print(f"✓ Endpoint AWS IoT Core: {endpoint}")
        return endpoint
    except ClientError as e:
        print(f"✗ Erreur récupération endpoint: {e}")
        return None


def update_env_file(endpoint, thing_name):
    """
    Met à jour le fichier .env avec les bonnes valeurs
    """
    try:
        # Lire le fichier .env existant
        with open(".env", "r") as f:
            lines = f.readlines()

        # Mettre à jour les lignes AWS IoT
        updated_lines = []
        for line in lines:
            if line.startswith("AWS_IOT_ENDPOINT="):
                updated_lines.append(f"AWS_IOT_ENDPOINT={endpoint}\n")
            elif line.startswith("AWS_IOT_CLIENT_ID="):
                updated_lines.append(f"AWS_IOT_CLIENT_ID={thing_name}\n")
            else:
                updated_lines.append(line)

        # Réécrire le fichier
        with open(".env", "w") as f:
            f.writelines(updated_lines)

        print("✓ Fichier .env mis à jour avec la configuration AWS IoT")

    except Exception as e:
        print(f"✗ Erreur mise à jour .env: {e}")


def main():
    """
    Configuration complète AWS IoT Core pour EFREI
    """
    print("🚀 Configuration AWS IoT Core - EFREI Groupe User03")
    print("Base de données: mariadb-efrei-iot-2025 (eu-west-3)")
    print("=" * 60)

    # Étape 1: Guide credentials
    setup_aws_credentials()

    input(
        "\n⏸️  Configurez vos credentials AWS puis appuyez sur Entrée pour continuer..."
    )

    # Étape 2: Test connexion
    print("\n2. Test de la connexion AWS...")
    if not check_aws_connection():
        print("❌ Arrêt - configurez d'abord vos credentials")
        return

    # Étape 3: Créer la Thing
    print("\n3. Création de la Thing IoT...")
    thing_name = create_iot_thing_for_efrei()
    if not thing_name:
        print("❌ Impossible de créer la Thing")
        return

    # Étape 4: Créer la politique
    print("\n4. Création de la politique de sécurité...")
    policy_name = create_iot_policy_for_efrei()
    if not policy_name:
        print("❌ Impossible de créer la politique")
        return

    # Étape 5: Créer les certificats
    print("\n5. Création des certificats...")
    cert_response = create_certificates_for_efrei()
    if not cert_response:
        print("❌ Impossible de créer les certificats")
        return

    certificate_arn = cert_response["certificateArn"]

    # Étape 6: Attacher la politique au certificat
    print("\n6. Attachement de la politique...")
    try:
        iot_client = boto3.client("iot", region_name="eu-west-3")
        iot_client.attach_policy(policyName=policy_name, target=certificate_arn)
        print("✓ Politique attachée au certificat")
    except Exception as e:
        print(f"✗ Erreur attachement politique: {e}")

    # Étape 7: Attacher le certificat à la Thing
    print("\n7. Attachement du certificat à la Thing...")
    try:
        iot_client.attach_thing_principal(
            thingName=thing_name, principal=certificate_arn
        )
        print("✓ Certificat attaché à la Thing")
    except Exception as e:
        print(f"✗ Erreur attachement certificat: {e}")

    # Étape 8: Récupérer l'endpoint
    print("\n8. Récupération de l'endpoint...")
    endpoint = get_iot_endpoint()
    if not endpoint:
        print("❌ Impossible de récupérer l'endpoint")
        return

    # Étape 9: Mettre à jour .env
    print("\n9. Mise à jour du fichier .env...")
    update_env_file(endpoint, thing_name)

    print("\n" + "=" * 60)
    print("🎉 Configuration AWS IoT Core terminée !")
    print("=" * 60)
    print(f"✓ Thing Name: {thing_name}")
    print(f"✓ Endpoint: {endpoint}")
    print(f"✓ Région: eu-west-3")
    print(f"✓ Certificats: aws-iot-certs/")

    print("\n📡 Topics MQTT configurés:")
    print("• efrei/grpuser03/led/commands - Commandes LED")
    print("• efrei/grpuser03/sensors/data - Données capteurs")
    print("• efrei/grpuser03/device/status - Statut dispositif")

    print("\n🚀 Prochaines étapes:")
    print("1. Lancez votre application: python app.py")
    print("2. Testez avec: curl http://localhost:5000/api/aws-iot/status")
    print("3. Configurez vos dispositifs IoT avec les certificats générés")


if __name__ == "__main__":
    main()
