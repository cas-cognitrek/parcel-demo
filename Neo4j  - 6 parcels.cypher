MATCH (n) DETACH DELETE n;
// =====================================================
// Parcel Demo — Multi-Parcel Seed (6 parcels)
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

// ---------- Helper: upsert a parcel “bundle” ----------
// Usage pattern repeated below: MERGE nodes, then MERGE rels

// ========== Parcel A: Single owner, active mortgage ==========
MERGE (pA:Parcel {parcelId: "012-345-101"})
  ON CREATE SET pA.legalDescription = "Lot 1, DL 1001, Plan 9001";
MERGE (tA:Title {titleId: "T-1001"}) ON CREATE SET tA.status = "Active";
MERGE (oA:Owner {ownerId: "O-2001"}) ON CREATE SET oA.name = "Alice Example";
MERGE (rA:RRR {rrrId: "R-3001"})
  ON CREATE SET rA.type = "Mortgage", rA.status = "Active", rA.holder = "Bank of Example";
MERGE (spA:SurveyPlan {planId: "SP-4001"}) ON CREATE SET spA.description = "Registered Survey Plan A";
MERGE (aA:Assessment {assessmentId: "A-5001"}) ON CREATE SET aA.year = 2025, aA.value = 870000;
MERGE (zA:Zoning {zoneId: "Z-6001"}) ON CREATE SET zA.zoneType = "Residential";

MERGE (pA)-[:HAS_TITLE]->(tA)
MERGE (tA)-[:OWNED_BY]->(oA)
MERGE (pA)-[:HAS_RRR]->(rA)
MERGE (pA)-[:HAS_PLAN]->(spA)
MERGE (pA)-[:HAS_ASSESSMENT]->(aA)
MERGE (pA)-[:HAS_ZONING]->(zA);

// ========== Parcel B: Joint owners (50/50), no mortgage ==========
MERGE (pB:Parcel {parcelId: "012-345-102"})
  ON CREATE SET pB.legalDescription = "Lot 2, DL 1002, Plan 9002";
MERGE (tB:Title {titleId: "T-1002"}) ON CREATE SET tB.status = "Active";
MERGE (oB1:Owner {ownerId: "O-2002"}) ON CREATE SET oB1.name = "Bob Example";
MERGE (oB2:Owner {ownerId: "O-2003"}) ON CREATE SET oB2.name = "Carol Example";
MERGE (spB:SurveyPlan {planId: "SP-4002"}) ON CREATE SET spB.description = "Registered Survey Plan B";
MERGE (aB:Assessment {assessmentId: "A-5002"}) ON CREATE SET aB.year = 2025, aB.value = 640000;
MERGE (zB:Zoning {zoneId: "Z-6002"}) ON CREATE SET zB.zoneType = "Residential";

MERGE (pB)-[:HAS_TITLE]->(tB)
MERGE (tB)-[:OWNED_BY {share:"50%"}]->(oB1)
MERGE (tB)-[:OWNED_BY {share:"50%"}]->(oB2)
MERGE (pB)-[:HAS_PLAN]->(spB)
MERGE (pB)-[:HAS_ASSESSMENT]->(aB)
MERGE (pB)-[:HAS_ZONING]->(zB);

// ========== Parcel C: Company owner, expired mortgage ==========
MERGE (pC:Parcel {parcelId: "012-345-103"})
  ON CREATE SET pC.legalDescription = "Lot 3, DL 1003, Plan 9003";
MERGE (tC:Title {titleId: "T-1003"}) ON CREATE SET tC.status = "Active";
MERGE (oC:Owner {ownerId: "O-2004"}) ON CREATE SET oC.name = "Example Holdings Ltd.", oC.type = "Company";
MERGE (rC1:RRR {rrrId: "R-3002"})
  ON CREATE SET rC1.type = "Mortgage", rC1.status = "Expired", rC1.holder = "Legacy Bank", rC1.expiredOn = date("2022-12-31");
MERGE (spC:SurveyPlan {planId: "SP-4003"}) ON CREATE SET spC.description = "Registered Survey Plan C";
MERGE (aC:Assessment {assessmentId: "A-5003"}) ON CREATE SET aC.year = 2024, aC.value = 1200000;
MERGE (zC:Zoning {zoneId: "Z-6003"}) ON CREATE SET zC.zoneType = "Commercial";

MERGE (pC)-[:HAS_TITLE]->(tC)
MERGE (tC)-[:OWNED_BY]->(oC)
MERGE (pC)-[:HAS_RRR]->(rC1)
MERGE (pC)-[:HAS_PLAN]->(spC)
MERGE (pC)-[:HAS_ASSESSMENT]->(aC)
MERGE (pC)-[:HAS_ZONING]->(zC);

// ========== Parcel D: Long-term lease (RRR: Lease) ==========
MERGE (pD:Parcel {parcelId: "012-345-104"})
  ON CREATE SET pD.legalDescription = "Lot 4, DL 1004, Plan 9004";
MERGE (tD:Title {titleId: "T-1004"}) ON CREATE SET tD.status = "Active";
MERGE (oD:Owner {ownerId: "O-2005"}) ON CREATE SET oD.name = "Dana Example";
MERGE (lesseeD:Owner {ownerId: "O-2006"}) ON CREATE SET lesseeD.name = "Tenant Co.", lesseeD.type = "Company";
MERGE (rD:RRR {rrrId: "R-3003"})
  ON CREATE SET rD.type = "Lease", rD.status = "Active", rD.termYears = 20, rD.commencement = date("2020-01-01");
MERGE (spD:SurveyPlan {planId: "SP-4004"}) ON CREATE SET spD.description = "Registered Survey Plan D";
MERGE (aD:Assessment {assessmentId: "A-5004"}) ON CREATE SET aD.year = 2025, aD.value = 720000;
MERGE (zD:Zoning {zoneId: "Z-6004"}) ON CREATE SET zD.zoneType = "Industrial";

MERGE (pD)-[:HAS_TITLE]->(tD)
MERGE (tD)-[:OWNED_BY]->(oD)
MERGE (pD)-[:HAS_RRR]->(rD)
MERGE (rD)-[:LESSEE]->(lesseeD)          // example sub-relationship for lease
MERGE (pD)-[:HAS_PLAN]->(spD)
MERGE (pD)-[:HAS_ASSESSMENT]->(aD)
MERGE (pD)-[:HAS_ZONING]->(zD);

// ========== Parcel E: Easement (RRR: Easement), Agriculture ==========
MERGE (pE:Parcel {parcelId: "012-345-105"})
  ON CREATE SET pE.legalDescription = "Lot 5, DL 1005, Plan 9005";
MERGE (tE:Title {titleId: "T-1005"}) ON CREATE SET tE.status = "Active";
MERGE (oE:Owner {ownerId: "O-2007"}) ON CREATE SET oE.name = "Evan Example";
MERGE (rE:RRR {rrrId: "R-3004"})
  ON CREATE SET rE.type = "Easement", rE.status = "Active", rE.purpose = "Access/ROW";
MERGE (spE:SurveyPlan {planId: "SP-4005"}) ON CREATE SET spE.description = "Registered Survey Plan E";
MERGE (aE:Assessment {assessmentId: "A-5005"}) ON CREATE SET aE.year = 2025, aE.value = 510000;
MERGE (zE:Zoning {zoneId: "Z-6005"}) ON CREATE SET zE.zoneType = "Agricultural";

MERGE (pE)-[:HAS_TITLE]->(tE)
MERGE (tE)-[:OWNED_BY]->(oE)
MERGE (pE)-[:HAS_RRR]->(rE)
MERGE (pE)-[:HAS_PLAN]->(spE)
MERGE (pE)-[:HAS_ASSESSMENT]->(aE)
MERGE (pE)-[:HAS_ZONING]->(zE);

// ========== Parcel F: Mixed-use zoning, assessment dip ==========
MERGE (pF:Parcel {parcelId: "012-345-106"})
  ON CREATE SET pF.legalDescription = "Lot 6, DL 1006, Plan 9006";
MERGE (tF:Title {titleId: "T-1006"}) ON CREATE SET tF.status = "Active";
MERGE (oF:Owner {ownerId: "O-2008"}) ON CREATE SET oF.name = "Fiona Example";
MERGE (rF:RRR {rrrId: "R-3005"})
  ON CREATE SET rF.type = "Caveat", rF.status = "Active", rF.note = "Caveat by municipality";
MERGE (spF:SurveyPlan {planId: "SP-4006"}) ON CREATE SET spF.description = "Registered Survey Plan F";
MERGE (aF:Assessment {assessmentId: "A-5006"}) ON CREATE SET aF.year = 2024, aF.value = 980000;
MERGE (zF:Zoning {zoneId: "Z-6006"}) ON CREATE SET zF.zoneType = "MixedUse";

MERGE (pF)-[:HAS_TITLE]->(tF)
MERGE (tF)-[:OWNED_BY]->(oF)
MERGE (pF)-[:HAS_RRR]->(rF)
MERGE (pF)-[:HAS_PLAN]->(spF)
MERGE (pF)-[:HAS_ASSESSMENT]->(aF)
MERGE (pF)-[:HAS_ZONING]->(zF);

// ---------- Verify ----------
MATCH (p:Parcel)
OPTIONAL MATCH (p)-[rel]-(n)
RETURN p, rel, n
ORDER BY p.parcelId;
