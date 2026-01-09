"""X/Twitter API tools for searching and posting replies."""

from dataclasses import dataclass

import tweepy

from src.config import get_config


@dataclass
class Tweet:
    """A tweet from X/Twitter."""

    id: str
    text: str
    author_id: str
    author_username: str | None = None


def get_x_client() -> tweepy.Client:
    """Get an authenticated X/Twitter API client."""
    config = get_config()
    return tweepy.Client(
        consumer_key=config.x_client_id,
        consumer_secret=config.x_client_secret,
        access_token=config.x_access_token,
        access_token_secret=config.x_access_token_secret,
    )


async def x_reply(
    in_reply_to_tweet_id: str,
    text: str,
    dry_run: bool = False,
) -> dict:
    """
    Post a reply to a tweet on X/Twitter.

    Args:
        in_reply_to_tweet_id: The ID of the tweet to reply to
        text: The reply text (max 280 characters)
        dry_run: If True, don't actually post (for testing)

    Returns:
        Response dict with tweet ID and status
    """
    if len(text) > 280:
        raise ValueError(f"Reply text too long: {len(text)} chars (max 280)")

    if dry_run:
        return {
            "dry_run": True,
            "would_post": {
                "text": text,
                "in_reply_to_tweet_id": in_reply_to_tweet_id,
            },
        }

    client = get_x_client()
    response = client.create_tweet(
        text=text,
        in_reply_to_tweet_id=in_reply_to_tweet_id,
    )

    return {
        "id": response.data["id"],
        "text": text,
        "in_reply_to_tweet_id": in_reply_to_tweet_id,
    }


async def x_search(
    query: str,
    max_results: int = 10,
) -> list[Tweet]:
    """
    Search for tweets matching a query.

    Args:
        query: The search query
        max_results: Maximum number of results (default 10)

    Returns:
        List of Tweet objects
    """
    client = get_x_client()
    response = client.search_recent_tweets(
        query=query,
        max_results=min(max_results, 100),  # API limit
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


async def get_tweet_by_id(tweet_id: str) -> Tweet | None:
    """
    Get a single tweet by ID.

    Args:
        tweet_id: The tweet ID

    Returns:
        Tweet object or None if not found
    """
    client = get_x_client()
    response = client.get_tweet(
        tweet_id,
        tweet_fields=["author_id", "text"],
        expansions=["author_id"],
        user_fields=["username"],
    )

    if not response.data:
        return None

    username = None
    if response.includes and "users" in response.includes:
        user = response.includes["users"][0]
        username = user.username

    return Tweet(
        id=str(response.data.id),
        text=response.data.text,
        author_id=str(response.data.author_id),
        author_username=username,
    )
