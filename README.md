# Instagram Follower Automation

Automated Instagram follower tool using [Instagrapi](https://github.com/subzeroid/instagrapi).

## Features

- Follow followers of target accounts
- Follow specific accounts directly
- Session persistence (avoids repeated logins)
- Rate limiting protection
- Configurable filters (follower count, private/business accounts)
- Random delays to mimic human behavior

## Installation

```bash
cd instagram_automation
pip install -r requirements.txt
```

## Configuration

Edit `config.json`:

```json
{
    "username": "YOUR_INSTAGRAM_USERNAME",
    "password": "YOUR_INSTAGRAM_PASSWORD",
    "target_accounts": ["account_to_follow_their_followers"],
    "specific_accounts_to_follow": ["user1", "user2"],
    "settings": {
        "max_followers_to_follow": 50,
        "delay_between_follows_min": 30,
        "delay_between_follows_max": 60,
        "skip_private_accounts": false,
        "skip_business_accounts": false,
        "min_followers": 10,
        "max_followers": 10000
    }
}
```

## Usage

### Run from config file
```bash
python instagram_follower.py
```

### Follow specific accounts via CLI
```bash
python instagram_follower.py --follow user1 user2 user3
```

### Follow followers of a target account
```bash
python instagram_follower.py --target celebrity_account --max 100
```

### Use custom config
```bash
python instagram_follower.py --config my_config.json
```

## Important Notes

- Use responsibly to avoid account restrictions
- Instagram has rate limits (~60 follows/hour, ~200/day recommended max)
- Session is saved to avoid repeated 2FA challenges
- Delays are randomized to appear human-like

## Disclaimer

This tool is for educational purposes. Use at your own risk. Automated actions may violate Instagram's Terms of Service.
