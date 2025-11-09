from flask import Flask, request
from flask_cors import CORS
from .routes.recommendation import recommendations_bp
from .routes.listings import listings_bp
import os
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__)

    load_dotenv()

    # Get Vercel URL from environment or allow all origins in production
    allowed_origins = [
        "http://localhost:5173", 
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173"
    ]
    
    # Add Vercel URL if provided
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        allowed_origins.append(f"https://{vercel_url}")
    
    # Allow all origins in production (Vercel will handle CORS)
    # Or specify your production domain
    production_url = os.getenv("PRODUCTION_URL")
    if production_url:
        allowed_origins.append(production_url)
    
    # In production (Vercel), allow all vercel.app domains
    # This handles preview deployments and production deployments
    is_production = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") in ["production", "preview"]
    
    # Function to check if origin should be allowed
    def origin_check(origin):
        if not origin:
            return False
        # Allow localhost in development
        if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
            return True
        # Allow all vercel.app domains in production
        if is_production and (origin.endswith(".vercel.app") or origin.endswith("vercel.app")):
            return True
        # Allow specific production URL if set
        if production_url and origin == production_url:
            return True
        # Allow vercel URL if set
        if vercel_url and origin == f"https://{vercel_url}":
            return True
        return False
    
    if is_production:
        # Use function to dynamically allow origins
        CORS(
            app,
            origins=origin_check,  # Use function to check origins
            supports_credentials=True,
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Authorization"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )
    else:
        # In development, use specific origins
        CORS(
            app,
            origins=allowed_origins if allowed_origins else ["*"],
            supports_credentials=True,
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Authorization"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )
    
    app.secret_key = os.getenv("SECRET_KEY")

    app.register_blueprint(recommendations_bp, url_prefix="/recommendations")
    app.register_blueprint(listings_bp, url_prefix="/listings")
    
    @app.route("/")
    def root():
        return {"message": "HackPrincetonF25 backend running on AWS-ready Flask app"}
    
    # Add manual CORS headers as fallback for all routes (in case Flask-CORS doesn't catch it)
    @app.after_request
    def after_request(response):
        # Get the origin from the request
        origin = request.headers.get('Origin')
        
        # Check if origin should be allowed
        if origin and origin_check(origin):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            response.headers.add('Access-Control-Expose-Headers', 'Authorization')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response

    return app
