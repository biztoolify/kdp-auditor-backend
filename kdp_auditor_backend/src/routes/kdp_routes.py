from flask import Blueprint, jsonify, request
from src.models.kdp_models import Book, BestsellerRank, Keyword, BookKeyword, Category, BookCategory, db
from src.services.amazon_service import AmazonService
from src.services.bsr_calculator import BSRCalculator
from src.services.keyword_service import KeywordService
from datetime import datetime
import re

kdp_bp = Blueprint('kdp', __name__)

# Initialize services
amazon_service = AmazonService()
bsr_calculator = BSRCalculator()
keyword_service = KeywordService()

def validate_asin(asin):
    """Validate ASIN format (10 characters, alphanumeric)"""
    if not asin or len(asin) != 10:
        return False
    return re.match(r'^[A-Z0-9]{10}$', asin.upper()) is not None

@kdp_bp.route('/book/<asin>', methods=['GET'])
def analyze_book(asin):
    """
    Retrieve comprehensive data for a given ASIN
    """
    try:
        # Validate ASIN format
        if not validate_asin(asin):
            return jsonify({'error': 'Invalid ASIN format. ASIN must be 10 alphanumeric characters.'}), 400
        
        asin = asin.upper()
        
        # Check if book exists in database
        book = Book.query.filter_by(asin=asin).first()
        
        if not book:
            # Fetch book data from Amazon
            book_data = amazon_service.get_book_data(asin)
            if not book_data:
                return jsonify({'error': 'Book not found or unable to fetch data from Amazon'}), 404
            
            # Create new book record
            book = Book(
                asin=asin,
                title=book_data.get('title'),
                author=book_data.get('author'),
                publisher=book_data.get('publisher'),
                publication_date=book_data.get('publication_date'),
                book_type=book_data.get('book_type'),
                marketplace=book_data.get('marketplace', 'amazon.com'),
                current_price=book_data.get('current_price'),
                average_rating=book_data.get('average_rating'),
                total_reviews=book_data.get('total_reviews', 0),
                cover_image_url=book_data.get('cover_image_url'),
                blurb=book_data.get('blurb')
            )
            db.session.add(book)
            db.session.commit()
        else:
            # Update existing book data
            updated_data = amazon_service.get_book_data(asin)
            if updated_data:
                book.current_price = updated_data.get('current_price', book.current_price)
                book.average_rating = updated_data.get('average_rating', book.average_rating)
                book.total_reviews = updated_data.get('total_reviews', book.total_reviews)
                book.updated_at = datetime.utcnow()
                db.session.commit()
        
        # Get current BSR and calculate sales estimates
        current_bsr = amazon_service.get_current_bsr(asin)
        if current_bsr:
            # Calculate sales estimates
            daily_sales, monthly_sales = bsr_calculator.calculate_sales_estimates(
                current_bsr, book.book_type, book.marketplace
            )
            
            # Store BSR record
            bsr_record = BestsellerRank(
                book_id=book.id,
                rank=current_bsr,
                estimated_daily_sales=daily_sales,
                estimated_monthly_sales=monthly_sales
            )
            db.session.add(bsr_record)
            db.session.commit()
        
        # Get keywords for this book
        keywords = keyword_service.get_book_keywords(asin)
        
        # Get categories
        categories = amazon_service.get_book_categories(asin)
        
        # Prepare response
        response_data = book.to_dict()
        
        # Add current BSR data
        latest_bsr = BestsellerRank.query.filter_by(book_id=book.id).order_by(BestsellerRank.timestamp.desc()).first()
        if latest_bsr:
            response_data['current_bsr'] = latest_bsr.to_dict()
        
        # Add BSR history (last 30 records)
        bsr_history = BestsellerRank.query.filter_by(book_id=book.id).order_by(BestsellerRank.timestamp.desc()).limit(30).all()
        response_data['bsr_history'] = [bsr.to_dict() for bsr in bsr_history]
        
        # Add keywords
        book_keywords = db.session.query(BookKeyword, Keyword).join(Keyword).filter(BookKeyword.book_id == book.id).all()
        response_data['keywords'] = [
            {
                **keyword.to_dict(),
                'relevance_score': book_keyword.relevance_score
            }
            for book_keyword, keyword in book_keywords
        ]
        
        # Add categories
        book_categories = db.session.query(BookCategory, Category).join(Category).filter(BookCategory.book_id == book.id).all()
        response_data['categories'] = [
            {
                **category.to_dict(),
                'rank_in_category': book_category.rank_in_category
            }
            for book_category, category in book_categories
        ]
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@kdp_bp.route('/keywords/suggest', methods=['GET'])
def suggest_keywords():
    """
    Get keyword suggestions, search volume, competition, and opportunity scores
    """
    try:
        query = request.args.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        # Get keyword suggestions
        suggestions = keyword_service.get_keyword_suggestions(query)
        
        return jsonify({
            'query': query,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@kdp_bp.route('/keywords/analyze', methods=['POST'])
def analyze_keywords():
    """
    Analyze a list of keywords for search volume, competition, and opportunity
    """
    try:
        data = request.json
        keywords = data.get('keywords', [])
        
        if not keywords or not isinstance(keywords, list):
            return jsonify({'error': 'Keywords array is required'}), 400
        
        results = []
        for keyword_text in keywords:
            keyword_data = keyword_service.analyze_keyword(keyword_text)
            results.append(keyword_data)
        
        return jsonify({
            'keywords': results
        })
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@kdp_bp.route('/niches/explore', methods=['GET'])
def explore_niches():
    """
    List popular or trending niches
    """
    try:
        # Get top-level categories with statistics
        categories = Category.query.filter_by(parent_category_id=None).all()
        
        niche_data = []
        for category in categories:
            # Calculate niche statistics
            stats = keyword_service.get_niche_statistics(category.id)
            niche_info = category.to_dict()
            niche_info.update(stats)
            niche_data.append(niche_info)
        
        return jsonify({
            'niches': niche_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@kdp_bp.route('/niche/<int:category_id>', methods=['GET'])
def get_niche_details(category_id):
    """
    Get detailed statistics for a specific category/niche
    """
    try:
        category = Category.query.get_or_404(category_id)
        
        # Get detailed niche statistics
        stats = keyword_service.get_detailed_niche_statistics(category_id)
        
        # Get top books in this category
        top_books = amazon_service.get_top_books_in_category(category_id)
        
        response_data = category.to_dict()
        response_data.update(stats)
        response_data['top_books'] = top_books
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@kdp_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'KDP Auditor API'
    })

# Error handlers
@kdp_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@kdp_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

