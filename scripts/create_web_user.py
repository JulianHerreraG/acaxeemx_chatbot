"""
Crea un usuario en Firebase Auth con rol developer para acaxee_web.
Uso: python -m scripts.create_web_user <email> <password> [displayName]
Ejemplo: python -m scripts.create_web_user dev@acaxee.local password123 Developer
"""
import sys
import json
import os
from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import credentials, auth

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Uso: python -m scripts.create_web_user <email> <password> [displayName]")
        sys.exit(1)

    email = args[0]
    password = args[1]
    display_name = args[2] if len(args) > 2 else "Developer"

    cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not cred_json:
        print("Error: FIREBASE_CREDENTIALS_JSON no está configurado en .env")
        sys.exit(1)

    cred_dict = json.loads(cred_json)
    cred = credentials.Certificate(cred_dict)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    print(f"Creando usuario: {email}...")
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True,
        )
        print(f"✓ Usuario creado: {user.uid}")
    except firebase_admin.exceptions.AlreadyExistsError:
        print(f"Usuario ya existe, buscando uid...")
        user = auth.get_user_by_email(email)
        print(f"✓ Usuario encontrado: {user.uid}")

    print("Asignando rol developer...")
    auth.set_custom_user_claims(user.uid, {"role": "developer"})
    print("✓ Rol asignado: developer")
    print()
    print("═" * 45)
    print("Usuario listo:")
    print(f"  Email:    {email}")
    print(f"  Password: {password}")
    print(f"  Rol:      developer")
    print("═" * 45)

if __name__ == "__main__":
    main()
