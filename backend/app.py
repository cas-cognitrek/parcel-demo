import os
from flask import Flask, jsonify
from neo4j import GraphDatabase
from flask_cors import CORS

# Initialize Flask
app = Flask(__name__)
CORS(app)  # enable CORS for frontend calls

# Load Neo4j connection details from environment variables
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = None
if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
else:
    app.logger.warning("Neo4j environment variables not set. API will run without DB connection.")

# ---------------------
# Routes
# ---------------------

# Root route
@app.route("/")
def index():
    return {
        "service": "parcel-backend",
        "status": "ok",
        "try": ["/health", "/api/v1/parcels/012-345-678"]
    }

# Health check
@app.route("/health")
def health():
    return {"status": "ok", "neo4j_connected": bool(driver)}

# Get parcel by ID
@app.route("/api/v1/parcels/<parcel_id>")
def get_parcel(parcel_id):
    if not driver:
        return jsonify({"error": "Neo4j not configured"}), 503

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Parcel {parcelId: $parcel_id})
            OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)-[:OWNED_BY]->(o:Owner)
            OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
            OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
            OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
            OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
            RETURN p, collect(DISTINCT t) AS titles, collect(DISTINCT o) AS owners,
                   collect(DISTINCT r) AS rrrs, collect(DISTINCT sp) AS plans,
                   collect(DISTINCT a) AS assessments, collect(DISTINCT z) AS zonings
            """,
            parcel_id=parcel_id
        )
        record = result.single()
        if not record:
            return jsonify({"error": f"Parcel {parcel_id} not found"}), 404

        parcel_data = {
            "parcel": record["p"],
            "titles": record["titles"],
            "owners": record["owners"],
            "rrrs": record["rrrs"],
            "plans": record["plans"],
            "assessments": record["assessments"],
            "zonings": record["zonings"],
        }
        return jsonify(parcel_data)

# ---------------------
# Local run
# ---------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
