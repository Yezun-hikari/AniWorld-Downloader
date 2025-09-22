"""
Database models and utilities for AniWorld Downloader web authentication
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List


class UserDatabase:
    """SQLite database manager for user authentication"""

    def __init__(self, db_path: str = "aniworld.db"):
        """
        Initialize the user database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT 0,
                    is_original_admin BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)

            # Create sessions table for session management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_token TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # Create download queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anime_title TEXT NOT NULL,
                    episode_urls TEXT NOT NULL,
                    language TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    total_episodes INTEGER NOT NULL,
                    completed_episodes INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'queued',
                    current_episode TEXT DEFAULT '',
                    progress_percentage REAL DEFAULT 0,
                    error_message TEXT DEFAULT '',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
                )
            """)

            conn.commit()

    def _hash_password(self, password: str, salt: str) -> str:
        """
        Hash a password with salt using SHA-256.

        Args:
            password: Plain text password
            salt: Salt string

        Returns:
            Hashed password
        """
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def create_user(self, username: str, password: str, is_admin: bool = False, is_original_admin: bool = False) -> bool:
        """
        Create a new user.

        Args:
            username: Username
            password: Plain text password
            is_admin: Whether user should have admin privileges
            is_original_admin: Whether this is the original admin user

        Returns:
            True if user was created successfully, False otherwise
        """
        try:
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, is_admin, is_original_admin)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, password_hash, salt, is_admin, is_original_admin))
                conn.commit()
                return True

        except sqlite3.IntegrityError:
            # Username already exists
            return False
        except Exception:
            return False

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify user credentials.

        Args:
            username: Username
            password: Plain text password

        Returns:
            User dictionary if credentials are valid, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, salt, is_admin, is_original_admin
                    FROM users WHERE username = ?
                """, (username,))

                row = cursor.fetchone()
                if not row:
                    return None

                user_id, username, stored_hash, salt, is_admin, is_original_admin = row

                # Verify password
                if self._hash_password(password, salt) == stored_hash:
                    # Update last login
                    cursor.execute("""
                        UPDATE users SET last_login = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (user_id,))
                    conn.commit()

                    return {
                        'id': user_id,
                        'username': username,
                        'is_admin': bool(is_admin),
                        'is_original_admin': bool(is_original_admin)
                    }

                return None

        except Exception:
            return None

    def create_session(self, user_id: int) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User ID

        Returns:
            Session token
        """
        session_token = secrets.token_urlsafe(32)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Clean up expired sessions first
            cursor.execute("""
                DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP
            """)

            # Create new session (expires in 30 days)
            cursor.execute("""
                INSERT INTO sessions (session_token, user_id, expires_at)
                VALUES (?, ?, datetime('now', '+30 days'))
            """, (session_token, user_id))

            conn.commit()

        return session_token

    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """
        Get user information by session token.

        Args:
            session_token: Session token

        Returns:
            User dictionary if session is valid, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.id, u.username, u.is_admin, u.is_original_admin
                    FROM users u
                    JOIN sessions s ON u.id = s.user_id
                    WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
                """, (session_token,))

                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'is_admin': bool(row[2]),
                        'is_original_admin': bool(row[3])
                    }

                return None

        except Exception:
            return None

    def delete_session(self, session_token: str) -> bool:
        """
        Delete a session (logout).

        Args:
            session_token: Session token to delete

        Returns:
            True if session was deleted, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sessions WHERE session_token = ?
                """, (session_token,))
                conn.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    def get_all_users(self) -> List[Dict]:
        """
        Get all users (admin only).

        Returns:
            List of user dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, is_admin, is_original_admin, created_at, last_login
                    FROM users ORDER BY username
                """)

                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row[0],
                        'username': row[1],
                        'is_admin': bool(row[2]),
                        'is_original_admin': bool(row[3]),
                        'created_at': row[4],
                        'last_login': row[5]
                    })

                return users

        except Exception:
            return []

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if user was deleted, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    def update_user(self, user_id: int, username: str = None, password: str = None, is_admin: bool = None) -> bool:
        """
        Update user information.

        Args:
            user_id: User ID to update
            username: New username (optional)
            password: New password (optional)
            is_admin: New admin status (optional)

        Returns:
            True if user was updated, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if username is not None:
                    updates.append("username = ?")
                    params.append(username)

                if password is not None:
                    salt = secrets.token_hex(16)
                    password_hash = self._hash_password(password, salt)
                    updates.append("password_hash = ?")
                    updates.append("salt = ?")
                    params.extend([password_hash, salt])

                if is_admin is not None:
                    updates.append("is_admin = ?")
                    params.append(is_admin)

                if not updates:
                    return True  # Nothing to update

                params.append(user_id)

                cursor.execute(f"""
                    UPDATE users SET {', '.join(updates)}
                    WHERE id = ?
                """, params)

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.IntegrityError:
            # Username already exists
            return False
        except Exception:
            return False

    def has_users(self) -> bool:
        """
        Check if any users exist in the database.

        Returns:
            True if at least one user exists, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                return count > 0

        except Exception:
            return False

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change a user's password.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password

        Returns:
            True if password was changed successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get current password hash and salt
                cursor.execute("""
                    SELECT password_hash, salt FROM users WHERE id = ?
                """, (user_id,))

                row = cursor.fetchone()
                if not row:
                    return False

                stored_hash, salt = row

                # Verify current password
                if self._hash_password(current_password, salt) != stored_hash:
                    return False

                # Generate new salt and hash for new password
                new_salt = secrets.token_hex(16)
                new_hash = self._hash_password(new_password, new_salt)

                # Update password
                cursor.execute("""
                    UPDATE users SET password_hash = ?, salt = ?
                    WHERE id = ?
                """, (new_hash, new_salt, user_id))

                conn.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP
                """)
                conn.commit()

        except Exception:
            pass

    # Download Queue Management Methods
    def add_to_download_queue(self, anime_title: str, episode_urls: list, language: str, provider: str, total_episodes: int, created_by: int = None) -> int:
        """Add a new download job to the queue."""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO download_queue (anime_title, episode_urls, language, provider, total_episodes, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (anime_title, json.dumps(episode_urls), language, provider, total_episodes, created_by))
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None

    def get_next_queued_download(self):
        """Get the next download job in the queue."""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, anime_title, episode_urls, language, provider, total_episodes
                    FROM download_queue
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'anime_title': row[1],
                        'episode_urls': json.loads(row[2]),
                        'language': row[3],
                        'provider': row[4],
                        'total_episodes': row[5]
                    }
                return None
        except Exception:
            return None

    def update_download_status(self, queue_id: int, status: str, completed_episodes: int = None, current_episode: str = None, error_message: str = None, total_episodes: int = None):
        """Update the status of a download job."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                updates = ["status = ?"]
                params = [status]

                if completed_episodes is not None:
                    updates.append("completed_episodes = ?")
                    params.append(completed_episodes)

                if current_episode is not None:
                    updates.append("current_episode = ?")
                    params.append(current_episode)

                if error_message is not None:
                    updates.append("error_message = ?")
                    params.append(error_message)

                if total_episodes is not None:
                    updates.append("total_episodes = ?")
                    params.append(total_episodes)

                # Update timestamps based on status
                if status == 'downloading':
                    updates.append("started_at = CURRENT_TIMESTAMP")
                elif status in ['completed', 'failed']:
                    updates.append("completed_at = CURRENT_TIMESTAMP")

                # Calculate progress percentage
                if completed_episodes is not None:
                    # Get total episodes for this job
                    cursor.execute("SELECT total_episodes FROM download_queue WHERE id = ?", (queue_id,))
                    total = cursor.fetchone()
                    if total:
                        percentage = (completed_episodes / total[0]) * 100 if total[0] > 0 else 0
                        updates.append("progress_percentage = ?")
                        params.append(percentage)

                params.append(queue_id)

                cursor.execute(f"""
                    UPDATE download_queue SET {', '.join(updates)}
                    WHERE id = ?
                """, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_download_queue_status(self):
        """Get the current status of all downloads (active + last 3 completed)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get active downloads (queued, downloading)
                cursor.execute("""
                    SELECT id, anime_title, total_episodes, completed_episodes, status,
                           current_episode, progress_percentage, error_message, created_at
                    FROM download_queue
                    WHERE status IN ('queued', 'downloading')
                    ORDER BY created_at ASC
                """)
                active_downloads = []
                for row in cursor.fetchall():
                    active_downloads.append({
                        'id': row[0],
                        'anime_title': row[1],
                        'total_episodes': row[2],
                        'completed_episodes': row[3],
                        'status': row[4],
                        'current_episode': row[5],
                        'progress_percentage': row[6],
                        'error_message': row[7],
                        'created_at': row[8]
                    })

                # Get last completed download
                cursor.execute("""
                    SELECT id, anime_title, total_episodes, completed_episodes, status,
                           current_episode, progress_percentage, error_message, completed_at
                    FROM download_queue
                    WHERE status IN ('completed', 'failed')
                    ORDER BY completed_at DESC
                    LIMIT 1
                """)
                completed_downloads = []
                for row in cursor.fetchall():
                    completed_downloads.append({
                        'id': row[0],
                        'anime_title': row[1],
                        'total_episodes': row[2],
                        'completed_episodes': row[3],
                        'status': row[4],
                        'current_episode': row[5],
                        'progress_percentage': row[6],
                        'error_message': row[7],
                        'completed_at': row[8]
                    })

                return {
                    'active': active_downloads,
                    'completed': completed_downloads
                }
        except Exception:
            return {'active': [], 'completed': []}

    def cleanup_old_downloads(self, keep_completed: int = 10):
        """Clean up old completed downloads, keeping only the most recent ones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM download_queue
                    WHERE status IN ('completed', 'failed')
                    AND id NOT IN (
                        SELECT id FROM download_queue
                        WHERE status IN ('completed', 'failed')
                        ORDER BY completed_at DESC
                        LIMIT ?
                    )
                """, (keep_completed,))
                conn.commit()
        except Exception:
            pass