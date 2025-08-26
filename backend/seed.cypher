MERGE (p:Parcel {parcelId:'012-345-678'})
  SET p.legalDesc='LOT 12 DISTRICT LOT 123', p.civicAddress='1234 Oak St', p.municipality='Sample City';
MERGE (t:Title {titleNumber:'CA1234567'}) SET t.status='ACTIVE', t.issueDate=date('2022-10-15');
MERGE (p)-[:HAS_TITLE]->(t);
MERGE (o:Owner {ownerKey:'own|tenant-a'}) SET o.name='Tenant A', o.type='PERSON';
MERGE (t)-[:HAS_OWNER]->(o);
MERGE (r:RRR {rrrId:'RRR-9988'}) SET r.category='CHARGE', r.type='MORTGAGE', r.status='ACTIVE',
      r.effectiveFrom=datetime('2024-03-01T00:00:00Z'), r.amount=250000, r.currency='CAD';
MERGE (t)-[:ENCUMBERED_BY]->(r);
MERGE (r)-[:APPLIES_TO]->(p);
MERGE (s:SurveyPlan {planNo:'EPP12345'}) SET s.registeredDate=date('2021-06-01');
MERGE (p)-[:AFFECTED_BY]->(s);
MERGE (a:Assessment {assmtKey:'012-345-678|2025'}) SET a.year=2025, a.totalValue=1000000,
      a.landValue=650000, a.improValue=350000;
MERGE (p)-[:HAS_ASSESSMENT]->(a);
MERGE (z:Zoning {code:'R1'}) SET z.bylaw='Bylaw-2020-01';
MERGE (p)-[:ZONED_AS]->(z);
