import os
from flask import Flask, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

app = Flask(__name__)
CORS(app)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

CYHER_PARCEL_VIEW = """
MATCH (p:Parcel {parcelId: $parcelId})
OPTIONAL MATCH (p)-[:HAS_TITLE]->(t:Title)
OPTIONAL MATCH (t)-[:HAS_OWNER]->(o:Owner)
OPTIONAL MATCH (t)-[:ENCUMBERED_BY]->(r:RRR)
OPTIONAL MATCH (p)-[:AFFECTED_BY]->(sp:SurveyPlan)
OPTIONAL MATCH (p)-[:HAS_ASSESSMENT]->(a:Assessment)
OPTIONAL MATCH (p)-[:ZONED_AS]->(z:Zoning)
WITH p, t,
     collect(DISTINCT {ownerKey: o.ownerKey, name: o.name, type: o.type}) AS owners,
     collect(DISTINCT {rrrId: r.rrrId, category: r.category, type: r.type,
                       status: r.status, effectiveFrom: r.effectiveFrom,
                       effectiveTo: r.effectiveTo, amount: r.amount, currency: r.currency}) AS rrrs,
     collect(DISTINCT sp.planNo) AS surveyPlans,
     head(collect(DISTINCT {year: a.year, totalValue: a.totalValue,
                            landValue: a.landValue, improValue: a.improValue})) AS assessment,
     head(collect(DISTINCT {code: z.code, bylaw: z.bylaw})) AS zoning
RETURN {
  parcelId: p.parcelId,
  legalDesc: p.legalDesc,
  civicAddress: p.civicAddress,
  municipality: p.municipality,
  title: CASE WHEN t IS NULL THEN null ELSE {titleNumber: t.titleNumber, status: t.status, issueDate: toString(t.issueDate)} END,
  owners: owners,
  rrr: [r IN rrrs WHERE r.rrrId IS NOT NULL],
  surveyPlans: [sp IN surveyPlans WHERE sp IS NOT NULL],
  assessment: assessment,
  zoning: zoning
} AS view
"""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/parcels/<parcel_id>")
def parcel_view(parcel_id):
    with driver.session() as session:
        rec = session.run(CYHER_PARCEL_VIEW, parcelId=parcel_id).single()
        if not rec:
            return jsonify({"error": "not found", "parcelId": parcel_id}), 404
        return jsonify(rec["view"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
