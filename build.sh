
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate

if [ "$CREATE_ADMIN_ON_DEPLOY" = "true" ]; then
    python manage.py create_admin
fi
