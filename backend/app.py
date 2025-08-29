import os, json, datetime
from flask import Flask, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase

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

DETAILS_CYPHER = """
MATCH (p:Parcel {id: $pid})
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
OPTIONAL MATCH (p)-[:OWNED_BY]->(o:Owner)
OPTIONAL MATCH (p)-[:HAS_RRR]->(r:RRR)
OPTIONAL MATCH (p)-[:HAS_ZONING]->(z:Zoning)
OPTIONAL MATCH (p)-[:HAS_PLAN]->(sp:SurveyPlan)
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
RETURN p, t, collect(DISTINCT o) as owners, collect(DISTINCT r) as rrrs, z, sp, a
"""

GRAPH_CYPHER = """
MATCH (p:Parcel {id:$pid})
OPTIONAL MATCH (p)-[e1:HAS_TITLE]->(t:Title)
OPTIONAL MATCH (p)-[e2:OWNED_BY]->(o:Owner)
OPTIONAL MATCH (p)-[e3:HAS_RRR]->(r:RRR)
OPTIONAL MATCH (p)-[e4:HAS_ZONING]->(z:Zoning)
OPTIONAL MATCH (p)-[e5:HAS_PLAN]->(sp:SurveyPlan)
OPTIONAL MATCH (p)-[e6:HAS_ASSESSMENT]->(a:Assessment)
RETURN p, collect(DISTINCT t) as titles, collect(DISTINCT o) as owners,
       collect(DISTINCT r) as rrrs, z, sp, a
"""

@app.get("/api/v1/parcels/<pid>")
def parcel_details(pid):
    pid = (pid or "").strip()
    with driver.session() as ses:
        rec = ses.run(DETAILS_CYPHER, pid=pid).single()
        if not rec:
            return jsonify({"error":"not_found", "pid": pid}), 404

        p, t, owners, rrrs, z, sp, a = rec["p"], rec["t"], rec["owners"], rec["rrrs"], rec["z"], rec["sp"], rec["a"]

        def node_props(n): return dict(n) if n else {}

        payload = {
            "parcel": node_props(p) if p else None,
            "titles": [ node_props(t) ] if t else [],
            "owners": [ node_props(o) for o in owners ],
            "rrrs":   [ node_props(r) for r in rrrs ],
            "zonings": [ node_props(z) ] if z else [],
            "plans":   [ node_props(sp) ] if sp else [],
            "assessments": [ node_props(a) ] if a else [],
        }

        parcel_props = payload["parcel"] or {}
        payload["parcelId"]   = parcel_props.get("id") or parcel_props.get("parcelId")
        payload["title"]      = payload["titles"][0] if payload["titles"] else None
        payload["surveyPlan"] = payload["plans"][0] if payload["plans"] else None
        payload["assessment"] = payload["assessments"][0] if payload["assessments"] else None

        return app.response_class(
            response=json.dumps(payload, default=to_jsonable),
            mimetype="application/json"
        )

@app.get("/api/v1/graph/parcel/<pid>")
def parcel_graph(pid):
    pid = (pid or "").strip()
    with driver.session() as ses:
        rec = ses.run(GRAPH_CYPHER, pid=pid).single()
        if not rec:
            return jsonify({"nodes":[], "edges":[]})
        p = rec["p"]
        titles, owners, rrrs, z, sp, a = rec["titles"], rec["owners"], rec["rrrs"], rec["z"], rec["sp"], rec["a"]

        nodes = [{"id": p.get("id"), "type":"Parcel", "label": f"Parcel {p.get('id')}"}]
        edges = []

        def add_node(n, typ, label_key="name"):
            if not n: return None
            nid = n.get("id") or n.get("number") or n.get("name")
            lbl = n.get(label_key) or n.get("number") or n.get("name") or typ
            nodes.append({"id": str(nid), "type": typ, "label": lbl})
            return str(nid)

        for t in titles:
            tid = add_node(t, "Title", "number")
            if tid: edges.append({"source": p.get("id"), "target": tid, "type": "HAS_TITLE"})
        for o in owners:
            oid = add_node(o, "Owner", "name")
            if oid: edges.append({"source": p.get("id"), "target": oid, "type": "OWNED_BY"})
        for r in rrrs:
            rid = add_node(r, "RRR", "type")
            if rid: edges.append({"source": p.get("id"), "target": rid, "type": "HAS_RRR"})
        if z:
            zid = add_node(z, "Zoning", "name")
            if zid: edges.append({"source": p.get("id"), "target": zid, "type":"HAS_ZONING"})
        if sp:
            spid = add_node(sp, "SurveyPlan", "number")
            if spid: edges.append({"source": p.get("id"), "target": spid, "type":"HAS_PLAN"})
        if a:
            aid = add_node(a, "Assessment", "value")
            if aid: edges.append({"source": p.get("id"), "target": aid, "type":"HAS_ASSESSMENT"})

        return jsonify({"nodes": nodes, "edges": edges})

@app.get("/api/v1/health")
def health():
    return jsonify({"ok": True})
