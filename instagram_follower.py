#!/usr/bin/env python3
"""
Instagram Follower Automation using Instagrapi
Follow followers of target accounts and specific accounts
Production-ready with persistent caching
"""

import json
import time
import random
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    PleaseWaitFewMinutes,
    UserNotFound,
    ClientError
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FollowCache:
    """Persistent cache to track all follow attempts."""

    def __init__(self, cache_file: str = "follow_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} users from cache")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def is_processed(self, user_id: int) -> bool:
        """Check if user has been processed before."""
        return str(user_id) in self.cache

    def add_user(self, user_id: int, username: str, status: str, source: str = ""):
        """Add user to cache with metadata."""
        self.cache[str(user_id)] = {
            "username": username,
            "status": status,  # "followed", "failed", "skipped", "already_following"
            "source": source,  # target account or "specific"
            "timestamp": datetime.now().isoformat(),
            "attempts": self.cache.get(str(user_id), {}).get("attempts", 0) + 1
        }
        self._save_cache()

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user info from cache."""
        return self.cache.get(str(user_id))

    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "total": len(self.cache),
            "followed": 0,
            "failed": 0,
            "skipped": 0,
            "already_following": 0
        }
        for user_data in self.cache.values():
            status = user_data.get("status", "unknown")
            if status in stats:
                stats[status] += 1
        return stats

    def clear_failed(self):
        """Clear failed attempts to retry them."""
        to_remove = [uid for uid, data in self.cache.items() if data.get("status") == "failed"]
        for uid in to_remove:
            del self.cache[uid]
        self._save_cache()
        logger.info(f"Cleared {len(to_remove)} failed entries from cache")


class InstagramFollowerBot:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the bot with configuration."""
        self.config = self._load_config(config_path)
        self.client = Client()
        self.session_file = self.config["settings"].get("session_file", "session.json")
        cache_file = self.config["settings"].get("cache_file", "follow_cache.json")
        self.cache = FollowCache(cache_file)

        # Show cache stats on startup
        stats = self.cache.get_stats()
        logger.info(f"Cache stats: {stats['total']} total, {stats['followed']} followed, "
                   f"{stats['skipped']} skipped, {stats['failed']} failed")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)

    def login(self) -> bool:
        """Login to Instagram with session persistence."""
        try:
            # Try to load existing session
            if os.path.exists(self.session_file):
                logger.info("Loading existing session...")
                self.client.load_settings(self.session_file)
                self.client.login(
                    self.config["username"],
                    self.config["password"]
                )
                # Verify session is valid
                try:
                    self.client.get_timeline_feed()
                    logger.info("Session loaded successfully!")
                    return True
                except LoginRequired:
                    logger.info("Session expired, logging in fresh...")
                    os.remove(self.session_file)

            # Fresh login
            logger.info(f"Logging in as {self.config['username']}...")
            self.client.login(
                self.config["username"],
                self.config["password"]
            )

            # Save session for future use
            self.client.dump_settings(self.session_file)
            logger.info("Login successful! Session saved.")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def _delay(self):
        """Random delay between actions to avoid detection."""
        min_delay = self.config["settings"]["delay_between_follows_min"]
        max_delay = self.config["settings"]["delay_between_follows_max"]
        delay = random.uniform(min_delay, max_delay)
        logger.info(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def _should_follow_user(self, user_info, source: str = "") -> bool:
        """Check if user meets criteria for following."""
        settings = self.config["settings"]
        user_id = user_info.pk
        username = user_info.username

        # Check persistent cache first
        if self.cache.is_processed(user_id):
            cached = self.cache.get_user(user_id)
            logger.debug(f"Skipping {username}: already in cache (status: {cached['status']})")
            return False

        # Check follower count criteria
        follower_count = user_info.follower_count
        if follower_count < settings.get("min_followers", 0):
            logger.debug(f"Skipping {username}: too few followers ({follower_count})")
            self.cache.add_user(user_id, username, "skipped", source)
            return False
        if follower_count > settings.get("max_followers", float('inf')):
            logger.debug(f"Skipping {username}: too many followers ({follower_count})")
            self.cache.add_user(user_id, username, "skipped", source)
            return False

        # Check private account
        if settings.get("skip_private_accounts") and user_info.is_private:
            logger.debug(f"Skipping {username}: private account")
            self.cache.add_user(user_id, username, "skipped", source)
            return False

        # Check business account
        if settings.get("skip_business_accounts") and user_info.is_business:
            logger.debug(f"Skipping {username}: business account")
            self.cache.add_user(user_id, username, "skipped", source)
            return False

        return True

    def follow_user(self, user_id: int, username: str, source: str = "") -> bool:
        """Follow a single user."""
        try:
            result = self.client.user_follow(user_id)
            if result:
                self.cache.add_user(user_id, username, "followed", source)
                logger.info(f"Successfully followed: {username}")
                return True
            else:
                self.cache.add_user(user_id, username, "failed", source)
                logger.warning(f"Failed to follow: {username}")
                return False

        except PleaseWaitFewMinutes as e:
            self.cache.add_user(user_id, username, "failed", source)
            logger.warning(f"Rate limited! Waiting 5 minutes... ({e})")
            time.sleep(300)
            return False

        except ClientError as e:
            self.cache.add_user(user_id, username, "failed", source)
            logger.error(f"Error following {username}: {e}")
            return False

    def follow_specific_accounts(self, accounts: List[str]) -> int:
        """Follow specific accounts by username."""
        followed_count = 0

        for username in accounts:
            try:
                logger.info(f"Looking up user: {username}")
                user_id = self.client.user_id_from_username(username)

                # Check cache first
                if self.cache.is_processed(user_id):
                    cached = self.cache.get_user(user_id)
                    logger.info(f"Skipping {username}: already processed (status: {cached['status']})")
                    continue

                user_info = self.client.user_info(user_id)

                # Check if already following on Instagram
                if user_info.following:
                    logger.info(f"Already following: {username}")
                    self.cache.add_user(user_id, username, "already_following", "specific")
                    continue

                if self.follow_user(user_id, username, "specific"):
                    followed_count += 1
                    self._delay()

            except UserNotFound:
                logger.warning(f"User not found: {username}")
            except Exception as e:
                logger.error(f"Error processing {username}: {e}")

        return followed_count

    def follow_account_followers(self, target_username: str, max_to_follow: Optional[int] = None) -> int:
        """Follow followers of a target account."""
        if max_to_follow is None:
            max_to_follow = self.config["settings"]["max_followers_to_follow"]

        try:
            # Get target account info
            logger.info(f"Getting followers of: {target_username}")
            user_id = self.client.user_id_from_username(target_username)

            # Get more followers than needed to account for cached/skipped users
            fetch_amount = max_to_follow * 3
            followers = self.client.user_followers(user_id, amount=fetch_amount)
            logger.info(f"Found {len(followers)} followers")

            followed_count = 0
            processed_count = 0

            for follower_id, follower_info in followers.items():
                if followed_count >= max_to_follow:
                    logger.info(f"Reached maximum follow limit: {max_to_follow}")
                    break

                # Quick cache check before API call
                if self.cache.is_processed(follower_id):
                    cached = self.cache.get_user(follower_id)
                    logger.debug(f"Skipping {follower_info.username}: in cache (status: {cached['status']})")
                    continue

                try:
                    processed_count += 1

                    # Get full user info for criteria check
                    full_info = self.client.user_info(follower_id)

                    # Check if already following on Instagram
                    if full_info.following:
                        logger.debug(f"Already following: {follower_info.username}")
                        self.cache.add_user(follower_id, follower_info.username, "already_following", target_username)
                        continue

                    if not self._should_follow_user(full_info, target_username):
                        continue

                    if self.follow_user(follower_id, follower_info.username, target_username):
                        followed_count += 1
                        self._delay()

                except Exception as e:
                    logger.error(f"Error processing follower {follower_info.username}: {e}")
                    continue

            logger.info(f"Processed {processed_count} users, followed {followed_count}")
            return followed_count

        except UserNotFound:
            logger.error(f"Target account not found: {target_username}")
            return 0
        except Exception as e:
            logger.error(f"Error getting followers of {target_username}: {e}")
            return 0

    def run(self):
        """Main execution method."""
        if not self.login():
            logger.error("Failed to login. Exiting.")
            return

        total_followed = 0

        # Follow specific accounts first
        specific_accounts = self.config.get("specific_accounts_to_follow", [])
        if specific_accounts:
            logger.info(f"Following {len(specific_accounts)} specific accounts...")
            count = self.follow_specific_accounts(specific_accounts)
            total_followed += count
            logger.info(f"Followed {count} specific accounts")

        # Follow followers of target accounts
        target_accounts = self.config.get("target_accounts", [])
        for target in target_accounts:
            logger.info(f"\nProcessing target account: {target}")
            count = self.follow_account_followers(target)
            total_followed += count
            logger.info(f"Followed {count} users from {target}'s followers")

        # Final stats
        stats = self.cache.get_stats()
        logger.info(f"\n{'='*50}")
        logger.info(f"Session: Followed {total_followed} users")
        logger.info(f"Total cache: {stats['total']} users")
        logger.info(f"  - Followed: {stats['followed']}")
        logger.info(f"  - Skipped: {stats['skipped']}")
        logger.info(f"  - Failed: {stats['failed']}")
        logger.info(f"  - Already following: {stats['already_following']}")
        logger.info(f"{'='*50}")

    def show_stats(self):
        """Display cache statistics."""
        stats = self.cache.get_stats()
        print(f"\nCache Statistics:")
        print(f"  Total processed: {stats['total']}")
        print(f"  Followed: {stats['followed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Already following: {stats['already_following']}")

    def retry_failed(self):
        """Clear failed entries to retry them."""
        self.cache.clear_failed()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Follower Automation")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--target", help="Target account to follow followers of")
    parser.add_argument("--follow", nargs="+", help="Specific accounts to follow")
    parser.add_argument("--max", type=int, help="Maximum users to follow")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--retry-failed", action="store_true", help="Clear failed entries to retry")

    args = parser.parse_args()

    bot = InstagramFollowerBot(args.config)

    # Handle utility commands
    if args.stats:
        bot.show_stats()
        return

    if args.retry_failed:
        bot.retry_failed()
        return

    if not bot.login():
        return

    total = 0

    # Follow specific accounts if provided via CLI
    if args.follow:
        count = bot.follow_specific_accounts(args.follow)
        total += count
        print(f"Followed {count} specific accounts")

    # Follow target account's followers if provided via CLI
    if args.target:
        count = bot.follow_account_followers(args.target, args.max)
        total += count
        print(f"Followed {count} users from {args.target}'s followers")

    # Run from config if no CLI args
    if not args.follow and not args.target:
        bot.run()
    else:
        print(f"\nTotal followed: {total}")
        bot.show_stats()


if __name__ == "__main__":
    main()
