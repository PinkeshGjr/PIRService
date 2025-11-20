#!/usr/bin/env python3
"""
Instagram Follower Automation using Instagrapi
Follow followers of target accounts and specific accounts
"""

import json
import time
import random
import logging
import os
from pathlib import Path
from typing import List, Optional
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


class InstagramFollowerBot:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the bot with configuration."""
        self.config = self._load_config(config_path)
        self.client = Client()
        self.followed_users = set()
        self.session_file = self.config["settings"].get("session_file", "session.json")

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

    def _should_follow_user(self, user_info) -> bool:
        """Check if user meets criteria for following."""
        settings = self.config["settings"]

        # Check if already following
        if user_info.pk in self.followed_users:
            return False

        # Check follower count criteria
        follower_count = user_info.follower_count
        if follower_count < settings.get("min_followers", 0):
            logger.debug(f"Skipping {user_info.username}: too few followers ({follower_count})")
            return False
        if follower_count > settings.get("max_followers", float('inf')):
            logger.debug(f"Skipping {user_info.username}: too many followers ({follower_count})")
            return False

        # Check private account
        if settings.get("skip_private_accounts") and user_info.is_private:
            logger.debug(f"Skipping {user_info.username}: private account")
            return False

        # Check business account
        if settings.get("skip_business_accounts") and user_info.is_business:
            logger.debug(f"Skipping {user_info.username}: business account")
            return False

        return True

    def follow_user(self, user_id: int, username: str) -> bool:
        """Follow a single user."""
        try:
            result = self.client.user_follow(user_id)
            if result:
                self.followed_users.add(user_id)
                logger.info(f"Successfully followed: {username}")
                return True
            else:
                logger.warning(f"Failed to follow: {username}")
                return False

        except PleaseWaitFewMinutes as e:
            logger.warning(f"Rate limited! Waiting 5 minutes... ({e})")
            time.sleep(300)
            return False

        except ClientError as e:
            logger.error(f"Error following {username}: {e}")
            return False

    def follow_specific_accounts(self, accounts: List[str]) -> int:
        """Follow specific accounts by username."""
        followed_count = 0

        for username in accounts:
            try:
                logger.info(f"Looking up user: {username}")
                user_id = self.client.user_id_from_username(username)
                user_info = self.client.user_info(user_id)

                # Check if already following
                if user_info.following:
                    logger.info(f"Already following: {username}")
                    continue

                if self.follow_user(user_id, username):
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

            # Get followers
            followers = self.client.user_followers(user_id, amount=max_to_follow * 2)
            logger.info(f"Found {len(followers)} followers")

            followed_count = 0

            for follower_id, follower_info in followers.items():
                if followed_count >= max_to_follow:
                    logger.info(f"Reached maximum follow limit: {max_to_follow}")
                    break

                try:
                    # Get full user info for criteria check
                    full_info = self.client.user_info(follower_id)

                    # Check if already following
                    if full_info.following:
                        logger.debug(f"Already following: {follower_info.username}")
                        continue

                    if not self._should_follow_user(full_info):
                        continue

                    if self.follow_user(follower_id, follower_info.username):
                        followed_count += 1
                        self._delay()

                except Exception as e:
                    logger.error(f"Error processing follower {follower_info.username}: {e}")
                    continue

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

        logger.info(f"\n{'='*50}")
        logger.info(f"Total users followed this session: {total_followed}")
        logger.info(f"{'='*50}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Follower Automation")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--target", help="Target account to follow followers of")
    parser.add_argument("--follow", nargs="+", help="Specific accounts to follow")
    parser.add_argument("--max", type=int, help="Maximum users to follow")

    args = parser.parse_args()

    bot = InstagramFollowerBot(args.config)

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


if __name__ == "__main__":
    main()
