"""System definitions B, C, D (and ablation variants) as pipeline configurations.

B  llm_only          the LLM sees only the code (no retrieval, no validator)
C  rag_no_validator  AST + hybrid retrieval + LLM, every claim reported
D  full_system       AST + hybrid retrieval + LLM + citation validator
C and D share LLM outputs for the same seed (D only adds the deterministic validator).
"""

from __future__ import annotations

from codemigrate.pipeline import SystemConfig


def llm_only(provider: str, seed: int, temperature: float) -> SystemConfig:
    return SystemConfig(name=f"B-llm-only[{provider}]", use_retrieval=False,
                        use_validator=False, provider=provider, seed=seed,
                        temperature=temperature, make_patches=False)


def rag_no_validator(provider: str, seed: int, temperature: float, retriever: str = "hybrid",
                     top_k: int = 5) -> SystemConfig:
    return SystemConfig(name=f"C-rag-no-validator[{provider}]", retriever=retriever,
                        top_k=top_k, use_validator=False, provider=provider, seed=seed,
                        temperature=temperature, make_patches=False)


def full_system(provider: str, seed: int, temperature: float, retriever: str = "hybrid",
                top_k: int = 5) -> SystemConfig:
    return SystemConfig(name=f"D-full[{provider}]", retriever=retriever, top_k=top_k,
                        use_validator=True, provider=provider, seed=seed,
                        temperature=temperature, make_patches=True)
