MATCH (n) DETACH DELETE n;
// =====================================================
// Parcel Demo — Multi-Parcel Seed (9 parcels)
// Safe to re-run (MERGE + IF NOT EXISTS)
// =====================================================

// --- OPTIONAL: wipe graph for a clean slate ---
// MATCH (n) DETACH DELETE n;

// ---------- Constraints (one-time) ----------
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

// -----------------------------------------------------
// Parcels 101–106 (from earlier script)
// -----------------------------------------------------
// ... keep your existing Parcel A–F blocks here ...

// -----------------------------------------------------
// Parcel 107: Strata/condo, 4 owners (25% each)
// -----------------------------------------------------
MERGE (p107:Parcel {parcelId: "012-345-107"})
  ON CREATE SET p107.legalDescription = "Strata Lot 7, DL 1007, Plan 9007";
MERGE (t107:Title {titleId: "T-1007"}) ON CREATE SET t107.status = "Active";

MERGE (o107a:Owner {ownerId: "O-2009"}) ON CREATE SET o107a.name = "George Example";
MERGE (o107b:Owner {ownerId: "O-2010"}) ON CREATE SET o107b.name = "Hannah Example";
MERGE (o107c:Owner {ownerId: "O-2011"}) ON CREATE SET o107c.name = "Irene Example";
MERGE (o107d:Owner {ownerId: "O-2012"}) ON CREATE SET o107d.name = "Jack Example";

MERGE (sp107:SurveyPlan {planId: "SP-4007"}) ON CREATE SET sp107.description = "Strata Plan 4007";
MERGE (a107:Assessment {assessmentId: "A-5007"}) ON CREATE SET a107.year = 2025, a107.value = 450000;
MERGE (z107:Zoning {zoneId: "Z-6007"}) ON CREATE SET z107.zoneType = "MultiFamily";

MERGE (p107)-[:HAS_TITLE]->(t107)
MERGE (t107)-[:OWNED_BY {share:"25%"}]->(o107a)
MERGE (t107)-[:OWNED_BY {share:"25%"}]->(o107b)
MERGE (t107)-[:OWNED_BY {share:"25%"}]->(o107c)
MERGE (t107)-[:OWNED_BY {share:"25%"}]->(o107d)
MERGE (p107)-[:HAS_PLAN]->(sp107)
MERGE (p107)-[:HAS_ASSESSMENT]->(a107)
MERGE (p107)-[:HAS_ZONING]->(z107);

// -----------------------------------------------------
// Parcel 108: Government-owned (Crown Land)
// -----------------------------------------------------
MERGE (p108:Parcel {parcelId: "012-345-108"})
  ON CREATE SET p108.legalDescription = "Parcel 8, Crown Land, DL 1008, Plan 9008";
MERGE (t108:Title {titleId: "T-1008"}) ON CREATE SET t108.status = "Active";
MERGE (o108:Owner {ownerId: "O-2013"})
  ON CREATE SET o108.name = "Province of British Columbia", o108.type = "Government";

MERGE (sp108:SurveyPlan {planId: "SP-4008"}) ON CREATE SET sp108.description = "Crown Survey Plan 4008";
MERGE (a108:Assessment {assessmentId: "A-5008"}) ON CREATE SET a108.year = 2025, a108.value = 0; // exempt
MERGE (z108:Zoning {zoneId: "Z-6008"}) ON CREATE SET z108.zoneType = "Crown";

MERGE (p108)-[:HAS_TITLE]->(t108)
MERGE (t108)-[:OWNED_BY]->(o108)
MERGE (p108)-[:HAS_PLAN]->(sp108)
MERGE (p108)-[:HAS_ASSESSMENT]->(a108)
MERGE (p108)-[:HAS_ZONING]->(z108);

// -----------------------------------------------------
// Parcel 109: Vacant lot, no assessment or zoning
// -----------------------------------------------------
MERGE (p109:Parcel {parcelId: "012-345-109"})
  ON CREATE SET p109.legalDescription = "Vacant Lot 9, DL 1009, Plan 9009";
MERGE (t109:Title {titleId: "T-1009"}) ON CREATE SET t109.status = "Active";
MERGE (o109:Owner {ownerId: "O-2014"}) ON CREATE SET o109.name = "Karen Example";

MERGE (sp109:SurveyPlan {planId: "SP-4009"}) ON CREATE SET sp109.description = "Survey Plan 4009";

MERGE (p109)-[:HAS_TITLE]->(t109)
MERGE (t109)-[:OWNED_BY]->(o109)
MERGE (p109)-[:HAS_PLAN]->(sp109);

// No RRR, no assessment, no zoning for vacant lot

// -----------------------------------------------------
// Verify
// -----------------------------------------------------
MATCH (p:Parcel)
RETURN p.parcelId, labels(p), p.legalDescription
ORDER BY p.parcelId;
