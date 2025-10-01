from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    asin = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(200))
    publisher = db.Column(db.String(200))
    publication_date = db.Column(db.Date)
    book_type = db.Column(db.String(20))  # 'ebook', 'paperback', 'hardcover'
    marketplace = db.Column(db.String(20), default='amazon.com')
    current_price = db.Column(db.Float)
    average_rating = db.Column(db.Float)
    total_reviews = db.Column(db.Integer, default=0)
    cover_image_url = db.Column(db.String(500))
    blurb = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bsr_history = db.relationship('BestsellerRank', backref='book', lazy=True, cascade='all, delete-orphan')
    book_keywords = db.relationship('BookKeyword', backref='book', lazy=True, cascade='all, delete-orphan')
    book_categories = db.relationship('BookCategory', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Book {self.asin}: {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'asin': self.asin,
            'title': self.title,
            'author': self.author,
            'publisher': self.publisher,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'book_type': self.book_type,
            'marketplace': self.marketplace,
            'current_price': self.current_price,
            'average_rating': self.average_rating,
            'total_reviews': self.total_reviews,
            'cover_image_url': self.cover_image_url,
            'blurb': self.blurb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BestsellerRank(db.Model):
    __tablename__ = 'bestseller_ranks'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    estimated_daily_sales = db.Column(db.Float)
    estimated_monthly_sales = db.Column(db.Float)
    category = db.Column(db.String(200))  # Optional: specific category for this BSR
    
    def __repr__(self):
        return f'<BSR {self.book_id}: #{self.rank} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'book_id': self.book_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'rank': self.rank,
            'estimated_daily_sales': self.estimated_daily_sales,
            'estimated_monthly_sales': self.estimated_monthly_sales,
            'category': self.category
        }

class Keyword(db.Model):
    __tablename__ = 'keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword_text = db.Column(db.String(200), unique=True, nullable=False, index=True)
    search_volume = db.Column(db.Integer)
    competition_score = db.Column(db.Float)  # 0.0 to 1.0, where 1.0 is highest competition
    opportunity_score = db.Column(db.Float)  # Calculated metric combining volume and competition
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    book_keywords = db.relationship('BookKeyword', backref='keyword', lazy=True)
    
    def __repr__(self):
        return f'<Keyword {self.keyword_text}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword_text': self.keyword_text,
            'search_volume': self.search_volume,
            'competition_score': self.competition_score,
            'opportunity_score': self.opportunity_score,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class BookKeyword(db.Model):
    __tablename__ = 'book_keywords'
    
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), primary_key=True)
    keyword_id = db.Column(db.Integer, db.ForeignKey('keywords.id'), primary_key=True)
    relevance_score = db.Column(db.Float)  # How relevant this keyword is to this book
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'book_id': self.book_id,
            'keyword_id': self.keyword_id,
            'relevance_score': self.relevance_score,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None
        }

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(200), unique=True, nullable=False)
    parent_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    amazon_category_id = db.Column(db.String(50))  # Amazon's internal category ID if available
    
    # Self-referential relationship for parent/child categories
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    book_categories = db.relationship('BookCategory', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.category_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'parent_category_id': self.parent_category_id,
            'amazon_category_id': self.amazon_category_id
        }

class BookCategory(db.Model):
    __tablename__ = 'book_categories'
    
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), primary_key=True)
    rank_in_category = db.Column(db.Integer)  # Book's rank within this specific category
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'book_id': self.book_id,
            'category_id': self.category_id,
            'rank_in_category': self.rank_in_category,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None
        }

