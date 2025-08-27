// Clear existing data
MATCH (n) DETACH DELETE n;

// Create a sample parcel
CREATE (p:Parcel {parcelId: "012-345-678", legalDescription: "Lot 1, District Lot 1234, Plan 5678"});

// Title + owner
CREATE (t:Title {titleId: "T-1001", status: "Active"})
CREATE (o:Owner {ownerId: "O-2001", name: "Alice Example"})
CREATE (p)-[:HAS_TITLE]->(t)
CREATE (t)-[:OWNED_BY]->(o);

// Right / restriction / responsibility (RRR)
CREATE (r:RRR {rrrId: "R-3001", type: "Mortgage", status: "Active"})
CREATE (p)-[:HAS_RRR]->(r);

// Survey plan
CREATE (sp:SurveyPlan {planId: "SP-4001", description: "Registered Survey Plan"})
CREATE (p)-[:HAS_PLAN]->(sp);

// Assessment
CREATE (a:Assessment {assessmentId: "A-5001", year: 2024, value: 850000})
CREATE (p)-[:HAS_ASSESSMENT]->(a);

// Zoning
CREATE (z:Zoning {zoneId: "Z-6001", zoneType: "Residential"})
CREATE (p)-[:HAS_ZONING]->(z);

// Return parcel with connected nodes
MATCH (p:Parcel {parcelId: "012-345-678"})
OPTIONAL MATCH (p)-[r]-(n)
RETURN p, collect(r), collect(n);
