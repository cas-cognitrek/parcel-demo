MATCH (n) DETACH DELETE n;
////////////////////////////////////////////////////////////////////////
// DEMO SEED — 9 parcels with full labels & relationships
// Parcels: 012-345-101 … 012-345-109
////////////////////////////////////////////////////////////////////////

/* Optional: wipe previous demo data
MATCH (n) DETACH DELETE n;
*/

/* Constraints (safe to re-run) */
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Parcel)      REQUIRE p.parcelId       IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Title)       REQUIRE t.titleId        IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Owner)       REQUIRE o.ownerId        IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:RRR)         REQUIRE r.rrrId          IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (sp:SurveyPlan) REQUIRE sp.planId        IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Assessment)  REQUIRE a.assessmentId   IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (z:Zoning)      REQUIRE z.zoneId         IS UNIQUE;

/* Seed 9 parcels with a consistent “star” around each */
UNWIND range(101, 109) AS i
WITH
  i,
  "012-345-" + i               AS pid,
  "T-" + i                     AS tid,
  "O-" + i                     AS oid,
  "R-" + i                     AS rid,
  "SP-" + i                    AS spid,
  "A-" + i                     AS aid,
  "Z-" + i                     AS zid,
  CASE WHEN i % 2 = 0 THEN "Mortgage" ELSE "Lease" END AS rrrType,
  CASE WHEN i % 3 = 0 THEN "Commercial" ELSE "Residential" END AS zoneType

// Parcel
MERGE (p:Parcel {parcelId: pid})
  ON CREATE SET
    p.legalDescription = "Lot " + i + ", District Lot 1234, Plan " + (5600 + i),
    p.createdAt = datetime()

// Title
MERGE (t:Title {titleId: tid})
  ON CREATE SET t.status = "Active", t.issueDate = date("2024-07-01")

// Owner
MERGE (o:Owner {ownerId: oid})
  ON CREATE SET o.name = "Owner " + i

// RRR (e.g., Mortgage / Lease)
MERGE (r:RRR {rrrId: rid})
  ON CREATE SET r.type = rrrType, r.status = "Registered"

// Survey Plan
MERGE (sp:SurveyPlan {planId: spid})
  ON CREATE SET sp.description = "Registered Survey Plan " + spid

// Assessment
MERGE (a:Assessment {assessmentId: aid})
  ON CREATE SET a.year = 2025, a.value = 500000 + (i * 10000)

// Zoning
MERGE (z:Zoning {zoneId: zid})
  ON CREATE SET z.zoneType = zoneType

// Relationships (idempotent)
MERGE (p)-[:HAS_TITLE]->(t)
MERGE (t)-[:OWNED_BY]->(o)
MERGE (p)-[:HAS_RRR]->(r)
MERGE (p)-[:HAS_PLAN]->(sp)
MERGE (p)-[:HAS_ASSESSMENT]->(a)
MERGE (p)-[:HAS_ZONING]->(z);

////////////////////////////////////////////////////////////////////////
// Quick sanity checks
////////////////////////////////////////////////////////////////////////

/* Count by label */
MATCH (n) RETURN labels(n) AS label, count(*) AS n ORDER BY n DESC;

/* See the star for one parcel */
MATCH (p:Parcel {parcelId:"012-345-101"})-[r]-(x) RETURN p,r,x;

/* Relationship types present */
MATCH ()-[r]->() RETURN type(r) AS relType, count(*) AS n ORDER BY n DESC;
