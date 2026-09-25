"""Executable dependency rules for the modular monolith."""

import ast
import os
from pathlib import Path
import subprocess
import sys
from importlib.util import resolve_name

ROOT = Path(__file__).resolve().parents[1] / "src"
PACKAGE = ROOT / "silent_orchestra"


def imports(path):
    package = ".".join(path.relative_to(ROOT).with_suffix("").parts[:-1])
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = (
                resolve_name("." * node.level + (node.module or ""), package)
                if node.level
                else node.module
            )
            for item in node.names:
                target = f"{module}.{item.name}"
                target_path = ROOT.joinpath(*target.split("."))
                yield target if target_path.is_dir() or target_path.with_suffix(".py").is_file() else module



def test_inner_layers_do_not_depend_on_frameworks_or_adapters():
    forbidden = {
        "sqlalchemy",
        "fastapi",
        "pydantic",
        "pydantic_settings",
        "ctypes",
        "subprocess",
        "platform",
    }
    for path in [
        *(PACKAGE / "modules").rglob("*.py"),
        *(PACKAGE / "shared").rglob("*.py"),
    ]:
        if "adapters" in path.parts:
            continue
        for dependency in imports(path):
            assert dependency.split(".")[0] not in forbidden, (path, dependency)
            if dependency.startswith("silent_orchestra."):
                assert dependency.split(".")[1] in {"modules", "shared"}, (
                    path,
                    dependency,
                )
                assert ".adapters" not in dependency, (path, dependency)
                if "domain" in path.parts:
                    assert ".application" not in dependency and not dependency.endswith(
                        (".api", ".ports")
                    ), (path, dependency)


def test_modules_only_use_other_modules_public_api():
    for path in (PACKAGE / "modules").rglob("*.py"):
        owner = path.relative_to(PACKAGE / "modules").parts[0]
        for dependency in imports(path):
            parts = dependency.split(".")
            if (
                parts[:2] == ["silent_orchestra", "modules"]
                and len(parts) > 2
                and parts[2] != owner
            ):
                assert parts[3:] == ["api"], (path, dependency)


def test_http_adapters_do_not_issue_sql():
    for path in (PACKAGE / "routers").glob("*.py"):
        assert not any(item.startswith("sqlalchemy") for item in imports(path)), path


def test_application_runs_without_site_packages_or_database():
    # A fresh interpreter prevents conftest's ORM mapping from hiding dependencies.
    program = """
from silent_orchestra.modules.agent.api import observe, contracts
from silent_orchestra.modules.agent.application.dependencies import AgentDependencies
from silent_orchestra.modules.agent.domain.entities import GestureObservation, GesturePattern
from silent_orchestra.modules.agent.application.intent_reasoner import infer_intent
from silent_orchestra.modules.agent.application.feedback_service import record_feedback
from silent_orchestra.modules.identity.api import User
from silent_orchestra.shared.policy import AgentPolicy

class MemoryPorts:
    policy = AgentPolicy()
    active_window = staticmethod(lambda: 'PowerPoint')
    def __init__(self):
        self.saved = []
        self.commits = 0
        self.executed = []
        self.patterns = []
    def get(self, entity, key):
        return next((item for item in self.saved if isinstance(item, entity) and item.id == key), None)
    def add(self, entity):
        self.saved.append(entity)
    def add_all(self, entities):
        self.saved.extend(entities)
    def commit(self):
        self.commits += 1
    def accidental_embeddings(self, context, observation):
        return []
    def executable_memories(self, context, observation):
        return self.patterns
    def execute_action(self, intent, target, magnitude):
        self.executed.append((intent, target, magnitude))
        return 'DRY_RUN', 'SIMULATED', None
    def execution_feedback(self, execution):
        return None

ports = MemoryPorts()
ports.add(User(id='u', name='User'))
dependencies = AgentDependencies(repository=ports, policy=ports.policy,
    execute_action=ports.execute_action, active_window=ports.active_window,
    require_user=lambda user_id: ports.get(User, user_id))
result = observe(contracts.ObserveRequest(user_id='u', context=contracts.ContextInput(),
    gesture=contracts.GestureInput(motion_type='swipe', direction='right')), dependencies)
assert not result['inference'].matched
assert not ports.executed
observation = result['observation']
pattern = GesturePattern(id='p', user_id='u', gesture_key=observation.gesture_key,
    gesture_embedding=observation.gesture_embedding, motion_type='swipe', direction='right',
    intent='NEXT_SLIDE', context_scope='presentation', target='powerpoint', confidence=.9,
    status='ACTIVE', auto_execute=True)
ports.patterns.append(pattern)
ports.add(pattern)
inference = infer_intent(dependencies, observation, result['context'])
assert inference.matched and inference.execution.status == 'SIMULATED'
assert ports.executed == [('NEXT_SLIDE', 'powerpoint', 1)]
feedback, updated = record_feedback(dependencies, inference.execution, 'u', 'WRONG_ACTION', None)
assert updated.confidence == .75
assert ports.commits == 3
"""
    subprocess.run(
        [sys.executable, "-S", "-c", program],
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=True,
        capture_output=True,
        text=True,
    )


def test_http_uses_public_module_api():
    for path in (PACKAGE / "routers").glob("*.py"):
        for dependency in imports(path):
            if dependency.startswith("silent_orchestra.modules."):
                assert dependency.endswith(".api"), (path, dependency)


def test_agent_does_not_import_identity_entities():
    for path in (PACKAGE / "modules" / "agent").rglob("*.py"):
        assert not any(
            dependency.startswith("silent_orchestra.modules.identity")
            for dependency in imports(path)
        ), path


def test_persistence_does_not_own_execution_or_policy():
    path = PACKAGE / "modules" / "agent" / "adapters" / "repository.py"
    for dependency in imports(path):
        assert not dependency.endswith(("action_executor", "policy", "config")), dependency
    assert "execute_action" not in path.read_text()
