from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    # Keep the original table name so existing registered accounts still work.
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    comparisons = db.relationship(
        "Comparison", back_populates="user", cascade="all, delete-orphan"
    )


class Comparison(db.Model):
    __tablename__ = "comparisons"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    problem_name = db.Column(db.String(120), nullable=False)
    test_input = db.Column(db.Text, default="")
    expected_output = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="comparisons")
    code_samples = db.relationship(
        "CodeSample", back_populates="comparison", cascade="all, delete-orphan"
    )


class CodeSample(db.Model):
    __tablename__ = "code_samples"

    id = db.Column(db.Integer, primary_key=True)
    comparison_id = db.Column(
        db.Integer, db.ForeignKey("comparisons.id"), nullable=False
    )
    code_type = db.Column(db.String(10), nullable=False)
    source_code = db.Column(db.Text, nullable=False)

    comparison = db.relationship("Comparison", back_populates="code_samples")
    analysis_result = db.relationship(
        "AnalysisResult",
        back_populates="code_sample",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"

    id = db.Column(db.Integer, primary_key=True)
    code_sample_id = db.Column(
        db.Integer, db.ForeignKey("code_samples.id"), unique=True, nullable=False
    )
    tests_passed = db.Column(db.Integer, default=0, nullable=False)
    tests_failed = db.Column(db.Integer, default=0, nullable=False)
    execution_time = db.Column(db.Float, default=0.0, nullable=False)
    complexity_score = db.Column(db.Integer, default=0, nullable=False)
    error_count = db.Column(db.Integer, default=0, nullable=False)
    output = db.Column(db.Text, default="")
    error_message = db.Column(db.Text, default="")

    code_sample = db.relationship("CodeSample", back_populates="analysis_result")
