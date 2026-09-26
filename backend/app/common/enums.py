from enum import StrEnum


class PhysicalType(StrEnum):
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"

class SemanticType(StrEnum):
    UNKNOWN = "unknown"

    CUSTOMER = "customer"
    PRODUCT = "product"
    REVENUE = "revenue"
    PROFIT = "profit"
    COST = "cost"

    QUANTITY = "quantity"

    DATE = "date"
    REGION = "region"

    EMPLOYEE = "employee"

    IDENTIFIER = "identifier"

class DatasetDomain(StrEnum):
    UNKNOWN = "unknown"

    RETAIL = "retail"

    FINANCE = "finance"

    HR = "hr"

    HEALTHCARE = "healthcare"

    MARKETING = "marketing"

    LOGISTICS = "logistics"

class Priority(StrEnum):
    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    CRITICAL = "critical"