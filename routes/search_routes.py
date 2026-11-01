from flask import Blueprint, jsonify, render_template, request, session, url_for

from models.post_model import get_discovery_posts, search_posts
from models.reel_model import search_reels
from models.user_model import search_users
from routes.helpers import login_required

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.get("/")
@login_required
def search():
    term = request.args.get("q", "").strip()[:80]
    active_filter = request.args.get("type", "all")
    if active_filter not in {"all", "people", "posts", "reels", "hashtags"}:
        active_filter = "all"
    viewer_id = session["user_id"]
    users = (
        search_users(term, viewer_id)
        if term and active_filter in {"all", "people"}
        else []
    )
    posts = []
    if active_filter in {"all", "posts", "hashtags"}:
        if term:
            posts = search_posts(
                term, viewer_id, hashtags_only=active_filter == "hashtags"
            )
        elif active_filter in {"all", "posts"}:
            posts = get_discovery_posts(viewer_id)
    reels = (
        search_reels(term, viewer_id)
        if active_filter == "reels" or (active_filter == "all" and term)
        else []
    )
    return render_template(
        "search/search.html",
        query=term,
        users=users,
        posts=posts,
        reels=reels,
        active_filter=active_filter,
    )


@search_bp.get("/suggestions")
@login_required
def suggestions():
    term = request.args.get("q", "").strip()[:80]
    if len(term) < 2:
        return jsonify([])
    results = search_users(term, session["user_id"], limit=6)
    static_root = url_for("static", filename="")
    return jsonify(
        [
            {
                "username": user["username"],
                "full_name": user["full_name"],
                "bio": user["bio"] or "",
                "avatar_url": (
                    static_root + user["avatar_path"] if user["avatar_path"] else None
                ),
                "profile_url": url_for(
                    "profile.view_profile", username=user["username"]
                ),
            }
            for user in results
        ]
    )
