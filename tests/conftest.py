"""Shared fixtures. All datasets are SYNTHETIC, built by claims_agent.seeds."""
import pytest

from claims_agent import seeds


@pytest.fixture(scope="session")
def case_dir(tmp_path_factory):
    cache = {}

    def get(name):
        if name not in cache:
            path = tmp_path_factory.mktemp(name)
            seeds.build_case(name, path)
            cache[name] = path
        return cache[name]

    return get
