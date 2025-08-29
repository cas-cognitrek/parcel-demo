import os, json, datetime, re
from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase

# === Config ===
NEO4J_URI      = os.getenv("NEO4J_URI",      "neo4j+s://YOUR_AURA_OR_RENDER")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

app = Flask(__name__)
CORS(app)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def to_jsonable(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return o

def norm_pid(pid: str) -> str:
    """Remove all non-digits; preserve leading zeros."""
    pid = (pid or "").strip()
    digits = re.sub(r"\D+", "", pid)
    return digits or pid

def node_to_props(n):
    """Safely convert neo4j Node-like to a plain dict of JSON-safe values."""
    if n is None:
        return None
    # Most neo4j Node objects implement .keys() and .get()
    try:
        out = {}
        for k in n.keys():
            v = n.get(k)
            # Simple JSON-safe normalization
            if isinstance(v, (datetime.date, datetime.datetime)):
                v = v.isoformat()
            elif isinstance(v, (list, tuple)):
                v = [
                    (vv.isoformat() if isinstance(vv, (datetime.date, datetime.datetime)) else vv)
                    for vv in v
                ]
            out[str(k)] = v
        return out
    except Exception:
        # Fallback: last resort try dict() casting
        try:
            return dict(n)
        except Exception:
            return None

# ---------- Health ----------
@app.get("/api/v1/health")
def health():
    return jsonify({"ok": True})

# ---------- Helper: list parcel IDs (debug) ----------
@app.get("/api/v1/parcels")
def list_parcels():
    limit = int(request.args.get("limit", "100"))
    with driver.session() as ses:
        rows = ses.run("""
            MATCH (p:Parcel)
            RETURN coalesce(p.id,p.parcelId,p.PID,p.pid) AS id
            ORDER BY id
            LIMIT $limit
        """, limit=limit).data()
    return jsonify({"parcels": [r["id"] for r in rows if r.get("id")]})

# ---------- Shared FLEX MATCH (single-query) ----------
FLEX_MATCH = """
WITH $pid_raw AS pid_raw, $pid_dashless AS pid_dashless
MATCH (p:Parcel)
WHERE
  p.id IN [pid_raw, pid_dashless] OR
  p.parcelId IN [pid_raw, pid_dashless] OR
  p.PID IN [pid_raw, pid_dashless] OR
  p.pid IN [pid_raw, pid_dashless] OR
  replace(p.id, '-', '') = pid_dashless OR
  replace(coalesce(p.parcelId, ''), '-', '') = pid_dashless OR
  replace(coalesce(p.PID, ''), '-', '') = pid_dashless OR
  replace(coalesce(p.pid, ''), '-', '') = pid_dashless
"""

# ---------- Details ----------
DETAILS_FLEX = FLEX_MATCH + """
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
WITH p, collect(DISTINCT t) AS titles
OPTIONAL MATCH (p)-[:OWNED_BY]->(o:Owner)
WITH p, titles, collect(DISTINCT o) AS owners
OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
WITH p, titles, owners, collect(DISTINCT r) AS rrrs
OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
WITH p, titles, owners, rrrs, collect(DISTINCT z) AS zonings
OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
WITH p, titles, owners, rrrs, zonings, collect(DISTINCT sp) AS plans
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
RETURN p, titles, owners, rrrs, zonings, plans, collect(DISTINCT a) AS assessments
LIMIT 1
"""

@app.get("/api/v1/parcels/<pid>")
def parcel_details(pid):
    pid_raw = (pid or "").strip()
    pid_dashless = norm_pid(pid_raw)
    with driver.session() as ses:
        rec = ses.run(DETAILS_FLEX, pid_raw=pid_raw, pid_dashless=pid_dashless).single()
        if not rec or rec["p"] is None:
            app.logger.warning(f"Parcel not found for pid_raw='{pid_raw}', pid_dashless='{pid_dashless}'")
            return jsonify({"error": "not_found", "pid": pid_raw}), 404

        p           = rec["p"]
        titles      = rec["titles"]      or []
        owners      = rec["owners"]      or []
        rrrs        = rec["rrrs"]        or []
        zonings     = rec["zonings"]     or []
        plans       = rec["plans"]       or []
        assessments = rec["assessments"] or []

        # Build strictly JSON-safe payload
        parcel_dict = node_to_props(p) or {}
        payload = {
            "parcel": parcel_dict,
            "titles": [ node_to_props(t) for t in titles if t ],
            "owners": [ node_to_props(o) for o in owners if o ],
            "rrrs":   [ node_to_props(r) for r in rrrs if r ],
            "zonings": [ node_to_props(z) for z in zonings if z ],
            "plans":   [ node_to_props(sp) for sp in plans if sp ],
            "assessments": [ node_to_props(a) for a in assessments if a ],
        }

        payload["parcelId"]   = parcel_dict.get("id") or parcel_dict.get("parcelId") or parcel_dict.get("PID") or parcel_dict.get("pid")
        payload["title"]      = (payload["titles"][0] if payload["titles"] else None)
        payload["surveyPlan"] = (payload["plans"][0] if payload["plans"] else None)
        payload["assessment"] = (payload["assessments"][0] if payload["assessments"] else None)

        # Return explicitly via Response to apply to_jsonable to any dates (if any)
        return app.response_class(
            response=json.dumps(payload, default=to_jsonable),
            mimetype="application/json"
        )

# ---------- Graph ----------
GRAPH_FLEX = FLEX_MATCH + """
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
WITH p, collect(DISTINCT t) AS titles
OPTIONAL MATCH (p)-[:OWNED_BY]->(o:Owner)
WITH p, titles, collect(DISTINCT o) AS owners
OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
WITH p, titles, owners, collect(DISTINCT r) AS rrrs
OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
WITH p, titles, owners, rrrs, collect(DISTINCT z) AS zonings
OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
WITH p, titles, owners, rrrs, zonings, collect(DISTINCT sp) AS plans
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
RETURN p, titles, owners, rrrs, zonings, plans, collect(DISTINCT a) AS assessments
LIMIT 1
"""

@app.get("/api/v1/graph/parcel/<pid>")
def parcel_graph(pid):
    pid_raw = (pid or "").strip()
    pid_dashless = norm_pid(pid_raw)
    with driver.session() as ses:
        rec = ses.run(GRAPH_FLEX, pid_raw=pid_raw, pid_dashless=pid_dashless).single()
        if not rec or rec["p"] is None:
            app.logger.warning(f"Graph: parcel not found for pid_raw='{pid_raw}', pid_dashless='{pid_dashless}'")
            return jsonify({"nodes": [], "edges": []})

        p           = rec["p"]
        titles      = rec["titles"]      or []
        owners      = rec["owners"]      or []
        rrrs        = rec["rrrs"]        or []
        zonings     = rec["zonings"]     or []
        plans       = rec["plans"]       or []
        assessments = rec["assessments"] or []

        root_props = node_to_props(p) or {}
        root_id = (root_props.get("id") or root_props.get("parcelId") or root_props.get("PID") or root_props.get("pid"))
        nodes = [{"id": root_id, "type": "Parcel", "label": f"Parcel {root_id}"}]
        edges = []

        def add_node(n, typ, label_key="name"):
            """Return node id if added; skip nodes without any usable id/label."""
            props = node_to_props(n)
            if not props:
                return None
            nid = props.get("id") or props.get("number") or props.get("name") or props.get("value")
            if nid is None or str(nid).strip() == "":
                return None
            lbl = props.get(label_key) or props.get("number") or props.get("name") or props.get("value") or typ
            nodes.append({"id": str(nid), "type": typ, "label": str(lbl)})
            return str(nid)

        for t in titles:
            tid = add_node(t, "Title", "number")
            if tid: edges.append({"source": root_id, "target": tid, "type": "HAS_TITLE"})
        for o in owners:
            oid = add_node(o, "Owner", "name")
            if oid: edges.append({"source": root_id, "target": oid, "type": "OWNED_BY"})
        for r in rrrs:
            rid = add_node(r, "RRR", "type")
            if rid: edges.append({"source": root_id, "target": rid, "type": "HAS_RRR"})
        for z in zonings:
            zid = add_node(z, "Zoning", "name")
            if zid: edges.append({"source": root_id, "target": zid, "type":"HAS_ZONING"})
        for sp in plans:
            spid = add_node(sp, "SurveyPlan", "number")
            if spid: edges.append({"source": root_id, "target": spid, "type":"HAS_PLAN"})
        for a in assessments:
            aid = add_node(a, "Assessment", "value")
            if aid: edges.append({"source": root_id, "target": aid, "type":"HAS_ASSESSMENT"})

        return jsonify({"nodes": nodes, "edges": edges})
