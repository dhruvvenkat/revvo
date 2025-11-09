import sys
import os
import json
from io import BytesIO
from urllib.parse import urlparse, parse_qs, quote

# Add the server directory to the path
server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
sys.path.insert(0, os.path.abspath(server_path))

try:
    from app import create_app
    # Create Flask app instance
    print("DEBUG - Initializing Flask app...")
    app = create_app()
    print("DEBUG - Flask app initialized successfully")
except Exception as e:
    # If app creation fails, we'll handle it in the handler
    import traceback
    app_init_trace = traceback.format_exc()
    print(f"ERROR - Failed to initialize Flask app: {str(e)}")
    print(f"ERROR - App init traceback:\n{app_init_trace}")
    app = None
    app_error = str(e)
    app_error_trace = app_init_trace

def handler(request):
    """
    Vercel serverless function handler for Flask app
    """
    try:
        # Debug: Log the entire request structure
        print(f"DEBUG - Request type: {type(request)}")
        print(f"DEBUG - Request is dict: {isinstance(request, dict)}")
        if isinstance(request, dict):
            print(f"DEBUG - Request keys: {list(request.keys())}")
        else:
            print(f"DEBUG - Request attributes: {dir(request)}")
        
        # Handle app initialization error
        if app is None:
            print(f"ERROR - Flask app is None, returning initialization error")
            # Get origin for CORS
            cors_origin = '*'
            try:
                if isinstance(request, dict):
                    headers_dict_raw = request.get('headers', {})
                    if isinstance(headers_dict_raw, dict):
                        headers_dict = {k.lower(): v for k, v in headers_dict_raw.items()}
                        origin = headers_dict.get('origin', '*')
                        if origin != '*' and ('.vercel.app' in origin or origin.endswith('vercel.app')):
                            cors_origin = origin
            except:
                pass
            
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': cors_origin,
                    'access-control-allow-origin': cors_origin,
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'access-control-allow-headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({
                    'error': f'Failed to initialize Flask app: {app_error}',
                    'type': 'InitializationError',
                    'message': 'A server error has occurred'
                })
            }
        
        # Vercel Python runtime passes request as a dict
        # Convert to dict if it's an object
        if not isinstance(request, dict):
            # Try to convert request object to dict
            req_dict = {}
            if hasattr(request, '__dict__'):
                req_dict = request.__dict__
            else:
                # Try common attributes
                for attr in ['path', 'method', 'headers', 'body', 'query', 'url']:
                    if hasattr(request, attr):
                        req_dict[attr] = getattr(request, attr)
            request = req_dict
        
        # Extract path from request
        path = request.get('path', '/')
        
        # If path is not in request, try to get from URL
        if path == '/' and 'url' in request:
            parsed_url = urlparse(request['url'])
            path = parsed_url.path
        
        # Vercel rewrites send the full path (e.g., /listings/?query=...)
        # We need to extract just the path part, not the query
        if '?' in path:
            path = path.split('?')[0]
        
        # Remove /api prefix if present (Vercel rewrites might add this)
        if path.startswith('/api'):
            path = path[4:] or '/'
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Get headers - make case-insensitive (do this early for OPTIONS handling)
        headers_dict_raw = request.get('headers', {})
        if not isinstance(headers_dict_raw, dict):
            # Try to convert to dict
            if hasattr(headers_dict_raw, '__dict__'):
                headers_dict_raw = headers_dict_raw.__dict__
            else:
                headers_dict_raw = {}
        
        # Normalize headers to lowercase keys for easier access
        headers_dict = {}
        for k, v in headers_dict_raw.items():
            headers_dict[k.lower()] = v
        
        # Get HTTP method
        method = request.get('method', 'GET').upper()
        
        # Handle OPTIONS preflight requests
        if method == 'OPTIONS':
            origin = headers_dict.get('origin') or headers_dict.get('Origin') or '*'
            print(f"DEBUG OPTIONS - Request origin: {origin}")
            
            # Determine CORS origin
            if origin and origin != '*' and isinstance(origin, str):
                if '.vercel.app' in origin or origin.endswith('vercel.app'):
                    cors_origin = origin
                    cors_credentials = 'true'
                else:
                    cors_origin = '*'
                    cors_credentials = 'false'
            else:
                cors_origin = '*'
                cors_credentials = 'false'
            
            print(f"DEBUG OPTIONS - Setting CORS origin to: {cors_origin}")
            
            # Return with both uppercase and lowercase headers
            cors_headers = {
                'Access-Control-Allow-Origin': cors_origin,
                'access-control-allow-origin': cors_origin,
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'access-control-allow-headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '3600',
                'access-control-max-age': '3600'
            }
            
            if cors_credentials == 'true':
                cors_headers['Access-Control-Allow-Credentials'] = 'true'
                cors_headers['access-control-allow-credentials'] = 'true'
            
            # Ensure all values are strings
            cors_headers_clean = {str(k): str(v) for k, v in cors_headers.items()}
            
            return {
                'statusCode': 200,
                'headers': cors_headers_clean,
                'body': ''
            }
        
        # Get request body
        body = b''
        body_data = request.get('body', '')
        if body_data:
            if isinstance(body_data, str):
                body = body_data.encode('utf-8')
            elif isinstance(body_data, bytes):
                body = body_data
            else:
                body = json.dumps(body_data).encode('utf-8')
        
        # Get query string from request
        query_string = ''
        if 'query' in request:
            query = request['query']
            if isinstance(query, dict):
                # Convert dict to query string
                query_parts = []
                for k, v in query.items():
                    if isinstance(v, list):
                        for item in v:
                            query_parts.append(f'{quote(str(k))}={quote(str(item))}')
                    else:
                        query_parts.append(f'{quote(str(k))}={quote(str(v))}')
                query_string = '&'.join(query_parts)
            elif isinstance(query, str):
                query_string = query
        elif 'url' in request:
            # Extract query from URL
            parsed_url = urlparse(request['url'])
            query_string = parsed_url.query
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'CONTENT_TYPE': headers_dict.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': BytesIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add HTTP headers to environ
        for key, value in headers_dict.items():
            if value is not None:
                key_upper = key.upper().replace('-', '_')
                if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                    environ[f'HTTP_{key_upper}'] = str(value)
        
        # Response data
        response_data = []
        status_code = [200]
        response_headers = []
        
        def start_response(status, response_headers_list):
            status_code[0] = int(status.split()[0])
            response_headers.extend(response_headers_list)
        
        # Call Flask app
        try:
            print(f"DEBUG - Calling Flask app with path: {path}, method: {method}")
            app_iter = app(environ, start_response)
            
            try:
                for data in app_iter:
                    response_data.append(data)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
        except Exception as flask_error:
            import traceback
            flask_trace = traceback.format_exc()
            print(f"ERROR - Flask app raised exception: {str(flask_error)}")
            print(f"ERROR - Flask traceback: {flask_trace}")
            # Re-raise to be caught by outer handler
            raise
        
        # Build response
        response_body = b''.join(response_data)
        if isinstance(response_body, bytes):
            try:
                response_body = response_body.decode('utf-8')
            except:
                response_body = str(response_body)
        
        # Convert headers to dict
        final_headers = {name: value for name, value in response_headers}
        
        # Always add CORS headers to ensure they're present
        # Get origin from headers (case-insensitive now)
        origin = headers_dict.get('origin') or headers_dict.get('Origin') or '*'
        
        # Debug logging (will appear in Vercel logs)
        print(f"DEBUG - Request origin: {origin}")
        print(f"DEBUG - All headers keys: {list(headers_dict.keys())}")
        print(f"DEBUG - Headers dict: {headers_dict}")
        
        # SIMPLIFIED: Always echo back the origin if it's a vercel.app domain, otherwise use *
        # This is the most permissive approach that should work
        if origin and origin != '*' and isinstance(origin, str):
            # If it's a vercel.app domain, use it; otherwise use *
            if '.vercel.app' in origin or origin.endswith('vercel.app'):
                cors_origin = origin
            else:
                cors_origin = '*'
        else:
            cors_origin = '*'
        
        # ALWAYS override CORS headers - these must be present
        # Use both uppercase and lowercase keys to ensure compatibility
        final_headers['Access-Control-Allow-Origin'] = cors_origin
        final_headers['access-control-allow-origin'] = cors_origin  # Lowercase version
        final_headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        final_headers['access-control-allow-headers'] = 'Content-Type, Authorization'
        final_headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        final_headers['access-control-allow-methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        final_headers['Access-Control-Expose-Headers'] = 'Authorization'
        final_headers['access-control-expose-headers'] = 'Authorization'
        
        # Only add credentials if we have a specific origin (not *)
        if cors_origin != '*':
            final_headers['Access-Control-Allow-Credentials'] = 'true'
            final_headers['access-control-allow-credentials'] = 'true'
        
        print(f"DEBUG - Setting CORS origin to: {cors_origin}")
        print(f"DEBUG - Final headers: {final_headers}")
        
        # Return response - ensure headers are strings
        response_headers_clean = {}
        for k, v in final_headers.items():
            response_headers_clean[str(k)] = str(v)
        
        return {
            'statusCode': status_code[0],
            'headers': response_headers_clean,
            'body': response_body
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # Log error (will appear in Vercel logs)
        print(f"ERROR - Exception in handler: {str(e)}")
        print(f"ERROR - Exception type: {type(e).__name__}")
        print(f"ERROR - Full traceback:\n{error_trace}")
        
        # Get origin for CORS even in error case
        cors_origin = '*'
        try:
            if isinstance(request, dict):
                headers_dict_raw = request.get('headers', {})
                if isinstance(headers_dict_raw, dict):
                    headers_dict = {k.lower(): v for k, v in headers_dict_raw.items()}
                    origin = headers_dict.get('origin', '*')
                    if origin != '*' and ('.vercel.app' in origin or origin.endswith('vercel.app')):
                        cors_origin = origin
        except Exception as cors_error:
            print(f"ERROR - Failed to extract origin for CORS: {str(cors_error)}")
        
        # Build error response with CORS headers
        error_response = {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': cors_origin,
                'access-control-allow-origin': cors_origin,
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'access-control-allow-headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Expose-Headers': 'Authorization',
                'access-control-expose-headers': 'Authorization'
            },
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__,
                'message': 'A server error has occurred'
            })
        }
        
        # Ensure all header values are strings
        error_response['headers'] = {str(k): str(v) for k, v in error_response['headers'].items()}
        
        print(f"ERROR - Returning error response with status 500")
        return error_response
