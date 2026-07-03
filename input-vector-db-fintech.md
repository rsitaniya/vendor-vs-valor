# Capability need — vector database for semantic search and portfolio intelligence

## Same company, new problem

We are the same Series A fintech startup (Bengaluru) building the institutional
portfolio analytics platform for Indian wealth managers described in our market
data profile. We now need to choose our vector database infrastructure.

We are building two features that require semantic search and vector similarity:

1. **Research and document intelligence** — wealth managers upload fund factsheets,
   SEBI research analyst reports, company annual reports, and third-party research
   PDFs. Advisors need to ask natural-language questions ("what did this fund say
   about its large-cap allocation in Q3?") and get answers grounded in the uploaded
   documents. This is a RAG (retrieval-augmented generation) pipeline over private,
   per-client document stores. Documents are in English and Indian-English; some
   contain tables, charts, and scanned pages (OCR required separately).

2. **Semantic portfolio alerts** — we have a stream of structured market events
   (earnings surprises, regulatory filings, credit rating changes, corporate actions)
   arriving via Kafka. We embed each event and do approximate nearest-neighbour
   search against a client's portfolio holdings and their stated investment thesis
   (also embedded at onboarding) to generate contextually relevant alerts. This is
   a high-write, moderate-read workload: ~50,000 new vectors per day at launch,
   scaling to ~500,000/day at ₹10,000 crore AUM. Query latency must be under 100ms
   at p99 for the alert path.

## What we need from the vector database

- **Storage**: starting at ~5 million vectors (768 or 1536 dimensions), growing to
  ~100 million over 18 months. Vectors are float32 embeddings from an LLM
  (likely text-embedding-3-small or a local BGE model — not yet decided).
- **Metadata filtering**: every vector is tagged with client_id, portfolio_id,
  document_type, and date. Queries must filter by client_id before ANN search —
  we cannot leak one wealth manager's data into another's search results. This is
  a hard security requirement, not a nice-to-have.
- **Multi-tenancy**: each wealth manager firm is a tenant. Document stores must
  be logically isolated. We need either namespace/collection-level isolation or
  row-level security enforced at the database layer.
- **Hybrid search**: for the document RAG use case, pure vector search is not
  enough. We need hybrid BM25 + vector search (dense + sparse) to handle proper
  noun lookups (e.g. "HDFC Flexi Cap Fund" must be retrievable even if the
  embedding distance is poor). Some vendors call this "sparse+dense" or
  "full-text + semantic".
- **Deletion and update**: when a wealth manager removes a client or a document
  is superseded, vectors must be deletable. This rules out append-only stores.
- **Throughput**: write throughput of 50,000 vectors/day is ~0.6 vectors/second
  average, but we batch-ingest on document upload (could be 10,000 vectors in
  10 minutes for a large PDF corpus). Read throughput: ~200 QPS at peak for the
  alert path.

## Team and stack context

Same team: 4 engineers (2 senior Python, 2 mid), 1 data engineer.

- **Existing stack**: FastAPI on AWS EKS (Kubernetes), PostgreSQL + TimescaleDB,
  Kafka (MSK), S3, all in AWS ap-south-1 (Mumbai).
- **Embedding model**: not yet locked. Likely OpenAI text-embedding-3-small
  (1536-dim) for the document RAG use case, possibly a self-hosted BGE-M3 model
  for cost control at scale. The vector DB must be embedding-model-agnostic.
- **Orchestration**: we use LangChain/LangGraph for our LLM pipelines. We want
  a vector DB that has a first-class LangChain integration, but we will not let
  that be the deciding factor.

## Budget

- Same runway (22 months, ₹3.2M raised).
- Vector DB budget: ₹1–2 lakh/month (~$1,200–2,400/month) at launch.
  We expect this to grow 5–8x as AUM scales, so pricing model matters —
  we want per-query or per-vector pricing that is predictable, not opaque
  "enterprise contact us" walls.
- We are open to self-hosting on our existing EKS cluster if the operational
  overhead is manageable for a 5-person engineering team.

## Constraints

- **Data residency**: all vector embeddings contain semantic representations of
  client portfolio data and private documents. Must run in AWS ap-south-1 or be
  self-hosted on our EKS cluster. No US-only SaaS that cannot offer an
  ap-south-1 deployment or a BYOC (bring-your-own-cloud) option.
- **Multi-tenancy isolation**: hard requirement — client data must not bleed
  across tenant boundaries at the query layer. We have seen RAG systems where
  a misconfigured metadata filter exposes one client's documents to another.
  The database must enforce this, not our application layer alone.
- **Vendor lock-in**: moderate concern. We want to be able to export our vectors
  and switch providers within 2 weeks of engineering effort. Proprietary
  embedding formats or closed export APIs are a yellow flag.
- **Compliance**: same SEBI/RIA regulatory environment as the market data profile.
  The vector DB will hold client financial documents — data processing agreements
  (DPAs) and audit logs are required.
- **No US CLOUD Act exposure**: client portfolio documents may contain PII.
  A US-headquartered vendor with no Indian data residency option is a risk we
  need to flag to counsel. Self-hosting OSS eliminates this.

## Timeline

- **6 weeks**: vector DB provisioned, schema designed, document ingestion pipeline
  live in staging with the first wealth manager's test document corpus.
- **3 months**: alert ANN search live in production.
- **6 months**: hybrid BM25 + vector search for document RAG live.

## What a good outcome looks like

Name the specific vector databases we should evaluate, with honest assessments
of their hybrid search maturity, multi-tenancy model, India/AWS Mumbai
availability, and pricing at our scale. If the right answer is a managed cloud
offering, say which one and what it costs. If the right answer is self-hosting
Qdrant or Weaviate on our EKS cluster, say what that operational burden looks
like for a 5-person team and what we give up versus the managed option. We want
a clear first choice, a runner-up, and an honest list of what we do not yet know.
