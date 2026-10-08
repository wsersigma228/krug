"""Shared visibility predicate for every existing public post surface."""
from sqlalchemy import or_, select
from backend.models import Community, Post, Project


def canonical_project_url(url):
    if url is None:
        return None
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    # GitHub repository URLs are case insensitive; tracking fragments do not identify a repository.
    if parts.hostname == "github.com":
        path = parts.path.rstrip("/").lower()
        if path.endswith(".git"):
            path = path[:-4]
        return "https://github.com" + path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def public_post():
    return (Post.is_published.is_(True) & or_(
        Post.project_id.is_(None),
        Post.project_id.in_(select(Project.id).where(Project.visibility == "public")),
    ) & or_(
        Post.community_id.is_(None),
        Post.community_id.in_(select(Community.id).where(Community.visibility == "public")),
    ))
