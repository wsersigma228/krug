# API guide

Interactive OpenAPI documentation is at `/docs`; its JSON schema is at
`/openapi.json`. Requests and responses use JSON except photo uploads/downloads.
Dates include timezone information. Send access tokens as
`Authorization: Bearer ACCESS_TOKEN`; refresh tokens are accepted only by `/refresh`.

## Accounts

| Method and path | Access | Body / result |
| --- | --- | --- |
| `POST /users` | Public | `{username,password,email?,language?}` → 201 account |
| `POST /login` | Public | `{username,password}` → access/refresh tokens |
| `POST /refresh` | Refresh token in body | `{refresh_token}` → new access token |
| `GET /me` | Signed in | Your account, including email/verification status and nullable language |
| `PATCH /me/language` | Signed in | `{language:"ru"}` or `{language:"en"}` → saved `{language}` |
| `POST /logout` | Signed in | 204; revokes all sessions for your account |
| `DELETE /users/{id}` | Account owner or admin | 204; removes account and its content |
| `POST /auth/email-verification/request` | Signed in | 202; queues verification if needed |
| `POST /auth/email-verification/confirm` | Public | `{token}` → 204 |
| `POST /auth/password-reset/request` | Public | `{email}` → same 202 for known/unknown email |
| `POST /auth/password-reset/confirm` | Public | `{token,password}` → 204; revokes sessions |
| `GET /me/notifications` | Signed in | `{email_publications}` |
| `PATCH /me/notifications` | Signed in | `{email_publications: true/false}`; enabling requires verified email |
| `GET /users/get`, `GET /admin/panel` | Admin | Administrative account list / access check |

Username is 3–50 characters at registration. New passwords are 8–100 characters.
Email is optional. Verification links expire after 60 minutes; reset links after
30 minutes. Each is single-use; requesting another invalidates the previous link
of the same kind. `/verify-email` and `/reset-password` open the UI using a token
in the URL fragment. Opening the page does not consume the token.

Account language accepts only `ru` or `en`; registration may omit it or send null.
Existing accounts stay null after migration `a75e9b024138`. The language PATCH
requires a non-null value and rejects missing/unknown fields or other languages
with 422. It locks the account and rechecks session revocation before saving.
Public profiles do not expose language. The UI initializes an unset account from
its current interface language when signed in; API clients may leave it unset.
`PATCH /me/language?initialize=true` sets an unset preference only, returning an
already-saved choice unchanged. This prevents first visits from overwriting an
explicit choice made on another device. Omit the query flag for manual changes.

Service and publication email copy uses the recipient's current saved language
when delivered, with English fallback for null. User-provided post titles are not
translated. A saved language adds `?lang=ru` or `?lang=en` before the token fragment
in service links; an unset account retains the original fragment-only link.
Theme is a browser preference and has no API endpoint.

## Profiles, posts and follows

| Method and path | Access | Body / result |
| --- | --- | --- |
| `GET /authors/{id}` | Public | `{id,username,bio,posts_count,subscribers_count,subscriptions_count}` |
| `PATCH /me/profile` | Signed in | `{bio}` (up to 500 characters) → public profile |
| `GET /explore` | Public | Page of published posts; optional full-text search |
| `GET /authors/{id}/posts` | Public | Page of this author's published posts |
| `GET /feed` | Signed in | Page of published posts from followed authors |
| `GET /posts` | Signed in | Page of your posts; optional publication/search filters |
| `POST /posts` | Signed in | `{title?,content,is_published?}` → 201 post; defaults to draft |
| `GET /posts/{id}` | Public for published; draft owner | Post |
| `PUT /posts/{id}` | Post owner | Supplied `{title?,content?,is_published?}` fields update the post |
| `DELETE /posts/{id}` | Post owner | 204; removes photo and interactions |
| `POST /subscriptions` | Signed in | `{author_id}` → 201; no self/duplicate subscription |
| `DELETE /subscriptions/{author_id}` | Signed in | 204; missing subscription is 404 |
| `GET /subscriptions`, `GET /subscribers` | Signed in | Page of public `{id,username}` author records |
| `GET /subscriptions/{author_id}/check` | Signed in | `{subscribed}` |

Titles are optional strings with a maximum of 200 characters; surrounding whitespace
is trimmed. `POST` defaults an omitted title to an empty string; an explicit empty
string also creates an untitled post. In `PUT`, omit the title to retain it, or send
an empty string to clear it. Explicit nulls are rejected. Post content is required
and nonempty on creation; omit unchanged fields in `PUT`. Post responses contain id, title, content,
is_published, author_id, created_at, updated_at and nullable image_url. Feed/explore
also include author_username. Public profile counts exclude drafts and expose no
email. Publishing creates email deliveries for verified, opted-in subscribers;
editing an already published post does not send another publication notification.
For an untitled post, publication email labels use the first 80 characters of
whitespace-normalized content. Responses retain `title` as a string, including
empty strings; existing titled posts are unaffected. No new migration is required.

## Photos and interactions

| Method and path | Access | Body / result |
| --- | --- | --- |
| `PUT /posts/{id}/image` | Post owner | Raw image bytes → updated post |
| `GET /posts/{id}/image` | Published post or draft owner | JPEG bytes; `Cache-Control: no-store` |
| `DELETE /posts/{id}/image` | Post owner | 204 |
| `GET /posts/{id}/likes` | Published post or draft owner | `{count,liked}`; anonymous liked is false |
| `PUT /posts/{id}/likes` | Signed in; published post or own draft | Idempotent; `{count,liked}` |
| `DELETE /posts/{id}/likes` | Same | Idempotent; `{count,liked}` |
| `GET /posts/{id}/comments` | Published post or draft owner | Page of comments |
| `POST /posts/{id}/comments` | Signed in; published post or own draft | `{content}` → 201 comment |
| `DELETE /posts/{id}/comments/{comment_id}` | Comment author or post owner | 204 |

Photos accept still JPEG/PNG/WebP up to 8 MiB and 16 megapixels, as raw request
body, **not multipart**. Decoding, orientation, resizing to fit 2560 × 2560 and JPEG
re-encoding remove metadata. Each post has one current photo. Draft image URLs
still require an access token; the URL itself grants no access.
Comments are flat, trimmed and 1–2000 characters; whitespace-only text is rejected.
Each comment returns id, post_id, user_id, username, content and created_at.
The post owner may moderate comments. Foreign drafts return 404 for all these
operations, including a comment author's attempt to delete a hidden comment.

## Pagination and search

Paginated GET endpoints accept `limit` (1–100, default 100) and optional opaque
`cursor`. They return `{items,next_cursor,has_more}`. Pass next_cursor unchanged
to the same endpoint with the same filters; stop when has_more is false.
Changing the page size is allowed. Unknown pagination parameters (including the
old `offset`) and invalid/mismatched cursors return 422.

Posts/comments sort newest first by creation time and ID. Follow lists sort by
the follow event. Pages are not snapshots: later edits, deletions and follows may
change later results. Cursors grant no permission and become invalid if SECRET_KEY
changes. `/posts` accepts `is_published`; `/posts` and `/explore` accept `search`
(up to 100 characters) and `search_language=simple|russian|english` (default simple).
Search is PostgreSQL full-text search, ranked before creation time/ID. Russian and
English apply stemming; simple matches exact tokens. Partial words/typos do not
match. Empty search returns chronological posts; stopword/punctuation-only search
can return no matches.

## Examples

These shell examples use an existing signed-in user's access token. Keep tokens
out of committed files and shared terminal output.

```bash
base=http://localhost:8000
curl "$base/explore?limit=20"
curl -X POST "$base/login" -H 'Content-Type: application/json' \
  -d '{"username":"example","password":"example-password"}'
read -r -s -p 'Access token: ' token; printf '\n'
curl -X POST "$base/posts" -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Hello","content":"My first post","is_published":false}'
# Replace 42 with the returned post id.
curl -X PUT "$base/posts/42/image" -H "Authorization: Bearer $token" \
  -H 'Content-Type: image/jpeg' --data-binary @photo.jpg
curl -X PUT "$base/posts/42" -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' -d '{"is_published":true}'
curl -X PUT "$base/posts/42/likes" -H "Authorization: Bearer $token"
curl -X POST "$base/posts/42/comments" -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' -d '{"content":"Hello!"}'
unset token
```

## Errors and health

Errors normally return JSON `{detail: ...}`; validation detail is a list. Common
statuses: 401 missing/invalid/revoked token, 403 prohibited operation or unverified
notification opt-in, 404 missing/inaccessible content, 409 duplicate account,
413 oversized photo, 422 invalid input/cursor/image and 429 account request limit.
429 includes `Retry-After`. Authentication limits count failed attempts and use
socket IP plus account identifier where available. A duplicate/self follow is 400.

`GET /` returns `{ok:true}` for process health. `GET /health` checks PostgreSQL and
Redis availability; it is not a test of SMTP, background processing or UI behavior.
Use actual worker logs and smoke checks for those paths.
