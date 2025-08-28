// Clean slate
MATCH (n) DETACH DELETE n;

// ---------- Base data ----------
WITH
  [
    {id:'012-345-101', legal:'Lot 1, District Lot 1234, Plan 5678'},
    {id:'012-345-102', legal:'Lot 2, District Lot 1234, Plan 5678'},
    {id:'012-345-103', legal:'Lot 3, District Lot 1234, Plan 5678'},
    {id:'012-345-104', legal:'Lot 4, District Lot 1234, Plan 5678'},
    {id:'012-345-105', legal:'Lot 5, District Lot 1234, Plan 5678'},
    {id:'012-345-106', legal:'Lot 6, District Lot 1234, Plan 5678'},
    {id:'012-345-107', legal:'Lot 7, District Lot 1234, Plan 5678'},
    {id:'012-345-108', legal:'Lot 8, District Lot 1234, Plan 5678'},
    {id:'012-345-109', legal:'Lot 9, District Lot 1234, Plan 5678'}
  ] AS parcels,
  ['Alice Example','Bob Example','Hank Example'] AS ownerNames,
  [
    {zoneId:'Z-6001', zoneType:'Residential'},
    {zoneId:'Z-6002', zoneType:'Commercial'}
  ] AS zones,
  [
    {rrrId:'R-3001', type:'Right of Way', description:'Registered right of way'},
    {rrrId:'R-3002', type:'Easement',     description:'Utility easement'}
  ] AS rrrs

// ---------- Dictionaries (Owners, Zoning, RRRs) ----------
UNWIND ownerNames AS ownerName
MERGE (o:Owner {name: ownerName})
  ON CREATE SET o.displayLabel = 'Owner: ' + ownerName
WITH parcels, zones, rrrs
UNWIND zones AS z
MERGE (zn:Zoning {zoneId: z.zoneId})
  ON CREATE SET zn.zoneType = z.zoneType,
                zn.displayLabel = 'Zoning ' + z.zoneId
WITH parcels, rrrs
UNWIND rrrs AS r
MERGE (rr:RRR {rrrId: r.rrrId})
  ON CREATE SET rr.type = r.type,
                rr.description = r.description,
                rr.displayLabel = 'RRR ' + r.rrrId

// ---------- Parcels ----------
WITH parcels
UNWIND parcels AS row
MERGE (p:Parcel {parcelId: row.id})
  ON CREATE SET
    p.legalDescription = row.legal,
    p.name            = 'Parcel ' + row.id,
    p.displayLabel    = p.name
  ON MATCH SET
    p.legalDescription = row.legal,
    p.name            = 'Parcel ' + row.id,
    p.displayLabel    = p.name

// ---------- Per-parcel wiring ----------
WITH range(1,9) AS idx
UNWIND idx AS i
MATCH (p:Parcel {parcelId: '012-345-10' + toString(i)})
WITH
  p, i,
  CASE WHEN i % 3 = 1 THEN 'Alice Example'
       WHEN i % 3 = 2 THEN 'Bob Example'
       ELSE 'Hank Example' END AS ownerName,
  CASE WHEN i % 2 = 1 THEN 'Z-6001' ELSE 'Z-6002' END AS zoneId,
  CASE WHEN i % 2 = 1 THEN 'R-3001' ELSE 'R-3002' END AS rrrId

// Title
MERGE (t:Title {titleId: 'T-10' + toString(i)})
  ON CREATE SET t.status = CASE WHEN i % 2 = 0 THEN 'Inactive' ELSE 'Active' END,
                t.issueDate = date('2024-07-01'),
                t.displayLabel = 'Title T-10' + toString(i)
MERGE (p)-[:HAS_TITLE]->(t)

// Owner
WITH p, i, ownerName, zoneId, rrrId, t
MATCH (o:Owner {name: ownerName})
MERGE (t)-[:OWNED_BY]->(o)

// Assessment
WITH p, i, ownerName, zoneId, rrrId
MERGE (a:Assessment {assessmentId: 'A-50' + toString(i)})
  ON CREATE SET a.year = 2025,
                a.value = 700000 + i * 25000,
                a.displayLabel = 'Assessment A-50' + toString(i)
MERGE (p)-[:HAS_ASSESSMENT]->(a)

// Survey Plan
WITH p, i, ownerName, zoneId, rrrId
MERGE (sp:SurveyPlan {planId: 'SP-20' + toString(i)})
  ON CREATE SET sp.description = 'Survey Plan ' + toString(i),
                sp.displayLabel = 'Plan SP-20' + toString(i)
MERGE (p)-[:HAS_PLAN]->(sp)

// Zoning
WITH p, i, ownerName, zoneId, rrrId
MATCH (zn:Zoning {zoneId: zoneId})
MERGE (p)-[:HAS_ZONING]->(zn)

// RRR
WITH p, i, ownerName, zoneId, rrrId
MATCH (rr:RRR {rrrId: rrrId})
MERGE (p)-[:HAS_RRR]->(rr);
