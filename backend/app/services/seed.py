from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Plan, Question, RoleCatalog, Skill
from app.services.ai.prompts import seed_prompts
from app.services.seed_data import BLUEPRINTS, COMPANIES, FAMILY_ALIASES, PLANS, QUESTIONS, ROLES
from app.services.skills_catalog import SKILLS


def seed_all(db: Session) -> None:
    if db.scalar(select(Question.id).limit(1)) is None:
        for cat, topic, fam, diff, text, points in QUESTIONS:
            db.add(Question(category=cat, topic=topic, role_family=fam, difficulty=diff, text=text, ideal_points=points))
    for code_plan in PLANS:
        if db.scalar(select(Plan).where(Plan.code == code_plan["code"])) is None:
            db.add(Plan(**code_plan))
    for slug, name, family in ROLES:
        if db.scalar(select(RoleCatalog).where(RoleCatalog.slug == slug)) is None:
            fam = family if family in BLUEPRINTS else FAMILY_ALIASES.get(family, "generic")
            db.add(RoleCatalog(slug=slug, name=name, family=family, blueprint=BLUEPRINTS[fam]))
    for name, country, site, industry in COMPANIES:
        if db.scalar(select(Company).where(Company.name == name)) is None:
            db.add(Company(name=name, country=country, website=site, industry=industry))
    for canon, (domain, aliases) in SKILLS.items():
        slug = canon.lower().replace(" ", "-").replace("/", "-").replace(".", "")
        if db.scalar(select(Skill).where(Skill.slug == slug)) is None:
            db.add(Skill(slug=slug, name=canon, category=domain, aliases=aliases))
    db.commit()
    seed_prompts(db)
