from setuptools import find_packages, setup

setup(
    name="dca-auditor",
    version="0.1.0",
    packages=find_packages(include=["auditor", "auditor.*"]),
)
