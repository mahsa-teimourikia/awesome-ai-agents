from pathlib import Path


ROOT = Path(__file__).parent.parent
CURRICULUM = ROOT / "curriculum"
TRACKS = ("beginner", "intermediate", "advanced")


def course_directories() -> list[Path]:
    return [
        course
        for track in TRACKS
        for course in sorted((CURRICULUM / track).iterdir())
        if course.is_dir()
    ]


def test_curriculum_tracks_exist():
    assert CURRICULUM.exists()
    assert all((CURRICULUM / track).is_dir() for track in TRACKS)


def test_every_course_has_one_readme_and_one_canonical_notebook():
    courses = course_directories()

    assert len(courses) == 47
    for course in courses:
        assert (course / "README.md").is_file(), f"{course} is missing README.md"
        notebooks = list(course.glob("*.ipynb"))
        assert len(notebooks) == 1, (
            f"{course} must contain exactly one canonical notebook; found {len(notebooks)}"
        )
