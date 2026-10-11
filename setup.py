"""Setup for testgen-agent."""

from setuptools import find_packages, setup

# The tool's modules sit flat at the repo root and import each other flat
# (`from config import AgentConfig`), so they are declared as top-level modules
# rather than moved into a package directory. `find_packages()` cannot see them
# — it looks for directories containing an `__init__.py` — which is why every
# one is listed here by hand. **A new module at the repo root must be added to
# this list**, or the installed package will be missing it and only the checkout
# will work.
MODULES = [
    "agent",
    "checkpoint",
    "collaborator_resolver",
    "compiler",
    "config",
    "coverage_analyzer",
    "java_analyzer",
    "llm_client",
    "main",
    "method_extractor",
    "mock_deps",
    "prompt_manager",
    "quality_analyzer",
    "repair_loop",
    "report_generator",
    "runlog",
    "skill_entry",
    "target_generator",
    "target_profile",
    "test_writer",
]

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="testgen-agent",
    version="0.2.0",
    description="Automated JUnit 4/5 test generation for any Java project, powered by LLMs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/u7465990/testgen-agent",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Code Generators",
    ],
    py_modules=MODULES,
    packages=find_packages(),
    # `prompts/` carries an __init__.py purely so its `.txt` templates can be
    # declared as package data and ride along in the wheel: agent.py resolves
    # them with `Path(__file__).parent / "prompts"`, so they have to land next
    # to the installed modules. Without this the tool installs, starts, and then
    # finds no prompt templates.
    package_data={"prompts": ["*.txt"]},
    include_package_data=True,
    install_requires=[
        "javalang>=0.13.0",
        "openai>=1.0.0",
        "anthropic>=0.49.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "testgen-agent=main:main",
        ],
    },
    python_requires=">=3.10",
)
