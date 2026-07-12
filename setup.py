"""Setup for testgen-agent."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="testgen-agent",
    version="0.2.0",
    description="Automated JUnit 4 test generation for any Java project, powered by LLMs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/testgen-agent",
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
    packages=find_packages(),
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
