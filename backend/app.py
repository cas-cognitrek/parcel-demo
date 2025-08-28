import os
import json
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from neo4j import GraphDatabase

# ----------------------------
# App & CORS
# ----------------------------
app = Flask(__name__)
CORS(app)

# ----------------------------
# Neo4j config (from env)
# ----------------------------
NEO4J_URI = (os.getenv("NEO4J_URI") or "").strip()
NEO4J_USER = (os.getenv("NEO4J_USER") or "").strip()
NEO4J_PASSWORD = (os.getenv("NEO4J_PASSWORD") or "").strip()

driver = None
if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
else:
    app.logger.warning("Neo4j env vars missing; API will run without DB connection.")

# ----------------------------
# Utilities
# ----------------------------
def send_json(data, status=200):
    """
    Return JSON. If the querystring includes ?pretty=1, pretty-print it.
    """
    if request.args.get("pretty"):
        return Response(
            json.dumps(data, indent=2, sort_keys=True),
            status=status,
            mimetype="application/json"
        )
    resp = jsonify(data)
    resp.status_code = status
    return resp

def node_to_dict(n):
    """Convert a Neo4j Node to a plain dict for JSON serialization."""
    if n is None:
        return None
    return {
        "id": getattr(n, "element_id", None),
        "labels": list(getattr(n, "labels", [])),
        "properties": dict(n),
    }

# ----------------------------
# Routes
# ----------------------------
@app.route("/api/v1/graph/parcel/<parcel_id>")
def graph_for_parcel(parcel_id):
    """
    Returns a small graph centered on a parcel:
      nodes:  the Parcel and all 1-hop neighbors
      links:  relationships among them
    Shape:
    {
      "nodes":[{"id":"<eid>","labels":["Parcel"],"props":{...}}, ...],
      "links":[{"id":"<eid>","type":"HAS_TITLE","source":"<eid>","target":"<eid>"}]
    }
    """
    if not driver:
        return send_json({"error": "Neo4j not configured"}, status=503)

    q = """
    MATCH (p:Parcel {parcelId:$parcel_id})
    OPTIONAL MATCH (p)-[r]-(m)
    WITH p, collect(DISTINCT m) AS ms, collect(DISTINCT r) AS rs
    RETURN p, ms AS others, rs AS rels
    """
    try:
        with driver.session() as s:
            rec = s.run(q, parcel_id=parcel_id).single()

        if not rec or not rec["p"]:
            return send_json({"nodes": [], "links": []})

        def n2d(n):
            return {
                "id": getattr(n, "element_id", None),
                "labels": list(getattr(n, "labels", [])),
                "props": dict(n),
            }

        def r2d(r):
            return {
                "id": getattr(r, "element_id", None),
                "type": r.type,
                "source": getattr(r.start_node, "element_id", None),
                "target": getattr(r.end_node, "element_id", None),
                "props": dict(r),
            }

        center = n2d(rec["p"])
        others = [n2d(x) for x in rec["others"] if x]
        rels   = [r2d(x) for x in rec["rels"] if x]

        return send_json({"nodes": [center, *others], "links": rels})
    except Exception as e:
        app.logger.exception("graph_for_parcel error")
        return send_json({"error":"Internal Server Error","detail":str(e)}, status=500)

@app.route("/")
def index():
    return send_json({
        "neo4j_connected": bool(driver),
        "service": "parcel-backend",
        "status": "ok",
        "try": ["/health", "/api/v1/parcels", "/api/v1/parcels/012-345-101"]
    })

@app.route("/health")
def health():
    return send_json({"status": "ok", "neo4j_connected": bool(driver)})

@app.route("/api/v1/parcels/<parcel_id>")
def get_parcel(parcel_id):
    if not driver:
        return send_json({"error": "Neo4j not configured"}, status=503)

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
                       collect(DISTINCT t)  AS titles,
                       collect(DISTINCT o)  AS owners,
                       collect(DISTINCT r)  AS rrrs,
                       collect(DISTINCT sp) AS plans,
                       collect(DISTINCT a)  AS assessments,
                       collect(DISTINCT z)  AS zonings
                """,
                parcel_id=parcel_id
            ).single()

        if not record or not record["p"]:
            return send_json({"error": f"Parcel {parcel_id} not found"}, status=404)

        out = {
            "parcel":      node_to_dict(record["p"]),
            "titles":      [node_to_dict(x) for x in record["titles"] if x],
            "owners":      [node_to_dict(x) for x in record["owners"] if x],
            "rrrs":        [node_to_dict(x) for x in record["rrrs"] if x],
            "plans":       [node_to_dict(x) for x in record["plans"] if x],
            "assessments": [node_to_dict(x) for x in record["assessments"] if x],
            "zonings":     [node_to_dict(x) for x in record["zonings"] if x],
        }
        return send_json(out)

    except Exception as e:
        app.logger.exception("Error fetching parcel %s", parcel_id)
        return send_json({"error": "Internal Server Error", "detail": str(e)}, status=500)

@app.route("/api/v1/parcels")
def list_parcels():
    """
    List parcel IDs (and optional basic props).
    Query params:
      - q: prefix filter, e.g. q=012-345-10
      - limit: max results (default 100)
      - offset: skip N (default 0)
      - props: if "1", include legalDescription
    """
    if not driver:
        return send_json({"error": "Neo4j not configured"}, status=503)

    q = (request.args.get("q") or "").strip()
    try:
        limit = min(int(request.args.get("limit") or 100), 1000)
    except ValueError:
        limit = 100
    try:
        offset = max(int(request.args.get("offset") or 0), 0)
    except ValueError:
        offset = 0
    want_props = request.args.get("props") == "1"

    cypher = """
        MATCH (p:Parcel)
        WHERE $q = "" OR p.parcelId STARTS WITH $q
        RETURN p.parcelId AS parcelId, p.legalDescription AS legalDescription
        ORDER BY parcelId
        SKIP $offset
        LIMIT $limit
    """

    with driver.session() as session:
        rows = session.run(
            cypher,
            q=q,
            offset=offset,
            limit=limit
        ).data()

    items = (
        [{"parcelId": r["parcelId"], "legalDescription": r["legalDescription"]} for r in rows]
        if want_props
        else [{"parcelId": r["parcelId"]} for r in rows]
    )

    return send_json({
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "items": items
    })

# ----------------------------
# Local dev runner
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
