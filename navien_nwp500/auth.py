"""
Authentication handling for NaviLink service.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aiohttp

from .config import NaviLinkConfig
from .exceptions import APIError, AuthenticationError, InvalidCredentialsError
from .models import UserInfo

logger = logging.getLogger(__name__)

class NaviLinkAuth:
    """
    Handles authentication and token management for NaviLink service.
    
    Provides enterprise-grade session management with automatic token refresh
    and comprehensive error handling.
    """
    
    def __init__(self, session: aiohttp.ClientSession, config: NaviLinkConfig):
        """
        Initialize authentication handler.
        
        Args:
            session: aiohttp session to use for requests
            config: NaviLink configuration object
        """
        self._session = session
        self.config = config
        self._user_info: Optional[UserInfo] = None
        self._credentials: Optional[Dict[str, str]] = None
        self._aws_credentials: Optional[Dict[str, str]] = None
        self._auth_headers: Optional[Dict[str, str]] = None
        self._authenticated_at: Optional[datetime] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        if self._owns_session:
            self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._owns_session and self._session:
            await self._session.close()
            
    async def authenticate(self, email: str, password: str) -> UserInfo:
        """
        Authenticate with NaviLink service.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            UserInfo object with authentication details
            
        Raises:
            AuthenticationError: If authentication fails
            InvalidCredentialsError: If credentials are invalid
            APIError: If API request fails
        """
        if not self._session:
            raise AuthenticationError("No session available")
            
        self._credentials = {"email": email, "password": password}
        
        try:
            async with self._session.post(
                f"{self.config.base_url}/user/sign-in",
                json={
                    "userId": email,  # Based on HAR, it's userId not email
                    "password": password
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "NaviLink-Python/0.1.0"
                }
            ) as response:
                if response.status == 401:
                    raise InvalidCredentialsError("Invalid email or password")
                elif response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Authentication failed: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                data = await response.json()
                logger.debug("Authentication successful")
                
                # Parse user info from response
                self._user_info = self._parse_user_info(data)
                return self._user_info
                
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Network error during authentication: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, InvalidCredentialsError, APIError)):
                raise
            raise AuthenticationError(f"Unexpected error during authentication: {e}")
    
    def _parse_user_info(self, response_data: Dict[str, Any]) -> UserInfo:
        """
        Parse user information from authentication response.
        
        Args:
            response_data: Response data from sign-in API
            
        Returns:
            UserInfo object
        """
        try:
            # Extract from the actual response structure based on HAR analysis
            data = response_data.get("data", {})
            user_info_data = data.get("userInfo", {})
            token_data = data.get("token", {})
            
            user_info = UserInfo(
                user_id=str(user_info_data.get("userSeq", "")),
                email=self._credentials.get("email", ""),  # Not returned in response
                user_type=user_info_data.get("userType", "O"),
                group_id=None,  # Will be determined later from device responses
                session_token=token_data.get("accessToken"),
                refresh_token=token_data.get("refreshToken"),
                token_expires_at=self._calculate_token_expiry(token_data)
            )
            
            # Store AWS credentials for WebSocket connection
            self._aws_credentials = {
                "accessKeyId": token_data.get("accessKeyId"),
                "secretKey": token_data.get("secretKey"),
                "sessionToken": token_data.get("sessionToken")
            }
            
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to parse user info: {e}")
            logger.debug(f"Response data: {response_data}")
            raise AuthenticationError(f"Failed to parse authentication response: {e}")
    
    def _calculate_token_expiry(self, token_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate when the token expires.
        
        Args:
            token_data: Token data from sign-in API response
            
        Returns:
            Token expiry datetime or None if not available
        """
        # Check for explicit expiry time in token data
        if "authenticationExpiresIn" in token_data:
            try:
                expires_in_seconds = int(token_data["authenticationExpiresIn"])
                return datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            except (ValueError, TypeError):
                pass
        
        if "authorizationExpiresIn" in token_data:
            try:
                expires_in_seconds = int(token_data["authorizationExpiresIn"])
                return datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            except (ValueError, TypeError):
                pass
                
        # Check for explicit expiry time in response
        if "expiresAt" in token_data:
            try:
                return datetime.fromisoformat(token_data["expiresAt"])
            except ValueError:
                pass
        
        if "expiresIn" in token_data:
            try:
                expires_in_seconds = int(token_data["expiresIn"])
                return datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            except (ValueError, TypeError):
                pass
        
        # Default to 1 hour based on HAR data showing 3600 seconds
        return datetime.utcnow() + timedelta(hours=1)
    
    async def refresh_token(self) -> UserInfo:
        """
        Refresh authentication token if possible.
        
        Returns:
            Updated UserInfo object
            
        Raises:
            AuthenticationError: If refresh fails
        """
        if not self._user_info or not self._user_info.refresh_token:
            # Fall back to re-authentication with stored credentials
            if self._credentials:
                logger.info("No refresh token available, re-authenticating")
                return await self.authenticate(
                    self._credentials["email"], 
                    self._credentials["password"]
                )
            else:
                raise AuthenticationError("No refresh token or credentials available")
        
        # TODO: Implement refresh token endpoint if available
        # For now, fall back to re-authentication
        if self._credentials:
            logger.info("Re-authenticating due to lack of refresh endpoint")
            return await self.authenticate(
                self._credentials["email"], 
                self._credentials["password"]
            )
        else:
            raise AuthenticationError("Cannot refresh token without stored credentials")
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated with valid token.
        
        Returns:
            True if authenticated and token is valid
        """
        if not self._user_info or not self._user_info.session_token:
            return False
            
        if self._user_info.token_expires_at:
            return datetime.utcnow() < self._user_info.token_expires_at
            
        return True
    
    async def ensure_authenticated(self) -> UserInfo:
        """
        Ensure we have a valid authentication token.
        
        Returns:
            UserInfo object with valid token
            
        Raises:
            AuthenticationError: If authentication cannot be established
        """
        if self.is_authenticated():
            return self._user_info
            
        logger.info("Token expired or missing, refreshing authentication")
        return await self.refresh_token()
    
    @property
    def user_info(self) -> Optional[UserInfo]:
        """Get current user info."""
        return self._user_info
    
    @property 
    def session_token(self) -> Optional[str]:
        """Get current session token."""
        return self._user_info.session_token if self._user_info else None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get headers for authenticated requests.
        
        Returns:
            Dictionary of headers to include in requests
        """
        headers = {
            "User-Agent": "NaviLink-Python/0.1.0",
            "Content-Type": "application/json"
        }
        
        # Based on HAR analysis, use raw token without Bearer prefix
        if self._user_info and self._user_info.session_token:
            headers["authorization"] = self._user_info.session_token
            
        return headers
    
    @property
    def aws_credentials(self) -> Optional[Dict[str, str]]:
        """Get AWS credentials for WebSocket connection."""
        return self._aws_credentials