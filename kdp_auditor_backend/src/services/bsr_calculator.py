from typing import Tuple, Optional
import math

class BSRCalculator:
    """
    Service for calculating estimated sales from Best Seller Rank (BSR)
    
    This implementation is based on industry research and observations.
    The actual conversion rates may vary and should be continuously refined.
    """
    
    def __init__(self):
        # BSR to sales conversion tables for different marketplaces and book types
        # These are approximations based on industry data
        self.conversion_tables = {
            'amazon.com': {
                'ebook': {
                    1: 5000,      # #1 BSR = ~5000 sales/day
                    10: 1500,     # #10 BSR = ~1500 sales/day
                    100: 300,     # #100 BSR = ~300 sales/day
                    1000: 50,     # #1000 BSR = ~50 sales/day
                    10000: 8,     # #10000 BSR = ~8 sales/day
                    100000: 1,    # #100000 BSR = ~1 sale/day
                    1000000: 0.1, # #1000000 BSR = ~0.1 sales/day
                },
                'paperback': {
                    1: 2000,
                    10: 600,
                    100: 120,
                    1000: 20,
                    10000: 3,
                    100000: 0.5,
                    1000000: 0.05,
                },
                'hardcover': {
                    1: 1000,
                    10: 300,
                    100: 60,
                    1000: 10,
                    10000: 1.5,
                    100000: 0.25,
                    1000000: 0.025,
                }
            },
            'amazon.co.uk': {
                # UK market is smaller, so adjust accordingly
                'ebook': {
                    1: 1500,
                    10: 450,
                    100: 90,
                    1000: 15,
                    10000: 2.4,
                    100000: 0.3,
                    1000000: 0.03,
                },
                'paperback': {
                    1: 600,
                    10: 180,
                    100: 36,
                    1000: 6,
                    10000: 0.9,
                    100000: 0.15,
                    1000000: 0.015,
                },
                'hardcover': {
                    1: 300,
                    10: 90,
                    100: 18,
                    1000: 3,
                    10000: 0.45,
                    100000: 0.075,
                    1000000: 0.0075,
                }
            }
        }
    
    def calculate_sales_estimates(self, bsr: int, book_type: str = 'ebook', 
                                marketplace: str = 'amazon.com') -> Tuple[float, float]:
        """
        Calculate estimated daily and monthly sales from BSR
        
        Args:
            bsr: Best Seller Rank
            book_type: Type of book ('ebook', 'paperback', 'hardcover')
            marketplace: Amazon marketplace ('amazon.com', 'amazon.co.uk', etc.)
        
        Returns:
            Tuple of (daily_sales, monthly_sales)
        """
        try:
            # Get conversion table for marketplace and book type
            marketplace_table = self.conversion_tables.get(marketplace, self.conversion_tables['amazon.com'])
            book_type_table = marketplace_table.get(book_type, marketplace_table['ebook'])
            
            # Calculate daily sales using interpolation
            daily_sales = self._interpolate_sales(bsr, book_type_table)
            
            # Calculate monthly sales (assuming 30 days)
            monthly_sales = daily_sales * 30
            
            return round(daily_sales, 2), round(monthly_sales, 2)
            
        except Exception as e:
            print(f"Error calculating sales estimates: {e}")
            return 0.0, 0.0
    
    def _interpolate_sales(self, bsr: int, conversion_table: dict) -> float:
        """
        Interpolate sales estimate between known BSR points
        """
        if bsr <= 0:
            return 0.0
        
        # Get sorted BSR points
        bsr_points = sorted(conversion_table.keys())
        
        # If BSR is better than best known point, extrapolate upward
        if bsr < bsr_points[0]:
            return self._extrapolate_high_performance(bsr, bsr_points[0], conversion_table[bsr_points[0]])
        
        # If BSR is worse than worst known point, extrapolate downward
        if bsr > bsr_points[-1]:
            return self._extrapolate_low_performance(bsr, bsr_points[-1], conversion_table[bsr_points[-1]])
        
        # Find the two points to interpolate between
        for i in range(len(bsr_points) - 1):
            lower_bsr = bsr_points[i]
            upper_bsr = bsr_points[i + 1]
            
            if lower_bsr <= bsr <= upper_bsr:
                lower_sales = conversion_table[lower_bsr]
                upper_sales = conversion_table[upper_bsr]
                
                # Logarithmic interpolation (more realistic for BSR)
                log_bsr = math.log10(bsr)
                log_lower = math.log10(lower_bsr)
                log_upper = math.log10(upper_bsr)
                
                # Interpolate in log space
                ratio = (log_bsr - log_lower) / (log_upper - log_lower)
                
                # Sales also follow logarithmic pattern
                log_lower_sales = math.log10(max(lower_sales, 0.001))  # Avoid log(0)
                log_upper_sales = math.log10(max(upper_sales, 0.001))
                
                log_sales = log_lower_sales + ratio * (log_upper_sales - log_lower_sales)
                
                return 10 ** log_sales
        
        return 0.0
    
    def _extrapolate_high_performance(self, bsr: int, known_bsr: int, known_sales: float) -> float:
        """
        Extrapolate sales for BSR better than known data points
        """
        # Assume exponential growth for very high performance
        ratio = known_bsr / bsr
        return known_sales * (ratio ** 0.7)  # Slightly sublinear growth
    
    def _extrapolate_low_performance(self, bsr: int, known_bsr: int, known_sales: float) -> float:
        """
        Extrapolate sales for BSR worse than known data points
        """
        # Assume exponential decay for very low performance
        ratio = bsr / known_bsr
        return known_sales / (ratio ** 0.8)  # Decay rate
    
    def get_bsr_for_target_sales(self, target_daily_sales: float, book_type: str = 'ebook', 
                                marketplace: str = 'amazon.com') -> Optional[int]:
        """
        Reverse calculation: find BSR needed to achieve target daily sales
        
        Args:
            target_daily_sales: Desired daily sales
            book_type: Type of book
            marketplace: Amazon marketplace
        
        Returns:
            Estimated BSR needed, or None if not achievable
        """
        try:
            marketplace_table = self.conversion_tables.get(marketplace, self.conversion_tables['amazon.com'])
            book_type_table = marketplace_table.get(book_type, marketplace_table['ebook'])
            
            # Binary search for the BSR that gives closest to target sales
            low_bsr = 1
            high_bsr = 10000000
            
            while high_bsr - low_bsr > 1:
                mid_bsr = (low_bsr + high_bsr) // 2
                estimated_sales = self._interpolate_sales(mid_bsr, book_type_table)
                
                if estimated_sales > target_daily_sales:
                    low_bsr = mid_bsr
                else:
                    high_bsr = mid_bsr
            
            return low_bsr
            
        except Exception as e:
            print(f"Error calculating target BSR: {e}")
            return None
    
    def get_sales_trend_analysis(self, bsr_history: list) -> dict:
        """
        Analyze sales trend from BSR history
        
        Args:
            bsr_history: List of BSR records with timestamps
        
        Returns:
            Dictionary with trend analysis
        """
        if len(bsr_history) < 2:
            return {'trend': 'insufficient_data'}
        
        # Sort by timestamp
        sorted_history = sorted(bsr_history, key=lambda x: x['timestamp'])
        
        # Calculate sales for each BSR point
        sales_data = []
        for record in sorted_history:
            daily_sales, _ = self.calculate_sales_estimates(
                record['rank'], 
                record.get('book_type', 'ebook'),
                record.get('marketplace', 'amazon.com')
            )
            sales_data.append(daily_sales)
        
        # Analyze trend
        if len(sales_data) >= 3:
            recent_avg = sum(sales_data[-3:]) / 3
            older_avg = sum(sales_data[:-3]) / len(sales_data[:-3]) if len(sales_data) > 3 else sales_data[0]
            
            change_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            
            if change_percent > 10:
                trend = 'improving'
            elif change_percent < -10:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            # Simple comparison for limited data
            if sales_data[-1] > sales_data[0]:
                trend = 'improving'
            elif sales_data[-1] < sales_data[0]:
                trend = 'declining'
            else:
                trend = 'stable'
        
        return {
            'trend': trend,
            'current_daily_sales': sales_data[-1],
            'average_daily_sales': sum(sales_data) / len(sales_data),
            'best_daily_sales': max(sales_data),
            'worst_daily_sales': min(sales_data),
            'change_percent': change_percent if 'change_percent' in locals() else 0
        }

