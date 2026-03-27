"""Script para criar o usuario administrador inicial.

Uso:
    python -m scripts.create_admin
    # ou
    python scripts/create_admin.py
"""

import os
import sys

# Permite rodar tanto como modulo quanto como script direto.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from remote_api.auth.crud import create_user, get_user_by_email
from remote_api.database import ensure_database_schema, session_scope


def main() -> None:
    email = "admin@example.com"
    password = "Admin@2025!"
    full_name = "Admin"
    role = "admin"

    print("Criando tabelas (se necessario)...")
    ensure_database_schema()

    with session_scope() as session:
        existing = get_user_by_email(session, email)
        if existing:
            print(f"Usuario ja existe: {email} (role={existing.role})")
            return

        user = create_user(
            session,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
        )
        session.commit()
        session.refresh(user)
        print("Admin criado com sucesso!")
        print(f"  ID    : {user.id}")
        print(f"  Nome  : {user.full_name}")
        print(f"  Email : {user.email}")
        print(f"  Role  : {user.role}")


if __name__ == "__main__":
    main()
