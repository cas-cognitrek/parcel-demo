import os
from flask import Flask, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase

app = Flask(__name__)
CORS(app)

# ---- Neo4j configuration ----
NEO4J_URI = (os.getenv("NEO4J_URI") or "").strip()
NEO4J_USER = (os.getenv("NEO4J_USER") or "").strip()
NEO4J_PASSWORD = (os.getenv("NEO4J_PASSWORD") or "").strip()

driver = None
if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
else:
    app.logger.warning("Neo4j env vars missing; API will run without DB connection.")

# ---- helpers ----
def node_to_dict(n):
    if n is None:
        return None
    return {
        "id": getattr(n, "element_id", None),
        "labels": list(getattr(n, "labels", [])),
        "properties": dict(n),
    }

# ---- routes ----
@app.route("/")
def index():
    return {
        "service": "parcel-backend",
        "status": "ok",
        "neo4j_connected": bool(driver),
        "try": ["/health", "/api/v1/parcels/012-345-678"],
    }

@app.route("/health")
def health():
    return {"status": "ok", "neo4j_connected": bool(driver)}

@app.route("/api/v1/parcels/<parcel_id>")
def get_parcel(parcel_id):
    if not driver:
        return jsonify({"error": "Neo4j not configured"}), 503

    try:
        with driver.session() as session:
            record = session.run(
                """
                MATCH (p:Parcel {parcelId: $parcel_id})
                OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)-[:OWNED_BY]->(o:Owner)
                OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
                OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
                OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
                OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
                RETURN p,
                       collect(DISTINCT t) AS titles,
                       collect(DISTINCT o) AS owners,
                       collect(DISTINCT r) AS rrrs,
                       collect(DISTINCT sp) AS plans,
                       collect(DISTINCT a) AS assessments,
                       collect(DISTINCT z) AS zonings
                """,
                parcel_id=parcel_id,
            ).single()

        if not record:
            return jsonify({"error": f"Parcel {parcel_id} not found"}), 404

        out = {
            "parcel": node_to_dict(record["p"]),
            "titles": [node_to_dict(x) for x in record["titles"] if x],
            "owners": [node_to_dict(x) for x in record["owners"] if x],
            "rrrs": [node_to_dict(x) for x in record["rrrs"] if x],
            "plans": [node_to_dict(x) for x in record["plans"] if x],
            "assessments": [node_to_dict(x) for x in record["assessments"] if x],
            "zonings": [node_to_dict(x) for x in record["zonings"] if x],
        }
        return jsonify(out)

    except Exception as e:
        app.logger.exception("Error fetching parcel %s", parcel_id)
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

# ---- local dev ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
