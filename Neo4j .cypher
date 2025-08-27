MATCH (n) DETACH DELETE n;
// -----------------------------
// 0) OPTIONAL: upgrade unlabeled parcel
//    If a node exists with parcelId but no :Parcel label, add the label
// -----------------------------
MATCH (n {parcelId: "012-345-678"})
WHERE NOT n:Parcel
SET n:Parcel;

// -----------------------------
// 1) Constraints (safe to re-run)
// -----------------------------
CREATE CONSTRAINT parcel_id IF NOT EXISTS
FOR (p:Parcel) REQUIRE p.parcelId IS UNIQUE;

CREATE CONSTRAINT title_id IF NOT EXISTS
FOR (t:Title) REQUIRE t.titleId IS UNIQUE;

CREATE CONSTRAINT owner_id IF NOT EXISTS
FOR (o:Owner) REQUIRE o.ownerId IS UNIQUE;

CREATE CONSTRAINT rrr_id IF NOT EXISTS
FOR (r:RRR) REQUIRE r.rrrId IS UNIQUE;

CREATE CONSTRAINT plan_id IF NOT EXISTS
FOR (sp:SurveyPlan) REQUIRE sp.planId IS UNIQUE;

CREATE CONSTRAINT assess_id IF NOT EXISTS
FOR (a:Assessment) REQUIRE a.assessmentId IS UNIQUE;

CREATE CONSTRAINT zone_id IF NOT EXISTS
FOR (z:Zoning) REQUIRE z.zoneId IS UNIQUE;

// -----------------------------
// 2) Upsert the parcel + related nodes
//    (MERGE ensures no duplicates; SET only on create)
// -----------------------------
MERGE (p:Parcel {parcelId: "012-345-678"})
  ON CREATE SET p.legalDescription = "Lot 1, District Lot 1234, Plan 5678";

MERGE (t:Title {titleId: "T-1001"})
  ON CREATE SET t.status = "Active";

MERGE (o:Owner {ownerId: "O-2001"})
  ON CREATE SET o.name = "Alice Example";

MERGE (r:RRR {rrrId: "R-3001"})
  ON CREATE SET r.type = "Mortgage", r.status = "Active";

MERGE (sp:SurveyPlan {planId: "SP-4001"})
  ON CREATE SET sp.description = "Registered Survey Plan";

MERGE (a:Assessment {assessmentId: "A-5001"})
  ON CREATE SET a.year = 2024, a.value = 850000;

MERGE (z:Zoning {zoneId: "Z-6001"})
  ON CREATE SET z.zoneType = "Residential";

// -----------------------------
// 3) Attach relationships to the SAME parcel
// -----------------------------
MERGE (p)-[:HAS_TITLE]->(t)
MERGE (t)-[:OWNED_BY]->(o)
MERGE (p)-[:HAS_RRR]->(r)
MERGE (p)-[:HAS_PLAN]->(sp)
MERGE (p)-[:HAS_ASSESSMENT]->(a)
MERGE (p)-[:HAS_ZONING]->(z);

// -----------------------------
// 4) Return for visual check
// -----------------------------
MATCH (p:Parcel {parcelId: "012-345-678"})
OPTIONAL MATCH (p)-[rel]-(n)
RETURN p, rel, n;
