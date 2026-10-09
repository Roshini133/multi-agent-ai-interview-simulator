"""Technical interviewer prompts and role-specific fallback question banks."""

TECH_SYSTEM = """You are {name}, a senior technical interviewer for a {role} position.
Rules:
- Ask exactly ONE technical question at difficulty {difficulty} (EASY = fundamentals, MEDIUM = applied/practical, HARD = design, trade-offs, edge cases).
- {action_rule}
- If resume facts are provided, you may ask about them, but ONLY use facts that appear in the resume text. Never invent projects or skills.
- Do not give the answer or feedback. Max 50 words.
- Do not repeat topics already asked.
Respond ONLY as JSON: {{"question": "...", "topic": "short topic label"}}"""

ACTION_RULES = {
    "increase": "The candidate answered strongly, so go deeper than the previous question.",
    "maintain": "Keep a similar depth to the previous question but change the topic.",
    "reinforce": "The candidate struggled, so ask a simpler concept-reinforcement question, ideally on a fundamental related to the previous topic.",
    "start": "This is the first technical question; begin with a solid, approachable one.",
}

RESUME_PROBES = [
    "Your resume mentions \"{item}\". Can you explain the technical approach you took and why you chose it?",
    "In your project \"{item}\", what was the hardest technical problem you faced and how did you solve it?",
    "Regarding \"{item}\" on your resume, what trade-offs or alternatives did you consider?",
]

_B = lambda t, q: (t, q)

TECH_FALLBACK: dict[str, dict[str, list[tuple[str, str]]]] = {
    "java_developer": {
        "EASY": [_B("oop", "Explain the four pillars of object-oriented programming with a Java example."), _B("collections", "What is the difference between ArrayList and LinkedList?"), _B("exceptions", "What is the difference between checked and unchecked exceptions in Java?")],
        "MEDIUM": [_B("hashmap", "How does HashMap work internally, and what happens on a hash collision?"), _B("concurrency", "What is the difference between synchronized methods and ReentrantLock?"), _B("spring", "How does dependency injection work in Spring, and why is it useful?")],
        "HARD": [_B("jvm", "Explain how JVM garbage collection works and how you would diagnose a memory leak."), _B("concurrency", "How would you design a thread-safe cache with expiry in Java?"), _B("microservices", "How would you handle distributed transactions across Spring microservices?")],
    },
    "python_developer": {
        "EASY": [_B("data_structures", "What is the difference between a list, a tuple and a set in Python?"), _B("functions", "Explain *args and **kwargs with an example."), _B("oop", "How do classes and inheritance work in Python?")],
        "MEDIUM": [_B("decorators", "What is a decorator and when would you write one?"), _B("generators", "How do generators differ from lists, and when are they useful?"), _B("web", "How would you structure a REST API in Flask or FastAPI, including validation and errors?")],
        "HARD": [_B("gil", "What is the GIL and how does it influence how you scale a Python service?"), _B("asyncio", "Explain how asyncio works and when it is better than threads."), _B("performance", "How would you profile and optimise a slow Python data-processing job?")],
    },
    "full_stack_developer": {
        "EASY": [_B("http", "What is the difference between GET and POST, and what are common HTTP status codes?"), _B("react", "What are props and state in React?"), _B("css", "Explain the CSS box model and how Flexbox helps layout.")],
        "MEDIUM": [_B("auth", "How would you implement authentication and authorisation in a web app?"), _B("react", "How do useEffect and useState work, and what causes unnecessary re-renders?"), _B("database", "When would you choose SQL over NoSQL for a project?")],
        "HARD": [_B("scaling", "How would you scale a web application that suddenly gets ten times more traffic?"), _B("security", "How do you defend a web application against XSS, CSRF and SQL injection?"), _B("architecture", "How would you design real-time notifications for a web app?")],
    },
    "ai_ml_engineer": {
        "EASY": [_B("ml_basics", "What is the difference between supervised and unsupervised learning?"), _B("overfitting", "What is overfitting and how can you reduce it?"), _B("metrics", "Explain precision, recall and when each matters most.")],
        "MEDIUM": [_B("neural_networks", "How do CNNs differ from RNNs/LSTMs, and when would you use each?"), _B("validation", "How do you build a trustworthy validation strategy for a small dataset?"), _B("embeddings", "What are embeddings and how are they used for semantic search?")],
        "HARD": [_B("transformers", "Explain the attention mechanism in transformers and why it scales better than recurrence for long context."), _B("mlops", "How would you deploy and monitor a model to detect data drift in production?"), _B("imbalance", "How would you handle a heavily imbalanced dataset end to end?")],
    },
    "data_analyst": {
        "EASY": [_B("sql", "What is the difference between INNER JOIN and LEFT JOIN?"), _B("statistics", "Explain mean, median and when the median is a better summary."), _B("cleaning", "How do you handle missing values in a dataset?")],
        "MEDIUM": [_B("sql", "How would you find the top three customers by revenue in each region using SQL?"), _B("visualization", "How do you choose the right chart for a business question?"), _B("hypothesis", "Explain hypothesis testing and p-values in simple terms.")],
        "HARD": [_B("experimentation", "How would you design and analyse an A/B test, including sample size and pitfalls?"), _B("pipelines", "How would you build a reliable, automated reporting pipeline?"), _B("causality", "Correlation is not causation - how would you investigate a suspected causal relationship?")],
    },
    "software_engineer": {
        "EASY": [_B("complexity", "What is Big-O notation, and what is the complexity of searching in an array vs a hash table?"), _B("data_structures", "What is the difference between a stack and a queue? Give a use case for each."), _B("oop", "What is polymorphism and why is it useful?")],
        "MEDIUM": [_B("database", "What is a database index and what are its trade-offs?"), _B("testing", "How do you decide what to unit test, and what makes a good test?"), _B("api", "How would you design a REST API for a library management system?")],
        "HARD": [_B("system_design", "How would you design a URL-shortening service that handles high traffic?"), _B("concurrency", "Explain race conditions and deadlocks and how to prevent them."), _B("scalability", "How would you introduce caching in a system and keep it consistent?")],
    },
}
