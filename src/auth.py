import json
import os
import secrets
import string
import logging
from datetime import datetime, timedelta
from typing import Optional, Union

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages user authentication via one-time access keys with optional time limits.
    
    Data structure:
    - valid_keys: {key: duration_hours or None}
    - authorized_users: {user_id: expiration_timestamp or None}
    
    None = permanent access
    """
    def __init__(self, db_file="access_db.json"):
        self.db_file = db_file
        self.authorized_users = {}  # {user_id: expiration_timestamp or None}
        self.valid_keys = {}        # {key: duration_hours or None}
        self._load_db()

    def _load_db(self):
        """Load data from JSON file with automatic migration"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    data = json.load(f)
                    
                    # Migrate old format (set) to new format (dict)
                    raw_users = data.get('authorized_users', [])
                    if isinstance(raw_users, list):
                        # Old format or new format stored as list
                        # Check if it's a list of user_ids (old) or list of [user_id, expiration] (new)
                        self.authorized_users = {}
                        for item in raw_users:
                            if isinstance(item, (list, tuple)) and len(item) == 2:
                                # New format: [user_id, expiration]
                                self.authorized_users[item[0]] = item[1]
                            else:
                                # Old format: just user_id - give permanent access
                                self.authorized_users[item] = None
                    else:
                        self.authorized_users = raw_users
                    
                    # Migrate valid_keys
                    raw_keys = data.get('valid_keys', [])
                    if isinstance(raw_keys, list):
                        # Old format: list of keys (no duration)
                        self.valid_keys = {key: None for key in raw_keys}
                    else:
                        self.valid_keys = raw_keys
                
                logger.info(f"Auth loaded: {len(self.authorized_users)} users, {len(self.valid_keys)} keys")
            except Exception as e:
                logger.error(f"Error loading auth db: {e}")
                self.authorized_users = {}
                self.valid_keys = {}

    def _save_db(self):
        """Save data to JSON file"""
        try:
            # Convert dicts to list format for JSON serialization
            users_list = [[user_id, expiration] for user_id, expiration in self.authorized_users.items()]
            keys_dict = self.valid_keys
            
            data = {
                'authorized_users': users_list,
                'valid_keys': keys_dict
            }
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving auth db: {e}")

    def is_authorized(self, user_id: int) -> bool:
        """
        Check if a user is authorized.
        Also checks expiration for time-limited users.
        """
        if user_id not in self.authorized_users:
            return False
        
        expiration = self.authorized_users[user_id]
        
        # None = permanent access
        if expiration is None:
            return True
        
        # Check if expired
        now = datetime.now().timestamp()
        if now > expiration:
            # User expired, remove them
            del self.authorized_users[user_id]
            self._save_db()
            logger.info(f"User {user_id} access expired and removed")
            return False
        
        return True

    def generate_key(self, duration_hours: Optional[float] = None) -> str:
        """
        Generate a new random access key and save it.
        
        Args:
            duration_hours: Duration in hours (None for permanent access)
        
        Returns:
            Generated key string
        """
        # Format: XXXX-XXXX-XXXX
        part1 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        part2 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        part3 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        key = f"{part1}-{part2}-{part3}"
        
        self.valid_keys[key] = duration_hours
        self._save_db()
        return key

    def redeem_key(self, key: str, user_id: int) -> bool:
        """
        Attempt to redeem a key for a user.
        The expiration timer starts when the key is redeemed.
        
        Returns True if successful, False if invalid.
        """
        # Reload DB to catch keys generated by external script
        self._load_db()
        
        key = key.strip().upper()
        if key not in self.valid_keys:
            return False
        
        duration_hours = self.valid_keys[key]
        
        # Calculate expiration timestamp
        if duration_hours is None:
            expiration = None  # Permanent access
        else:
            expiration = (datetime.now() + timedelta(hours=duration_hours)).timestamp()
        
        # Remove key and add user
        del self.valid_keys[key]
        self.authorized_users[user_id] = expiration
        self._save_db()
        
        if expiration:
            logger.info(f"Key redeemed by user {user_id} with {duration_hours}h access")
        else:
            logger.info(f"Key redeemed by user {user_id} with permanent access")
        
        return True
    
    def get_user_expiration(self, user_id: int) -> Optional[datetime]:
        """Get the expiration datetime for a user (None if permanent)"""
        if user_id not in self.authorized_users:
            return None
        
        expiration = self.authorized_users[user_id]
        if expiration is None:
            return None
        
        return datetime.fromtimestamp(expiration)
