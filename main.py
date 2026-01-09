"""Twitter Reply Agent - Main entry point."""

import argparse
import asyncio
import sys

from dotenv import load_dotenv


async def run_manual(dry_run: bool = False, tweet_url: str | None = None) -> None:
    """Run the agent with manual tweet input."""
    from src.agent import react_to_tweet
    from src.sources.manual import get_tweet_from_url, get_tweet_input

    if tweet_url:
        tweet = await get_tweet_from_url(tweet_url)
    else:
        tweet = await get_tweet_input()

    if tweet is None:
        print("No tweet to react to.")
        return

    print(f"\nReacting to tweet by @{tweet.author_username or tweet.author_id}...")
    print(f"Tweet: {tweet.text}\n")

    result = await react_to_tweet(tweet, dry_run=dry_run)

    if result.success:
        print("\nAgent completed successfully.")
        if dry_run:
            print("[DRY RUN - no tweet was posted]")
    else:
        print(f"\nAgent failed: {result.error}")


async def run_keyword_search(dry_run: bool = False) -> None:
    """Run the agent with keyword search."""
    from src.agent import react_to_tweet
    from src.sources.keyword_search import interactive_keyword_search

    tweets = await interactive_keyword_search()

    if not tweets:
        print("No tweets found.")
        return

    print("\nWhich tweet do you want to react to? (enter number, or 'q' to quit)")
    choice = input("> ").strip()

    if choice.lower() == "q":
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tweets):
            tweet = tweets[idx]
        else:
            print("Invalid choice.")
            return
    except ValueError:
        print("Invalid input.")
        return

    print(f"\nReacting to tweet by @{tweet.author_username or tweet.author_id}...")
    result = await react_to_tweet(tweet, dry_run=dry_run)

    if result.success:
        print("\nAgent completed successfully.")
        if dry_run:
            print("[DRY RUN - no tweet was posted]")
    else:
        print(f"\nAgent failed: {result.error}")


async def run_mentions(dry_run: bool = False) -> None:
    """Run the agent on recent mentions."""
    from src.agent import react_to_tweet
    from src.sources.mentions import poll_mentions, MentionsTracker

    tracker = MentionsTracker()
    mentions = await poll_mentions(tracker=tracker)

    if not mentions:
        print("No new mentions.")
        return

    print(f"Found {len(mentions)} new mentions:")
    for i, mention in enumerate(mentions, 1):
        author = mention.author_username or mention.author_id
        text = mention.text[:60] + ("..." if len(mention.text) > 60 else "")
        print(f"  {i}. @{author}: {text}")

    print("\nReact to all? (y/n)")
    choice = input("> ").strip().lower()

    if choice != "y":
        return

    for mention in mentions:
        print(f"\nReacting to @{mention.author_username or mention.author_id}...")
        result = await react_to_tweet(mention, dry_run=dry_run)

        if result.success:
            tracker.mark_processed(mention.id)
            print("Done.")
        else:
            print(f"Failed: {result.error}")


def main() -> None:
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Twitter Reply Agent - React to tweets with context-aware replies"
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "search", "mentions"],
        default="manual",
        help="Mode: manual (paste URL), search (keyword search), or mentions (monitor mentions)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually post tweets (for testing)",
    )
    parser.add_argument(
        "--tweet-url",
        type=str,
        help="Tweet URL to react to (manual mode only)",
    )

    args = parser.parse_args()

    if args.mode == "manual":
        asyncio.run(run_manual(dry_run=args.dry_run, tweet_url=args.tweet_url))
    elif args.mode == "search":
        asyncio.run(run_keyword_search(dry_run=args.dry_run))
    elif args.mode == "mentions":
        asyncio.run(run_mentions(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
