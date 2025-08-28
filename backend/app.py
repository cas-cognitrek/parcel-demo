import os
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase, basic_auth

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
NEO4J_USER = os.getenv("NEO4J_USER", "").strip()
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "").strip()

app = Flask(__name__)
CORS(app)  # allow all origins; tighten if needed

driver = None  # will be initialized lazily


def get_driver():
    """Create the global Neo4j driver lazily to survive short cold starts on Render."""
    global driver
    if driver is None:
        if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
            # We keep driver None; routes will return graceful messages.
            return None
        # neo4j+s / bolt+s supported; SSL managed by Neo4j Aura/Server
        auth = basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        app.logger.info("Initializing Neo4j driver to %s", NEO4J_URI)
        _driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
        driver = _driver
    return driver


def ping_neo4j() -> bool:
    drv = get_driver()
    if not drv:
        return False
    try:
        with drv.session() as s:
            s.run("RETURN 1").single()
        return True
    except Exception as e:
        app.logger.warning("Neo4j ping failed: %s", e)
        return False


def node_to_dict(n) -> Optional[Dict[str, Any]]:
    if n is None:
        return None
    try:
        node_id = getattr(n, "element_id", None)
    except Exception:
        node_id = None
    if node_id is None and hasattr(n, "id"):
        node_id = n.id
    return {
        "id": node_id,
        "labels": list(n.labels) if hasattr(n, "labels") else [],
        "properties": dict(n),
    }


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return jsonify({
        "service": "parcel-backend",
        "status": "ok",
        "neo4j_connected": ping_neo4j(),
        "try": [
            "/health",
            "/api/v1/parcels",
            "/api/v1/parcels/012-345-106"
        ],
    })


@app.route("/api/v1/parcels", methods=["GET"])
def list_parcels():
    """
    Returns a simple list of parcel IDs (for dropdowns).
    Optional query params:
      - q: substring filter
      - limit: max number (default 200)
    """
    drv = get_driver()
    if not drv:
        return jsonify({"parcels": [], "error": "neo4j_not_configured"}), 200

    q = request.args.get("q", "").strip()
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200

    try:
        with drv.session() as s:
            if q:
                recs = s.run(
                    """
                    MATCH (p:Parcel)
                    WHERE toLower(p.parcelId) CONTAINS toLower($q)
                    RETURN p.parcelId AS id
                    ORDER BY id
                    LIMIT $limit
                    """,
                    q=q, limit=limit
                ).values()
            else:
                recs = s.run(
                    """
                    MATCH (p:Parcel)
                    RETURN p.parcelId AS id
                    ORDER BY id
                    LIMIT $limit
                    """,
                    limit=limit
                ).values()
        return jsonify({"parcels": [r[0] for r in recs]})
    except Exception as e:
        app.logger.exception("list_parcels failed")
        return jsonify({"parcels": [], "error": "server", "message": str(e)}), 500


@app.route("/api/v1/parcels/<parcel_id>", methods=["GET"])
def get_parcel(parcel_id: str):
    """
    Returns the parcel star (Parcel + Title/Owner/Zoning/Plan/RRR/Assessment).
    Tolerates :SurveyPlan or :Plan labels for survey plans.
    """
    drv = get_driver()
    if not drv:
        return jsonify({"error": "neo4j_not_configured", "parcelId": parcel_id}), 200

    QUERY = """
    MATCH (p:Parcel {parcelId:$parcelId})
    OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
    OPTIONAL MATCH (t)-[:OWNED_BY]->(o:Owner)
    OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
    OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
    OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp)
    WHERE sp:SurveyPlan OR sp:Plan
    OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
    RETURN
      p,
      collect(DISTINCT t)  AS titles,
      collect(DISTINCT o)  AS owners,
      collect(DISTINCT z)  AS zonings,
      collect(DISTINCT a)  AS assessments,
      collect(DISTINCT sp) AS plans,
      collect(DISTINCT r)  AS rrrs
    """

    try:
        with drv.session() as s:
            rec = s.run(QUERY, parcelId=parcel_id).single()
            if not rec:
                return jsonify({"error": "not_found", "parcelId": parcel_id}), 404

            p = rec["p"]
            payload = {
                "parcel": node_to_dict(p),
                "titles":      [node_to_dict(n) for n in rec["titles"]],
                "owners":      [node_to_dict(n) for n in rec["owners"]],
                "zoning":      [node_to_dict(n) for n in rec["zonings"]],
                "assessments": [node_to_dict(n) for n in rec["assessments"]],
                "plans":       [node_to_dict(n) for n in rec["plans"]],
                "rrrs":        [node_to_dict(n) for n in rec["rrrs"]],
            }
            return jsonify(payload)
    except Exception as e:
        app.logger.exception("get_parcel failed for %s", parcel_id)
        return jsonify({"error": "server", "message": str(e)}), 500


# Optional: simple debug graph dump for a parcel (useful during setup)
@app.route("/api/v1/parcels/<parcel_id>/graph", methods=["GET"])
def get_parcel_graph(parcel_id: str):
    """
    Returns all relationships around a parcel (undirected). Handy for debugging.
    """
    drv = get_driver()
    if not drv:
        return jsonify({"nodes": [], "rels": [], "error": "neo4j_not_configured"}), 200

    QUERY = """
    MATCH (p:Parcel {parcelId:$parcelId})-[r]-(m)
    RETURN p, r, m
    """
    try:
        with drv.session() as s:
            results = s.run(QUERY, parcelId=parcel_id)

            nodes_map: Dict[str, Dict[str, Any]] = {}
            rels: List[Dict[str, Any]] = []

            def ensure_node(n):
                d = node_to_dict(n)
                if not d:
                    return None
                nid = str(d["id"])
                if nid not in nodes_map:
                    nodes_map[nid] = d
                return nid

            for rec in results:
                p = rec["p"]
                m = rec["m"]
                r = rec["r"]

                src = ensure_node(p)
                dst = ensure_node(m)
                r_id = getattr(r, "element_id", None)
                if r_id is None and hasattr(r, "id"):
                    r_id = r.id
                rels.append({
                    "id": str(r_id),
                    "type": r.type,
                    "start": src,
                    "end": dst,
                    "properties": dict(r),
                })

            return jsonify({
                "nodes": list(nodes_map.values()),
                "rels": rels
            })
    except Exception as e:
        app.logger.exception("get_parcel_graph failed for %s", parcel_id)
        return jsonify({"error": "server", "message": str(e)}), 500


# ------------------------------------------------------------------------------
# Local dev entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Local dev server (Render will use gunicorn)
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
