"""Canonical skills with aliases. Used for deterministic extraction, normalisation and matching."""

import re

# canonical name -> (domain, aliases)
SKILLS: dict[str, tuple[str, list[str]]] = {
    "JavaScript": ("frontend", ["javascript", "js", "es6", "ecmascript"]),
    "TypeScript": ("frontend", ["typescript", "ts"]),
    "React": ("frontend", ["react", "react.js", "reactjs"]),
    "Next.js": ("frontend", ["next.js", "nextjs", "next js"]),
    "Vue": ("frontend", ["vue", "vue.js", "vuejs", "nuxt"]),
    "Angular": ("frontend", ["angular"]),
    "HTML": ("frontend", ["html", "html5"]),
    "CSS": ("frontend", ["css", "css3", "scss", "sass", "tailwind", "tailwindcss"]),
    "Redux": ("frontend", ["redux", "zustand", "mobx"]),
    "Web Performance": ("frontend", ["web performance", "core web vitals", "lighthouse", "производительность фронтенда"]),
    "Browser Internals": ("frontend", ["browser", "event loop", "dom", "rendering pipeline"]),
    "Python": ("backend", ["python", "питон"]),
    "Java": ("backend", ["java", "spring", "spring boot"]),
    "Go": ("backend", ["golang", "go"]),
    "Node.js": ("backend", ["node.js", "nodejs", "node", "express", "nestjs"]),
    "C#": ("backend", ["c#", ".net", "dotnet", "asp.net"]),
    "PHP": ("backend", ["php", "laravel", "symfony"]),
    "Kotlin": ("mobile", ["kotlin"]),
    "Swift": ("mobile", ["swift", "ios"]),
    "FastAPI": ("backend", ["fastapi"]),
    "Django": ("backend", ["django"]),
    "REST API": ("backend", ["rest api", "restful", "rest-api", "api design"]),
    "GraphQL": ("backend", ["graphql"]),
    "gRPC": ("backend", ["grpc"]),
    "SQL": ("data", ["sql"]),
    "PostgreSQL": ("data", ["postgresql", "postgres", "psql"]),
    "MySQL": ("data", ["mysql", "mariadb"]),
    "MongoDB": ("data", ["mongodb", "mongo"]),
    "Redis": ("backend", ["redis"]),
    "Kafka": ("backend", ["kafka"]),
    "RabbitMQ": ("backend", ["rabbitmq", "rabbit mq"]),
    "Message Queues": ("backend", ["message queue", "queues", "очереди", "celery", "sqs"]),
    "Caching": ("backend", ["caching", "cache", "кэширование", "кеширование", "memcached"]),
    "Concurrency": ("backend", ["concurrency", "multithreading", "async", "asyncio", "goroutines", "многопоточность"]),
    "Microservices": ("architecture", ["microservices", "микросервисы", "microservice"]),
    "System Design": ("architecture", ["system design", "системный дизайн", "high load", "highload", "scalability", "масштабирование"]),
    "Testing": ("qa", ["testing", "unit tests", "pytest", "jest", "tdd", "тестирование", "cypress", "playwright"]),
    "Git": ("tools", ["git", "github", "gitlab"]),
    "Docker": ("devops", ["docker", "containers", "контейнеры"]),
    "Kubernetes": ("devops", ["kubernetes", "k8s", "helm"]),
    "CI/CD": ("devops", ["ci/cd", "ci", "github actions", "gitlab ci", "jenkins"]),
    "Linux": ("devops", ["linux", "bash", "unix"]),
    "AWS": ("devops", ["aws", "amazon web services", "ec2", "s3", "lambda"]),
    "GCP": ("devops", ["gcp", "google cloud"]),
    "Azure": ("devops", ["azure"]),
    "Terraform": ("devops", ["terraform", "iac", "ansible"]),
    "Networking": ("devops", ["networking", "tcp/ip", "dns", "http", "сети"]),
    "Monitoring": ("devops", ["monitoring", "prometheus", "grafana", "observability", "мониторинг", "elk"]),
    "Machine Learning": ("ml", ["machine learning", "ml", "машинное обучение", "scikit-learn", "sklearn"]),
    "Deep Learning": ("ml", ["deep learning", "pytorch", "tensorflow", "keras", "нейросети", "neural networks"]),
    "NLP": ("ml", ["nlp", "llm", "transformers", "natural language processing"]),
    "Computer Vision": ("ml", ["computer vision", "cv models", "opencv", "компьютерное зрение"]),
    "Statistics": ("ml", ["statistics", "статистика", "a/b testing", "a/b тесты", "hypothesis testing"]),
    "Pandas": ("data", ["pandas", "numpy"]),
    "Spark": ("data", ["spark", "pyspark", "hadoop"]),
    "Airflow": ("data", ["airflow", "dagster", "etl"]),
    "MLOps": ("ml", ["mlops", "mlflow", "model serving", "kubeflow"]),
    "Data Visualization": ("data", ["tableau", "power bi", "superset", "data visualization"]),
    "Product Management": ("product", ["product management", "roadmap", "discovery", "prioritization", "jtbd"]),
    "Agile": ("product", ["agile", "scrum", "kanban"]),
}

DOMAIN_TO_FAMILY = {
    "frontend": "frontend", "backend": "backend", "data": "backend", "devops": "devops", "ml": "ml",
    "architecture": "backend", "qa": "qa", "tools": "other", "product": "product", "mobile": "mobile",
}

_GO_RE = re.compile(r"(?<![\w.])Go(?![\w])")


def _alias_pattern(alias: str) -> re.Pattern:
    esc = re.escape(alias)
    return re.compile(rf"(?<![\w.#+/-]){esc}(?![\w#+-])", re.IGNORECASE)


_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (canon, alias, _alias_pattern(alias)) for canon, (_, aliases) in SKILLS.items() for alias in aliases
]


def extract_skills(text: str) -> list[str]:
    """Return canonical skills mentioned in text, ordered by first occurrence."""
    found: dict[str, int] = {}
    for canon, alias, pat in _PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        if alias == "go":
            m = _GO_RE.search(text)  # case-sensitive: avoid matching the English verb "go"
            if not m:
                continue
        pos = m.start()
        if canon not in found or pos < found[canon]:
            found[canon] = pos
    return sorted(found, key=found.get)


def normalize_skill(name: str) -> str:
    n = name.strip().lower()
    for canon, (_, aliases) in SKILLS.items():
        if n == canon.lower() or n in aliases:
            return canon
    return name.strip()


def skill_domain(name: str) -> str:
    canon = normalize_skill(name)
    return SKILLS.get(canon, ("other", []))[0]


def infer_family(skills: list[str]) -> str:
    counts: dict[str, int] = {}
    for s in skills:
        fam = DOMAIN_TO_FAMILY.get(skill_domain(s), "other")
        counts[fam] = counts.get(fam, 0) + 1
    if counts.get("frontend", 0) >= 2 and counts.get("backend", 0) >= 2:
        return "fullstack"
    if not counts:
        return "other"
    return max(counts, key=counts.get)
