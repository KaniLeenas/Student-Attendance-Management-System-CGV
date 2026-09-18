#!/usr/bin/env python
"""
Create / list / delete SAMS login accounts.

    $ python manage_users.py add admin admin123 admin "Dr Rasika Ranaweera"
    $ python manage_users.py add staff01 pass123 staff "Group Member 1"
    $ python manage_users.py list
    $ python manage_users.py delete 3
"""

import sys

from core.database import Database
from core.auth import hash_password, ROLES


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]

    db = Database()

    if not db.ping():
        print("ERROR: Cannot reach MySQL. Please start MySQL in XAMPP first.")
        return 2

    if not argv or argv[0] == "list":
        users = db.list_users()

        if not users:
            print("No accounts yet.")
        else:
            for u in users:
                print(
                    f"  [{u['user_id']}] {u['username']:<16} "
                    f"{u['role']:<6} {u['full_name'] or ''}"
                )

        return 0

    if argv[0] == "add":
        if len(argv) < 4:
            print(
                "Usage: python manage_users.py add "
                "<username> <password> <admin|staff> [full name]"
            )
            return 2

        username = argv[1]
        password = argv[2]
        role = argv[3]
        full_name = " ".join(argv[4:]) if len(argv) > 4 else ""

        if role not in ROLES:
            print(f"Error: role must be one of {ROLES}")
            return 2

        if db.get_user_by_username(username):
            print(f"Error: '{username}' already exists.")
            return 1

        db.create_user(
            username,
            hash_password(password),
            role,
            full_name
        )

        print(f"Created {role} account '{username}'.")
        return 0

    if argv[0] == "delete":
        if len(argv) < 2:
            print("Usage: python manage_users.py delete <user_id>")
            return 2

        try:
            user_id = int(argv[1])
        except ValueError:
            print("Error: user_id must be a number.")
            return 2

        db.delete_user(user_id)
        print(f"Deleted account #{user_id}.")
        return 0

    print(
        "Usage:\n"
        "  python manage_users.py list\n"
        "  python manage_users.py add <username> <password> "
        "<admin|staff> [full name]\n"
        "  python manage_users.py delete <user_id>"
    )

    return 2


if __name__ == "__main__":
    sys.exit(main())
    sys.exit(main())
