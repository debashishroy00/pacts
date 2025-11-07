"""
Runtime Profile Management for PACTS Universal Discovery

Automatically detects whether the target application is a static HTML site
or a dynamic SPA, and adjusts discovery/execution behavior accordingly.

Week 8 EDR: Universal Discovery & Planner Cohesion Architecture
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from backend.utils import ulog  # Week 8 EDR: Unified structured logging

logger = logging.getLogger(__name__)

# Profile types
STATIC = "STATIC"
DYNAMIC = "DYNAMIC"


@dataclass
class ProfileConfig:
    """Configuration for a runtime profile."""
    name: str
    network_idle_timeout: int  # ms
    element_visible_timeout: int  # ms
    post_action_settle: int  # ms
    max_heal_rounds: int
    cache_ttl: int  # seconds
    retry_on_stale: bool


# Profile configurations
PROFILE_CONFIGS: Dict[str, ProfileConfig] = {
    STATIC: ProfileConfig(
        name=STATIC,
        network_idle_timeout=2000,
        element_visible_timeout=5000,
        post_action_settle=300,
        max_heal_rounds=3,
        cache_ttl=3600,  # 1 hour
        retry_on_stale=True,
    ),
    DYNAMIC: ProfileConfig(
        name=DYNAMIC,
        network_idle_timeout=5000,
        element_visible_timeout=10000,
        post_action_settle=1500,
        max_heal_rounds=5,
        cache_ttl=1800,  # 30 minutes
        retry_on_stale=True,
    ),
}


def detect_profile(url: str, html_content: Optional[str] = None) -> str:
    """
    Auto-detect runtime profile based on URL and optional HTML content.

    Args:
        url: Current page URL
        html_content: Optional page HTML for deeper inspection

    Returns:
        Profile name (STATIC or DYNAMIC)
    """
    url_lower = url.lower()

    # Explicit SPA patterns
    spa_indicators = [
        "lightning.force.com",
        "salesforce.com",
        "/app/",
        "/react/",
        "/angular/",
        "/vue/",
        "github.com",
        "notion.so",
        "trello.com",
        "asana.com",
    ]

    for indicator in spa_indicators:
        if indicator in url_lower:
            logger.info(f"[PROFILE] Detected DYNAMIC (SPA) from URL pattern: {indicator}")
            return DYNAMIC

    # Inspect HTML content if available
    if html_content:
        html_lower = html_content.lower()

        # Check for SPA framework signatures
        spa_frameworks = [
            "react",
            "angular",
            "vue.js",
            "__next",
            "nuxt",
            "svelte",
            "ember",
            "backbone",
        ]

        for framework in spa_frameworks:
            if framework in html_lower:
                logger.info(f"[PROFILE] Detected DYNAMIC (SPA) from HTML content: {framework}")
                return DYNAMIC

    # Default to STATIC for traditional websites
    logger.info(f"[PROFILE] Detected STATIC (traditional web)")
    return STATIC


def get_profile(url: str, html_content: Optional[str] = None) -> str:
    """
    Get runtime profile with override support.

    Priority:
    1. PACTS_PROFILE_OVERRIDE (env var)
    2. Auto-detection from URL/HTML
    3. PACTS_PROFILE_DEFAULT (env var)
    4. STATIC (fallback)

    Args:
        url: Current page URL
        html_content: Optional page HTML for deeper inspection

    Returns:
        Profile name (STATIC or DYNAMIC)
    """
    # Check for explicit override
    override = os.getenv("PACTS_PROFILE_OVERRIDE", "").strip().upper()
    if override in (STATIC, DYNAMIC):
        logger.info(f"[PROFILE] Using override: {override}")
        ulog.profile(using=override, detail="env-override")
        return override

    # Auto-detect
    detected = detect_profile(url, html_content)

    # Determine signal for logging
    signal = ""
    if "lightning.force.com" in url.lower():
        signal = "sf-lightning"
    elif "react" in (html_content or "").lower():
        signal = "react"
    elif "angular" in (html_content or "").lower():
        signal = "angular"
    else:
        signal = url[:50]  # First 50 chars of URL

    # Fall back to default if set
    default = os.getenv("PACTS_PROFILE_DEFAULT", "").strip().upper()
    if default in (STATIC, DYNAMIC) and not detected:
        logger.info(f"[PROFILE] Using default: {default}")
        ulog.profile(using=default, detail="env-default")
        return default

    # Use detected profile
    logger.info(f"[PROFILE] Using detected profile: {detected}")
    ulog.profile(using=detected, detail=signal)
    return detected


def get_config(profile: str) -> ProfileConfig:
    """
    Get configuration for a runtime profile.

    Args:
        profile: Profile name (STATIC or DYNAMIC)

    Returns:
        ProfileConfig instance
    """
    if profile not in PROFILE_CONFIGS:
        logger.warning(f"[PROFILE] Unknown profile '{profile}', using STATIC")
        profile = STATIC

    config = PROFILE_CONFIGS[profile]
    logger.debug(f"[PROFILE] Config for {profile}: {config}")
    return config


def get_cache_key_prefix(url: str, profile: Optional[str] = None) -> str:
    """
    Generate cache key prefix with profile.

    Format: {domain}:{profile}
    Example: lightning.force.com:DYNAMIC

    Args:
        url: Current page URL
        profile: Optional profile override (auto-detected if None)

    Returns:
        Cache key prefix string
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc or "unknown"

    if profile is None:
        profile = get_profile(url)

    prefix = f"{domain}:{profile}"
    logger.debug(f"[PROFILE] Cache key prefix: {prefix}")
    return prefix


def log_profile_info(url: str, profile: Optional[str] = None) -> None:
    """
    Log profile detection and configuration details.

    Args:
        url: Current page URL
        profile: Optional profile override (auto-detected if None)
    """
    if profile is None:
        profile = get_profile(url)

    config = get_config(profile)

    logger.info(f"[PROFILE] ═══════════════════════════════════════")
    logger.info(f"[PROFILE] URL: {url}")
    logger.info(f"[PROFILE] Profile: {profile}")
    logger.info(f"[PROFILE] Network Idle Timeout: {config.network_idle_timeout}ms")
    logger.info(f"[PROFILE] Element Visible Timeout: {config.element_visible_timeout}ms")
    logger.info(f"[PROFILE] Post-Action Settle: {config.post_action_settle}ms")
    logger.info(f"[PROFILE] Max Heal Rounds: {config.max_heal_rounds}")
    logger.info(f"[PROFILE] Cache TTL: {config.cache_ttl}s")
    logger.info(f"[PROFILE] ═══════════════════════════════════════")
