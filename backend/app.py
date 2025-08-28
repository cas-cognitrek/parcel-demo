import os
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase, basic_auth
from neo4j.time import Date, DateTime, Time, Duration
try:
    from neo4j.spatial import Point
except Exception:
    Point = None  # fallback ako verzija drajvera nema neo4j.spatial

# ------------------------------------------------------------------------------
# Konfiguracija
# ------------------------------------------------------------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "").strip()
NEO4J_USER = os.getenv("NEO4J_USER", "").strip()
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "").strip()

app = Flask(__name__)
CORS(app)

_driver = None  # lenjo inicijalizovan Neo4j driver


# ------------------------------------------------------------------------------
# JSON sanitizacija (fix: "Object of type Date is not JSON serializable")
# ------------------------------------------------------------------------------

def _coerce_neo4j_value(v):
    # Temporal
    if isinstance(v, (Date, DateTime, Time)):
        return v.iso_format()
    if isinstance(v, Duration):
        return str(v)

    # Spatial
    if Point and isinstance(v, Point):
        out = {"srid": v.srid, "x": v.x, "y": v.y}
        if hasattr(v, "z"):
            out["z"] = v.z
        return out

    # Kolekcije
    if isinstance(v, list):
        return [_coerce_neo4j_value(x) for x in v]
    if isinstance(v, tuple):
        return tuple(_coerce_neo4j_value(x) for x in v)
    if isinstance(v, dict):
        return {k: _coerce_neo4j_value(val) for k, val in v.items()}

    # primitivni tipovi / None
    return v


def send_json(data: Any, status: int = 200):
    return jsonify(_coerce_neo4j_value(data)), status


# ------------------------------------------------------------------------------
# Neo4j pomoćne funkcije
# ------------------------------------------------------------------------------

def get_driver():
    global _driver
    if _driver is None:
        if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
            return None
        auth = basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        app.logger.info("Initializing Neo4j driver -> %s", NEO4J_URI)
        _driver = GraphDatabase.driver(NEO4J_URI, auth=auth)
    return _driver


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
    node_id = getattr(n, "element_id", None)
    if node_id is None and hasattr(n, "id"):
        node_id = n.id
    props = {k: _coerce_neo4j_value(v) for k, v in dict(n).items()}
    return {
        "id": node_id,
        "labels": list(n.labels) if hasattr(n, "labels") else [],
        "properties": props,
    }


# ------------------------------------------------------------------------------
# Rute
# ------------------------------------------------------------------------------

@app.route("/health")
def health():
    return send_json({"status": "ok"})


@app.route("/")
def root():
    return send_json({
        "service": "parcel-backend",
        "status": "ok",
        "neo4j_connected": ping_neo4j(),
        "try": [
            "/health",
            "/api/v1/parcels",
            "/api/v1/parcels/012-345-106",
            "/api/v1/graph/parcel/012-345-106"
        ],
    })


@app.route("/api/v1/parcels", methods=["GET"])
def list_parcels():
    """
    Lista parcelId vrednosti za dropdown.
      ?q=substring  (opciono)
      ?limit=200    (opciono)
    """
    drv = get_driver()
    if not drv:
        return send_json({"parcels": [], "error": "neo4j_not_configured"})

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
        return send_json({"parcels": [r[0] for r in recs]})
    except Exception as e:
        app.logger.exception("list_parcels failed")
        return send_json({"parcels": [], "error": "server", "message": str(e)}, 500)


@app.route("/api/v1/parcels/<parcel_id>", methods=["GET"])
def get_parcel(parcel_id: str):
    """
    Vraća parcelu i povezane čvorove (Title/Owner/Zoning/Assessment/Plan/RRR).
    Dozvoljava i :SurveyPlan i :Plan labelu za planove.
    """
    drv = get_driver()
    if not drv:
        return send_json({"error": "neo4j_not_configured", "parcelId": parcel_id})

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
                return send_json({"error": "not_found", "parcelId": parcel_id}, 404)

            payload = {
                "parcel":      node_to_dict(rec["p"]),
                "titles":      [node_to_dict(n) for n in rec["titles"]],
                "owners":      [node_to_dict(n) for n in rec["owners"]],
                "zoning":      [node_to_dict(n) for n in rec["zonings"]],
                "assessments": [node_to_dict(n) for n in rec["assessments"]],
                "plans":       [node_to_dict(n) for n in rec["plans"]],
                "rrrs":        [node_to_dict(n) for n in rec["rrrs"]],
            }
            return send_json(payload)
    except Exception as e:
        app.logger.exception("Error fetching parcel %s", parcel_id)
        return send_json({"error": "server", "message": str(e)}, 500)


@app.route("/api/v1/graph/parcel/<parcel_id>", methods=["GET"])
def graph_for_parcel(parcel_id: str):
    """
    Debug podgraf oko parcele (nedirekciono).
    Odgovor:
      { nodes: [ {id, labels, properties}, ... ],
        links: [ {id, type, start, end, properties}, ... ] }
    """
    drv = get_driver()
    if not drv:
        return send_json({"nodes": [], "links": [], "error": "neo4j_not_configured"})

    QUERY = """
    MATCH (p:Parcel {parcelId:$parcelId})
    OPTIONAL MATCH (p)-[r]-(m)
    RETURN p, r, m
    """
    try:
        with drv.session() as s:
            rs = s.run(QUERY, parcelId=parcel_id)

            nodes: Dict[str, Dict[str, Any]] = {}
            links: List[Dict[str, Any]] = []

            def add_node(n):
                d = node_to_dict(n)
                if not d:
                    return None
                nid = str(d["id"])
                if nid not in nodes:
                    nodes[nid] = d
                return nid

            for rec in rs:
                p = rec["p"]
                pid = add_node(p)

                r = rec["r"]
                m = rec["m"]
                if r is not None and m is not None:
                    mid = add_node(m)
                    rid = getattr(r, "element_id", None)
                    if rid is None and hasattr(r, "id"):
                        rid = r.id
                    links.append({
                        "id": str(rid),
                        "type": r.type,
                        "start": pid,
                        "end": mid,
                        "properties": _coerce_neo4j_value(dict(r)),
                    })

            return send_json({
                "nodes": list(nodes.values()),
                "links": links
            })
    except Exception as e:
        app.logger.exception("graph_for_parcel error")
        return send_json({"error": "server", "message": str(e)}, 500)


# ------------------------------------------------------------------------------
# Lokalni razvoj
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
