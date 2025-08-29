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

# ---------- Parcel details (single-query flexible match) ----------
DETAILS_FLEX = """
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
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
OPTIONAL MATCH (p)-[:OWNED_BY]->(o:Owner)
OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
RETURN p,
       collect(DISTINCT t)  AS titles,
       collect(DISTINCT o)  AS owners,
       collect(DISTINCT r)  AS rrrs,
       z, sp, a
LIMIT 1
"""

@app.get("/api/v1/parcels/<pid>")
def parcel_details(pid):
    pid_raw = (pid or "").strip()
    pid_dashless = norm_pid(pid_raw)
    with driver.session() as ses:
        rec = ses.run(DETAILS_FLEX, pid_raw=pid_raw, pid_dashless=pid_dashless).single()
        if not rec:
            app.logger.warning(f"Parcel not found for pid_raw='{pid_raw}', pid_dashless='{pid_dashless}'")
            return jsonify({"error": "not_found", "pid": pid_raw}), 404

        p, titles, owners, rrrs, z, sp, a = rec["p"], rec["titles"], rec["owners"], rec["rrrs"], rec["z"], rec["sp"], rec["a"]
        def node_props(n): return dict(n) if n else {}

        payload = {
            "parcel": node_props(p) if p else None,
            "titles": [ node_props(t) for t in titles if t ],
            "owners": [ node_props(o) for o in owners if o ],
            "rrrs":   [ node_props(r) for r in rrrs if r ],
            "zonings": [ node_props(z) ] if z else [],
            "plans":   [ node_props(sp) ] if sp else [],
            "assessments": [ node_props(a) ] if a else [],
        }
        parcel_props = payload["parcel"] or {}
        payload["parcelId"]   = parcel_props.get("id") or parcel_props.get("parcelId") or parcel_props.get("PID") or parcel_props.get("pid")
        payload["title"]      = payload["titles"][0] if payload["titles"] else None
        payload["surveyPlan"] = payload["plans"][0] if payload["plans"] else None
        payload["assessment"] = payload["assessments"][0] if payload["assessments"] else None

        return app.response_class(
            response=json.dumps(payload, default=to_jsonable),
            mimetype="application/json"
        )

# ---------- Parcel graph (single-query flexible match) ----------
GRAPH_FLEX = """
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
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
OPTIONAL MATCH (p)-[:OWNED_BY]->(o:Owner)
OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
RETURN p,
       collect(DISTINCT t) AS titles,
       collect(DISTINCT o) AS owners,
       collect(DISTINCT r) AS rrrs,
       z, sp, a
LIMIT 1
"""

@app.get("/api/v1/graph/parcel/<pid>")
def parcel_graph(pid):
    pid_raw = (pid or "").strip()
    pid_dashless = norm_pid(pid_raw)
    with driver.session() as ses:
        rec = ses.run(GRAPH_FLEX, pid_raw=pid_raw, pid_dashless=pid_dashless).single()
        if not rec:
            app.logger.warning(f"Graph: parcel not found for pid_raw='{pid_raw}', pid_dashless='{pid_dashless}'")
            return jsonify({"nodes": [], "edges": []})

        p = rec["p"]
        titles, owners, rrrs, z, sp, a = rec["titles"], rec["owners"], rec["rrrs"], rec["z"], rec["sp"], rec["a"]

        root_id = (p.get("id") or p.get("parcelId") or p.get("PID") or p.get("pid"))
        nodes = [{"id": root_id, "type": "Parcel", "label": f"Parcel {root_id}"}]
        edges = []

        def add_node(n, typ, label_key="name"):
            if not n: return None
            nid = n.get("id") or n.get("number") or n.get("name") or n.get("value")
            lbl = n.get(label_key) or n.get("number") or n.get("name") or n.get("value") or typ
            nodes.append({"id": str(nid), "type": typ, "label": str(lbl)})
            return str(nid)

        for t in titles or []:
            tid = add_node(t, "Title", "number")
            if tid: edges.append({"source": root_id, "target": tid, "type": "HAS_TITLE"})
        for o in owners or []:
            oid = add_node(o, "Owner", "name")
            if oid: edges.append({"source": root_id, "target": oid, "type": "OWNED_BY"})
        for r in rrrs or []:
            rid = add_node(r, "RRR", "type")
            if rid: edges.append({"source": root_id, "target": rid, "type": "HAS_RRR"})
        if z:
            zid = add_node(z, "Zoning", "name")
            if zid: edges.append({"source": root_id, "target": zid, "type":"HAS_ZONING"})
        if sp:
            spid = add_node(sp, "SurveyPlan", "number")
            if spid: edges.append({"source": root_id, "target": spid, "type":"HAS_PLAN"})
        if a:
            aid = add_node(a, "Assessment", "value")
            if aid: edges.append({"source": root_id, "target": aid, "type":"HAS_ASSESSMENT"})

        return jsonify({"nodes": nodes, "edges": edges})
