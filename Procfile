web: gunicorn aizaah.wsgi --workers 2 --threads 2 --worker-class gthread --timeout 60 --log-file -
release: python manage.py migrate --noinput
