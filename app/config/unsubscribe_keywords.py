"""
Unsubscribe and email preference keywords configuration.

This module contains all the keywords used for identifying unsubscribe pages,
email preference centers, and related functionality across the domain crawler.
"""

# High priority keywords - these indicate strong likelihood of unsubscribe functionality
HIGH_PRIORITY_KEYWORDS = [
    # Direct unsubscribe terms
    'unsubscribe',
    'opt-out', 
    'opt out',
    
    # Preference-related terms
    'preferences',
    'preference center',
    'email preferences',
    'subscription preferences',
    'manage preferences',
    'marketing preferences',
    'communication preferences',
    
    # Settings and management
    'email settings',
    'manage email',
    'email management',
    'subscription management',
]

# Medium priority keywords - these might lead to unsubscribe pages
MEDIUM_PRIORITY_KEYWORDS = [
    # Legal and policy pages
    'privacy',
    'privacy policy',
    'legal',
    'terms',
    
    # Contact and support
    'contact',
    'support',
    'help',
    
    # Account and profile
    'account',
    'profile',
    'settings',
    'manage account',
    'account settings',
    
    # Communication
    'newsletter',
    'communications',
    'email communications',
]

# URL patterns that commonly contain unsubscribe functionality
UNSUBSCRIBE_URL_PATTERNS = [
    '/unsubscribe',
    '/opt-out',
    '/optout',
    '/preferences',
    '/email-preferences',
    '/subscription-preferences',
    '/manage-preferences',
    '/marketing-preferences',
    '/communication-preferences',
    '/email-settings',
    '/subscription-management',
    '/newsletter-preferences',
    '/email-management',
]

# Common subdomain patterns for unsubscribe pages
UNSUBSCRIBE_SUBDOMAIN_PATTERNS = [
    'preferences',
    'unsubscribe',
    'optout',
    'email',
    'newsletter',
    'manage',
    'account',
]

# Text patterns that indicate unsubscribe functionality
UNSUBSCRIBE_TEXT_PATTERNS = [
    'unsubscribe from',
    'stop receiving',
    'remove me',
    'cancel subscription',
    'email preferences',
    'manage your preferences',
    'update your preferences',
    'change your preferences',
    'subscription preferences',
    'marketing preferences',
    'communication preferences',
    'email settings',
    'manage email',
    'email management',
    'subscription management',
]

# Keywords for confidence scoring
CONFIDENCE_KEYWORDS = {
    # High confidence indicators
    'unsubscribe': 0.9,
    'opt-out': 0.9,
    'opt out': 0.9,
    'preferences': 0.8,
    'preference center': 0.8,
    'email preferences': 0.8,
    'subscription preferences': 0.8,
    'manage preferences': 0.8,
    'marketing preferences': 0.8,
    'communication preferences': 0.8,
    'email settings': 0.7,
    'manage email': 0.7,
    'email management': 0.7,
    'subscription management': 0.7,
    
    # Medium confidence indicators
    'privacy': 0.6,
    'privacy policy': 0.6,
    'contact': 0.5,
    'support': 0.5,
    'account': 0.5,
    'profile': 0.5,
    'settings': 0.5,
    'manage account': 0.5,
    'newsletter': 0.4,
    'communications': 0.4,
    'email communications': 0.4,
}

# Context-based confidence bonuses
CONTEXT_BONUSES = {
    'footer': 0.3,
    'navigation': 0.2,
    'sidebar': 0.1,
    'header': 0.1,
}

# Minimum confidence thresholds
MIN_CONFIDENCE_THRESHOLDS = {
    'confident_result': 0.8,  # Minimum confidence for a confident result
    'promising_link': 0.3,    # Minimum confidence for a promising link
    'candidate': 0.5,         # Minimum confidence for a candidate
}
