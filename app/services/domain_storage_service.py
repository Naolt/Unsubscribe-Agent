import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from app.models.domain_crawler import (
    DomainQueryRequest,
    DomainQueryResult,
    UnsubscribeCandidate
)

logger = logging.getLogger(__name__)


class DomainStorageService:
    """Service for storing and querying domain unsubscribe page index"""
    
    def __init__(self, storage_path: str = "data/domain_index.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, dict] = {}
        self._load_index()
        logger.info(f"DomainStorageService initialized with {len(self._index)} domains")
    
    def _load_index(self):
        """Load the domain index from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self._index = json.load(f)
                logger.info(f"Loaded domain index with {len(self._index)} domains")
            except Exception as e:
                logger.error(f"Failed to load domain index: {e}")
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self):
        """Save the domain index to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self._index, f, indent=2, default=str)
            logger.debug(f"Saved domain index with {len(self._index)} domains")
        except Exception as e:
            logger.error(f"Failed to save domain index: {e}")
    
    def add_domain_entry(self, domain: str, candidate: UnsubscribeCandidate):
        """Add or update a domain entry in the index"""
        logger.info(f"Adding domain entry for {domain}: {candidate.url}")
        
        self._index[domain] = {
            "unsubscribe_url": candidate.url,
            "confidence": candidate.confidence,
            "discovered_at": datetime.utcnow().isoformat(),
            "last_verified": None,
            "reason": candidate.reason,
            "found_on_page": candidate.found_on_page,
            "has_email_form": candidate.has_email_form,
            "has_unsubscribe_text": candidate.has_unsubscribe_text
        }
        
        self._save_index()
    
    def query_domain(self, request: DomainQueryRequest) -> DomainQueryResult:
        """Query the domain index for a specific domain"""
        logger.info(f"Querying domain index for {request.domain}")
        
        # Normalize domain (remove www, convert to lowercase)
        normalized_domain = self._normalize_domain(request.domain)
        
        if normalized_domain not in self._index:
            return DomainQueryResult(
                domain=request.domain,
                found=False
            )
        
        entry = self._index[normalized_domain]
        
        # Check if entry is considered inactive
        if not request.include_inactive:
            discovered_at = datetime.fromisoformat(entry["discovered_at"])
            cutoff_date = datetime.utcnow() - timedelta(days=30)  # 30 days
            
            if discovered_at < cutoff_date:
                return DomainQueryResult(
                    domain=request.domain,
                    found=False
                )
        
        # Parse dates
        discovered_at = datetime.fromisoformat(entry["discovered_at"])
        last_verified = datetime.fromisoformat(entry["last_verified"]) if entry["last_verified"] else None
        
        return DomainQueryResult(
            domain=request.domain,
            found=True,
            unsubscribe_url=entry["unsubscribe_url"],
            confidence=entry["confidence"],
            discovered_at=discovered_at,
            last_verified=last_verified
        )
    
    def get_best_entry(self, domain: str) -> Optional[dict]:
        """Get the best unsubscribe entry for a domain"""
        request = DomainQueryRequest(domain=domain, include_inactive=False)
        result = self.query_domain(request)
        
        if not result.found:
            return None
        
        return {
            "domain": result.domain,
            "unsubscribe_url": result.unsubscribe_url,
            "confidence": result.confidence,
            "discovered_at": result.discovered_at,
            "last_verified": result.last_verified
        }
    
    def update_verification(self, domain: str, success: bool):
        """Update the verification status of a domain entry"""
        normalized_domain = self._normalize_domain(domain)
        
        if normalized_domain not in self._index:
            logger.warning(f"Domain {domain} not found in index for verification update")
            return
        
        entry = self._index[normalized_domain]
        entry["last_verified"] = datetime.utcnow().isoformat()
        
        # Adjust confidence based on verification result
        if success:
            entry["confidence"] = min(entry["confidence"] + 0.1, 1.0)
        else:
            entry["confidence"] = max(entry["confidence"] - 0.2, 0.0)
        
        self._save_index()
        logger.info(f"Updated verification for {domain}: success={success}, new_confidence={entry['confidence']}")
    
    def list_domains(self) -> List[str]:
        """List all domains in the index"""
        return list(self._index.keys())
    
    def get_stats(self) -> Dict:
        """Get statistics about the domain index"""
        total_domains = len(self._index)
        
        # Count verified entries
        verified_count = sum(1 for entry in self._index.values() if entry.get("last_verified"))
        
        # Calculate average confidence
        confidences = [entry["confidence"] for entry in self._index.values()]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Count by confidence levels
        high_confidence = sum(1 for conf in confidences if conf >= 0.8)
        medium_confidence = sum(1 for conf in confidences if 0.5 <= conf < 0.8)
        low_confidence = sum(1 for conf in confidences if conf < 0.5)
        
        return {
            "total_domains": total_domains,
            "verified_entries": verified_count,
            "average_confidence": round(average_confidence, 2),
            "high_confidence_entries": high_confidence,
            "medium_confidence_entries": medium_confidence,
            "low_confidence_entries": low_confidence,
            "storage_path": str(self.storage_path)
        }
    
    def remove_domain(self, domain: str) -> bool:
        """Remove a domain from the index"""
        normalized_domain = self._normalize_domain(domain)
        
        if normalized_domain in self._index:
            del self._index[normalized_domain]
            self._save_index()
            logger.info(f"Removed domain {domain} from index")
            return True
        
        logger.warning(f"Domain {domain} not found in index for removal")
        return False
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain name for consistent storage"""
        domain = domain.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
