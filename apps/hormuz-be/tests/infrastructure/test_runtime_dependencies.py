def test_backend_runtime_dependencies_are_importable() -> None:
    from agents import Agent
    from git import Repo
    from github import Github

    assert Agent is not None
    assert Repo is not None
    assert Github is not None
