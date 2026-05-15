from __future__ import annotations

from src.schema.schema_registry import SchemaRegistry
from src.sql_validation.syntax_validator import SQLSyntaxValidator
from src.sql_validation.safety_validator import SQLSafetyValidator
from src.sql_validation.schema_validator import SQLSchemaValidator
from src.sql_validation.join_validator import SQLJoinValidator
from src.sql_validation.aggregation_validator import SQLAggregationValidator
from src.sql_validation.semantic_validator import SQLSemanticValidator
from src.sql_validation.sql_rewriter import SQLRewriter
from src.sql_validation.validation_result import ValidationResult

class ValidationPipeline:
    """Orchestrates all SQL validators in sequence.
    
    Order:
    1. Rewrite (Syntax cleanup & basic typing fixes)
    2. Syntax Validator
    3. Safety Validator (SQL Injection / Destructive ops)
    4. Schema Validator (Tables / Columns exist)
    5. Join Validator (Semantic join paths)
    6. Aggregation Validator (Logical aggregations)
    """

    def __init__(self, registry: SchemaRegistry | None = None) -> None:
        self.registry = registry or SchemaRegistry()
        self.rewriter = SQLRewriter()
        
        self.validators = [
            ("syntax", SQLSyntaxValidator()),
            ("safety", SQLSafetyValidator()),
            ("schema", SQLSchemaValidator(registry=self.registry)),
            ("join", SQLJoinValidator()),
            ("aggregation", SQLAggregationValidator(registry=self.registry))
        ]
        
        self.semantic_validator = SQLSemanticValidator()

    def validate(self, sql: str, benchmark_case: dict | None = None) -> ValidationResult:
        # Step 1: Attempt to normalize/rewrite first
        try:
            rewritten_sql = self.rewriter.rewrite(sql)
        except Exception:
            rewritten_sql = sql
            
        current_sql = rewritten_sql
        all_issues = []
        is_valid = True
        
        # Step 2: Run core validators sequentially
        for name, validator in self.validators:
            result = validator.validate(current_sql)
            all_issues.extend(result.issues)
            if not result.ok:
                is_valid = False
                # If a fundamental validator fails, we can stop early
                if name in ("syntax", "safety"):
                    break
        
        # Step 3: Run semantic benchmark validator if case is provided
        if is_valid and benchmark_case:
            semantic_result = self.semantic_validator.validate_against_case(current_sql, benchmark_case)
            all_issues.extend(semantic_result.issues)
            if not semantic_result.ok:
                is_valid = False

        return ValidationResult(is_valid, all_issues, current_sql)
