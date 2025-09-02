// Backend API base (Render service root + API prefix)
window.API_BASE = "https://parcel-demo-backend.onrender.com/api/v1";

// GeoJSON file served by the frontend (keep name if you didn’t change it)
window.GEOJSON_URL = "synthetic_parcels.geojson";

// Use the backend API for details/graph lookups
window.USING_API = true;

/*
Notes:
- Your backend exposes routes under /api/v1 (e.g., /api/v1/health, /api/v1/parcels/:pid).
- If you ever point to a different backend URL, keep the /api/v1 suffix unless you change the Flask routes.
*/
