# parcel-demo
Use Case of parcel in Neo4j and ESRI  

Awesome—here’s a clean high-level diagram you can drop into docs/slides.

```
┌──────────────────────────┐
│        Frontend          │
│  (Leaflet static site)   │
│  • index.html            │
│  • config.js (API_BASE)  │
│  • *.geojson/*.json      │
└─────────────┬────────────┘
              │  HTTPS (CORS)
              │  GET /health
              │  GET /api/v1/parcels/<id>
┌─────────────▼────────────┐
│        Flask API         │
│  parcel-backend (Render) │
│  • Routes: /, /health,   │
│    /api/v1/parcels/<id>  │
│  • Pretty JSON (?pretty) │
│  • Translates Cypher→JSON│
└─────────────┬────────────┘
              │  Bolt/neo4j+s (TLS)
              │
┌─────────────▼────────────┐
│         Neo4j Aura       │
│  Parcel graph model:     │
│  Parcel─HAS_TITLE→Title  │
│         └OWNED_BY→Owner  │
│  Parcel─HAS_RRR→RRR      │
│  Parcel─HAS_PLAN→Survey  │
│  Parcel─HAS_ASSESSMENT→A │
│  Parcel─HAS_ZONING→Zoning│
└──────────────────────────┘
```

### How data flows

1. User clicks a parcel on the map → frontend requests
    `GET {API_BASE}/api/v1/parcels/<parcelId>`
2. Flask queries Neo4j with Cypher, converts nodes to plain JSON.
3. JSON comes back to the browser; the popup renders parcel details.

### Why this split matters

- **Loose coupling:** you can swap Leaflet → ESRI later without touching the API/DB.
- **Security/control:** browser never talks to Neo4j directly; the API is the contract.
- **Scalability:** you can add auth, caching, logging, or new endpoints without changing the frontend.

If you want, I can also produce a small PNG/PDF version of this diagram for your slide deck.
