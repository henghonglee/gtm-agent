"""Mentions monitor source for finding tweets that mention you."""

import json
from pathlib import Path

from src.tools.x_tools import Tweet, get_x_client


async def get_mentions(
    max_results: int = 10,
    since_id: str | None = None,
) -> list[Tweet]:
    """
    Get recent mentions of the authenticated user.

    Args:
        max_results: Maximum number of results (default 10)
        since_id: Only get mentions newer than this ID (for pagination)

    Returns:
        List of Tweet objects mentioning the user
    """
    client = get_x_client()

    # First get the authenticated user's ID
    me = client.get_me()
    if not me.data:
        raise RuntimeError("Could not get authenticated user")

    user_id = me.data.id

    # Get mentions
    response = client.get_users_mentions(
        user_id,
        max_results=min(max_results, 100),
        since_id=since_id,
        tweet_fields=["author_id", "text"],
        expansions=["author_id"],
        user_fields=["username"],
    )

    if not response.data:
        return []

    # Build user lookup
    users = {}
    if response.includes and "users" in response.includes:
        for user in response.includes["users"]:
            users[user.id] = user.username

    tweets = []
    for tweet in response.data:
        tweets.append(
            Tweet(
                id=str(tweet.id),
                text=tweet.text,
                author_id=str(tweet.author_id),
                author_username=users.get(tweet.author_id),
            )
        )

    return tweets


class MentionsTracker:
    """Tracks processed mentions to avoid duplicates."""

    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file or Path(".mentions_state.json")
        self.processed_ids: set[str] = set()
        self._load_state()

    def _load_state(self) -> None:
        """Load processed IDs from state file."""
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            self.processed_ids = set(data.get("processed_ids", []))

    def _save_state(self) -> None:
        """Save processed IDs to state file."""
        data = {"processed_ids": list(self.processed_ids)}
        self.state_file.write_text(json.dumps(data, indent=2))

    def mark_processed(self, tweet_id: str) -> None:
        """Mark a tweet as processed."""
        self.processed_ids.add(tweet_id)
        self._save_state()

    def is_processed(self, tweet_id: str) -> bool:
        """Check if a tweet has been processed."""
        return tweet_id in self.processed_ids

    def filter_unprocessed(self, tweets: list[Tweet]) -> list[Tweet]:
        """Filter out already processed tweets."""
        return [t for t in tweets if not self.is_processed(t.id)]


async def poll_mentions(
    tracker: MentionsTracker | None = None,
    max_results: int = 10,
) -> list[Tweet]:
    """
    Poll for new mentions, filtering out already processed ones.

    Args:
        tracker: Optional MentionsTracker for deduplication
        max_results: Maximum number of results

    Returns:
        List of new, unprocessed Tweet objects
    """
    mentions = await get_mentions(max_results=max_results)

    if tracker:
        mentions = tracker.filter_unprocessed(mentions)

    return mentions
