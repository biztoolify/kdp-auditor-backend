import requests
import time
import random
from typing import List, Dict, Optional
from src.models.kdp_models import Keyword, BookKeyword, Category, db
from datetime import datetime, timedelta
import re

class KeywordService:
    """
    Service for keyword research, analysis, and niche identification
    """
    
    def __init__(self):
        self.amazon_base_url = "https://completion.amazon.com/api/2017/suggestions"
        
    def get_keyword_suggestions(self, seed_keyword: str, limit: int = 50) -> List[Dict]:
        """
        Generate keyword suggestions based on a seed keyword
        
        Args:
            seed_keyword: The base keyword to expand upon
            limit: Maximum number of suggestions to return
        
        Returns:
            List of keyword dictionaries with metrics
        """
        try:
            suggestions = []
            
            # Get Amazon autocomplete suggestions
            amazon_suggestions = self._get_amazon_autocomplete(seed_keyword)
            
            # Get related keywords using various techniques
            related_keywords = self._generate_related_keywords(seed_keyword)
            
            # Combine and deduplicate
            all_keywords = list(set(amazon_suggestions + related_keywords))
            
            # Analyze each keyword
            for keyword in all_keywords[:limit]:
                keyword_data = self.analyze_keyword(keyword)
                if keyword_data:
                    suggestions.append(keyword_data)
            
            # Sort by opportunity score
            suggestions.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
            
            return suggestions[:limit]
            
        except Exception as e:
            print(f"Error getting keyword suggestions: {e}")
            return []
    
    def analyze_keyword(self, keyword_text: str) -> Optional[Dict]:
        """
        Analyze a single keyword for search volume, competition, and opportunity
        
        Args:
            keyword_text: The keyword to analyze
        
        Returns:
            Dictionary with keyword analysis data
        """
        try:
            # Check if keyword exists in database and is recent
            existing_keyword = Keyword.query.filter_by(keyword_text=keyword_text.lower()).first()
            
            if existing_keyword and self._is_data_fresh(existing_keyword.last_updated):
                return existing_keyword.to_dict()
            
            # Perform fresh analysis
            search_volume = self._estimate_search_volume(keyword_text)
            competition_score = self._calculate_competition_score(keyword_text)
            opportunity_score = self._calculate_opportunity_score(search_volume, competition_score)
            
            # Update or create keyword record
            if existing_keyword:
                existing_keyword.search_volume = search_volume
                existing_keyword.competition_score = competition_score
                existing_keyword.opportunity_score = opportunity_score
                existing_keyword.last_updated = datetime.utcnow()
                keyword_obj = existing_keyword
            else:
                keyword_obj = Keyword(
                    keyword_text=keyword_text.lower(),
                    search_volume=search_volume,
                    competition_score=competition_score,
                    opportunity_score=opportunity_score
                )
                db.session.add(keyword_obj)
            
            db.session.commit()
            
            return keyword_obj.to_dict()
            
        except Exception as e:
            print(f"Error analyzing keyword '{keyword_text}': {e}")
            return None
    
    def get_book_keywords(self, asin: str) -> List[Dict]:
        """
        Extract and analyze keywords for a specific book
        
        This would involve analyzing the book's title, subtitle, description,
        and potentially reverse-engineering from its category rankings.
        """
        try:
            # This is a placeholder implementation
            # In reality, this would involve sophisticated text analysis
            # and potentially scraping the book's Amazon page
            
            keywords = []
            
            # For now, return empty list
            # TODO: Implement actual keyword extraction logic
            
            return keywords
            
        except Exception as e:
            print(f"Error getting keywords for book {asin}: {e}")
            return []
    
    def get_niche_statistics(self, category_id: int) -> Dict:
        """
        Calculate statistics for a niche/category
        
        Args:
            category_id: The category to analyze
        
        Returns:
            Dictionary with niche statistics
        """
        try:
            # This would involve analyzing books in the category
            # For now, return placeholder data
            
            stats = {
                'total_books': 0,
                'average_bsr': 0,
                'average_reviews': 0,
                'average_rating': 0.0,
                'competition_level': 'medium',
                'opportunity_score': 0.5,
                'trending': False
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting niche statistics for category {category_id}: {e}")
            return {}
    
    def get_detailed_niche_statistics(self, category_id: int) -> Dict:
        """
        Get detailed statistics for a specific niche
        """
        try:
            basic_stats = self.get_niche_statistics(category_id)
            
            # Add more detailed metrics
            detailed_stats = basic_stats.copy()
            detailed_stats.update({
                'price_ranges': {
                    'min': 0.99,
                    'max': 29.99,
                    'average': 9.99
                },
                'publication_trends': {
                    'books_last_month': 0,
                    'books_last_year': 0,
                    'growth_rate': 0.0
                },
                'top_keywords': [],
                'seasonal_trends': {}
            })
            
            return detailed_stats
            
        except Exception as e:
            print(f"Error getting detailed niche statistics: {e}")
            return {}
    
    def _get_amazon_autocomplete(self, query: str) -> List[str]:
        """
        Get autocomplete suggestions from Amazon
        
        Note: This is a simplified implementation. Amazon's autocomplete API
        may have rate limits and anti-bot measures.
        """
        try:
            suggestions = []
            
            # Try different prefixes and suffixes
            variations = [
                query,
                f"{query} book",
                f"{query} kindle",
                f"best {query}",
                f"{query} guide"
            ]
            
            for variation in variations:
                time.sleep(random.uniform(0.5, 1.5))  # Rate limiting
                
                params = {
                    'search-alias': 'digital-text',
                    'client': 'amazon-search-ui',
                    'mkt': '1',
                    'q': variation
                }
                
                try:
                    response = requests.get(self.amazon_base_url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if 'suggestions' in data:
                            for suggestion in data['suggestions']:
                                if 'value' in suggestion:
                                    suggestions.append(suggestion['value'])
                except:
                    continue
            
            return list(set(suggestions))  # Remove duplicates
            
        except Exception as e:
            print(f"Error getting Amazon autocomplete: {e}")
            return []
    
    def _generate_related_keywords(self, seed_keyword: str) -> List[str]:
        """
        Generate related keywords using various techniques
        """
        related = []
        
        # Common prefixes and suffixes for book keywords
        prefixes = ['best', 'top', 'ultimate', 'complete', 'beginner', 'advanced', 'how to']
        suffixes = ['book', 'guide', 'manual', 'handbook', 'for beginners', 'step by step']
        
        # Generate combinations
        for prefix in prefixes:
            related.append(f"{prefix} {seed_keyword}")
        
        for suffix in suffixes:
            related.append(f"{seed_keyword} {suffix}")
        
        # Add some variations
        words = seed_keyword.split()
        if len(words) > 1:
            # Try different word orders
            related.append(' '.join(reversed(words)))
        
        return related
    
    def _estimate_search_volume(self, keyword: str) -> int:
        """
        Estimate monthly search volume for a keyword
        
        This is a placeholder implementation. In reality, this would require
        access to keyword research tools or APIs like Google Keyword Planner,
        SEMrush, or Ahrefs.
        """
        # Simple heuristic based on keyword length and common words
        base_volume = 1000
        
        # Longer keywords typically have lower volume
        length_factor = max(0.1, 1.0 - (len(keyword.split()) - 1) * 0.2)
        
        # Common words get higher volume
        common_words = ['book', 'guide', 'how', 'best', 'top', 'learn']
        common_factor = 1.0
        for word in common_words:
            if word in keyword.lower():
                common_factor *= 1.5
        
        estimated_volume = int(base_volume * length_factor * common_factor)
        
        # Add some randomness to make it more realistic
        estimated_volume = int(estimated_volume * random.uniform(0.5, 2.0))
        
        return max(10, estimated_volume)  # Minimum 10 searches per month
    
    def _calculate_competition_score(self, keyword: str) -> float:
        """
        Calculate competition score (0.0 to 1.0, where 1.0 is highest competition)
        
        This would typically involve analyzing:
        - Number of books targeting this keyword
        - Quality of competing books (reviews, ratings, BSR)
        - Advertising competition
        """
        # Placeholder implementation
        # In reality, this would require extensive analysis
        
        # Simple heuristic: shorter, more generic keywords have higher competition
        word_count = len(keyword.split())
        
        if word_count == 1:
            base_competition = 0.8
        elif word_count == 2:
            base_competition = 0.6
        elif word_count == 3:
            base_competition = 0.4
        else:
            base_competition = 0.2
        
        # Add randomness
        competition = base_competition * random.uniform(0.7, 1.3)
        
        return min(1.0, max(0.0, competition))
    
    def _calculate_opportunity_score(self, search_volume: int, competition_score: float) -> float:
        """
        Calculate opportunity score combining volume and competition
        
        Higher volume and lower competition = higher opportunity
        """
        if search_volume <= 0:
            return 0.0
        
        # Normalize search volume (log scale)
        import math
        volume_score = min(1.0, math.log10(search_volume) / 4.0)  # Assuming max ~10k searches
        
        # Invert competition (lower competition = higher score)
        competition_score_inverted = 1.0 - competition_score
        
        # Weighted combination (volume is slightly more important)
        opportunity = (volume_score * 0.6) + (competition_score_inverted * 0.4)
        
        return round(opportunity, 3)
    
    def _is_data_fresh(self, last_updated: datetime, max_age_days: int = 7) -> bool:
        """
        Check if keyword data is fresh enough to use
        """
        if not last_updated:
            return False
        
        age = datetime.utcnow() - last_updated
        return age.days < max_age_days

