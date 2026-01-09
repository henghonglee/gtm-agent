"""Keyword search source for finding tweets to react to."""

from src.tools.x_tools import Tweet, x_search


async def search_tweets(
    keywords: list[str],
    max_results: int = 10,
    exclude_retweets: bool = True,
    exclude_replies: bool = True,
    language: str = "en",
) -> list[Tweet]:
    """
    Search for tweets matching keywords.

    Args:
        keywords: List of keywords to search for
        max_results: Maximum number of results (default 10)
        exclude_retweets: Exclude retweets (default True)
        exclude_replies: Exclude replies (default True)
        language: Language filter (default "en")

    Returns:
        List of Tweet objects matching the search
    """
    # Build query with filters
    query_parts = []

    # Add keywords (OR logic)
    if len(keywords) == 1:
        query_parts.append(keywords[0])
    else:
        query_parts.append(f"({' OR '.join(keywords)})")

    # Add filters
    if exclude_retweets:
        query_parts.append("-is:retweet")
    if exclude_replies:
        query_parts.append("-is:reply")
    if language:
        query_parts.append(f"lang:{language}")

    query = " ".join(query_parts)

    return await x_search(query, max_results=max_results)


async def interactive_keyword_search() -> list[Tweet]:
    """
    Interactive prompt for keyword search.

    Returns:
        List of Tweet objects from search
    """
    print("Enter keywords to search for (comma-separated):")
    user_input = input("> ").strip()

    if not user_input:
        return []

    keywords = [k.strip() for k in user_input.split(",") if k.strip()]

    print(f"Searching for: {keywords}")
    tweets = await search_tweets(keywords)

    if not tweets:
        print("No tweets found.")
        return []

    print(f"Found {len(tweets)} tweets:")
    for i, tweet in enumerate(tweets, 1):
        author = tweet.author_username or tweet.author_id
        text_preview = tweet.text[:60] + ("..." if len(tweet.text) > 60 else "")
        print(f"  {i}. @{author}: {text_preview}")

    return tweets
