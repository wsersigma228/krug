# Multilingual full-text search

[Русская версия](search.ru.md)

## Scope and language modes

`GET /posts` searches the signed-in user's own titles and content, including
drafts unless `is_published` filters them. `GET /explore` is public and searches
published posts across all authors, returning author usernames alongside posts.
The feed has no search parameter. Visibility is enforced in the SQL query.
Both endpoints accept `search` (up to 100 characters), `search_language`, `limit`
and `cursor`. Search mode is independent of RU/EN interface/account language;
it never translates content.

| Mode | Matching | Example |
| --- | --- | --- |
| `simple` (default) | Case-normalized exact tokens, without stemming | `dunyo` matches `Dunyo` |
| `russian` | Russian stemming and stopwords | `кошка` matches `кошки` |
| `english` | English stemming and stopwords | `run` matches `running` |

An explicit mode avoids guessing ambiguous short queries. Latin script cannot
distinguish English from Uzbek. Simple mode handles exact tokens in mixed text,
but does not implement universal morphology, transliteration, accent removal,
apostrophe normalization or specialized CJK segmentation. One Russian query does
not also enable English stemming. Separate language results are not merged.

## Stored vectors and indexes

Each post has `search_simple`, `search_russian` and `search_english` generated,
stored `tsvector` columns, with a GIN index for each. The application chooses one
column from a fixed allowlist matching its query configuration. Pydantic rejects
unknown modes with 422; SQLAlchemy passes user text as a query parameter.

```sql
setweight(to_tsvector('pg_catalog.russian'::regconfig, coalesce(title, '')), 'A')
||
setweight(to_tsvector('pg_catalog.russian'::regconfig, coalesce(content, '')), 'B')
```

Title matches have higher default weight than body matches; this does not mean
every title match outranks every body match. PostgreSQL recalculates vectors on
text changes, including direct SQL updates. Existing rows gain vectors during
migration. SQLAlchemy defers loading these columns; the API does not expose them.

Three vectors cost storage and work on writes, but keep document/query
configuration consistent for phrases, exclusion and ranking. A single per-post
language would require classification and a mixed-language policy. Many more
languages would warrant revisiting this choice.

GIN accelerates the `@@` match filter, not query-dependent relevance sorting.
Common words can produce many candidates; PostgreSQL may prefer an author index
followed by vector filtering instead of GIN.

## Queries and API examples

```http
GET /explore?search=run&search_language=english&limit=20
GET /posts?search=кошка&search_language=russian&limit=20
GET /posts?search=run&search_language=english&is_published=true
GET /posts?search=Python%20PostgreSQL&search_language=simple
```

Only `/posts` requires a Bearer token. Clients must URL-encode spaces, quotes
and non-ASCII text. Empty/whitespace search returns the chronological list.
Punctuation-only or stopword-only search can produce no results; it is not a
request to list everything. Edge whitespace is trimmed. Without search, language
mode does not change matching.

| `websearch_to_tsquery` input | Meaning |
| --- | --- |
| `python postgres` | Both words |
| `python OR postgres` | Either word |
| `"red green"` | Phrase |
| `python -django` | Python excluding Django |

Title and body form one document; phrases are not limited to one field.
PostgreSQL positional limits still apply to very long text. FTS replaces substring
`ILIKE` with word/stem matching: partial words and typos do not match. `pg_trgm`
and fuzzy search are not implemented.

An abbreviated response:

```json
{"items":[{"id":42,"title":"Example"}],"next_cursor":"opaque-token","has_more":true}
```

The database fetches `limit + 1` rows to determine `has_more`, without counting.
Limit is 1–100, default 100; an exhausted page has a null next cursor.

## Ranking and cursor boundaries

Search sorts by `(rank DESC, created_at DESC, id DESC)`. Its cursor includes rank
as well as creation time and ID, so an older highly ranked post can precede a
newer lower-ranked post without losing the latter on the next page:

```sql
WHERE (rank, created_at, id) < (:rank, :created_at, :id)
ORDER BY rank DESC, created_at DESC, id DESC
```

`ts_rank` is cast to double precision before sorting/comparison, without manual
rounding in Python/JSON. The shared HMAC-signed cursor implementation validates
ranking mode and request scope; chronological/ranked cursors cannot be interchanged.
Own-post search scope includes `posts_search_v1`, user ID, query, language and
publication filter. Explore scope includes its public endpoint, query and language.
Keep filters unchanged when passing `next_cursor`; page size may change.
Invalid/tampered/mismatched cursors return 422 and grant no permissions.

Pages are not snapshots: text edits can change rank and move records across a
boundary. Deleting the boundary row does not invalidate its saved values. Search
cursors from the substring implementation are invalid; ordinary list cursors
remain compatible. A strict snapshot would require a separate search-session design.

## Source and migration

| Path | Responsibility |
| --- | --- |
| `backend/models.py` | Generated vectors and ORM indexes |
| `backend/search.py` | Shared own/public SQL, ranking and pages |
| `backend/pagination.py` | Signed cursors, rank and scope validation |
| `backend/routes/posts.py` | Own posts and public explore |
| `backend/schemas.py` | Query validation |
| `alembic/versions/c18f72a9d604_add_multilingual_search.py` | Vector/index migration |
| `tests/test_search.py`, `tests/test_frontend.py` | Own/public search checks |
| `tests/test_cursor.py`, `tests/test_migrations.py` | Boundaries and schema round trips |
| `scripts/explain_search.py` | Repeatable temporary-table query plans |

Run `.venv/bin/alembic upgrade head` on the execution host before starting code
that expects the schema. `scripts/start` migrates with the new image before
starting web/worker/beat. Stored vectors process existing rows; normal GIN creation
blocks writes. Schedule maintenance for a large live table. Downgrade removes
search indexes/columns while preserving post text. The migration owns its
expressions rather than importing evolving model helpers.

## Verification and historical measurements

On Fedora or another Linux execution host, using a separate `test_db`:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.explain_search
```

The benchmark creates a temporary `posts` table visible only to its connection,
including generated columns/indexes. It inserts 30,000 synthetic posts across
30 authors, updates statistics, runs `EXPLAIN (ANALYZE, BUFFERS)` for rare/common
words and rolls back. Application posts are unchanged; databases not named
`test_db` are rejected. Tests cover morphology, title weights, cursor boundaries,
visibility, vector updates and schema round trips; current pass results must be
obtained from an actual run.

The earlier search note records results from 20 September 2026; these are
historical, not measurements of the current deployment or this RU/EN change:

| Query | Execution time | Candidate filtering |
| --- | ---: | --- |
| title/content `ILIKE`, `quartz` | 39.782 ms | Author index, text checks for 1,000 rows |
| FTS simple, `quartz` | 20.210 ms | Author index intersected with GIN |
| FTS Russian, `кошка` | 17.923 ms | Author index intersected with GIN |
| FTS English, `run` | 17.228 ms | Author index intersected with GIN |
| FTS simple, common `common` | 10.866 ms | Author index, vector checks for 1,000 rows |

The selected author had 1,000 posts and 50 rare matches; there were 150 globally.
For the rare term, the recorded plan used GIN and read 50 table blocks. This was
one sequential synthetic run, without cache normalization, with different
selection/order semantics from the ILIKE baseline. It establishes no general
speedup ratio. Repeat measurements for real workloads. The Russian note preserves
a historical 136-test result without a commit identifier; it is not evidence
that today's suite, CI or deployment passed.

References: [PostgreSQL 15 FTS tables/indexes](https://www.postgresql.org/docs/15/textsearch-tables.html),
[query processing and ranking](https://www.postgresql.org/docs/15/textsearch-controls.html).
