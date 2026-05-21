from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, StructuredInputDefinition
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[1]
AGENT_HOST_SRC = ROOT / "src" / "agent_host"
if str(AGENT_HOST_SRC) not in sys.path:
    sys.path.insert(0, str(AGENT_HOST_SRC))

from app.schemas import ExecutionResult, IntentResult, SqlPlan

PROMPTS_DIR = ROOT / "src" / "agent_host" / "prompts"
PROJECT_ENDPOINT_ENV = "FOUNDRY_PROJECT_ENDPOINT"


@dataclass(frozen=True)
class AgentSpec:
    name: str
    prompt_file: str


AGENT_SPECS = (
    AgentSpec(name="wfm-intent-classifier", prompt_file="intent-classifier.yaml"),
    AgentSpec(name="wfm-sql-builder", prompt_file="sql-builder.yaml"),
    AgentSpec(name="wfm-query-executor", prompt_file="query-executor.yaml"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or delete the WFM Foundry agents used by the local MAF workflow."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the three WFM agents instead of creating a new version.",
    )
    return parser.parse_args()


def load_prompt_definition(prompt_file: str) -> dict[str, Any]:
    prompt_path = PROMPTS_DIR / prompt_file
    if not prompt_path.is_file():
        raise FileNotFoundError("Prompt file not found: " + str(prompt_path))
    with prompt_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("Prompt file is not a YAML mapping: " + str(prompt_path))
    system_prompt = str(payload.get("system_prompt") or "").strip()
    if not system_prompt:
        raise ValueError("Prompt file is missing system_prompt: " + str(prompt_path))
    model_deployment = str(payload.get("model_deployment") or "gpt-5.2").strip()
    return {
        "system_prompt": system_prompt,
        "model_deployment": model_deployment,
        "path": prompt_path,
    }


def build_project_client() -> AIProjectClient:
    endpoint = os.environ.get(PROJECT_ENDPOINT_ENV, "").strip()
    if not endpoint:
        raise SystemExit(PROJECT_ENDPOINT_ENV + " must be set.")
    return AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())


def build_structured_inputs(agent_name: str) -> dict[str, StructuredInputDefinition] | None:
    if agent_name == "wfm-sql-builder":
        return {
            "intentResult": StructuredInputDefinition(
                description="Intent classification result with candidate_tables and language_hint.",
                required=True,
                schema=IntentResult.json_schema(),
            ),
            "tableSchemas": StructuredInputDefinition(
                description="Column and join metadata for the shortlisted candidate tables.",
                required=True,
                schema={"type": "object", "additionalProperties": True},
            ),
            "buId": StructuredInputDefinition(
                description="Business unit identifier that must be applied as a mandatory filter.",
                required=True,
                schema={"type": "string"},
            ),
            "userQuestion": StructuredInputDefinition(
                description="Original user question in the user's own language.",
                required=True,
                schema={"type": "string"},
            ),
        }
    if agent_name == "wfm-query-executor":
        return {
            "sqlPlan": StructuredInputDefinition(
                description="Approved SQL plan with statement, tables_used, assumptions, and explanation.",
                required=True,
                schema=SqlPlan.json_schema(),
            ),
            "executionResult": StructuredInputDefinition(
                description="Verified query execution payload including rows, row_count, and execution_ms.",
                required=True,
                schema=ExecutionResult.json_schema(),
            ),
            "userLanguage": StructuredInputDefinition(
                description="BCP-47 language code to use for the final answer.",
                required=True,
                schema={"type": "string"},
            ),
        }
    return None


def create_agents(project: AIProjectClient) -> None:
    for spec in AGENT_SPECS:
        prompt_definition = load_prompt_definition(spec.prompt_file)
        definition_kwargs: dict[str, Any] = {
            "model": prompt_definition["model_deployment"],
            "instructions": prompt_definition["system_prompt"],
        }
        structured_inputs = build_structured_inputs(spec.name)
        if structured_inputs:
            definition_kwargs["structured_inputs"] = structured_inputs
        agent = project.agents.create_version(
            agent_name=spec.name,
            definition=PromptAgentDefinition(**definition_kwargs),
        )
        version = (
            getattr(agent, "version", None)
            or getattr(agent, "id", None)
            or getattr(agent, "name", None)
            or "unknown"
        )
        print(
            "Created {0} from {1} using model {2} (version={3})".format(
                spec.name,
                prompt_definition["path"].name,
                prompt_definition["model_deployment"],
                version,
            )
        )


def delete_agents(project: AIProjectClient) -> None:
    for spec in AGENT_SPECS:
        deleted = _delete_agent(project.agents, spec.name)
        if deleted:
            print("Deleted " + spec.name)
        else:
            print("Skipped {0} (not found or delete API unavailable)".format(spec.name))


def _delete_agent(agents_client: Any, agent_name: str) -> bool:
    delete_attempts = (
        ("delete_agent", (), {"agent_name": agent_name}),
        ("delete_agent", (), {"name": agent_name}),
        ("delete_agent", (agent_name,), {}),
        ("delete", (), {"agent_name": agent_name}),
        ("delete", (), {"name": agent_name}),
        ("delete", (agent_name,), {}),
    )
    for method_name, args, kwargs in delete_attempts:
        method = getattr(agents_client, method_name, None)
        if not callable(method):
            continue
        try:
            method(*args, **kwargs)
            return True
        except TypeError:
            continue
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "404" in message:
                return False
            raise
    return False


def main() -> None:
    args = parse_args()
    project = build_project_client()
    if args.delete:
        delete_agents(project)
        return
    create_agents(project)


if __name__ == "__main__":
    main()
