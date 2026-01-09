"""Manual post input source."""

import re

from src.tools.x_tools import Tweet, get_tweet_by_id


def _extract_tweet_id_from_url(url: str) -> str | None:
    """
    Extract tweet ID from a Twitter/X URL.

    Supports formats:
    - https://twitter.com/user/status/1234567890
    - https://x.com/user/status/1234567890
    - 1234567890 (just the ID)
    """
    # Just an ID
    if url.isdigit():
        return url

    # URL pattern
    pattern = r"(?:twitter\.com|x\.com)/\w+/status/(\d+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)

    return None


async def get_tweet_from_url(url_or_id: str) -> Tweet | None:
    """
    Get a tweet from a URL or ID.

    Args:
        url_or_id: Either a tweet URL or just the tweet ID

    Returns:
        Tweet object or None if not found
    """
    tweet_id = _extract_tweet_id_from_url(url_or_id)
    if not tweet_id:
        return None

    return await get_tweet_by_id(tweet_id)


async def get_tweet_input() -> Tweet | None:
    """
    Interactive prompt to get a tweet from user input.

    Returns:
        Tweet object or None if user cancels
    """
    print("Enter a tweet URL or ID (or 'q' to quit):")
    user_input = input("> ").strip()

    if user_input.lower() == "q":
        return None

    tweet = await get_tweet_from_url(user_input)
    if tweet is None:
        print(f"Could not find tweet: {user_input}")
        return None

    print(f"Found tweet by @{tweet.author_username or tweet.author_id}:")
    print(f"  {tweet.text[:100]}{'...' if len(tweet.text) > 100 else ''}")

    return tweet
