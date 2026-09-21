import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# Enable full traceback output in browser
os.environ['DJANGO_SETTINGS_MODULE'] = 'aizaah.settings'

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception:
    import traceback
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = traceback.format_exc().encode('utf-8')
        response_headers = [('Content-type', 'text/plain; charset=utf-8'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]