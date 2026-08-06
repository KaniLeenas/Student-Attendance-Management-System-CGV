
import sys

from core.database import Database
from core.auth import hash_password, ROLES


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    db = Database()
    if not db.ping():
        print("ERROR: cannot reach MySQL - start it in XAMPP first.")
        return 2

    if not argv or argv[0] == "list":
        users = db.list_users()
        if not users:
            print("No accounts yet.")
        for u in users:
            print(f"  [{u['user_id']}] {u['username']:<16} "
                  f"{u['role']:<6} {u['full_name'] or ''}")
        return 0

    if argv[0] == "add":
        if len(argv) < 4:
            print("Usage: python manage_users.py add "
                  "<username> <password> <admin|staff> [full name]")
            return 2
        username, password, role = argv[1], argv[2], argv[3]
        full_name = " ".join(argv[4:]) if len(argv) > 4 else ""
        if role not in ROLES:
            print(f"role must be one of {ROLES}")
            return 2
        if db.get_user_by_username(username):
            print(f"'{username}' already exists.")
            return 1
        db.create_user(username, hash_password(password), role, full_name)
        print(f"Created {role} account '{username}'.")
        return 0

    if argv[0] == "delete" and len(argv) > 1:
        db.delete_user(int(argv[1]))
        print(f"Deleted account #{argv[1]}.")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())