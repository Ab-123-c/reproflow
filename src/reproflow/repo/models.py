from pydantic import BaseModel, Field


class RepositoryProfile(BaseModel):
    root: str
    language: str
    python_version: str | None = None
    package_manager: str | None = None
    test_framework: str | None = None
    install_command: str | None = None
    test_command: str | None = None
    important_files: list[str] = Field(default_factory=list)
