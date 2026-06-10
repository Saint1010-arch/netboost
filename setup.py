from setuptools import setup, find_packages

setup(
    name="netboost",
    version="1.0.0",
    description="One-click network diagnosis and optimization",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="NetBoost",
    url="https://github.com/yourname/netboost",
    packages=find_packages(),
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "netboost=netboost.__main__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Networking",
    ],
)
