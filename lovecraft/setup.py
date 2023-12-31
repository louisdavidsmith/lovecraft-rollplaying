from setuptools import find_packages, setup

req = [
    "mistralai",
    "langchain",
    "pydantic",
    "setfit",
    "sentence_transformers",
    "scikit-learn==1.2.2",
    "structlog",
    "sqlite-vss",
    "sqlite-utils",
]

setup(
    name="lovecraft",
    version="0.1.0",
    description="A example Python package",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=req,
)
