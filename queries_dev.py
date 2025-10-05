#!/usr/bin/env python3
from __future__ import annotations
import argparse, os
import pandas as pd
import database_queries as q

# ---------- tiny IO helpers ---------------------------------------------------
def write(df: pd.DataFrame, out: str | None):
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Wrote {len(df):,} rows to {out}")
    else:
        # print a small preview to stdout
        if df is None or df.empty:
            print("(no rows)")
            return
        print(df.head(20).to_string(index=False))

def add_common_filters(p: argparse.ArgumentParser):
    p.add_argument("--db", default=q.DB_PATH_DEFAULT, help="DuckDB path")
    p.add_argument("--start", help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", help="End date (YYYY-MM-DD)")
    p.add_argument("--bbox", help="min_lat,min_lon,max_lat,max_lon")
    p.add_argument("--limit", type=int, help="Row limit")

def parse_bbox(s: str | None):
    if not s:
        return None
    parts = [float(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise SystemExit("--bbox must be: min_lat,min_lon,max_lat,max_lon")
    return tuple(parts)

# ---------- main --------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser("queries dev CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ---- originals -----------------------------------------------------------
    # users-for-hashtag
    u4h = sub.add_parser("users-for-hashtag", help="Users who used a given hashtag(s)")
    add_common_filters(u4h)
    u4h.add_argument("--hashtag", nargs="+", required=True, help="Exact hashtag tokens (as stored)")
    u4h.add_argument("--order-by", default="n DESC")
    u4h.add_argument("-o", "--out")

    # hashtags-for-users
    h4u = sub.add_parser("hashtags-for-users", help="Hashtags used by specific users/uids")
    add_common_filters(h4u)
    h4u.add_argument("--user", nargs="*")
    h4u.add_argument("--uid", type=int, nargs="*")
    h4u.add_argument("--order-by", default="n DESC")
    h4u.add_argument("-o", "--out")

    # all-users
    au = sub.add_parser("all-users", help="List users from materialized 'users' table")
    au.add_argument("--db", default=q.DB_PATH_DEFAULT)
    au.add_argument("--order-by", default="changesets_count DESC")
    au.add_argument("--limit", type=int, default=1000)
    au.add_argument("-o", "--out")

    # all-hashtags
    ah = sub.add_parser("all-hashtags", help="Global hashtag counts")
    add_common_filters(ah)
    ah.add_argument("--order-by", default="n DESC")
    ah.add_argument("-o", "--out")

    # hashtags-between-dates
    hbd = sub.add_parser("hashtags-between-dates", help="Global hashtag counts between two dates")
    hbd.add_argument("--db", default=q.DB_PATH_DEFAULT)
    hbd.add_argument("--start", required=True)
    hbd.add_argument("--end", required=True)
    hbd.add_argument("--order-by", default="n DESC")
    hbd.add_argument("--limit", type=int, default=1000)
    hbd.add_argument("-o", "--out")

    # users-in-bbox
    uib = sub.add_parser("users-in-bbox", help="Users with centroids in bbox")
    add_common_filters(uib)
    uib.add_argument("--order-by", default="changesets_in_bbox DESC")
    uib.add_argument("-o", "--out")

    # hashtags-in-bbox
    hib = sub.add_parser("hashtags-in-bbox", help="Hashtag usage within bbox")
    add_common_filters(hib)
    hib.add_argument("--order-by", default="n DESC")
    hib.add_argument("-o", "--out")

    # hashtags-for-users-in-bbox
    h4uib = sub.add_parser("hashtags-for-users-in-bbox", help="Hashtags by specific users inside bbox")
    add_common_filters(h4uib)
    h4uib.add_argument("--user", nargs="*")
    h4uib.add_argument("--uid", type=int, nargs="*")
    h4uib.add_argument("--order-by", default="n DESC")
    h4uib.add_argument("-o", "--out")

    # users-for-hashtag-in-bbox
    u4hib = sub.add_parser("users-for-hashtag-in-bbox", help="Users for a hashtag inside bbox")
    add_common_filters(u4hib)
    u4hib.add_argument("--hashtag", nargs="+", required=True)
    u4hib.add_argument("--order-by", default="n DESC")
    u4hib.add_argument("-o", "--out")

    # user-points
    up = sub.add_parser("user-points", help="Centroids (user_points) for given users/uids")
    up.add_argument("--db", default=q.DB_PATH_DEFAULT)
    up.add_argument("--user", nargs="*")
    up.add_argument("--uid", type=int, nargs="*")
    up.add_argument("--start")
    up.add_argument("--end")
    up.add_argument("-o", "--out")

    # hashtag-points
    hp = sub.add_parser("hashtag-points", help="Centroids for changesets using hashtag(s)")
    hp.add_argument("--db", default=q.DB_PATH_DEFAULT)
    hp.add_argument("--hashtag", nargs="+", required=True)
    hp.add_argument("--start")
    hp.add_argument("--end")
    hp.add_argument("-o", "--out")

    # count-hashtag
    ch = sub.add_parser("count-hashtag", help="Counts for one or more hashtags")
    ch.add_argument("--db", default=q.DB_PATH_DEFAULT)
    ch.add_argument("--hashtag", nargs="+", required=True)
    ch.add_argument("--start")
    ch.add_argument("--end")
    ch.add_argument("-o", "--out")

    # count-user-changes
    cuc = sub.add_parser("count-user-changes", help="Changeset counts per user")
    cuc.add_argument("--db", default=q.DB_PATH_DEFAULT)
    cuc.add_argument("--user", nargs="*")
    cuc.add_argument("--uid", type=int, nargs="*")
    cuc.add_argument("--start")
    cuc.add_argument("--end")
    cuc.add_argument("-o", "--out")

    # ---- new ones we added ---------------------------------------------------
    # changesets (rich filter)
    cs = sub.add_parser("changesets", help="General changeset search (users/tags/comments/date/bbox)")
    add_common_filters(cs)
    cs.add_argument("--user", nargs="*")
    cs.add_argument("--uid", type=int, nargs="*")
    cs.add_argument("--hashtag", nargs="*")
    cs.add_argument("--like", nargs="*")
    cs.add_argument("--comment-like", nargs="*")
    cs.add_argument("--order-by", default="created_at DESC")
    cs.add_argument("-o", "--out")

    # top-users
    tu = sub.add_parser("top-users", help="Top-N users by changesets")
    add_common_filters(tu)
    tu.add_argument("--hashtag", nargs="*")
    tu.add_argument("--like", nargs="*")
    tu.add_argument("--order-by", default="changesets DESC")
    tu.add_argument("-o", "--out")

    # top-hashtags
    th = sub.add_parser("top-hashtags", help="Top-N hashtags")
    add_common_filters(th)
    th.add_argument("--user", nargs="*")
    th.add_argument("--uid", type=int, nargs="*")
    th.add_argument("--order-by", default="n DESC")
    th.add_argument("-o", "--out")

    # top-comments
    tc = sub.add_parser("top-comments", help="Top-N most frequent comments")
    add_common_filters(tc)
    tc.add_argument("--hashtag", nargs="*")
    tc.add_argument("--like", nargs="*")
    tc.add_argument("--order-by", default="n DESC")
    tc.add_argument("-o", "--out")

    args = ap.parse_args()
    bbox = parse_bbox(getattr(args, "bbox", None))

    # ---- dispatch -----------------------------------------------------------
    if args.cmd == "users-for-hashtag":
        df = q.get_users_for_hashtag(
            hashtag=args.hashtag,
            start_date=args.start, end_date=args.end, bbox=bbox,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "hashtags-for-users":
        df = q.get_hashtags_for_users(
            usernames=args.user, uids=args.uid,
            start_date=args.start, end_date=args.end, bbox=bbox,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "all-users":
        df = q.get_all_users(order_by=args.order_by, limit=args.limit, db_path=args.db)
        write(df, args.out)

    elif args.cmd == "all-hashtags":
        df = q.get_all_hashtags(
            start_date=args.start, end_date=args.end, bbox=bbox,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "hashtags-between-dates":
        df = q.get_hashtags_between_dates(
            args.start, args.end,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "users-in-bbox":
        if bbox is None: raise SystemExit("--bbox is required")
        df = q.get_users_in_bbox(
            bbox=bbox, start_date=args.start, end_date=args.end,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "hashtags-in-bbox":
        if bbox is None: raise SystemExit("--bbox is required")
        df = q.get_hashtags_in_bbox(
            bbox=bbox, start_date=args.start, end_date=args.end,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "hashtags-for-users-in-bbox":
        if bbox is None: raise SystemExit("--bbox is required")
        df = q.get_hashtags_for_users_in_bbox(
            usernames=args.user, uids=args.uid, bbox=bbox,
            start_date=args.start, end_date=args.end,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "users-for-hashtag-in-bbox":
        if bbox is None: raise SystemExit("--bbox is required")
        df = q.get_users_for_hashtag_in_bbox(
            hashtag=args.hashtag, bbox=bbox,
            start_date=args.start, end_date=args.end,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "user-points":
        df = q.get_user_points(
            usernames=args.user, uids=args.uid,
            start_date=args.start, end_date=args.end,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "hashtag-points":
        df = q.get_hashtag_points(
            hashtag=args.hashtag,
            start_date=args.start, end_date=args.end,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "count-hashtag":
        df = q.count_hashtag(
            hashtag=args.hashtag,
            start_date=args.start, end_date=args.end,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "count-user-changes":
        df = q.count_user_changes(
            uids=args.uid, usernames=args.user,
            start_date=args.start, end_date=args.end,
            db_path=args.db
        )
        write(df, args.out)

    # new ones
    elif args.cmd == "changesets":
        df = q.get_changesets_filtered(
            usernames=args.user, uids=args.uid,
            hashtag=args.hashtag, like=args.like,
            comment_like=getattr(args, "comment_like", None),
            start_date=args.start, end_date=args.end, bbox=bbox,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "top-users":
        df = q.get_top_users(
            start_date=args.start, end_date=args.end, bbox=bbox,
            hashtag=args.hashtag, like=args.like,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "top-hashtags":
        df = q.get_top_hashtags(
            usernames=args.user, uids=args.uid,
            start_date=args.start, end_date=args.end, bbox=bbox,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

    elif args.cmd == "top-comments":
        df = q.get_top_comments(
            start_date=args.start, end_date=args.end, bbox=bbox,
            hashtag=args.hashtag, like=args.like,
            order_by=args.order_by, limit=args.limit,
            db_path=args.db
        )
        write(df, args.out)

if __name__ == "__main__":
    main()
