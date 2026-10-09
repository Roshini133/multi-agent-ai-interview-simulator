"""Job-role catalogue: labels, vocabularies used for relevance heuristics."""

ROLES: dict[str, dict] = {
    "java_developer": {
        "label": "Java Developer",
        "keywords": ["java", "spring", "jvm", "oop", "collections", "hibernate", "maven", "concurrency", "rest", "sql", "junit", "microservices", "thread", "stream"],
    },
    "python_developer": {
        "label": "Python Developer",
        "keywords": ["python", "flask", "django", "fastapi", "decorator", "generator", "gil", "pandas", "pytest", "asyncio", "list", "dict", "sql", "rest"],
    },
    "full_stack_developer": {
        "label": "Full Stack Developer",
        "keywords": ["react", "javascript", "node", "api", "rest", "html", "css", "database", "sql", "state", "authentication", "docker", "typescript", "frontend", "backend"],
    },
    "ai_ml_engineer": {
        "label": "AI/ML Engineer",
        "keywords": ["model", "training", "overfitting", "regularization", "cnn", "lstm", "transformer", "embedding", "loss", "gradient", "precision", "recall", "validation", "feature", "dataset", "pytorch", "tensorflow"],
    },
    "data_analyst": {
        "label": "Data Analyst",
        "keywords": ["sql", "join", "aggregate", "dashboard", "visualization", "pandas", "excel", "statistics", "hypothesis", "outlier", "cleaning", "kpi", "tableau", "power bi", "correlation"],
    },
    "software_engineer": {
        "label": "Software Engineer",
        "keywords": ["algorithm", "data structure", "complexity", "hash", "tree", "graph", "testing", "design pattern", "database", "index", "api", "concurrency", "git", "cache", "scalability"],
    },
}


def role_label(role_key: str) -> str:
    return ROLES.get(role_key, {}).get("label", role_key.replace("_", " ").title())


def is_valid_role(role_key: str) -> bool:
    return role_key in ROLES
