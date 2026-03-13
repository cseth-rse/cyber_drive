#!/usr/bin/env python
# seed.py – populate levels and sample courses
from app.database import SessionLocal
from app.models import Level, Course

LEVELS = [
    {"name": "100L", "order": 1},
    {"name": "200L", "order": 2},
    {"name": "300L", "order": 3},
    {"name": "400L", "order": 4},
    {"name": "500L", "order": 5},
]

COURSES_BY_LEVEL = {
    "100L": [
        ("CSC101", "Introduction to Computing", "Fundamentals of computer science and programming."),
        ("MTH101", "Calculus I", "Limits, derivatives, and integrals."),
        ("PHY101", "General Physics I", "Mechanics, waves, and thermodynamics."),
        ("ENG101", "Communication Skills", "Technical writing and oral communication."),
    ],
    "200L": [
        ("CSC201", "Data Structures", "Arrays, linked lists, stacks, queues, trees, and graphs."),
        ("CSC203", "Discrete Mathematics", "Logic, sets, relations, and graph theory."),
        ("CSC205", "Computer Architecture", "Instruction sets, memory hierarchy, and pipelining."),
        ("MTH201", "Calculus II", "Multivariable calculus and differential equations."),
    ],
    "300L": [
        ("CSC301", "Algorithms", "Algorithm design, analysis, and complexity."),
        ("CSC303", "Operating Systems", "Process management, memory, and file systems."),
        ("CSC305", "Database Systems", "Relational models, SQL, and transactions."),
        ("CSC307", "Computer Networks", "Protocols, TCP/IP, and network security."),
    ],
    "400L": [
        ("CSC401", "Software Engineering", "SDLC, design patterns, and project management."),
        ("CSC403", "Artificial Intelligence", "Search, knowledge representation, and ML basics."),
        ("CSC405", "Compiler Construction", "Lexing, parsing, and code generation."),
        ("CSC407", "Embedded Systems", "Microcontrollers, real-time OS, and hardware interfacing."),
    ],
    "500L": [
        ("CSC501", "Advanced Machine Learning", "Deep learning, neural networks, and model deployment."),
        ("CSC503", "Distributed Systems", "Consensus, replication, and cloud computing."),
        ("CSC505", "Information Security", "Cryptography, penetration testing, and secure design."),
        ("CSC507", "Research Methods", "Academic writing, ethics, and research design."),
    ],
}


def main():
    db = SessionLocal()
    try:
        print("🌱 Seeding database...")

        for level_data in LEVELS:
            level = db.query(Level).filter(Level.name == level_data["name"]).first()
            if not level:
                level = Level(**level_data)
                db.add(level)
                db.commit()
                db.refresh(level)
            print(f"  ✔ Level: {level.name}")

            for code, title, description in COURSES_BY_LEVEL[level.name]:
                course = db.query(Course).filter(
                    Course.code == code, Course.level_id == level.id
                ).first()
                if not course:
                    course = Course(code=code, title=title, description=description, level_id=level.id)
                    db.add(course)
                    db.commit()
                print(f"      ✔ {code} – {title}")

        print("\n✅ Seeding complete.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
