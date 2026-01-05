"""
Twitter Monitor - Monitors @ultrawavetrader for new tweets without API keys
Uses snscrape to fetch tweets
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import subprocess
import json
import re

logger = logging.getLogger(__name__)


class Tweet:
    """Represents a tweet with relevant information"""

    def __init__(self, id: str, text: str, created_at: datetime, url: str):
        self.id = id
        self.text = text
        self.created_at = created_at
        self.url = url

    def __repr__(self):
        return f"Tweet(id={self.id}, created_at={self.created_at}, text={self.text[:50]}...)"


class TwitterMonitor:
    """
    Monitors a Twitter account for new tweets using snscrape
    No API key required
    """

    def __init__(self, username: str, poll_interval: int = 10, max_tweet_age: int = 300):
        """
        Initialize Twitter monitor

        Args:
            username: Twitter username to monitor (without @)
            poll_interval: Seconds between checks for new tweets
            max_tweet_age: Only process tweets newer than this (in seconds)
        """
        self.username = username
        self.poll_interval = poll_interval
        self.max_tweet_age = max_tweet_age
        self.last_tweet_id = None
        self.processed_tweet_ids = set()

        logger.info(f"Initialized Twitter monitor for @{username}")

    def fetch_recent_tweets(self, limit: int = 10) -> List[Tweet]:
        """
        Fetch recent tweets from the user using snscrape

        Args:
            limit: Maximum number of tweets to fetch

        Returns:
            List of Tweet objects
        """
        try:
            # Use snscrape CLI to fetch tweets
            # Format: snscrape --jsonl twitter-user username
            cmd = [
                'snscrape',
                '--jsonl',
                '--max-results', str(limit),
                'twitter-user',
                self.username
            ]

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"snscrape failed: {result.stderr}")
                return []

            tweets = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                try:
                    tweet_data = json.loads(line)
                    tweet = Tweet(
                        id=str(tweet_data['id']),
                        text=tweet_data['content'],
                        created_at=datetime.fromisoformat(tweet_data['date'].replace('Z', '+00:00')),
                        url=tweet_data['url']
                    )
                    tweets.append(tweet)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing tweet data: {e}")
                    continue

            logger.info(f"Fetched {len(tweets)} tweets from @{self.username}")
            return tweets

        except subprocess.TimeoutExpired:
            logger.error("snscrape command timed out")
            return []
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []

    def get_new_tweets(self) -> List[Tweet]:
        """
        Get new tweets that haven't been processed yet

        Returns:
            List of new Tweet objects
        """
        all_tweets = self.fetch_recent_tweets(limit=20)

        if not all_tweets:
            return []

        # Filter out old tweets and already processed tweets
        cutoff_time = datetime.now(all_tweets[0].created_at.tzinfo) - timedelta(seconds=self.max_tweet_age)

        new_tweets = []
        for tweet in all_tweets:
            # Skip if already processed
            if tweet.id in self.processed_tweet_ids:
                continue

            # Skip if too old
            if tweet.created_at < cutoff_time:
                continue

            new_tweets.append(tweet)
            self.processed_tweet_ids.add(tweet.id)

        # Keep processed IDs set from growing too large
        if len(self.processed_tweet_ids) > 1000:
            self.processed_tweet_ids = set(list(self.processed_tweet_ids)[-500:])

        if new_tweets:
            logger.info(f"Found {len(new_tweets)} new tweets")
            for tweet in new_tweets:
                logger.info(f"New tweet: {tweet}")

        return new_tweets

    async def start_monitoring(self, callback):
        """
        Start monitoring for new tweets and call callback for each new tweet

        Args:
            callback: Async function to call with each new tweet
        """
        logger.info(f"Starting to monitor @{self.username} every {self.poll_interval}s")

        # Initial fetch to establish baseline
        initial_tweets = self.fetch_recent_tweets(limit=5)
        for tweet in initial_tweets:
            self.processed_tweet_ids.add(tweet.id)
        logger.info(f"Marked {len(initial_tweets)} existing tweets as processed")

        while True:
            try:
                new_tweets = self.get_new_tweets()

                for tweet in new_tweets:
                    try:
                        await callback(tweet)
                    except Exception as e:
                        logger.error(f"Error in tweet callback: {e}", exc_info=True)

                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    def stop_monitoring(self):
        """Stop monitoring (cleanup if needed)"""
        logger.info(f"Stopped monitoring @{self.username}")


# Test function
async def test_monitor():
    """Test the Twitter monitor"""

    async def print_tweet(tweet: Tweet):
        print(f"\n{'='*60}")
        print(f"New tweet from @{tweet.url.split('/')[3]}")
        print(f"Time: {tweet.created_at}")
        print(f"Text: {tweet.text}")
        print(f"URL: {tweet.url}")
        print(f"{'='*60}\n")

    monitor = TwitterMonitor("ultrawavetrader", poll_interval=15)
    await monitor.start_monitoring(print_tweet)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(test_monitor())
